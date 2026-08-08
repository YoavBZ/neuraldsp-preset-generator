"""Command-line tools and the Swift sources used by the Audio Unit backend.

The scripts remain directly executable. Making the directory a package ensures
non-editable installs also carry the two Swift helpers that `match.renderer_au`
compiles at runtime.
"""
