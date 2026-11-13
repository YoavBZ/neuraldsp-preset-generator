"""The model path's product wrapper (`scripts/model_preset.py`): writing the picked settings onto the start, its
refusals, and the stages' arguments. The stages themselves need the model's data and are smoke-tested, not here."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import model_preset as M  # noqa: E402
from format.parser import parse_file  # noqa: E402
from format.structured import build  # noqa: E402

EXAMPLE = REPO_ROOT / "samples" / "Example_Clean_PR12.xml"


def result(**settings):
    return {"amp": "pr12", "cls": "clean", "select": 1, "settings": settings,
            "distances": {"pr12": 0.1, "sw50r": 0.2, "ac20": 0.3},
            "output_gain": {"from": 5.0, "to": 7.3, "wanted": 2.3, "shortfall": 0.0}}


def values(path):
    return {k: p.value for k, p in build(parse_file(str(path))).by_path.items()}


def test_writes_the_stored_values_and_nothing_else(tmp_path):
    out = tmp_path / "m.xml"
    changes = M.write_preset(result(**{"parameters/outputGain": "7.3", "parameters/gateActive": "true"}), out,
                             "Model test", EXAMPLE)
    assert changes == [("parameters/outputGain", "5", "7.3")]          # gateActive already true: no change
    before, after = values(EXAMPLE), values(out)
    assert after[("parameters", "outputGain")] == "7.3"
    diff = {k for k in before if before[k] != after[k]}
    name_keys = {("", "name"), ("", "presetNameProp")}
    assert diff - name_keys == {("parameters", "outputGain")}


def test_refuses_another_amp(tmp_path):
    r = result(**{"parameters/outputGain": "7.3"})
    r["select"] = 2
    with pytest.raises(SystemExit):
        M.write_preset(r, tmp_path / "m.xml", None, EXAMPLE)


def test_refuses_a_key_the_start_lacks(tmp_path):
    with pytest.raises(SystemExit):
        M.write_preset(result(**{"parameters/noSuchKnob": "1"}), tmp_path / "m.xml", None, EXAMPLE)


def test_stage_arguments():
    a = argparse.Namespace(song="~/s.wav", work=pathlib.Path("/w"), start=12.5, part=None, part_from="research",
                           cls="crunch")
    assert M.stage_args("separate", a)[1:] == ["--out", "/w", "--start", "12.5"]
    assert M.stage_args("answers", a) == ["/w", "--cls", "crunch"]
    assert M.stage_args("render", a) == ["/w"] and M.stage_args("pick", a) == ["/w"]
    a.start = None
    assert "--start" not in M.stage_args("separate", a) and "--part" not in M.stage_args("separate", a)
    a.part, a.part_from = [30.0, 60.0], "the user"
    assert M.stage_args("separate", a)[1:] == ["--out", "/w", "--part", "30.0", "60.0", "--part-from", "the user"]


def test_every_start_names_a_class_and_amp():
    from learn.knob_ceiling import START

    assert set(START) == {"clean", "crunch"} and all(set(v) == {"pr12", "sw50r", "ac20"} for v in START.values())


def test_write_only_from_a_work_dir(tmp_path, monkeypatch):
    work = tmp_path / "w"
    work.mkdir()
    (work / "preset.json").write_text(json.dumps(result(**{"parameters/outputGain": "7.3"})))
    (work / "window.json").write_text(json.dumps({"song": "s.wav", "start_s": 30.0, "chosen_by": "exposure"}))
    monkeypatch.setattr(M, "template_for", lambda amp, cls: EXAMPLE)
    out = tmp_path / "m.xml"
    M.run(M.build_parser().parse_args(["--work", str(work), "--out", str(out), "--write-only"]))
    assert values(out)[("parameters", "outputGain")] == "7.3"


def test_refuses_to_overwrite(tmp_path):
    out = tmp_path / "m.xml"
    out.write_text("x")
    p = subprocess.run([sys.executable, str(REPO_ROOT / "scripts/model_preset.py"), "--work", str(tmp_path),
                        "--out", str(out), "--write-only"], capture_output=True, text=True)
    assert p.returncode != 0 and "already exists" in p.stderr


def test_the_documented_command_parses():
    """The reference's command is skipped by the skills' command test (it needs the model), so its flags are checked
    here: an agent copies it verbatim."""
    import re
    import shlex

    doc = (REPO_ROOT / "reference/model-path.md").read_text()
    block = re.search(r"```bash\n(python [^`]*?model_preset\.py.*?)```", doc, re.S).group(1)
    argv = shlex.split(block.replace("\\\n", " "))[2:]
    args = M.build_parser().parse_args([a.replace("PART_START", "30").replace("PART_END", "60") for a in argv])
    assert args.song and args.cls == "clean" and args.part == [30.0, 60.0] and args.part_from == "the user"
    assert args.start is None and args.name


def test_relative_paths_resolve_before_the_stages(tmp_path, monkeypatch):
    """The stages run from the plugin root, so a relative --work or --song must reach them absolute."""
    monkeypatch.chdir(tmp_path)
    seen = {}
    monkeypatch.setattr(M, "ADOPTED", EXAMPLE)                       # any existing file: the data is present
    monkeypatch.setattr(M, "run_stages", lambda a: seen.update(work=a.work, song=a.song) or (_ for _ in ()).throw(
        SystemExit(0)))
    with pytest.raises(SystemExit):
        M.run(M.build_parser().parse_args(["--song", "s.wav", "--cls", "clean", "--work", "w", "--out", "o.xml"]))
    assert seen["work"] == (tmp_path / "w").resolve() and seen["song"] == (tmp_path / "s.wav").resolve()


def delay_rec(on, amp="pr12"):
    return {"on": on, "vote": 0.8 if on else 0.2, "threshold": 0.7, "time_ms": 380.0, "time_from": "halves",
            "mix": 0.3, "feedback": 0.3, "mix_feedback_from": M.DELAY_DEFAULT_FROM, "amp": amp,
            "settings": {"delay/delayActive": "true", "delay/delaySync": "0", "delay/delayTime": "380.0",
                         "delay/delayMix": "0.300", "delay/delayFeedback": "0.300"} if on else {}}


def work_dir(tmp_path, delay=None):
    work = tmp_path / "w"
    work.mkdir()
    (work / "preset.json").write_text(json.dumps(result(**{"parameters/outputGain": "7.3"})))
    (work / "window.json").write_text(json.dumps({"song": "s.wav", "start_s": 30.0, "chosen_by": "exposure"}))
    if delay is not None:
        (work / "delay.json").write_text(json.dumps(delay))
    return work


@pytest.mark.parametrize("on", [True, False])
def test_the_delay_reader_writes_its_delay_only_when_on(tmp_path, monkeypatch, on):
    work = work_dir(tmp_path, delay_rec(on))
    monkeypatch.setattr(M, "template_for", lambda amp, cls: EXAMPLE)
    out = tmp_path / "m.xml"
    M.run(M.build_parser().parse_args(["--work", str(work), "--out", str(out), "--write-only", "--delay-reader"]))
    v, before = values(out), values(EXAMPLE)
    keys = [("delay", k) for k in ("delayActive", "delaySync", "delayTime", "delayMix", "delayFeedback")]
    if on:
        assert [v[k] for k in keys] == ["true", "0", "380.0", "0.300", "0.300"]
    else:
        assert [v[k] for k in keys] == [before[k] for k in keys]


def test_without_the_flag_the_delay_file_is_ignored(tmp_path, monkeypatch):
    work = work_dir(tmp_path, delay_rec(True))
    monkeypatch.setattr(M, "template_for", lambda amp, cls: EXAMPLE)
    out = tmp_path / "m.xml"
    M.run(M.build_parser().parse_args(["--work", str(work), "--out", str(out), "--write-only"]))
    assert values(out)[("delay", "delayActive")] == values(EXAMPLE)[("delay", "delayActive")]


def test_the_delay_reader_refusals(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "template_for", lambda amp, cls: EXAMPLE)
    parse = M.build_parser().parse_args
    work = work_dir(tmp_path, delay_rec(True, amp="ac20"))
    for extra in (["--delay-reader"],                                   # read for another amp
                  ["--delay-reader", "--delay-mix", "0.2"],             # a lone mix
                  ["--delay-mix", "0.2", "--delay-feedback", "0.2"],    # mix and feedback without the reader
                  ["--delay-reader", "--delay-mix", "30", "--delay-feedback", "0.3"]):   # a percent, not 0-1
        with pytest.raises(SystemExit):
            M.run(parse(["--work", str(work), "--out", str(tmp_path / "m.xml"), "--write-only", *extra]))


def test_the_delay_stage_arguments():
    a = argparse.Namespace(work=pathlib.Path("/w"), delay_mix=0.25, delay_feedback=0.4, delay_source="research")
    assert M.delay_args(a) == ["/w", "--mix", "0.25", "--feedback", "0.4", "--source", "research"]
    a.delay_mix = a.delay_feedback = None
    assert M.delay_args(a) == ["/w"]


def test_a_delay_read_with_another_pair_is_refused_on_write_only(tmp_path, monkeypatch):
    """The stored delay.json holds the default 0.30/0.30: asking for research's pair must not write 0.30 silently, and
    a delay read with research's pair must not pass as the default."""
    monkeypatch.setattr(M, "template_for", lambda amp, cls: EXAMPLE)
    parse = M.build_parser().parse_args
    work = work_dir(tmp_path, delay_rec(True))
    with pytest.raises(SystemExit):
        M.run(parse(["--work", str(work), "--out", str(tmp_path / "a.xml"), "--write-only", "--delay-reader",
                     "--delay-mix", "0.5", "--delay-feedback", "0.5"]))
    M.run(parse(["--work", str(work), "--out", str(tmp_path / "b.xml"), "--write-only", "--delay-reader",
                 "--delay-mix", "0.3", "--delay-feedback", "0.3"]))                       # the same pair: written
    d = delay_rec(True)
    d["mix_feedback_from"] = "the song research"
    (work / "delay.json").write_text(json.dumps(d))
    with pytest.raises(SystemExit):
        M.run(parse(["--work", str(work), "--out", str(tmp_path / "c.xml"), "--write-only", "--delay-reader"]))


