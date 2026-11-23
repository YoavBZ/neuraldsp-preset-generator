"""MuScriptor's runner (`learn/tx_run.py`; `docs/note-transcriber-plan.md`): the argument parser, the declared
settings, the input guard (every refusal), the weights' check, the note record and the pairing of start and end
events into notes. Pure: runs on the light CI runner (no numpy); MuScriptor and torch are never imported."""
import ast
import json
import pathlib
import subprocess
import sys

import pytest

from learn import tx_run as R

REPO = pathlib.Path(__file__).resolve().parents[1]
SHA = "a" * 64


def _args(settings=None, pairs=("in.wav", "out.json"), device="mps"):
    return ["--weights", "w.safetensors", "--device", device, "--settings", json.dumps(settings or R.MASKED),
            "--inputs", "inputs.json", *pairs]


def test_the_declared_settings():
    assert R.SETTING_KEYS == ("use_sampling", "cfg_coef", "instruments", "batch_size", "beam_size", "prelude_forcing")
    assert R.MASKED == {"use_sampling": False, "cfg_coef": 1.0, "batch_size": 1, "beam_size": 1,
                        "prelude_forcing": True,
                        "instruments": ["acoustic_guitar", "clean_electric_guitar", "distorted_electric_guitar"]}
    assert R.FREE == dict(R.MASKED, instruments=None) and R.DECLARED_SETTINGS == (R.MASKED, R.FREE)
    assert R.SOURCE_KINDS == ("list", "truth", "goat-dev") and R.DEVICES == ("mps", "cpu") and R.THREADS == 4
    assert R.WEIGHTS == {
        "medium": ("ac80adbdf85d87231735fd948af7013441c0afced316c4e9067fd5d8a7fb97ec", 1228144472),
        "small": ("bbd482c786b895cf7d8f44185073d951adae2ebb8a66f82ca84cd1f84569549c", 411888600)}


