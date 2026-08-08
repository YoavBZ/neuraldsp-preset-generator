// Render many parameter sets through one plugin instance, so a search can
// afford to ask what a preset sounds like.
//
//   swiftc -swift-version 5 -O scripts/au_render_server.swift -o /tmp/au_render_server
//   /tmp/au_render_server aumf NMAS NDSP < commands.jsonl
//
// scripts/au_render.swift renders once and exits. Measured on Morgan, that
// costs 1.25 s to instantiate and 0.18 s to write state before any audio is
// processed, against 0.31 s of actual DSP for a 2-second render — so a search
// that renders a few hundred candidates spends most of its time starting up.
// This helper instantiates once, allocates once, and then reads render
// commands, one JSON object per line on stdin:
//
//   {"out":"/tmp/a.wav","edits":[{"module":"sw50rAmp","key":"sw50rBright","value":"true"}],
//    "selectAmp":2,"gateOff":true,"amplitude":0.25}
//   {"out":"/tmp/b.wav","state":"/tmp/prepared.bin","input":"/tmp/di.wav","amplitude":1.0}
//   {"quit":true}
//
// Each reply is one JSON object on stdout, with the peak so a silent render is
// never mistaken for a measurement, and per-phase timings:
//
//   {"ok":true,"out":"/tmp/a.wav","peak":0.5546125,"frames":96000,"ms":{…}}
//
// Every command starts from the state the plugin had at startup, so a sequence
// of renders is order-independent and repeatable. `edits` writes attributes in
// the plugin's live XML state; `state` replaces the whole blob, which is what a
// record-state plugin like Tone King needs. The two are mutually exclusive.
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

func ms(_ from: DispatchTime, _ to: DispatchTime) -> Double {
    Double(to.uptimeNanoseconds &- from.uptimeNanoseconds) / 1e6
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(2)
}

/// One JSON object per line, flushed immediately: a caller drives this
/// interactively and must not wait on a buffer to fill.
func reply(_ fields: [String]) {
    FileHandle.standardOutput.write(("{" + fields.joined(separator: ",") + "}\n").data(using: .utf8)!)
}

func quoted(_ s: String) -> String {
    let escaped = s.replacingOccurrences(of: "\\", with: "\\\\")
        .replacingOccurrences(of: "\"", with: "\\\"")
    return "\"\(escaped)\""
}

// --- arguments --------------------------------------------------------------
var args: [String] = []
var defaultSettleMicroseconds: UInt32 = 0
var argIndex = 0
let rawArgs = CommandLine.arguments
while argIndex < rawArgs.count {
    if rawArgs[argIndex] == "--settle" {
        guard argIndex + 1 < rawArgs.count, let value = Double(rawArgs[argIndex + 1]), value >= 0 else {
            fail("--settle needs a non-negative number of milliseconds")
        }
        defaultSettleMicroseconds = UInt32(value * 1000.0)
        argIndex += 2
    } else {
        args.append(rawArgs[argIndex])
        argIndex += 1
    }
}
guard args.count >= 4 else {
    fail("usage: au_render_server <type> <sub> <manu> [--settle ms] < commands.jsonl")
}

let startup = DispatchTime.now()
let desc = AudioComponentDescription(
    componentType: fourCC(args[1]), componentSubType: fourCC(args[2]),
    componentManufacturer: fourCC(args[3]), componentFlags: 0, componentFlagsMask: 0)

let sem = DispatchSemaphore(value: 0)
var unit: AUAudioUnit!
AUAudioUnit.instantiate(with: desc, options: []) { au, e in
    unit = au
    if let e { fail("instantiate: \(e)") }
    sem.signal()
}
sem.wait()
let instantiateMs = ms(startup, DispatchTime.now())

// The component's own version, in the same dotted form `auval` prints. A render
// is identified by the plugin that made it — `match/renderer.py` puts this in the
// cache key rather than beside it, so a plugin update invalidates every entry
// instead of silently serving audio the installed version would not produce.
var componentVersion = "unknown"
var rawVersion: UInt32 = 0
if AudioComponentGetVersion(unit.component, &rawVersion) == noErr {
    componentVersion = "\((rawVersion >> 16) & 0xffff).\((rawVersion >> 8) & 0xff).\(rawVersion & 0xff)"
}

guard let baseState = unit.fullState, let baseBlob = baseState["jucePluginState"] as? Data else {
    fail("plugin returned no jucePluginState")
}

