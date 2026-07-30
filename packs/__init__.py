"""Per-plugin knowledge packs.

A *pack* is everything this tool knows about one Neural DSP plugin:

    packs/<pack_id>/
        manifest.json   committed, hand-curated parameter facts (the contract)
        recipes.json    committed, composable tone recipes
        tone.md         committed, musical knowledge for that plugin
        templates/      git-ignored, the user's own presets
        observed.json   git-ignored, generated from templates/

The first three ship. Everything derived from the user's own preset library
stays local, and lives under the data root rather than here — see `packs.paths`
and NOTICE.md.
"""
