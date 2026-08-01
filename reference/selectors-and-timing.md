# Selectors and musical timing

## Musically-timed delay: use milliseconds

When someone asks for a "dotted eighth delay" or "quarter-note slapback", **do
not reach for the sync-note selector.** Compute the milliseconds:

```python
from packs.timing import note_ms
note_ms(120, "1/8 dotted")   # 375.0
note_ms(96,  "quarter")      # 625.0
```

```json
{"module": "delay", "key": "delayTime", "value": 375}
```

This is exact, needs no selector, and leaves the delay free-running so it sounds
right regardless of host tempo. `note_ms` accepts the spellings people actually
use: `1/8 dotted`, `dotted eighth`, `1/8D`, `quarter triplet`, `1/8T`, `1/16`.

If the user doesn't give a tempo, ask — or read `delay/delayTempo` from the
preset, which is in BPM (40–240).

Reach for `delaySyncNote` **only** when the user explicitly wants the delay to
follow host tempo changes. That also needs `delaySync` set to `DAW`; on `Free`
the selector does nothing and `delayTime` is what matters.

Same pattern for tremolo: prefer `tremoloRate` in Hz with `tremoloSync` off.
Its real range is 0.15–15 Hz, so fast tremolo is available.

Note that `delayTime` maxes out at 1500 ms, so a whole note below 40 BPM won't
fit. The tool will tell you.

## The sync-note tables

Both are declared in the manifest and can be set by name (`"1/8D"`) or index.
They were measured against the running plugin — see
[docs/measuring-against-the-plugin.md](../docs/measuring-against-the-plugin.md).

**They are ordered by note duration, not grouped by kind.** A triplet is shorter
than the straight note of the same denomination and a dotted note is longer, so
the three families interleave and the indices look shuffled. `enums.delayNote`:

| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|----|
| 1/64T | 1/64 | 1/32T | 1/64D | 1/32 | 1/16T | 1/32D | 1/16 | 1/8T | 1/16D | 1/8 |

| 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 |
|----|----|----|----|----|----|----|----|----|----|
| 1/4T | 1/8D | 1/4 | 1/2T | 1/4D | 1/2 | 1/1T | 1/2D | 1/1 | 1/1D |

**Tremolo uses a different table.** `enums.tremoloNote` is the same sequence
starting at `1/32T`, so it has 19 entries and **every index is shifted down by
two**: 1/4 is 13 for delay and 11 for tremolo. Reusing one table for both would
silently mistime every tremolo.

Out-of-range values are not safe to guess at. Writing 19 to `tremoloSyncNote`
doesn't fail and doesn't clamp to the top — the plugin stores 9.

## Two controls that look like selectors and aren't

`ac20Power` and both `*CabPan` params were declared as selectors on the strength
of their names. They are not:

- `ac20Power` is an ordinary knob, stored 0.0–1.0, shown as 0–100%.
- `*CabPan` is a signed number from -50 to 50. Negative is left, 0 is centre;
  the plugin displays -25 as `25 L`.

A name ending in `Pan`, `Power` or `Mode` is a hint, not a fact.
`scripts/bootstrap_pack.py` no longer guesses `Pan` or `Power` as selectors for
this reason — guessing "selector" is the expensive way to be wrong, because it
turns a legible number into an opaque index.

## Selectors whose member names are still unknown

Two: `leftRoomMicType` and `rightRoomMicType`. The plugin accepts 0, 1 and 2 and
silently rewrites anything higher to 0 — measured — but publishes no names for
them, and **has no control for them anywhere in its UI**: the cab page offers
two mics and a Room Send level, nothing else. So there is no screen to read them
off either. Treat them as vestigial and leave them at whatever the template
holds.

These were previously declared against `enums.internalMic`, the eleven-entry
close-mic catalog (ten mics plus `Custom IR`). That was wrong in the dangerous direction: writing
`"Ribbon 121"` (8) to a room mic passed validation and landed on 0.

Writing one of these still works — the tool validates it as an integer and warns
that the value is unverified.

## Discovering a selector's members

If the plugin publishes strings for the control, the probe reads them directly
and nothing below is needed:

```bash
swiftc -swift-version 5 -O scripts/au_probe.swift -o /tmp/au_probe
/tmp/au_probe aumf NMAS NDSP values cabParameters/leftRoomMicType 0,1,2
```

That writes each index into the preset document, hands it to the plugin, and
reports the label the plugin shows.

If it comes back empty, the UI workflow below is the fallback — but check the UI
actually has the control first. Morgan's two room mic selectors publish no
labels *and* have no control, so nothing below will recover them; the workflow
is here for the next pack, not for those two.

Selectors in this format are **index-based**: the stored integer is the option's
position in the control, counting from 0. That's confirmed for the mic catalog
and for both sync-note tables.

1. **Read the options off the UI, in order.** Open the control and list its
   entries top to bottom. No integers involved — this is just reading labels.
2. **Write them into the manifest** as `members`, indexed from 0, and set
   `"members_confidence": "assumed-ordinal"`.
3. **Verify with a single probe.** Pick one index in the middle, predict its
   label, and check:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/probe.py" \
     --param cabParameters/leftRoomMicType --values 1 \
     --out-dir ~/Library/Audio/Presets/Neural\ DSP/Morgan\ Amps\ Suite/User
   ```

   That writes one disposable preset called `probe leftRoomMicType 01`. Load it
   and read the control. If the label matches your prediction, the ordering
   holds and the whole table is confirmed — drop `members_confidence`. If it
   doesn't, the mapping isn't a plain index and needs a full sweep.

### Full sweep, if ordinal ordering doesn't hold

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/probe.py" \
  --param cabParameters/leftRoomMicType --values 0-2 --out-dir <user preset folder>
```

One preset per value, each **named after the value it carries**, so the plugin's
own preset browser labels them: `probe leftRoomMicType 00`, `01`, `02`. The user
loads each and reads the control. They report labels; you write integers.

The probe presets are disposable — clone the template, change one selector and
the name, nothing else. Delete them when the table is filled in.

Cap the sweep. The probe's `values` mode tells you where the plugin stops
accepting an index; don't sweep 0-63 hoping to find the end.

## Recording what you learn

Once a mapping is known, write it into `packs/<id>/manifest.json` — as a shared
`enums` table when more than one parameter uses it, or inline `members` when it
is one control's own list:

```json
"delay/delaySyncNote": {
  "kind": "enum",
  "enum": "delayNote",
  "ui": "Sync note"
}
```

Drop `needs_confirmation` and the discovery note at the same time. Then
`show.py` prints the label instead of the bare integer, specs can set it by
name, and out-of-range values become a hard error instead of a warning — the
same treatment the mic catalog already gets.
