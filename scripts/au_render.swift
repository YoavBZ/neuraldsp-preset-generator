// Render audio through the plugin offline, so what a control does to the sound
// can be measured instead of inferred from its name.
//
//   swiftc -swift-version 5 -O scripts/au_render.swift -o /tmp/au_render
//   /tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rTrebleBoost false off.wav 0.005
//   /tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rTrebleBoost true  on.wav  0.005
//   python3 scripts/spectrum_diff.py off.wav on.wav
//
// The last argument is the input amplitude. Run any comparison at two levels
// far apart: a difference that survives both is a filter, one that only shows
// up when loud is the amp saturating.
//
// The excitation is seeded white noise, so both states of a switch see
// byte-identical input and any difference in the output is the switch alone.
//
// Offline manual rendering: nothing reaches an output device, and the edited
// state goes to an instance that dies with the process.
// See docs/measuring-against-the-plugin.md.

import AVFoundation
import AudioToolbox
import Foundation

func fourCC(_ s: String) -> OSType {
    var r: OSType = 0
    for b in s.utf8.prefix(4) { r = (r << 8) | OSType(b) }
    return r
}

let args = CommandLine.arguments
guard args.count >= 7 else {
    FileHandle.standardError.write("usage: render <type> <sub> <manu> <element/key> <value> <out.wav>\n".data(using: .utf8)!)
    exit(2)
}
let desc = AudioComponentDescription(
    componentType: fourCC(args[1]), componentSubType: fourCC(args[2]),
    componentManufacturer: fourCC(args[3]), componentFlags: 0, componentFlagsMask: 0)

let sem = DispatchSemaphore(value: 0)
var unit: AUAudioUnit!
AUAudioUnit.instantiate(with: desc, options: []) { au, e in
    unit = au
    if let e { FileHandle.standardError.write("instantiate: \(e)\n".data(using: .utf8)!); exit(1) }
    sem.signal()
}
sem.wait()

// --- set the one parameter under test, via the preset document -------------
guard let baseState = unit.fullState, let blob = baseState["jucePluginState"] as? Data else { exit(1) }
let bytes = [UInt8](blob)
guard let xmlStart = bytes.firstRange(of: Array("<?xml".utf8))?.lowerBound else { exit(1) }
let header = Array(bytes[0..<xmlStart])
var docEnd = bytes.count
while docEnd > xmlStart, bytes[docEnd - 1] == 0 { docEnd -= 1 }
let trailer = Array(bytes[docEnd...])
let doc = String(decoding: bytes[xmlStart..<docEnd], as: UTF8.self)

let spec = args[4].split(separator: "/", maxSplits: 1).map(String.init)
guard spec.count == 2 else {
    FileHandle.standardError.write("expected <element>/<key>, got \(args[4])\n".data(using: .utf8)!)
    exit(2)
}
let ns = doc as NSString
let elemRE = try! NSRegularExpression(pattern: "<\(spec[0])\\b[^>]*>")
guard let em = elemRE.firstMatch(in: doc, range: NSRange(location: 0, length: ns.length)) else { exit(1) }
let kvRE = try! NSRegularExpression(pattern: "\\b\(spec[1])=\"([^\"]*)\"")
guard let km = kvRE.firstMatch(in: doc, range: em.range) else { exit(1) }
var newDoc = ns.replacingCharacters(in: km.range(at: 1), with: args[5])

// Make the amp that owns the parameter the live one, or the switch under test
// is out of circuit and the render is identical either way.
let ampIndex: String
if spec[0].hasPrefix("ac20") { ampIndex = "0" }
else if spec[0].hasPrefix("pr12") { ampIndex = "1" }
else { ampIndex = "2" }
let ampRE = try! NSRegularExpression(pattern: "selectedAmp=\"[^\"]*\"")
let before = newDoc
newDoc = ampRE.stringByReplacingMatches(
    in: newDoc, range: NSRange(location: 0, length: (newDoc as NSString).length),
    withTemplate: "selectedAmp=\"\(ampIndex)\"")
if newDoc == before {
    FileHandle.standardError.write(
        "warning: could not select amp \(ampIndex); the control under test may be out of circuit\n"
            .data(using: .utf8)!)
}
// The gate would squash a quiet test signal and hide the difference.
newDoc = newDoc.replacingOccurrences(of: "gateActive=\"true\"", with: "gateActive=\"false\"")

