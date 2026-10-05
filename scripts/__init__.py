"""Command-line tools and the Swift sources used by the Audio Unit backend.

The scripts remain directly executable. Making the directory a package ensures
non-editable installs also carry the Swift sources: the two `match.renderer_au`
compiles at runtime (`au_probe`, `au_render_server`) and the two command-line
helpers the docs build (`au_render`, `au_silence_check`).
"""
