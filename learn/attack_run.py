"""librosa's spectral-flux onset detector, run inside the Basic Pitch venv (note-rebuild-plan 12m; ledger `note-rebuild`
`phase_nr_1_redo_calib_amend`). Called only by `learn/note_attacks.py`, as

    ~/ndsp-presets/tools/basic-pitch-venv/bin/python -I learn/attack_run.py --hop 256 --delta 0.07 \
        in1.wav out1.json [in2.wav out2.json ...]

`librosa.onset.onset_detect` with the library's defaults except `hop_length` (and `delta`, the declared threshold), on
the transcriber's own input (22.05 kHz mono). Each output holds the onset times in seconds (to 0.1 ms), the settings,
the input's sha256 and the librosa version. librosa is hash-locked in that venv; nothing in the main `.venv` or on CI
imports it through this file (its module level is the standard library; it runs under `-I`). Python 3.9 syntax.
"""

import hashlib
import json
import sys


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_args(argv):
    """(Pure.) -> (hop, delta, [(in, out)]). Refuses a missing setting or an odd pair list."""
    hop, delta, rest, i = None, None, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--hop":
            hop, i = int(argv[i + 1]), i + 2
        elif a == "--delta":
            delta, i = float(argv[i + 1]), i + 2
        else:
            rest.append(a)
            i += 1
    if hop is None or delta is None:
        raise SystemExit("attack_run: --hop and --delta are required")
    if not rest or len(rest) % 2:
        raise SystemExit("attack_run: give input and output files in pairs")
    return hop, delta, list(zip(rest[::2], rest[1::2]))


def main(argv=None):
    hop, delta, pairs = parse_args(sys.argv[1:] if argv is None else argv)
    import librosa                                       # the venv's only
    import soundfile as sf

    for src, dst in pairs:
        y, sr = sf.read(src, dtype="float64", always_2d=True)   # as the review measured it
        y = y.mean(axis=1)
        t = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop, delta=delta, units="time")
        out = {"onsets": [round(float(x), 4) for x in t], "hop_length": hop, "delta": delta, "sr": sr,
               "librosa": librosa.__version__, "input_sha256": file_sha(src)}
        with open(dst, "w") as f:
            json.dump(out, f, indent=1)
        print(f"attack_run: {len(t)} onsets -> {dst}", flush=True)


if __name__ == "__main__":
    main()
