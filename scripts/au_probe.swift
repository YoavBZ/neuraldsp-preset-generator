// Read a Neural DSP plugin's own answers out of its Audio Unit.
//
//   swiftc -swift-version 5 -O scripts/au_probe.swift -o /tmp/au_probe
//   /tmp/au_probe aumf NMAS NDSP params
//   /tmp/au_probe aumf NMAS NDSP revmap
//   /tmp/au_probe aumf NMAS NDSP values delay/delaySyncNote 0,1,2,3
//
// Modes:
//   params  every published control: name, range, and the strings the plugin
//           formats for its own minimum and maximum.
//   state   the plugin's state tree, flattened. The preset document lives in
//           `jucePluginState` and uses the same key names a saved preset does.
//   revmap  write each key of that document in turn and report which control
//           moved. This is the direction that matters: it is the path a
//           generated preset actually takes.
//   values  write chosen values to one key and report, for each, the control
//           that moved, its label, and the value the plugin kept — which is
//           where clamping and rejection become visible.
//   table   sweep a control and record where its label changes.
//   dumpraw write the raw state blobs to files, for looking at the framing.
//
// Nothing is rendered to an output device and no file the plugin owns is
// touched: the edited state goes to an instance that dies with the process.
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
guard args.count >= 5 else {
    FileHandle.standardError.write("usage: auprobe <type> <subtype> <manu> <mode> [args...]\n".data(using: .utf8)!)
    exit(2)
}
let desc = AudioComponentDescription(
    componentType: fourCC(args[1]),
    componentSubType: fourCC(args[2]),
    componentManufacturer: fourCC(args[3]),
    componentFlags: 0, componentFlagsMask: 0)
let mode = args[4]

let sem = DispatchSemaphore(value: 0)
var unit: AUAudioUnit!
var err: Error?
AUAudioUnit.instantiate(with: desc, options: []) { au, e in
    unit = au; err = e; sem.signal()
}
sem.wait()
if let err { FileHandle.standardError.write("instantiate failed: \(err)\n".data(using: .utf8)!); exit(1) }

func jsonOut(_ obj: Any) {
    let d = try! JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys])
    FileHandle.standardOutput.write(d)
    FileHandle.standardOutput.write("\n".data(using: .utf8)!)
}

/// Every scalar leaf of the state tree, flattened to dotted paths, so two
/// states can be compared key by key.
func flatten(_ value: Any, _ path: String, into out: inout [String: String]) {
    switch value {
    case let d as [String: Any]:
        for (k, v) in d { flatten(v, path.isEmpty ? k : "\(path).\(k)", into: &out) }
    case let a as [Any]:
        for (i, v) in a.enumerated() { flatten(v, "\(path)[\(i)]", into: &out) }
    case let data as Data:
        // JUCE-style plugins hide the real preset in an opaque blob. If it is
        // text, keep it as text so the diff can see individual keys.
        if let s = String(data: data, encoding: .utf8), !s.isEmpty {
            out[path] = s
        } else {
            out[path] = "<\(data.count) bytes>"
        }
    default:
        out[path] = String(describing: value)
    }
}

