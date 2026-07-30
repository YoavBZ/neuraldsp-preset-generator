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
preset, which is in BPM.

Reach for `delaySyncNote` **only** when the user explicitly wants the delay to
follow host tempo changes. In that case, see the discovery workflow below,
because the mapping is not yet known.

Same pattern for tremolo: prefer `tremoloRate` in Hz with `tremoloSync` off.

Note that `delayTime` maxes out at 1500 ms, so a whole note below 40 BPM won't
fit. The tool will tell you.

## Why some selectors have no member names

Six selectors in the Morgan pack have no `members` table:
`delaySyncNote`, `tremoloSyncNote`, `delaySync`, `ac20Power`, and both
`CabPan` params.

This isn't an oversight that can be fixed by looking harder. **The plugin UI
displays a selector's label but never the integer stored in the file**, so the
mapping cannot be read off the screen. Asking a user to "note which integer each
setting gives" is asking for something the interface doesn't show.

Writing one of these still works — the tool validates it as an integer and warns
that the value is unverified. It just may not land on the setting you intended.

## Discovering a selector's members

Selectors in this format are **index-based**: the stored integer is the option's
position in the control, counting from 0. That's confirmed for the mic catalog
(0 = the first mic listed, 8 = the ninth).

So the cheap path needs one look and one load:

1. **Read the options off the UI, in order.** Open the control and list its
   entries top to bottom. No integers involved — this is just reading labels.
2. **Write them into the manifest** as `members`, indexed from 0, and set
   `"members_confidence": "assumed-ordinal"`.
3. **Verify with a single probe.** Pick one index in the middle, predict its
   label, and check:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/probe.py" \
     --param delay/delaySyncNote --values 7 \
     --out-dir ~/Library/Audio/Presets/Neural\ DSP/Morgan\ Amps\ Suite/User
   ```

   That writes one disposable preset called `probe delaySyncNote 07`. Load it and
   read the Sync Note control. If the label matches your prediction, the ordering
   holds and the whole table is confirmed — drop `members_confidence`. If it
   doesn't, the mapping isn't a plain index and needs a full sweep.

### Full sweep, if ordinal ordering doesn't hold

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/probe.py" \
  --param delay/delaySyncNote --values 0-15 --out-dir <user preset folder>
```

One preset per value, each **named after the value it carries**, so the plugin's
own preset browser labels them: `probe delaySyncNote 00`, `01`, `02`… The user
loads each and reads the control. They report labels; you write integers.

The probe presets are disposable — clone the template, change one selector and
the name, nothing else. Delete them when the table is filled in.

Cap the sweep. If you don't know how many options there are, the option list from
step 1 tells you; don't sweep 0-63 hoping to find the end.

## Recording what you learn

Once a mapping is known, write it into `packs/<id>/manifest.json`:

```json
"delay/delaySyncNote": {
  "kind": "enum",
  "ui": "Sync note",
  "members": {"0": "1/1", "1": "1/2", "2": "1/2 dotted", "…": "…"},
  "members_confidence": "verified-by-probe"
}
```

Drop `needs_confirmation` and the discovery note at the same time. Then
`show.py` prints the label instead of the bare integer, specs can set it by
name, and out-of-range values become a hard error instead of a warning — the
same treatment the mic catalog already gets.