// The live state of an XML-state plugin is a length-framed header, an XML
// document, and a trailer. Split it once; every command re-edits the pristine
// document rather than the previous command's output, so renders do not depend
// on the order they were asked for.
let baseBytes = [UInt8](baseBlob)
var baseHeader: [UInt8] = []
var baseTrailer: [UInt8] = []
var baseDocument: String? = nil
if let xmlStart = baseBytes.firstRange(of: Array("<?xml".utf8))?.lowerBound {
    baseHeader = Array(baseBytes[0..<xmlStart])
    var documentEnd = baseBytes.count
    while documentEnd > xmlStart, baseBytes[documentEnd - 1] == 0 { documentEnd -= 1 }
    baseTrailer = Array(baseBytes[documentEnd...])
    baseDocument = String(decoding: baseBytes[xmlStart..<documentEnd], as: UTF8.self)
}

// --- one-time render setup --------------------------------------------------
let sampleRate = 48000.0
let frames: AUAudioFrameCount = 512
let format = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 2)!
try! unit.inputBusses[0].setFormat(format)
try! unit.outputBusses[0].setFormat(format)
unit.inputBusses[0].isEnabled = true
unit.outputBusses[0].isEnabled = true
unit.maximumFramesToRender = frames
try! unit.allocateRenderResources()
let outBuffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames)!

// --- excitation -------------------------------------------------------------
// Cached by description: a search renders hundreds of parameter sets through
// the same DI, and decoding it every time would be most of the wall clock.
var excitationCache: [String: [[Float]]] = [:]

func generated(_ excitation: String, _ amplitude: Float) -> [[Float]] {
    let total = Int(sampleRate * 2.0)
    var seed: UInt64 = 0x5eed_1234_abcd_0001
    func nextFloat() -> Float {
        seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17
        return Float(Double(seed >> 11) / Double(1 << 53)) * 2.0 - 1.0
    }
    var samples = [Float](repeating: 0, count: total)
    if excitation.hasPrefix("sine:") {
        let freq = Double(excitation.dropFirst(5)) ?? 220.0
        for i in 0..<total {
            samples[i] = Float(sin(2.0 * Double.pi * freq * Double(i) / sampleRate)) * amplitude
        }
    } else {
        for i in 0..<total { samples[i] = nextFloat() * amplitude }
    }
    return [samples]
}

/// Read a whole file, looping until it is consumed.
///
/// `AVAudioFile.read(into:)` fills *up to* the buffer's capacity and routinely
/// stops short: asked for all 144000 frames of a 3-second file in one call it
/// returns 143340, and the shortfall varies with the length. Reading once and
/// trusting `frameLength` therefore truncated every `--input` render by a few
/// hundred frames — silently, and by a different amount for every DI. That is the
/// path a search runs on, so the loop is the whole point of this function.
func fromFile(_ path: String, _ amplitude: Float) -> [[Float]]? {
    guard let file = try? AVAudioFile(forReading: URL(fileURLWithPath: path)) else { return nil }
    let inputFormat = file.processingFormat
    let channelCount = Int(inputFormat.channelCount)
    guard inputFormat.sampleRate == sampleRate, file.length > 0, channelCount > 0,
        let buffer = AVAudioPCMBuffer(pcmFormat: inputFormat, frameCapacity: 8192)
    else { return nil }

    var channels = [[Float]](repeating: [], count: channelCount)
    for channel in 0..<channelCount {
        channels[channel].reserveCapacity(Int(file.length))
    }
    while file.framePosition < file.length {
        guard (try? file.read(into: buffer)) != nil, buffer.frameLength > 0,
            let samples = buffer.floatChannelData
        else { break }
        for channel in 0..<channelCount {
            for f in 0..<Int(buffer.frameLength) {
                channels[channel].append(samples[channel][f] * amplitude)
            }
        }
    }
    // A partial read is worse than none: it would render the front of the DI and
    // report success, and every measurement downstream would be of a signal the
    // caller did not supply.
    guard channels[0].count == Int(file.length) else { return nil }
    return channels
}

// --- command loop -----------------------------------------------------------
reply(["\"ready\":true", "\"instantiate_ms\":\(String(format: "%.3f", instantiateMs))",
       "\"xml_state\":\(baseDocument != nil)", "\"version\":\(quoted(componentVersion))"])

