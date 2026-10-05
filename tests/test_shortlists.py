"""The song-only shortlist measurement (`docs/song-only-shortlist-plan.md`), the
audition page and the DI library."""

from __future__ import annotations

import itertools
import json
import math
import pathlib
import random
import statistics
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import audition as A  # noqa: E402
import build_di_library as L  # noqa: E402
import score_shortlists as S  # noqa: E402


def _d(values):
    return {f"{c}|{h}|{b}": v[i] for c, v in values.items()
            for i, h in enumerate(("A", "B", "full")) for b in S.BAND_SETS}


def test_one_preset_is_the_mean_of_its_halves_and_a_list_is_picked_on_the_other_half():
    d = _d({"x": (1.0, 3.0, 2.0), "y": (2.0, 1.0, 1.5), "z": (4.0, 4.0, 4.0)})
    assert S.one(d, "x", "recording") == 2.0
    # chosen on A (x) scored on B (3.0); chosen on B (y) scored on A (2.0)
    assert S.best(d, ["x", "y", "z"], "recording") == 2.5
    assert S.best(d, ["z"], "recording") == 4.0
    assert S.best({}, ["x"], "recording") is None


def test_random_four_is_the_median_of_lists_drawn_at_random():
    pytest.importorskip("numpy", reason="needs the analysis extra")
    rng = random.Random(3)
    factory = [f"pr12:factory:{i}" for i in range(7)]
    d = _d({c: (rng.uniform(1, 3), rng.uniform(1, 3), 2.0) for c in factory})
    exact = statistics.median(S.best(d, list(subset), "recording")
                              for subset in itertools.combinations(factory, 4))
    got = S.random_median(d, factory, "recording", 4, "seed")
    assert abs(got - exact) < 0.05
    assert got == S.random_median(d, factory, "recording", 4, "seed")


def test_the_house_list_is_chosen_without_the_held_out_band():
    # Preset "a" is best on band x's parts, "b" on band y's: each band's house list must
    # lead with the other band's winner.
    factory = ["a", "b", "c", "d", "e"]
    def part(winner):
        return _d({c: (1.0, 1.0, 1.0) if c == winner else (2.0, 2.0, 2.0) for c in factory})
    dist = {"x1": part("a"), "x2": part("a"), "y1": part("b"), "y2": part("b")}
    band_of = {"x1": "x", "x2": "x", "y1": "y", "y2": "y"}
    random1 = {p: 2.0 for p in dist}
    lists = S.house_lists(dist, list(dist), band_of, factory, "recording", random1)
    assert lists["x"][0] == "b" and lists["y"][0] == "a"
    assert all(len(set(v)) == 4 for v in lists.values())


def test_a_refused_generated_preset_counts_as_a_loss():
    rows = [{"part": f"p{i}", "band": f"b{i}",
             "arms": {b: {"G1": math.inf if i < 2 else 0.5, "template+R": 1.0}
                      for b in S.BAND_SETS}} for i in range(3)]
    c = S.compare(rows, "G1", "template+R", "recording")
    assert c["parts"] == 3 and c["closer_on"] == 1 and c["median_of_band_medians"] == S.LOSS
    assert not c["passes"]


def test_a_comparison_passes_only_when_ten_percent_closer_on_most_parts():
    def rows(ratios):
        return [{"part": f"p{i}", "band": f"b{i}",
                 "arms": {b: {"G1": r, "template+R": 1.0} for b in S.BAND_SETS}}
                for i, r in enumerate(ratios)]

    good = S.compare(rows([0.85, 0.88, 0.89, 1.2]), "G1", "template+R", "recording")
    assert good["passes"] and good["closer_on"] == 3
    assert good["near"]                            # 3 of 4 is one part from the line
    clear = S.compare(rows([0.7] * 7 + [1.2]), "G1", "template+R", "recording")
    assert clear["passes"] and not clear["near"]
    near = S.compare(rows([0.95, 0.95, 0.95, 0.95]), "G1", "template+R", "recording")
    assert not near["passes"]                      # closer everywhere, but under 10%
    few = S.compare(rows([0.5, 0.5, 1.1, 1.1]), "G1", "template+R", "recording")
    assert not few["passes"]                       # not more than half the parts


