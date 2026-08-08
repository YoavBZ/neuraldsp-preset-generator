// Render audio through the plugin offline, so what a control does to the sound
// can be measured instead of inferred from its name.
//
//   swiftc -swift-version 5 -O scripts/au_render.swift -o /tmp/au_render
//   /tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rTrebleBoost false off.wav 0.005
//   /tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rTrebleBoost true  on.wav  0.005
//   /tmp/au_render aumf TKI2 NDSP --state prepared.bin out.wav 0.005
//   python3 scripts/spectrum_diff.py off.wav on.wav
//
// The last argument is the input amplitude. Run any comparison at two levels
// far apart: a difference that survives both is a filter, one that only shows
// up when loud is the amp saturating.
//
// The excitation is seeded white noise, so both states of a switch see
// byte-identical input and any difference in the output is the switch alone.
//
// Three options change how a render is made rather than what is rendered, and
// all three default to the behavior every published measurement used:
//
//   --timings         write per-phase wall time as JSON to stderr
//   --input di.wav    render a recorded signal instead of noise or a sine
//   --settle <ms>     wait <ms> after writing state instead of the default 200
//   --output-gain <dB> set Morgan's output trim before rendering
//
//   /tmp/au_render aumf NMAS NDSP --state prepared.bin out.wav 1.0 \
//     --input di.wav --timings --settle 50
//
// --input takes a 48 kHz file, mono or stereo, and the amplitude argument
// becomes a linear gain on it. Measuring a control still wants noise or a sine:
// a recording only excites the frequencies it happens to contain.
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

// --- phase timing -----------------------------------------------------------
// One question: how much of a render is the plugin processing audio, and how
// much is this process getting to the point where it can. The marks are taken on
// every run -- reading a clock costs nothing against an instantiate -- and only
// the report at the end is gated on --timings.
final class Phases {
    private let started = DispatchTime.now()
    private var previous = DispatchTime.now()
    private var marks: [(String, Double)] = []

    /// Record the time since the previous mark under `name`.
    func mark(_ name: String) {
        let now = DispatchTime.now()
        marks.append((name, Self.ms(previous, now)))
        previous = now
    }

    /// Record a duration measured separately, e.g. a total accumulated inside a loop.
    func add(_ name: String, _ milliseconds: Double) {
        marks.append((name, milliseconds))
    }

    static func ms(_ from: DispatchTime, _ to: DispatchTime) -> Double {
        Double(to.uptimeNanoseconds &- from.uptimeNanoseconds) / 1e6
    }

    /// The process cannot see its own spawn and runtime start: a caller gets
    /// those by subtracting this total from the wall time it measured itself.
    func json() -> String {
        let all = marks + [("total_in_process", Self.ms(started, DispatchTime.now()))]
        let body = all.map { "\"\($0.0)_ms\":\(String(format: "%.3f", $0.1))" }.joined(separator: ",")
        return "{" + body + "}"
    }
}
let phases = Phases()

// --- arguments --------------------------------------------------------------
// Options are stripped before the positional arguments are read, so every
// invocation in docs/measuring-against-the-plugin.md keeps its exact meaning.
var args: [String] = []
var reportTimings = false
var inputFile: String? = nil
var settleMicroseconds: UInt32 = 200000
var outputGainDB: String? = nil
var argIndex = 0
let rawArgs = CommandLine.arguments
while argIndex < rawArgs.count {
    let arg = rawArgs[argIndex]
    // --state is positional: it marks how args[5] is read, not how it renders.
    switch arg {
    case "--timings":
        reportTimings = true
        argIndex += 1
    case "--input", "--settle", "--output-gain":
        guard argIndex + 1 < rawArgs.count else {
            FileHandle.standardError.write("\(arg) needs a value\n".data(using: .utf8)!)
            exit(2)
        }
        if arg == "--input" {
            inputFile = rawArgs[argIndex + 1]
        } else if arg == "--settle" {
            guard let ms = Double(rawArgs[argIndex + 1]), ms >= 0 else {
                FileHandle.standardError.write("--settle needs a non-negative number of milliseconds\n".data(using: .utf8)!)
                exit(2)
            }
            settleMicroseconds = UInt32(ms * 1000.0)
        } else {
            guard Double(rawArgs[argIndex + 1]) != nil else {
                FileHandle.standardError.write("--output-gain needs a number in dB\n".data(using: .utf8)!)
                exit(2)
            }
            outputGainDB = rawArgs[argIndex + 1]
        }
        argIndex += 2
    default:
        args.append(arg)
        argIndex += 1
    }
}
guard args.count >= 7 else {
    FileHandle.standardError.write(("usage: render <type> <sub> <manu> <element/key> <value> <out.wav>"
        + " [amplitude] [excitation] [--input di.wav] [--settle ms] [--timings]\n").data(using: .utf8)!)
    exit(2)
}
// 0.25 is a level chosen for the generated excitations. A recording arrives at
// whatever level it was played at, so leave it alone unless asked.
let defaultAmplitude: Float = inputFile == nil ? 0.25 : 1.0
let desc = AudioComponentDescription(
    componentType: fourCC(args[1]), componentSubType: fourCC(args[2]),
    componentManufacturer: fourCC(args[3]), componentFlags: 0, componentFlagsMask: 0)
