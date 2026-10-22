# The arrangement prior (`arrangement-1`)

What research found about a song's guitars, kept as data: how many guitars, of what
kind, which sections each plays, and the sound changes between sections. `generate`
writes one when it researches a real song (step 2). The ML side cuts the separated
guitar into sections, groups the ones that sound alike and fits a preset per group; it
aligns this file's section names and order to the audio and checks every claim
against it. The file is a prior, never ground truth: one average preset for a whole song
is hurt exactly when guitars or sounds change, and web sources about that are often
wrong or incomplete.

Where it goes: `research/<artist>-<title>/arrangement.json` under the data root. Print
the path, write the file there, then check it (it lists every problem, or prints a
one-line summary):

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/arrangement.py" path "ARTIST" "TITLE"
python "${CLAUDE_PLUGIN_ROOT}/scripts/arrangement.py" check ARRANGEMENT.json
```

In a clone or worktree, pass the data root before the subcommand
(`arrangement.py --data-dir ~/ndsp-presets path ...`), or the path lands in the checkout.

## Rules

- **The whole song, not only the part asked for.** The file describes every guitar on the
  recording (rhythm, 12-string, acoustic, overdubs) and every section, because its reader fits
  a preset per section. Research the other parts at least to their instrument, role and
  sections; list what you could not find in `gaps`, never leave a guitar out as out of scope.
  Keep it bounded: for the parts the user did not ask about, one lineup or credits source and
  one structure source are enough; leave their `rig` null unless a source you already have
  states it, and do not fetch lessons or rundowns for them.
- **Every item carries a `confidence`**:
  - `documented`: a source states it, and the item cites that source;
  - `corroborated`: two or more independent sources state it, and the item cites them;
  - `inferred`: your reasoning, which no source states outright (cite what it rests on,
    if anything);
  - `unknown`: kept so the gap is visible.

  Never upgrade an inference by phrasing it as fact.
- **Sections are names plus order.** Sources name sections ("the second verse", "the
  outro solo") far more often than they give seconds. Give seconds (`start_s`/`end_s`,
  a change's `at_s`) only from the user or from a source timestamped against the same
  recording, and say which in `time_basis`; otherwise leave them null with
  `time_basis: "unknown"`. Never estimate seconds: the ML side would read them as
  timing. Number repeated sections (`chorus 1`, `chorus 2`).
- **Every key is present.** Use null (or an empty list) for what is unknown or absent;
  only `guitars` must name at least one guitar.
- **Name the recording.** Live takes, remasters and album edits differ in arrangement
  and length; `song.recording` says which one the research describes.
- **Doubled parts.** Set `doubled` to `true` when a part is double-tracked (two takes
  of the same part, usually panned apart): a separator hears them as one sound. Use
  `null` when no source says.
- **Tuning and capo** go on each guitar when known (`tuning`: "standard", "half step
  down", "drop D", ...; `capo`: a fret number); null otherwise.
- **Gaps are data too.** List what you looked for and did not find.

## Fields

| Field | What |
|---|---|
| `schema` | `"arrangement-1"` |
| `song` | `artist`, `title`, `recording` (which version), `duration_s` (or null) |
| `guitars[]` | `id`, `player` (or null), `instrument` (e.g. "12-string electric", "electric", "acoustic"), `rig` (`guitar`, `amp`, `effects`: list), `role` (rhythm, lead, fills, arpeggio, ...), `pan` (`L`, `R`, `C` or null), `doubled` (true, false, null), `tuning`, `capo`, `confidence`, `sources` |
| `sections[]` | `name`, `order`, `start_s`, `end_s`, `time_basis` (`user`, `source timestamp`, `unknown`), `guitars` (guitar id to what it plays there and how it sounds), `confidence`, `sources` |
| `changes[]` | `guitar`, `at_section` (a section name, or null), `at_s` (or null), `time_basis` (as for sections), `what` (e.g. "drive pedal on"), `confidence`, `sources` |
| `sources[]` | `id`, `url`, `kind` (`rig rundown`, `interview`, `lesson`, `tab`, `forum`, `article`, `liner notes`, `video`, `other`), `note` |
| `gaps[]` | sentences: what was looked for and not found |

## Example

A made-up song, to show the shape. Every claim in a real file needs a real source.

```json
{
  "schema": "arrangement-1",
  "song": {"artist": "Example Band", "title": "Example Song",
           "recording": "studio album version, 1979", "duration_s": null},
  "guitars": [
    {"id": "g1", "player": "First Player", "instrument": "electric",
     "rig": {"guitar": "Telecaster", "amp": "Fender Deluxe", "effects": ["spring reverb"]},
     "role": "rhythm", "pan": "L", "doubled": true, "tuning": "standard", "capo": null,
     "confidence": "documented", "sources": ["s1"]},
    {"id": "g2", "player": "Second Player", "instrument": "electric",
     "rig": {"guitar": null, "amp": null, "effects": ["overdrive"]},
     "role": "lead", "pan": "C", "doubled": false, "tuning": "standard", "capo": null,
     "confidence": "corroborated", "sources": ["s1", "s2"]}
  ],
  "sections": [
    {"name": "intro", "order": 1, "start_s": null, "end_s": null,
     "time_basis": "unknown", "guitars": {"g1": "clean arpeggios"},
     "confidence": "documented", "sources": ["s2"]},
    {"name": "chorus 1", "order": 2, "start_s": null, "end_s": null,
     "time_basis": "unknown", "guitars": {"g1": "driven chords", "g2": "fills"},
     "confidence": "inferred", "sources": []},
    {"name": "solo", "order": 3, "start_s": null, "end_s": null,
     "time_basis": "unknown", "guitars": {"g2": "lead, overdrive on"},
     "confidence": "documented", "sources": ["s2"]}
  ],
  "changes": [
    {"guitar": "g2", "at_section": "solo", "at_s": null, "time_basis": "unknown",
     "what": "overdrive on",
     "confidence": "documented", "sources": ["s2"]}
  ],
  "sources": [
    {"id": "s1", "url": "https://example.com/rig-rundown", "kind": "rig rundown",
     "note": "names the first player's guitar and amp, and both players' roles"},
    {"id": "s2", "url": "https://example.com/lesson", "kind": "lesson",
     "note": "transcribes the intro and the solo"}
  ],
  "gaps": ["No source gives timestamps.", "Whether g1 changes sound in the chorus is my inference."]
}
```