def test_the_module_level_is_the_standard_library():
    tree = ast.parse((REPO / "learn" / "tx_run.py").read_text())
    top = {a.name.split(".")[0] for n in tree.body if isinstance(n, ast.Import) for a in n.names}
    top |= {n.module.split(".")[0] for n in tree.body if isinstance(n, ast.ImportFrom)}
    assert top <= {"hashlib", "json", "os", "sys"}
    r = subprocess.run([sys.executable, "-c", "import sys; sys.modules['numpy'] = None; import learn.tx_run, "
                        "learn.note_tx; print(sorted(m for m in ('torch', 'muscriptor', 'numpy', 'soundfile') "
                        "if sys.modules.get(m) is not None))"], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "[]"                           # nothing on CI or in the main .venv imports them


def test_parse_args():
    got = R.parse_args(_args(pairs=("a.wav", "a.json", "b.wav", "b.json")))
    assert got["weights"] == "w.safetensors" and got["device"] == "mps" and got["inputs"] == "inputs.json"
    assert got["settings"] == R.MASKED and got["pairs"] == [("a.wav", "a.json"), ("b.wav", "b.json")]
    assert R.parse_args(_args(settings=R.FREE, device="cpu"))["settings"]["instruments"] is None


@pytest.mark.parametrize("argv,match", [
    (["--device", "mps", "--settings", json.dumps(R.MASKED), "--inputs", "i.json", "a.wav", "a.json"], "--weights"),
    (_args()[:-6] + _args()[-4:], "--settings"),
    (_args(device="cuda"), "device"),
    (_args(pairs=("a.wav",)), "pairs"),
    (_args(pairs=()), "pairs"),
    (_args(settings={**R.MASKED, "temperature": 1.0}), "exactly"),
    (_args(settings={k: v for k, v in R.MASKED.items() if k != "beam_size"}), "exactly"),
    (_args(settings={**R.MASKED, "use_sampling": True}), "declared"),
    (_args(settings={**R.MASKED, "cfg_coef": 2.0}), "declared"),
    (_args(settings={**R.MASKED, "instruments": ["acoustic_guitar"]}), "declared"),
    (["--weights", "w", "--device", "mps", "--settings", "{not json", "--inputs", "i", "a", "b"], "JSON"),
])
def test_parse_args_refusals(argv, match):
    with pytest.raises(SystemExit, match=match):
        R.parse_args(argv)


def test_network_off():
    assert R.env_refusal({"HF_HUB_OFFLINE": "1"}) is None
    assert "HF_HUB_OFFLINE" in R.env_refusal({})
    assert "HF_HUB_OFFLINE" in R.env_refusal({"HF_HUB_OFFLINE": "0"})


@pytest.mark.parametrize("src", ["list:scale-c-major", "truth:P1|chords|x@10", "goat-dev:item_3"])
def test_declared_sources_pass(src):
    assert R.source_refusal(src) is None


@pytest.mark.parametrize("src", ["part:bks|unit-1", "stem:xlnoG|p1", "song:anything", "replay:p7", "P1|chords|x@10",
                                 "/Users/someone/song.wav", "list:", "goat:item_3", "truth", None, 3])
def test_every_other_source_is_refused(src):
    assert R.source_refusal(src) is not None


def test_the_manifest_guard():
    doc = {"inputs": [{"sha256": SHA, "source": "list:bend"}, {"sha256": "b" * 64, "source": "goat-dev:item_9"}]}
    src = R.manifest_sources(doc)
    assert src == {SHA: "list:bend", "b" * 64: "goat-dev:item_9"}
    assert R.input_source(SHA, src) == "list:bend"
    with pytest.raises(SystemExit, match="not in the manifest"):
        R.input_source("c" * 64, src)                          # an unlisted input: never transcribed
    for bad in ("part:bks|1", "stem:xlnoG|1", "song:x"):
        with pytest.raises(SystemExit, match="not declared material"):
            R.manifest_sources({"inputs": doc["inputs"] + [{"sha256": "d" * 64, "source": bad}]})
    with pytest.raises(SystemExit, match="two sources"):
        R.manifest_sources({"inputs": doc["inputs"] + [{"sha256": SHA, "source": "list:chords-six"}]})
    with pytest.raises(SystemExit, match="no sha256"):
        R.manifest_sources({"inputs": [{"sha256": "short", "source": "list:bend"}]})
    with pytest.raises(SystemExit, match="no input"):
        R.manifest_sources({"inputs": []})


def test_the_weights_check():
    assert R.weights_size(R.WEIGHTS["medium"][0]) == "medium" and R.weights_size(R.WEIGHTS["small"][0]) == "small"
    with pytest.raises(SystemExit, match="not a declared"):
        R.weights_size("0" * 64)


def test_start_and_end_events_paired_into_notes():
    ev = [{"type": "start", "index": 0, "pitch": 64, "time": 0.51234, "instrument": "clean_electric_guitar"},
          {"type": "start", "index": 1, "pitch": 40, "time": 0.5, "instrument": "acoustic_guitar"},
          {"type": "start", "index": 2, "pitch": 36, "time": 0.7, "instrument": "drums"},
          {"type": "end", "index": 1, "time": 1.2},
          {"type": "end", "index": 0, "time": 1.00006},
          {"type": "end", "index": 9, "time": 2.0},               # no start: counted, dropped
          {"type": "start", "index": 3, "pitch": 67, "time": 3.0, "instrument": "clean_electric_guitar"},
          {"type": "start", "index": 4, "pitch": 69, "time": 4.0, "instrument": "clean_electric_guitar"},
          {"type": "end", "index": 4, "time": 3.9}]               # an end before its start: held at the start
    notes, cnt = R.notes_from_events(ev, 10.25)
    assert notes == [{"on": 0.5, "off": 1.2, "pitch": 40, "instrument": "acoustic_guitar"},
                     {"on": 0.5123, "off": 1.0001, "pitch": 64, "instrument": "clean_electric_guitar"},
                     {"on": 3.0, "off": 10.25, "pitch": 67, "instrument": "clean_electric_guitar"},
                     {"on": 4.0, "off": 4.0, "pitch": 69, "instrument": "clean_electric_guitar"}]
    assert cnt == {"unfinished": 1, "drums": 1, "orphan_ends": 1,
                   "by_group": {"clean_electric_guitar": 3, "acoustic_guitar": 1}}
    assert R.notes_from_events([], 10.0) == ([], {"unfinished": 0, "drums": 0, "orphan_ends": 0, "by_group": {}})


def test_event_dict_reads_muscriptors_event_classes():
    class NoteStartEvent:
        def __init__(self):
            self.pitch, self.start_time, self.index, self.instrument = 60, 1.25, 7, "clean_electric_guitar"

    class NoteEndEvent:
        def __init__(self, st):
            self.end_time, self.start_event = 2.0, st

    class ProgressEvent:
        completed, total = 1, 3
    s = NoteStartEvent()
    assert R.event_dict(s) == {"type": "start", "index": 7, "pitch": 60, "time": 1.25,
                               "instrument": "clean_electric_guitar"}
    assert R.event_dict(NoteEndEvent(s)) == {"type": "end", "index": 7, "time": 2.0}
    assert R.event_dict(ProgressEvent()) is None


def _setup(tmp_path, sources):
    wav = tmp_path / "in.wav"
    wav.write_bytes(b"RIFF0000WAVEfmt ")
    man = tmp_path / "inputs.json"
    man.write_text(json.dumps({"inputs": [{"sha256": R.file_sha(wav) if s == "own" else SHA, "source": src}
                                          for s, src in sources]}))
    w = tmp_path / "w.safetensors"
    w.write_bytes(b"0" * 10)
    return ["--weights", str(w), "--device", "cpu", "--settings", json.dumps(R.MASKED), "--inputs", str(man),
            str(wav), str(tmp_path / "out.json")]


def test_main_refuses_before_any_model_loads(tmp_path, monkeypatch):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    argv = _setup(tmp_path, [("own", "list:bend")])
    with pytest.raises(SystemExit, match="HF_HUB_OFFLINE"):
        R.main(argv)
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    with pytest.raises(SystemExit, match="not in the manifest"):
        R.main(_setup(tmp_path, [("other", "list:bend")]))     # an input the manifest does not list
    with pytest.raises(SystemExit, match="not declared material"):
        R.main(_setup(tmp_path, [("own", "part:bks|1")]))       # a row part named in the manifest
    with pytest.raises(SystemExit, match="no declared size"):
        R.main(_setup(tmp_path, [("own", "goat-dev:item_9")]))  # a weights file that is not a declared one
    assert "muscriptor" not in sys.modules