phases.mark("startup")

let sem = DispatchSemaphore(value: 0)
var unit: AUAudioUnit!
AUAudioUnit.instantiate(with: desc, options: []) { au, e in
    unit = au
    if let e { FileHandle.standardError.write("instantiate: \(e)\n".data(using: .utf8)!); exit(1) }
    sem.signal()
}
sem.wait()
phases.mark("instantiate")

// --- load a prepared record state, or edit one XML-state parameter ----------
guard let baseState = unit.fullState, let blob = baseState["jucePluginState"] as? Data else { exit(1) }
var st = baseState
let outPath: String
let inputAmplitude: Float
let excitation: String

if args[4] == "--state" {
    if outputGainDB != nil {
        FileHandle.standardError.write(
            "--output-gain currently supports XML-state plugins only\n".data(using: .utf8)!)
        exit(2)
    }
    st["jucePluginState"] = try! Data(contentsOf: URL(fileURLWithPath: args[5]))
    outPath = args[6]
    inputAmplitude = args.count > 7 ? (Float(args[7]) ?? 0.25) : defaultAmplitude
    excitation = args.count > 8 ? args[8] : "noise"
} else {
    let bytes = [UInt8](blob)
    guard let xmlStart = bytes.firstRange(of: Array("<?xml".utf8))?.lowerBound else {
        FileHandle.standardError.write(
            "state is not XML; pass --state <prepared-state.bin> instead\n".data(using: .utf8)!)
        exit(2)
    }
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

    // Make the amp that owns the parameter the live one, or the switch under
    // test is out of circuit and the render is identical either way.
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
    newDoc = newDoc.replacingOccurrences(
        of: "gateActive=\"true\"", with: "gateActive=\"false\"")

    // Drive calibration has to vary the preamp input while keeping the written
    // float file below full scale. Morgan's outputGain is a linear post-amp trim;
    // writing it here preserves the volume/input interaction under test and keeps
    // a downstream over-level output from being mistaken for preamp distortion.
    if let gain = outputGainDB {
        let current = newDoc as NSString
        let parametersRE = try! NSRegularExpression(pattern: "<parameters\\b[^>]*>")
        guard let parameters = parametersRE.firstMatch(
            in: newDoc, range: NSRange(location: 0, length: current.length))
        else {
            FileHandle.standardError.write(
                "could not find Morgan's parameters element for --output-gain\n".data(using: .utf8)!)
            exit(2)
        }
        let element = current.substring(with: parameters.range) as NSString
        let gainRE = try! NSRegularExpression(pattern: "\\boutputGain=\"([^\"]*)\"")
        guard let match = gainRE.firstMatch(
            in: element as String,
            range: NSRange(location: 0, length: element.length))
        else {
            FileHandle.standardError.write(
                "could not find parameters/outputGain for --output-gain\n".data(using: .utf8)!)
            exit(2)
        }
        let valueRange = NSRange(
            location: parameters.range.location + match.range(at: 1).location,
            length: match.range(at: 1).length)
        newDoc = current.replacingCharacters(in: valueRange, with: gain)
    }

    var framedHeader = header
    let n = UInt32(Array(newDoc.utf8).count)
    if framedHeader.count >= 8 {
        framedHeader[4] = UInt8(n & 0xff); framedHeader[5] = UInt8((n >> 8) & 0xff)
        framedHeader[6] = UInt8((n >> 16) & 0xff); framedHeader[7] = UInt8((n >> 24) & 0xff)
    }
    st["jucePluginState"] = Data(framedHeader) + Data(newDoc.utf8) + Data(trailer)
    outPath = args[6]
    inputAmplitude = args.count > 7 ? (Float(args[7]) ?? 0.25) : defaultAmplitude
    excitation = args.count > 8 ? args[8] : "noise"
}
phases.mark("state_build")
unit.fullState = st
phases.mark("state_apply")
// A state write reaches the plugin's audio thread asynchronously, so rendering
// immediately can capture the settings this render was meant to replace. Every
// published measurement used 200 ms; --settle exists to measure what the
// plugin actually needs rather than keep trusting the guess.
usleep(settleMicroseconds)
phases.mark("settle")

// --- offline render --------------------------------------------------------
let sampleRate = 48000.0
let format = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 2)!
try! unit.inputBusses[0].setFormat(format)
try! unit.outputBusses[0].setFormat(format)
unit.inputBusses[0].isEnabled = true
unit.outputBusses[0].isEnabled = true
unit.maximumFramesToRender = 512
try! unit.allocateRenderResources()
phases.mark("prepare")

let frames: AUAudioFrameCount = 512

