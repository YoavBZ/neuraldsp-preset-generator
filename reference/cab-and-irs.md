# Cab, mics, and impulse responses

## Two cab slots

The cab section has a `left*` and a `right*` slot, each with its own mic,
placement, level and phase, plus an optional room mic.

| what | keys | kind |
|---|---|---|
| Slot on/off | `leftCabActive` / `rightCabActive` | switch |
| Mic choice | `leftMicType` / `rightMicType` | enum (by name) |
| Placement | `*CabPosition`, `*CabDistance` | fraction 0–1 |
| Level | `*CabMicLevel` | dB |
| Phase / stereo / pan | `*CabPhase`, `*CabStereo`, `*CabPan` | switch / switch / enum |
| Room mic | `*RoomActive`, `*RoomMicType`, `*RoomMicLevel` | switch / enum / dB |

`*CabPosition` runs from the speaker cap (bright, aggressive) at 0 to the cone
edge (darker, rounder) at 1. `*CabDistance` moves the mic back — more room, less
proximity bass.

## Mics by name

Set a mic by name; the manifest resolves it to the stored index:

```json
{"module": "cabParameters", "key": "rightMicType", "value": "Ribbon 121"}
```

The catalog lives in `packs/morgan/manifest.json` under `enums.internalMic`
(10 internal mics: Dynamic 57, Dynamic 57 Off-Axis, Dynamic 409, Dynamic 421,
Condenser 184, Condenser 414, Condenser 4006, Condenser U47, Ribbon 121,
Ribbon 160). `show.py` prints the mic name for each slot. An unknown name or an
out-of-range index is a hard error, so you cannot write a mic that doesn't exist.

A common pairing: a dynamic on one slot for body and attack, a ribbon on the
other for smoothed top end, with the ribbon a little further back.

## Custom impulse responses

A preset that uses a third-party IR stores it as an **absolute path** that only
exists on the machine it was saved on. Cloning such a preset carries that dead
path — and the original author's home directory — into your output.

**Pass `--strip-irs` unless you know the template is IR-free.** It clears the
paths so the cab falls back to the internal mics, making the preset portable
on any machine. Verified to produce byte-identical encoding to an IR-free
preset's empty field.

### Stripping is one-way

An empty value's bytes merge into the neighbouring markers, so after stripping,
`leftChosenIRFilePath` / `rightChosenIRFilePath` are **no longer addressable**
in the output file. You cannot set an IR path back on a stripped preset with
this tool — you'd have to go back to an IR-carrying template.

That's fine for generated presets, which should be portable. Just don't strip a
template the user wants to keep IR-based, and say what you did.

`samples/Example_Clean_PR12.xml` is already IR-free, so `--strip-irs` is a
harmless no-op there.
