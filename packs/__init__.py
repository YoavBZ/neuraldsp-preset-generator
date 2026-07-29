"""Per-plugin knowledge packs.

A *pack* is everything this tool knows about one Neural DSP plugin:

    packs/<pack_id>/
        manifest.json   committed, hand-curated parameter facts (the contract)
        tone.md         committed, musical knowledge for that plugin
        templates/      git-ignored, the user's own presets
        observed.json   git-ignored, generated from templates/

Only `manifest.json` and `tone.md` ship. Everything derived from the user's
own preset library stays local — see NOTICE.md.
"""
