#!/bin/zsh
# E1e build (phase_fx_reader_e1e): the 770 wide draws' mixes rebuilt (zero renders) and re-separated by X-LANCE on MPS,
# saved as audio. Un-niced. Scoring is run separately, after the declaration's review.
setopt no_bg_nice
cd /Users/yoavbz/projects/neuraldsp-preset-generator
export PYTHONPATH=.
MSST=$HOME/ndsp-presets/tools/msst-venv/bin/python
echo "start $(date)"
$MSST -u -m learn.fx_reader e1e-build --device mps || { echo "BUILD FAILED $(date)"; exit 1; }
echo "E1E BUILD DONE $(date)"