var st = baseState
var framedHeader = header
let n = UInt32(Array(newDoc.utf8).count)
if framedHeader.count >= 8 {
    framedHeader[4] = UInt8(n & 0xff); framedHeader[5] = UInt8((n >> 8) & 0xff)
    framedHeader[6] = UInt8((n >> 16) & 0xff); framedHeader[7] = UInt8((n >> 24) & 0xff)
}
st["jucePluginState"] = Data(framedHeader) + Data(newDoc.utf8) + Data(trailer)
unit.fullState = st
usleep(200000)

// --- offline render --------------------------------------------------------
let sampleRate = 48000.0
let format = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 2)!
try! unit.inputBusses[0].setFormat(format)
try! unit.outputBusses[0].setFormat(format)
unit.inputBusses[0].isEnabled = true
unit.outputBusses[0].isEnabled = true
FileHandle.standardError.write("buses in=\(unit.inputBusses.count) out=\(unit.outputBusses.count) inEnabled=\(unit.inputBusses[0].isEnabled)\n".data(using: .utf8)!)
unit.maximumFramesToRender = 512
try! unit.allocateRenderResources()

let total = Int(sampleRate * 2.0)
let frames: AUAudioFrameCount = 512

// White noise: flat excitation, so the output spectrum is the plugin's
// response. Seeded, so both states of a switch see byte-identical input and
// any difference in the output is the switch and nothing else.
var seed: UInt64 = 0x5eed_1234_abcd_0001
func nextFloat() -> Float {
    seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17
    return Float(Double(seed >> 11) / Double(1 << 53)) * 2.0 - 1.0
}
var noise = [Float](repeating: 0, count: total)
let amp = args.count > 7 ? (Float(args[7]) ?? 0.25) : 0.25
// An 8th argument switches the excitation to a sine, e.g. "sine:220". Noise
// measures what a control does to the spectrum; a sine measures how much
// distortion the amp is making, which is what "break-up" actually means.
let source = args.count > 8 ? args[8] : "noise"
if source.hasPrefix("sine:") {
    let freq = Double(source.dropFirst(5)) ?? 220.0
    for i in 0..<total {
        noise[i] = Float(sin(2.0 * Double.pi * freq * Double(i) / sampleRate)) * amp
    }
} else {
    for i in 0..<total { noise[i] = nextFloat() * amp }
}

var cursor = 0
var pulls = 0
let inputBlock: AURenderPullInputBlock = { _, _, frameCount, _, audioBufferList in
    pulls += 1
    let abl = UnsafeMutableAudioBufferListPointer(audioBufferList)
    for buffer in abl {
        let ptr = buffer.mData!.assumingMemoryBound(to: Float.self)
        for f in 0..<Int(frameCount) {
            ptr[f] = (cursor + f) < total ? noise[cursor + f] : 0
        }
    }
    cursor += Int(frameCount)
    return noErr
}

let outBuffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames)!
let outURL = URL(fileURLWithPath: args[6])
var file: AVAudioFile? = try! AVAudioFile(forWriting: outURL, settings: format.settings,
                                          commonFormat: .pcmFormatFloat32, interleaved: false)

var flags = AudioUnitRenderActionFlags()
var timestamp = AudioTimeStamp()
timestamp.mFlags = .sampleTimeValid
var rendered = 0
while rendered < total {
    flags = AudioUnitRenderActionFlags()
    outBuffer.frameLength = frames
    let status = unit.renderBlock(&flags, &timestamp, frames, 0,
                                  outBuffer.mutableAudioBufferList, inputBlock)
    if status != noErr {
        FileHandle.standardError.write("render failed: \(status)\n".data(using: .utf8)!)
        exit(1)
    }
    timestamp.mSampleTime += Double(frames)
    try! file!.write(from: outBuffer)
    rendered += Int(frames)
}
// Release it explicitly: this is what patches the RIFF and `data` chunk sizes.
// Without it the samples are on disk but every reader sees a 0-length file.
file = nil
FileHandle.standardError.write("wrote \(args[6]) (input pulled \(pulls) times)\n".data(using: .utf8)!)