def test_part_refusals(tmp_path):
    parse = M.build_parser().parse_args
    base = ["--song", "s.wav", "--cls", "clean", "--work", str(tmp_path / "w"), "--out", str(tmp_path / "o.xml")]
    for extra in (["--part", "30", "40"],                          # 10 s: no room for a window clear of the edges
                  ["--part", "30", "60", "--start", "35"]):         # both
        with pytest.raises(SystemExit):
            M.run(parse(base + extra))


def test_a_resumed_run_must_have_the_same_part(tmp_path, monkeypatch):
    work = tmp_path / "w"
    work.mkdir()
    song = (tmp_path / "s.wav").resolve()
    (work / "window.json").write_text(json.dumps({"song": str(song), "start_s": 40.0, "part_s": [30.0, 60.0],
                                                  "part_from": "research", "chosen_by": "selector"}))
    monkeypatch.setattr(M, "interpreters", lambda: {"msst": EXAMPLE, "torch": EXAMPLE, "main": EXAMPLE})
    a = M.build_parser().parse_args(["--song", str(song), "--cls", "clean", "--work", str(work), "--out", "o.xml",
                                     "--part", "35", "60"])
    a.work, a.song = work, song
    with pytest.raises(SystemExit):
        M.run_stages(a)


def test_the_window_line():
    assert M.window_how({"chosen_by": "given"}) == "given"
    assert "30.0-60.0" in M.window_how({"chosen_by": "selector", "part_s": [30, 60], "part_from": "the user"})
    assert "whole song" in M.window_how({"chosen_by": "selector", "part_s": [0, 200],
                                         "part_from": "the whole song (no part named)"})
