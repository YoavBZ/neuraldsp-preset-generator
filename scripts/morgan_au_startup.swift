// One fixed Morgan instantiation/version/process-exit probe. No render setup,
// fullState access, preset loading, parameter changes, audio buffers or files.
import Foundation
import AVFoundation
import AudioToolbox
import Darwin

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    _exit(1)
}

func fourCC(_ text: String) -> UInt32 {
    text.utf8.reduce(0) { ($0 << 8) | UInt32($1) }
}

guard CommandLine.arguments.count == 1 else { fail("no arguments accepted") }
let desc = AudioComponentDescription(componentType: fourCC("aumf"),
    componentSubType: fourCC("NMAS"), componentManufacturer: fourCC("NDSP"),
    componentFlags: 0, componentFlagsMask: 0)
var instance: AUAudioUnit?
let startupDeadline = DispatchWorkItem { fail("instantiate callback deadline exhausted") }
DispatchQueue.global().asyncAfter(deadline: .now() + .seconds(20), execute: startupDeadline)
AUAudioUnit.instantiate(with: desc, options: []) { unit, error in
    DispatchQueue.main.async {
        startupDeadline.cancel()
        if let error = error { fail("instantiate: \(error)") }
        guard let unit = unit else { fail("no instance returned") }
        instance = unit // retain until explicit process exit
        var rawVersion: UInt32 = 0
        let status = AudioComponentGetVersion(unit.component, &rawVersion)
        guard status == noErr else { fail("component version error: \(status)") }
        let version = "\((rawVersion >> 16) & 0xffff).\((rawVersion >> 8) & 0xff).\(rawVersion & 0xff)"
        let reply: [String: Any] = ["ready": true, "version": version,
                                  "scope": "instance-version-only"]
        guard let output = try? JSONSerialization.data(withJSONObject: reply) else {
            fail("startup reply encoding failed")
        }
        FileHandle.standardOutput.write(output + Data([10]))
        // Keep the main queue available while Python sends the sole quit line.
        DispatchQueue.global().async {
            guard let line = readLine(), let data = line.data(using: .utf8),
                  let command = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
                  command.count == 1, command["quit"] as? Bool == true else {
                fail("only quit command accepted")
            }
            // Process termination, not destructor/teardown completion.
            _exit(0)
        }
    }
}
// Service the main queue; never block it waiting for asynchronous instantiation.
dispatchMain()