def test_the_render_canary_tolerance_and_drift_are_strict():
    assert S.REPRO == 0.01 and S.DRIFT_DB == 0.1


def test_audition_clips_meet_the_loudness_target_without_passing_the_ceiling():
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    pytest.importorskip("pyloudnorm", reason="needs the analysis extra")
    import pyloudnorm

    rate = 48000
    t = np.arange(rate * 3) / rate
    quiet = (0.01 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    clip, gain = A.matched(quiet, rate)
    assert gain > 0
    assert abs(pyloudnorm.Meter(rate).integrated_loudness(clip) - A.TARGET_LUFS) < 0.1
    spiky = quiet.copy()
    spiky[::rate // 4] = 0.9                       # peaks the loudness match would clip
    clip, _ = A.matched(spiky, rate)
    assert 20 * np.log10(np.abs(clip).max()) <= A.CEILING_DB + 1e-3


def test_the_audition_page_lists_every_candidate_for_every_riff_and_escapes_text():
    record = {"song": {"path": "/x/My <Song>.mp3", "start_s": 83.0, "seconds": 12.0,
                       "file": "song.wav"},
              "dis": [{"id": "riff-1", "name": "dark"}, {"id": "riff-2", "name": "bright"}],
              "candidates": [{"id": c, "amp": "PR12", "note": "a <b> note",
                              "renders": {"riff-1": f"{c}-riff-1.wav", "riff-2": f"{c}-riff-2.wav"}}
                             for c in "AB"]}
    page = A.page(record)
    for c in "AB":
        for r in ("riff-1", "riff-2"):
            assert f'src="{c}-{r}.wav"' in page
    assert "My &lt;Song&gt;.mp3" in page and "a &lt;b&gt; note" in page
    assert "1:23.0" in page and "1:35.0" in page


def test_riffs_are_placed_in_thirds_by_rank():
    words = L.thirds({f"r{i}": i for i in range(6)}, ("dark", "middle", "bright"))
    assert [words[f"r{i}"] for i in range(6)] == ["dark", "dark", "middle", "middle",
                                                  "bright", "bright"]


def test_a_riff_description_counts_plucked_notes():
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    rate = 48000
    out = np.zeros(rate * 4)
    t = np.arange(rate // 2) / rate
    note = np.sin(2 * np.pi * 196 * t) * np.exp(-6 * t)
    for k in range(8):                             # two plucks a second
        out[k * rate // 2:(k + 1) * rate // 2] += note
    playing, notes, brightness = L.describe(out, rate)
    assert playing > 0.5 and 1.5 <= notes <= 2.5 and 150 < brightness < 600


def _spec(path, amp, volume):
    path.write_text(json.dumps({"name": f"{amp} {volume}", "parameters": [
        {"module": "", "key": "selectedAmp", "value": amp.upper()},
        {"module": f"{amp}Amp", "key": f"{amp}Volume", "value": volume}]}))


def test_collect_remakes_each_generated_preset_and_refuses_what_breaks_the_brief(tmp_path):
    import subprocess

    import prepare_shortlist_runs as P

    sandboxes, out = tmp_path / "sandboxes", tmp_path / "run"
    sandbox = sandboxes / "song"
    (sandbox / "out" / "part-1").mkdir(parents=True)
    (sandbox / "plugin").symlink_to(ROOT)
    out.mkdir()
    (out / "parts-map.json").write_text(json.dumps(
        {"songs": {"song": {"part-1": {"part": "x-y-z"}}}}))
    generated = []
    for i, (amp, volume) in enumerate((("pr12", 30), ("pr12", 50), ("sw50r", 40), ("sw50r", 60)), 1):
        spec = sandbox / "out" / "part-1" / f"G{i}.spec.json"
        _spec(spec, amp, volume)
        args = ["--spec", f"out/part-1/G{i}.spec.json"]
        subprocess.run([sys.executable, str(ROOT / "scripts" / "apply_spec.py"), "--template",
                        str(ROOT / P.TEMPLATE), "--out", str(sandbox / "out" / "part-1" / f"G{i}.xml"),
                        *args], check=True, capture_output=True, cwd=sandbox)
        generated.append({"label": f"G{i}", "file": f"out/part-1/G{i}.xml", "apply_spec_args": args})
    factory = sorted(P.factory_names()) if P.FACTORY.exists() else []
    if len(factory) < 108:
        pytest.skip("needs the plugin's factory presets")
    by_amp = {}
    for name in factory:
        by_amp.setdefault(P._amp_name(P.factory_names()[name]), []).append(name)
    picks = by_amp["PR12"][:2] + by_amp["SW50R"][:2]
    result = {"generated": generated,
              "factory": [{"label": f"F{i}", "preset": n} for i, n in enumerate(picks, 1)]}

    def run(change=None):
        got = json.loads(json.dumps(result))
        if change:
            change(got)
        (sandbox / "out" / "result.json").write_text(json.dumps({"parts": {"part-1": got}}))
        P.collect(type("Args", (), {"sandbox_dir": sandboxes, "out_dir": out})())
        return json.loads((out / "render-manifest.json").read_text())

    assert sorted(run()["parts"]["x-y-z"]) == sorted(S.F + S.G)

    def other_spec(got):            # the recorded arguments no longer make G1
        _spec(sandbox / "out" / "part-1" / "G1.spec.json", "pr12", 31)

    def lower_case(got):            # a factory name spelled otherwise than on disk
        got["factory"][0]["preset"] = got["factory"][0]["preset"].lower()

    def one_amp(got):
        got["factory"] = [{"label": f"F{i}", "preset": n}
                          for i, n in enumerate(by_amp["PR12"][:4], 1)]

    def template_flag(got):
        got["generated"][0]["apply_spec_args"] = ["--template", "x.xml"]

    for change in (lower_case, one_amp, template_flag, other_spec):
        with pytest.raises(SystemExit):
            run(change)


def test_the_audit_flags_reads_outside_the_sandbox_and_answers_in_results(tmp_path):
    import audit_shortlist_runs as U

    sandbox = "/Users/someone/shortlist-sandboxes/song"

    def use(name, args):
        return {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": name, "input": args}]}}

    def result(text):
        return {"type": "user", "message": {"content": [
            {"type": "tool_result", "content": [{"type": "text", "text": text}]}]}}

    fine = [use("Bash", {"command": f"cd {sandbox} && python plugin/scripts/show.py x.xml"}),
            use("Bash", {"command": f"cd '{sandbox}' && {U.PYTHON} plugin/scripts/fingerprint.py "
                                    "excerpts/part-1.wav --regime mix"}),
            use("Read", {"file_path": f"{sandbox}/plugin/skills/generate/SKILL.md"}),
            use("Read", {"file_path": f"{U.FACTORY}/Neural DSP/Blue Hotel.xml"}),
            use("Glob", {"pattern": "*.xml", "path": U.FACTORY}),
            use("WebSearch", {"query": "band song guitar amp"}),
            result("Traceback: /Users/yoavbz/projects/neuraldsp-preset-generator/.venv/lib/x.py")]
    bad = [use("Bash", {"command": "cat docs/reach-sets.json"}),
           use("Bash", {"command": f"cd {sandbox} && cat ~/ndsp-presets/runs/kill/amp-reach.json"}),
           use("Bash", {"command": f"cd {sandbox} && ls ../../"}),
           use("Grep", {"pattern": "PR12"}),
           use("Read", {"file_path": "/Users/someone/projects/neuraldsp-preset-generator/docs/x.md"}),
           use("WebFetch", {"url": "https://github.com/YoavBZ/neuraldsp-preset-generator"}),
           use("Skill", {"skill": "neuraldsp-preset-generator:generate"}),
           result("see github.com/YoavBZ/neuraldsp-preset-generator for amp-reach results")]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in fine))
    assert U.audit(path, sandbox) == []
    for entry in bad:
        path.write_text(json.dumps(entry))
        assert U.audit(path, sandbox), entry