// The excitation, one array per channel. Generated here by default; read from
// a file when --input names one, because matching a recorded tone needs the
// plugin to see a guitar rather than noise.
var channels: [[Float]] = []
if let inputFile {
    guard let file = try? AVAudioFile(forReading: URL(fileURLWithPath: inputFile)) else {
        FileHandle.standardError.write("could not read \(inputFile)\n".data(using: .utf8)!)
        exit(2)
    }
    let inputFormat = file.processingFormat
    guard inputFormat.sampleRate == sampleRate else {
        FileHandle.standardError.write(
            "--input must be \(Int(sampleRate)) Hz; \(inputFile) is \(Int(inputFormat.sampleRate)) Hz\n"
                .data(using: .utf8)!)
        exit(2)
    }
    guard let buffer = AVAudioPCMBuffer(pcmFormat: inputFormat,
                                        frameCapacity: AVAudioFrameCount(file.length)),
        (try? file.read(into: buffer)) != nil, let samples = buffer.floatChannelData,
        buffer.frameLength > 0
    else {
        FileHandle.standardError.write("could not decode \(inputFile)\n".data(using: .utf8)!)
        exit(2)
    }
    for channel in 0..<Int(inputFormat.channelCount) {
        var taken = [Float](repeating: 0, count: Int(buffer.frameLength))
        for f in 0..<Int(buffer.frameLength) { taken[f] = samples[channel][f] * inputAmplitude }
        channels.append(taken)
    }
} else {
    let generated = Int(sampleRate * 2.0)
    // White noise: flat excitation, so the output spectrum is the plugin's
    // response. Seeded, so both states of a switch see byte-identical input and
    // any difference in the output is the switch and nothing else.
    var seed: UInt64 = 0x5eed_1234_abcd_0001
    func nextFloat() -> Float {
        seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17
        return Float(Double(seed >> 11) / Double(1 << 53)) * 2.0 - 1.0
    }
    var noise = [Float](repeating: 0, count: generated)
    // The optional excitation switches to a sine, e.g. "sine:222.65625". Noise
    // measures what a control does to the spectrum; a sine measures how much
    // distortion the amp is making, which is what "break-up" actually means.
    if excitation.hasPrefix("sine:") {
        let freq = Double(excitation.dropFirst(5)) ?? 220.0
        for i in 0..<generated {
            noise[i] = Float(sin(2.0 * Double.pi * freq * Double(i) / sampleRate)) * inputAmplitude
        }
    } else {
        for i in 0..<generated { noise[i] = nextFloat() * inputAmplitude }
    }
    channels.append(noise)
}
let total = channels[0].count
phases.mark("excitation")

var cursor = 0
var pulls = 0
let inputBlock: AURenderPullInputBlock = { _, _, frameCount, _, audioBufferList in
    pulls += 1
    let abl = UnsafeMutableAudioBufferListPointer(audioBufferList)
    for (index, buffer) in abl.enumerated() {
        // A mono excitation feeds both channels, which is what the generated
        // noise and sine have always done.
        let source = channels[min(index, channels.count - 1)]
        let ptr = buffer.mData!.assumingMemoryBound(to: Float.self)
        for f in 0..<Int(frameCount) {
            ptr[f] = (cursor + f) < total ? source[cursor + f] : 0
        }
    }
    cursor += Int(frameCount)
    return noErr
}

let outBuffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames)!
let outURL = URL(fileURLWithPath: outPath)
var file: AVAudioFile? = try! AVAudioFile(forWriting: outURL, settings: format.settings,
                                          commonFormat: .pcmFormatFloat32, interleaved: false)

var flags = AudioUnitRenderActionFlags()
var timestamp = AudioTimeStamp()
timestamp.mFlags = .sampleTimeValid
var rendered = 0
// Split the loop into the plugin's own time and the file's, because the whole
// point of measuring is to find out which one a render is actually spending.
var renderBlockMs = 0.0
var writeMs = 0.0
while rendered < total {
    flags = AudioUnitRenderActionFlags()
    outBuffer.frameLength = frames
    let blockStart = DispatchTime.now()
    let status = unit.renderBlock(&flags, &timestamp, frames, 0,
                                  outBuffer.mutableAudioBufferList, inputBlock)
    renderBlockMs += Phases.ms(blockStart, DispatchTime.now())
    if status != noErr {
        FileHandle.standardError.write("render failed: \(status)\n".data(using: .utf8)!)
        exit(1)
    }
    timestamp.mSampleTime += Double(frames)
    let writeStart = DispatchTime.now()
    try! file!.write(from: outBuffer)
    writeMs += Phases.ms(writeStart, DispatchTime.now())
    rendered += Int(frames)
}
phases.mark("render_loop")
phases.add("render_block", renderBlockMs)
phases.add("file_write", writeMs)
// Release it explicitly: this is what patches the RIFF and `data` chunk sizes.
// Without it the samples are on disk but every reader sees a 0-length file.
file = nil
phases.mark("file_close")
FileHandle.standardError.write("wrote \(outPath) (input pulled \(pulls) times)\n".data(using: .utf8)!)
if reportTimings {
    // render_block and file_write are the two halves of render_loop, not extra
    // phases: adding every field together double-counts the loop.
    phases.add("audio", Double(total) / sampleRate * 1000.0)
    FileHandle.standardError.write((phases.json() + "\n").data(using: .utf8)!)
}
