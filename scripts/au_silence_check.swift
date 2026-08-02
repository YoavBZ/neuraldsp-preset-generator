// Does this plugin produce audio at all in a headless process?
//
//   swiftc -swift-version 5 -O scripts/au_silence_check.swift -o /tmp/silence
//   /tmp/silence aumf NMAS NDSP     # Morgan: produces audio
//   /tmp/silence aumf TKI2 NDSP     # Tone King: exact zeros
//
// This exists because `scripts/au_render.swift` gets audio out of Morgan and
// silence out of Tone King, and the difference had to be attributed to the
// plugin rather than to the harness. It deliberately shares nothing with
// au_render: no state is set, no document is edited, no parameter is touched.
// It instantiates, feeds noise, and reports the peak — through the v2
// `AudioUnitRender` path, which is what `auval` uses.
//
// It also reports the properties that would otherwise be plausible
// explanations: bus counts and channel capabilities, bypass, and latency.
//
// If this prints a non-zero peak for one plugin and 0.0 for another, the
// harness is not the variable. See docs/measuring-against-the-plugin.md.
import AudioToolbox
import Foundation
func fourCC(_ s: String) -> OSType { var r: OSType = 0; for b in s.utf8.prefix(4) { r = (r << 8) | OSType(b) }; return r }
let a = CommandLine.arguments
var desc = AudioComponentDescription(componentType: fourCC(a[1]), componentSubType: fourCC(a[2]),
    componentManufacturer: fourCC(a[3]), componentFlags: 0, componentFlagsMask: 0)
guard let comp = AudioComponentFindNext(nil, &desc) else { print("no component"); exit(1) }
var unit: AudioUnit?
guard AudioComponentInstanceNew(comp, &unit) == noErr, let au = unit else { print("instantiate failed"); exit(1) }

let sr = 48000.0
var asbd = AudioStreamBasicDescription(
    mSampleRate: sr, mFormatID: kAudioFormatLinearPCM,
    mFormatFlags: kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked | kAudioFormatFlagIsNonInterleaved,
    mBytesPerPacket: 4, mFramesPerPacket: 1, mBytesPerFrame: 4,
    mChannelsPerFrame: 2, mBitsPerChannel: 32, mReserved: 0)
let sz = UInt32(MemoryLayout<AudioStreamBasicDescription>.size)
AudioUnitSetProperty(au, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Input, 0, &asbd, sz)
AudioUnitSetProperty(au, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Output, 0, &asbd, sz)
var maxFrames: UInt32 = 512
AudioUnitSetProperty(au, kAudioUnitProperty_MaximumFramesPerSlice, kAudioUnitScope_Global, 0, &maxFrames, UInt32(MemoryLayout<UInt32>.size))

var seed: UInt64 = 0x5eed1234
func nf() -> Float { seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17
    return Float(Double(seed >> 11) / Double(1 << 53)) * 2 - 1 }
let cb: AURenderCallback = { _, _, _, _, frames, io in
    guard let io = io else { return noErr }
    let l = UnsafeMutableAudioBufferListPointer(io)
    for b in l { if let m = b.mData { let p = m.assumingMemoryBound(to: Float.self)
        for i in 0..<Int(frames) { p[i] = nf() * 0.25 } } }
    return noErr }
var input = AURenderCallbackStruct(inputProc: cb, inputProcRefCon: nil)
AudioUnitSetProperty(au, kAudioUnitProperty_SetRenderCallback, kAudioUnitScope_Input, 0,
                     &input, UInt32(MemoryLayout<AURenderCallbackStruct>.size))
var bypass: UInt32 = 0
AudioUnitSetProperty(au, kAudioUnitProperty_BypassEffect, kAudioUnitScope_Global, 0,
                     &bypass, UInt32(MemoryLayout<UInt32>.size))
var readBypass: UInt32 = 9; var bsz = UInt32(MemoryLayout<UInt32>.size)
AudioUnitGetProperty(au, kAudioUnitProperty_BypassEffect, kAudioUnitScope_Global, 0, &readBypass, &bsz)
print("bypass =", readBypass)
var latency: Float64 = -1; var lsz = UInt32(MemoryLayout<Float64>.size)
AudioUnitGetProperty(au, kAudioUnitProperty_Latency, kAudioUnitScope_Global, 0, &latency, &lsz)
print("latency =", latency, "s")
guard AudioUnitInitialize(au) == noErr else { print("initialize failed"); exit(1) }

let frames: UInt32 = 512
let abl = AudioBufferList.allocate(maximumBuffers: 2)
var storage = [[Float]](repeating: [Float](repeating: 0, count: Int(frames)), count: 2)
var peak: Float = 0
var ts = AudioTimeStamp(); ts.mFlags = .sampleTimeValid
for _ in 0..<200 {
    for c in 0..<2 {
        storage[c].withUnsafeMutableBufferPointer { p in
            abl[c] = AudioBuffer(mNumberChannels: 1, mDataByteSize: frames * 4, mData: p.baseAddress)
        }
    }
    var flags = AudioUnitRenderActionFlags()
    let s = AudioUnitRender(au, &flags, &ts, 0, frames, abl.unsafeMutablePointer)
    if s != noErr { print("render status \(s)"); break }
    ts.mSampleTime += Double(frames)
    for c in 0..<2 { for v in storage[c] { peak = max(peak, abs(v)) } }
}
print("peak = \(peak)")
if peak == 0 {
    let warning = "This plugin produced no audio at all. That is a fact about this "
        + "process, not about any control: do not read it as a measurement.\n"
    FileHandle.standardError.write(warning.data(using: .utf8)!)
}
