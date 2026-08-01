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
| Phase / stereo | `*CabPhase`, `*CabStereo` | switch / switch |
| Pan | `*CabPan` | -50 (hard left) to 50 (hard right), 0 = centre |
| Room mic | `*RoomActive`, `*RoomMicType`, `*RoomMicLevel` | switch / enum / dB |

`*CabPan` is a number, not a selector — the plugin shows -25 as `25 L`. The room
mic selector takes only 0–2 and is **not** the eleven-entry close-mic catalog;
writing a close-mic index like 8 there lands on 0.

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

**Index 10 is `Custom IR`, not a mic.** The plugin's dropdown lists the ten
internal mics and then a separate CUSTOM IR section with a Load button; picking
a file sets this selector to 10. It is the selector, not the path, that decides
whether the cab plays a modelled mic or the file — which matters for stripping,
below. Only write 10 alongside a valid `*ChosenIRFilePath`; on its own it leaves
the plugin showing `Custom IR / No File`.

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

It also moves any mic selector sitting on `Custom IR` (10) back to that side's
plugin default — Dynamic 57 on the left, Condenser 184 on the right. Clearing
the path alone used to leave the selector pointing at a file that was no longer
named, so the plugin showed `Custom IR / No File`: a preset in a worse state
than before it was stripped, and silently so.

### Stripping changes the sound

Clearing an IR is reversible — the field stays addressable and you can set a
path back on a stripped preset. But swapping a third-party IR for an internal
mic is a real tonal change, not a formality. Don't strip a preset the user wants
to keep IR-based, and always say what you did.

`samples/Example_Clean_PR12.xml` is already IR-free, so `--strip-irs` is a
harmless no-op there.
