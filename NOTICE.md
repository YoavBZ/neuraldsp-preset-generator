# NOTICE

This project exists for **personal interoperability** with Neural DSP plugins —
production packs currently target **Morgan Amps Suite** and **Tone King Imperial
MKII**, and any other plugin can be supported by adding a pack. It lets someone
who has legitimately purchased a plugin generate and edit preset files (`.xml`)
for their own copy.

## What is and isn't included here

- **No Neural DSP code, audio, or impulse responses.** Nothing from the plugin
  binary or its sample content is in this repository.
- **No factory presets.** The plugin's own presets are git-ignored and are not
  redistributed.
- **No third-party presets.** Presets from other authors are git-ignored — they
  routinely embed absolute IR paths from their creator's machine and reference
  commercial IR packs.
- **Two guitar riffs are included** in `samples/riffs/`, for hearing presets on the
  audition page. They are not MIT-licensed. They come from *Guitar-TECHS: An Electric
  Guitar Dataset Covering Techniques, Musical Excerpts, Chords and Scales Using a
  Diverse Array of Hardware*, by Hegel Emmanuel Pedroza Villalobos, Termeh Taheri,
  Wallace Abreu, Ryan Corey and Iran R. Roman (Zenodo record 14963133,
  https://zenodo.org/records/14963133; ICASSP 2025,
  doi:10.1109/ICASSP49660.2025.10887996), licensed CC BY 4.0
  (https://creativecommons.org/licenses/by/4.0/). Changes: excerpts of its part-P1
  direct-input recordings were cut, joined, faded and level-adjusted by
  `research/build_riffs.py`; `samples/riffs/riffs.json` records the sources.
- **One example preset is included**: `samples/Example_Clean_PR12.xml`, generated
  by this project. Because the writer is template-based (it clones a preset and
  mutates values rather than synthesizing bytes from scratch), that file
  necessarily carries the plugin's file structure: ~87% of its bytes are
  parameter key names and format markers that are identical in every Morgan
  preset. The tone settings are this project's own.
- **The observed-value catalog** (`packs/<id>/observed.json`) is derived from
  whichever presets you supply, so it is git-ignored too — build your own with
  `python scripts/build_observed.py`.
- **The pack manifest** (`packs/<id>/manifest.json`) *is* committed. It contains
  only parameter names, kinds, units, ranges and selector labels — the factual
  description needed to read and write presets for a licensed copy. It carries
  no Neural DSP code, audio, impulse responses, preset content, or values taken
  from factory presets.

## Format documentation

The binary format is undocumented. What is described here was determined by
inspecting preset files, for the sole purpose of reading and writing presets for
a licensed copy of the plugin.

**Credit:** the meaning of the format's marker bytes was learned from the notes
in [vian21/toneparse](https://github.com/vian21/toneparse). All code in this
repository is original — no code is taken from that project, which carries no
license of its own. The acknowledgement is for factual insight into the file
layout, not for reused source.

This project is not affiliated with, endorsed by, or supported by Neural DSP.
"Morgan", "Morgan Amps Suite", "Tone King", "Tone King Imperial MKII", and
"Neural DSP" are the trademarks of their
respective owners and are used here only to describe what the tool interoperates
with.

If you are Neural DSP and would like this project changed or taken down, please
open an issue — it will be honoured.