while let line = readLine(strippingNewline: true) {
    if line.trimmingCharacters(in: .whitespaces).isEmpty { continue }
    let commandStart = DispatchTime.now()

    guard let data = line.data(using: .utf8),
        let command = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    else {
        reply(["\"ok\":false", "\"error\":\"line is not a JSON object\""])
        continue
    }
    if command["quit"] as? Bool == true { break }
    guard let outPath = command["out"] as? String else {
        reply(["\"ok\":false", "\"error\":\"command needs an out path\""])
        continue
    }
    let amplitude = Float((command["amplitude"] as? NSNumber)?.doubleValue ?? 0.25)
    let excitation = command["excitation"] as? String ?? "noise"
    let settle = (command["settle"] as? NSNumber).map { UInt32($0.doubleValue * 1000.0) }
        ?? defaultSettleMicroseconds

    // --- build this command's state -----------------------------------------
    var state = baseState
    if let statePath = command["state"] as? String {
        guard let blob = try? Data(contentsOf: URL(fileURLWithPath: statePath)) else {
            reply(["\"ok\":false", "\"error\":\("could not read \(statePath)".debugDescription)"])
            continue
        }
        state["jucePluginState"] = blob
    } else if let document = baseDocument {
        var edited = document
        var failure: String? = nil
        for case let edit as [String: Any] in (command["edits"] as? [Any] ?? []) {
            guard let module = edit["module"] as? String, let key = edit["key"] as? String else {
                failure = "an edit needs a module and a key"
                break
            }
            let value: String
            if let text = edit["value"] as? String {
                value = text
            } else if let number = edit["value"] as? NSNumber {
                value = number.stringValue
            } else {
                failure = "edit \(module)/\(key) needs a string or number value"
                break
            }
            let ns = edited as NSString
            let elementRE = try! NSRegularExpression(pattern: "<\(module)\\b[^>]*>")
            guard let element = elementRE.firstMatch(
                in: edited, range: NSRange(location: 0, length: ns.length))
            else {
                failure = "no <\(module)> element in the plugin's state"
                break
            }
            let keyRE = try! NSRegularExpression(pattern: "\\b\(key)=\"([^\"]*)\"")
            guard let match = keyRE.firstMatch(in: edited, range: element.range) else {
                failure = "no \(key) attribute on <\(module)>"
                break
            }
            edited = ns.replacingCharacters(in: match.range(at: 1), with: value)
        }
        if let failure {
            reply(["\"ok\":false", "\"error\":\(quoted(failure))"])
            continue
        }
        // Writing a control on an amp that is not selected is a silent no-op,
        // so the caller says which amp this parameter set is about.
        if let amp = command["selectAmp"] as? NSNumber {
            let ampRE = try! NSRegularExpression(pattern: "selectedAmp=\"[^\"]*\"")
            edited = ampRE.stringByReplacingMatches(
                in: edited, range: NSRange(location: 0, length: (edited as NSString).length),
                withTemplate: "selectedAmp=\"\(amp.stringValue)\"")
        }
        if command["gateOff"] as? Bool == true {
            edited = edited.replacingOccurrences(of: "gateActive=\"true\"", with: "gateActive=\"false\"")
        }
        var header = baseHeader
        let length = UInt32(Array(edited.utf8).count)
        if header.count >= 8 {
            header[4] = UInt8(length & 0xff); header[5] = UInt8((length >> 8) & 0xff)
            header[6] = UInt8((length >> 16) & 0xff); header[7] = UInt8((length >> 24) & 0xff)
        }
        state["jucePluginState"] = Data(header) + Data(edited.utf8) + Data(baseTrailer)
    } else if command["edits"] != nil {
        reply(["\"ok\":false", "\"error\":\"this plugin's state is not XML; pass state instead of edits\""])
        continue
    }

    let stateStart = DispatchTime.now()
    // scripts/au_render.swift writes state to an unallocated instance and
    // allocates afterwards, and its renders are bit-identical across processes.
    // "isolate" reproduces that order here.
    //
    // It does *not* make a second render in the same process match the first,
    // which this comment used to claim: on Morgan 1.1.1 two renders of identical
    // parameters differ by -15.4 dB relative to the signal without it and
    // -15.7 dB with it. Only a fresh process is bit-exact.
    //
    // What it does do is make Tone King audible at all. That plugin renders exact
    // zeros on its first allocation of render resources — the silence this project
    // spent months attributing to bare instantiation — and renders normally once
    // they have been cycled. "realloc" below works just as well, so it is the
    // reallocation that matters rather than the order of the state write. See
    // match/renderer_au.py, which turns this on by itself when a first render
    // comes back silent.
    let isolate = command["isolate"] as? Bool == true
    if isolate { unit.deallocateRenderResources() }
    unit.fullState = state
    if isolate {
        try! unit.allocateRenderResources()
        unit.reset()
    }
    let stateMs = ms(stateStart, DispatchTime.now())
    if settle > 0 { usleep(settle) }

    // --- excitation ---------------------------------------------------------
    let inputPath = command["input"] as? String
    let cacheKey = "\(inputPath ?? excitation)|\(amplitude)"
    var channels = excitationCache[cacheKey]
    let excitationStart = DispatchTime.now()
    if channels == nil {
        if let inputPath {
            guard let loaded = fromFile(inputPath, amplitude) else {
                reply(["\"ok\":false",
                       "\"error\":\(quoted("could not read \(inputPath) as \(Int(sampleRate)) Hz audio"))"])
                continue
            }
            channels = loaded
        } else {
            channels = generated(excitation, amplitude)
        }
        excitationCache[cacheKey] = channels
    }
    let excitationMs = ms(excitationStart, DispatchTime.now())
    let source = channels!
    let total = source[0].count

    // --- render -------------------------------------------------------------
    // Clear whatever the previous command left ringing in the delay and reverb,
    // or a render carries the tail of the one before it. `reset` alone does not
    // make consecutive renders of one parameter set identical — see
    // docs/measuring-against-the-plugin.md — so two heavier options exist to
    // find out what does.
    unit.reset()
    if command["realloc"] as? Bool == true {
        unit.deallocateRenderResources()
        try! unit.allocateRenderResources()
        unit.reset()
    }

    var cursor = 0
    let inputBlock: AURenderPullInputBlock = { _, _, frameCount, _, audioBufferList in
        let abl = UnsafeMutableAudioBufferListPointer(audioBufferList)
        for (index, buffer) in abl.enumerated() {
            let channel = source[min(index, source.count - 1)]
            let ptr = buffer.mData!.assumingMemoryBound(to: Float.self)
            for f in 0..<Int(frameCount) {
                ptr[f] = (cursor + f) < total ? channel[cursor + f] : 0
            }
        }
        cursor += Int(frameCount)
        return noErr
    }

    var file: AVAudioFile?
    do {
        file = try AVAudioFile(forWriting: URL(fileURLWithPath: outPath), settings: format.settings,
                               commonFormat: .pcmFormatFloat32, interleaved: false)
    } catch {
        reply(["\"ok\":false", "\"error\":\(quoted("could not open \(outPath) for writing"))"])
        continue
    }

    var flags = AudioUnitRenderActionFlags()
    var timestamp = AudioTimeStamp()
    timestamp.mFlags = .sampleTimeValid

    // Optionally render and discard first, so anything the plugin smooths
    // towards its new setting has arrived before the audio that gets kept.
    if let warmup = command["warmup"] as? NSNumber, warmup.doubleValue > 0 {
        let discard = Int(warmup.doubleValue * sampleRate)
        var done = 0
        while done < discard {
            flags = AudioUnitRenderActionFlags()
            outBuffer.frameLength = frames
            _ = unit.renderBlock(&flags, &timestamp, frames, 0,
                                 outBuffer.mutableAudioBufferList, inputBlock)
            timestamp.mSampleTime += Double(frames)
            done += Int(frames)
        }
        cursor = 0
        timestamp.mSampleTime = 0
    }

    var rendered = 0
    var renderMs = 0.0
    var writeMs = 0.0
    var peak: Float = 0
    var renderError: OSStatus = noErr
    while rendered < total {
        flags = AudioUnitRenderActionFlags()
        outBuffer.frameLength = frames
        let blockStart = DispatchTime.now()
        let status = unit.renderBlock(&flags, &timestamp, frames, 0,
                                      outBuffer.mutableAudioBufferList, inputBlock)
        renderMs += ms(blockStart, DispatchTime.now())
        if status != noErr {
            renderError = status
            break
        }
        // Peak here rather than from the file afterwards: a caller needs to know
        // a render was silent before it draws a conclusion from it.
        if let channelData = outBuffer.floatChannelData {
            for channel in 0..<Int(format.channelCount) {
                for f in 0..<Int(frames) { peak = max(peak, abs(channelData[channel][f])) }
            }
        }
        timestamp.mSampleTime += Double(frames)
        let writeStart = DispatchTime.now()
        try! file!.write(from: outBuffer)
        writeMs += ms(writeStart, DispatchTime.now())
        rendered += Int(frames)
    }
    // Release it explicitly: this is what patches the RIFF and `data` chunk
    // sizes. Without it the samples are on disk but every reader sees 0 length.
    file = nil

    if renderError != noErr {
        reply(["\"ok\":false", "\"error\":\(quoted("render failed: \(renderError)"))"])
        continue
    }
    let timings = ["state_apply": stateMs, "excitation": excitationMs, "render_block": renderMs,
                   "file_write": writeMs, "total": ms(commandStart, DispatchTime.now())]
        .map { "\(quoted($0.key)):\(String(format: "%.3f", $0.value))" }
        .sorted()
        .joined(separator: ",")
    reply(["\"ok\":true", "\"out\":\(quoted(outPath))",
           "\"peak\":\(String(format: "%.7f", peak))", "\"frames\":\(rendered)",
           "\"ms\":{\(timings)}"])
}