switch mode {
case "params":
    var rows: [[String: Any]] = []
    for p in unit.parameterTree?.allParameters ?? [] {
        var row: [String: Any] = [
            "address": p.address,
            "identifier": p.identifier,
            "displayName": p.displayName,
            "min": p.minValue,
            "max": p.maxValue,
            "value": p.value,
            "unit": p.unit.rawValue,
            "unitName": p.unitName ?? NSNull(),
            "flags": p.flags.rawValue,
        ]
        if let vs = p.valueStrings { row["valueStrings"] = vs }
        // The formatted string the plugin itself would show for min/max, which
        // carries the unit and the plugin's own rounding.
        row["minString"] = p.string(fromValue: [p.minValue])
        row["maxString"] = p.string(fromValue: [p.maxValue])
        row["valueString"] = p.string(fromValue: [p.value])
        rows.append(row)
    }
    jsonOut(rows)

case "state":
    var flat: [String: String] = [:]
    flatten(unit.fullState ?? [:], "", into: &flat)
    jsonOut(flat)

case "map":
    // Perturb one parameter at a time and hand the whole state back out. The
    // caller diffs the preset keys, which is the ground-truth link between a
    // published parameter and the key a saved preset carries.
    func stateXML() -> String {
        var flat: [String: String] = [:]
        flatten(unit.fullState ?? [:], "", into: &flat)
        return flat["jucePluginState"] ?? ""
    }
    let baseline = stateXML()
    var result: [[String: Any]] = []
    for p in unit.parameterTree?.allParameters ?? [] {
        let original = p.value
        // Move to whichever end is further away, so the change is unmistakable.
        let target = abs(p.maxValue - original) >= abs(original - p.minValue) ? p.maxValue : p.minValue
        if target == original { continue }
        p.value = target
        usleep(15000)
        result.append([
            "address": p.address,
            "displayName": p.displayName,
            "from": original,
            "to": target,
            "after": stateXML(),
        ])
        p.value = original
        usleep(15000)
    }
    jsonOut(["baseline": baseline, "params": result])

case "table":
    // Sweep a selector across its normalised range and record every point where
    // the plugin's own label changes, together with the state at that point.
    // The label is what the UI shows; the state carries the integer a preset
    // stores. Recording both together is what links them.
    func stateXML() -> String {
        var flat: [String: String] = [:]
        flatten(unit.fullState ?? [:], "", into: &flat)
        return flat["jucePluginState"] ?? ""
    }
    let addresses = args[5].split(separator: ",").compactMap { AUParameterAddress($0) }
    let steps = args.count > 6 ? (Int(args[6]) ?? 2001) : 2001
    var out: [[String: Any]] = []
    for addr in addresses {
        guard let p = unit.parameterTree?.parameter(withAddress: addr) else { continue }
        let original = p.value
        var stops: [[String: Any]] = []
        var lastLabel: String? = nil
        for i in 0..<steps {
            let norm = p.minValue + (p.maxValue - p.minValue) * Float(i) / Float(steps - 1)
            let label = p.string(fromValue: [norm])
            if label != lastLabel {
                p.value = norm
                usleep(12000)
                stops.append(["normalized": norm, "label": label, "state": stateXML()])
                lastLabel = label
            }
        }
        p.value = original
        usleep(12000)
        out.append(["address": addr, "displayName": p.displayName, "stops": stops])
    }
    jsonOut(out)

case "dumpraw":
    guard let st = unit.fullState else { exit(1) }
    for (k, v) in st {
        if let d = v as? Data {
            try! d.write(to: URL(fileURLWithPath: "\(args[5]).\(k).bin"))
            FileHandle.standardError.write("wrote \(k): \(d.count) bytes\n".data(using: .utf8)!)
        }
    }

case "revmap":
    // The direction that matters: write a value into the preset document, hand
    // it to the plugin, and see which published control moved. This is exactly
    // what a generated preset does, so it tests the real path rather than an
    // inference from names.
    guard let baseState = unit.fullState,
          let blob = baseState["jucePluginState"] as? Data else { exit(1) }

    let params = unit.parameterTree?.allParameters ?? []
    func readValues() -> [AUParameterAddress: Float] {
        var out: [AUParameterAddress: Float] = [:]
        for p in params { out[p.address] = p.value }
        return out
    }
    func labels() -> [AUParameterAddress: String] {
        var out: [AUParameterAddress: String] = [:]
        for p in params { var v = p.value; out[p.address] = p.string(fromValue: &v) }
        return out
    }

    // The document sits inside a framed blob. Locate it so the frame can be
    // rebuilt byte for byte around an edited document.
    let bytes = [UInt8](blob)
    guard let xmlStart = bytes.firstRange(of: Array("<?xml".utf8))?.lowerBound else {
        FileHandle.standardError.write("no document in state blob\n".data(using: .utf8)!)
        exit(1)
    }
    let header = Array(bytes[0..<xmlStart])
    var docEnd = bytes.count
    while docEnd > xmlStart, bytes[docEnd - 1] == 0 { docEnd -= 1 }
    let trailer = Array(bytes[docEnd...])
    let doc = String(decoding: bytes[xmlStart..<docEnd], as: UTF8.self)

    func framed(_ newDoc: String) -> Data {
        var out = header
        // "VC2!" then a little-endian length of the document itself, not
        // counting the NUL that follows it. Rewrite it or the plugin reads a
        // truncated document.
        let n = Array(newDoc.utf8).count
        if out.count >= 8 {
            let len = UInt32(n)
            out[4] = UInt8(len & 0xff)
            out[5] = UInt8((len >> 8) & 0xff)
            out[6] = UInt8((len >> 16) & 0xff)
            out[7] = UInt8((len >> 24) & 0xff)
        }
        return Data(out) + Data(newDoc.utf8) + Data(trailer)
    }

    func apply(_ newDoc: String) {
        var st = baseState
        st["jucePluginState"] = framed(newDoc)
        unit.fullState = st
        usleep(60000)
    }

    // Re-apply the untouched document first: the reference must be the state
    // after a load, not after instantiation, or every key looks changed.
    apply(doc)
    let baseValues = readValues()
    let baseLabels = labels()

    // Each attribute of the document, with the element that carries it.
    let attrRE = try! NSRegularExpression(pattern: "<([A-Za-z0-9_]+)((?:\\s+[A-Za-z0-9_]+=\"[^\"]*\")+)")
    let kvRE = try! NSRegularExpression(pattern: "([A-Za-z0-9_]+)=\"([^\"]*)\"")
    let ns = doc as NSString
    var targets: [(element: String, key: String, value: String, range: NSRange)] = []
    for m in attrRE.matches(in: doc, range: NSRange(location: 0, length: ns.length)) {
        let element = ns.substring(with: m.range(at: 1))
        let attrsRange = m.range(at: 2)
        for km in kvRE.matches(in: doc, range: attrsRange) {
            targets.append((element,
                            ns.substring(with: km.range(at: 1)),
                            ns.substring(with: km.range(at: 2)),
                            km.range(at: 2)))
        }
    }

    let only = args.count > 5 ? args[5] : ""

    var results: [[String: Any]] = []
    for t in targets {
        if !only.isEmpty && t.key != only { continue }
        // Pick a replacement that is unmistakably different from what is there.
        let probe: String
        if t.value == "true" { probe = "false" }
        else if t.value == "false" { probe = "true" }
        else if let d = Double(t.value) { probe = d == 0 ? "1" : (abs(d) < 1.001 ? "0" : "1") }
        else { continue }

        apply(ns.replacingCharacters(in: t.range, with: probe))
        let after = readValues()
        let afterLabels = labels()
        var moved: [[String: Any]] = []
        for p in params where abs((after[p.address] ?? 0) - (baseValues[p.address] ?? 0)) > 1e-6 {
            moved.append([
                "address": p.address,
                "name": p.displayName,
                "fromValue": baseValues[p.address] ?? 0,
                "toValue": after[p.address] ?? 0,
                "fromLabel": baseLabels[p.address] ?? "",
                "toLabel": afterLabels[p.address] ?? "",
            ])
        }
        results.append([
            "element": t.element, "key": t.key,
            "was": t.value, "probe": probe, "moved": moved,
        ])
        apply(doc)
    }
    jsonOut(results)

case "values":
    // Write specific values into one preset key, hand each to the plugin, and
    // report what the plugin makes of it. Answers three different questions
    // with one mechanism: what a selector index is called, where a range
    // clamps, and what unit a number is in.
    guard let baseState = unit.fullState,
          let blob = baseState["jucePluginState"] as? Data else { exit(1) }
    let params = unit.parameterTree?.allParameters ?? []

    let bytes = [UInt8](blob)
    guard let xmlStart = bytes.firstRange(of: Array("<?xml".utf8))?.lowerBound else { exit(1) }
    let header = Array(bytes[0..<xmlStart])
    var docEnd = bytes.count
    while docEnd > xmlStart, bytes[docEnd - 1] == 0 { docEnd -= 1 }
    let trailer = Array(bytes[docEnd...])
    let doc = String(decoding: bytes[xmlStart..<docEnd], as: UTF8.self)

    func framed(_ newDoc: String) -> Data {
        var out = header
        let n = Array(newDoc.utf8).count
        if out.count >= 8 {
            let len = UInt32(n)
            out[4] = UInt8(len & 0xff); out[5] = UInt8((len >> 8) & 0xff)
            out[6] = UInt8((len >> 16) & 0xff); out[7] = UInt8((len >> 24) & 0xff)
        }
        return Data(out) + Data(newDoc.utf8) + Data(trailer)
    }
    func apply(_ newDoc: String) {
        var st = baseState
        st["jucePluginState"] = framed(newDoc)
        unit.fullState = st
        usleep(60000)
    }
    func label(_ p: AUParameter) -> String { var v = p.value; return p.string(fromValue: &v) }

    // element/key, then the values to try.
    let spec = args[5].split(separator: "/", maxSplits: 1).map(String.init)
    let (element, key) = (spec[0], spec[1])
    let wanted = args[6].split(separator: ",").map(String.init)

    // Find the attribute inside the right element.
    let ns = doc as NSString
    let elemRE = try! NSRegularExpression(pattern: "<\(element)\\b[^>]*>")
    guard let em = elemRE.firstMatch(in: doc, range: NSRange(location: 0, length: ns.length)) else {
        FileHandle.standardError.write("no element \(element)\n".data(using: .utf8)!); exit(1)
    }
    let kvRE = try! NSRegularExpression(pattern: "\\b\(key)=\"([^\"]*)\"")
    guard let km = kvRE.firstMatch(in: doc, range: em.range) else {
        FileHandle.standardError.write("no key \(key) in \(element)\n".data(using: .utf8)!); exit(1)
    }
    let valueRange = km.range(at: 1)

    apply(doc)
    var before: [AUParameterAddress: Float] = [:]
    for p in params { before[p.address] = p.value }

    var rows: [[String: Any]] = []
    for w in wanted {
        apply(ns.replacingCharacters(in: valueRange, with: w))
        var moved: [[String: Any]] = []
        for p in params where abs(p.value - (before[p.address] ?? 0)) > 1e-9 {
            moved.append(["address": p.address, "name": p.displayName,
                          "label": label(p), "normalized": p.value])
        }
        // Read the value the plugin kept, which is where clamping shows up.
        let after = unit.fullState?["jucePluginState"] as? Data
        var kept = ""
        if let after {
            let ab = [UInt8](after)
            if let s = ab.firstRange(of: Array("<?xml".utf8))?.lowerBound {
                let adoc = String(decoding: ab[s...], as: UTF8.self)
                let ans = adoc as NSString
                if let aem = elemRE.firstMatch(in: adoc, range: NSRange(location: 0, length: ans.length)),
                   let akm = kvRE.firstMatch(in: adoc, range: aem.range) {
                    kept = ans.substring(with: akm.range(at: 1))
                }
            }
        }
        rows.append(["wrote": w, "keptInState": kept, "moved": moved])
        apply(doc)
    }
    jsonOut(["element": element, "key": key, "results": rows])

default:
    FileHandle.standardError.write("unknown mode \(mode)\n".data(using: .utf8)!)
    exit(2)
}
