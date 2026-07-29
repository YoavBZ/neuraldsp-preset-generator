# NOTICE

This project exists for **personal interoperability** with Neural DSP's Morgan
Amps Suite: it lets someone who has legitimately purchased the plugin generate
and edit preset files (`.xml`) for their own copy.

## What is and isn't included here

- **No Neural DSP code, audio, or impulse responses.** Nothing from the plugin
  binary or its sample content is in this repository.
- **No factory presets.** The plugin's own presets are git-ignored and are not
  redistributed.
- **No third-party presets.** Presets from other authors are git-ignored — they
  routinely embed absolute IR paths from their creator's machine and reference
  commercial IR packs.
- **One example preset is included**: `samples/Example_Clean_PR12.xml`, generated
  by this project. Because the writer is template-based (it clones a preset and
  mutates values rather than synthesizing bytes from scratch), that file
  necessarily carries the plugin's file structure: ~87% of its bytes are
  parameter key names and format markers that are identical in every Morgan
  preset. The tone settings are this project's own.
- **The parameter catalog** (`schema/morgan_schema.json`) is derived from
  whichever presets you supply, so it is git-ignored too — build your own with
  `python -m schema.build_schema`.

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
"Morgan", "Morgan Amps Suite", and "Neural DSP" are the trademarks of their
respective owners and are used here only to describe what the tool interoperates
with.

If you are Neural DSP and would like this project changed or taken down, please
open an issue — it will be honoured.
