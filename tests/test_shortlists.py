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


def test_a_refused_generated_preset_loses_on_either_side_of_a_comparison():
    rows = [{"part": f"p{i}", "band": f"b{i}",
             "arms": {b: {"G4": math.inf if i < 2 else 0.5, "F4": 1.0} for b in S.BAND_SETS}}
            for i in range(3)]
    c = S.compare(rows, "G4", "F4", "recording")
    assert c["parts"] == 3 and c["closer_on"] == 1 and c["median_of_band_medians"] == S.LOSS
    c = S.compare(rows, "F4", "G4", "recording")
    assert c["parts"] == 3 and c["closer_on"] == 2 and c["median_of_band_medians"] == -S.LOSS
    both = [{"part": "p", "band": "b", "arms": {"recording": {"G1": math.inf, "G4": math.inf}}}]
    assert S.compare(both, "G4", "G1", "recording")["median_of_band_medians"] == 0.0


def test_a_comparison_passes_only_when_ten_percent_closer_on_most_parts():
    def rows(ratios, second="template+R"):
        return [{"part": f"p{i}", "band": f"b{i}",
                 "arms": {b: {"G1": r, second: 1.0} for b in S.BAND_SETS}}
                for i, r in enumerate(ratios)]

    good = S.compare(rows([0.85, 0.88, 0.89, 1.2]), "G1", "template+R", "recording")
    assert good["passes"] and good["closer_on"] == 3
    assert good["near"]                            # one part fewer would fail it
    clear = S.compare(rows([0.7] * 7 + [1.2]), "G1", "template+R", "recording")
    assert clear["passes"] and not clear["near"]
    near = S.compare(rows([0.95, 0.95, 0.95, 0.95]), "G1", "template+R", "recording")
    assert not near["passes"]                      # closer everywhere, but under 10%
    few = S.compare(rows([0.5, 0.5, 1.1, 1.1]), "G1", "template+R", "recording")
    assert not few["passes"]                       # not more than half the parts
    far = S.compare(rows([1.3] * 6 + [0.9] * 5), "G1", "template+R", "recording")
    assert not far["passes"] and not far["near"]   # a clear failure is not inconclusive
    level = S.compare(rows([1.0, 0.99, 0.98, 1.01], "house-4"), "G1", "house-4", "recording",
                      "not worse")
    assert level["passes"]                         # "not worse": median <= 0, half closer


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

    if not P.FACTORY.exists() or len(P.factory_names()) < 108:
        pytest.skip("needs the plugin's factory presets")
    sandboxes, out = tmp_path / "sandboxes", tmp_path / "run"
    sandbox = sandboxes / "song"
    (sandbox / "out" / "part-1").mkdir(parents=True)
    P.export_plugin(sandbox / "plugin", "HEAD")
    out.mkdir()
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                            text=True, check=True).stdout.strip()
    (out / "parts-map.json").write_text(json.dumps({"commit": commit, "songs": {"song": {
        "parts": {"part-1": {"part": "x-y-z"}},
        "plugin_sha256": P.tree_sha(sandbox / "plugin")}}}))
    generated = []
    for i, (amp, volume) in enumerate((("pr12", 30), ("pr12", 50), ("sw50r", 40), ("sw50r", 60)), 1):
        _spec(sandbox / "out" / "part-1" / f"G{i}.spec.json", amp, volume)
        args = ["--spec", f"out/part-1/G{i}.spec.json"]
        subprocess.run([sys.executable, str(ROOT / "scripts" / "apply_spec.py"), "--template",
                        str(ROOT / P.TEMPLATE), "--out", str(sandbox / "out" / "part-1" / f"G{i}.xml"),
                        *args], check=True, capture_output=True, cwd=sandbox)
        generated.append({"label": f"G{i}", "file": f"out/part-1/G{i}.xml", "apply_spec_args": args})
    by_amp = {}
    for name, path in sorted(P.factory_names().items()):
        by_amp.setdefault(P._amp_name(path), []).append(name)
    picks = by_amp["PR12"][:2] + by_amp["SW50R"][:2]
    result = {"generated": generated,
              "factory": [{"label": f"F{i}", "preset": n} for i, n in enumerate(picks, 1)]}

    def run(change=None, exclude=()):
        got = json.loads(json.dumps(result))
        if change:
            change(got)
        (sandbox / "out" / "result.json").write_text(json.dumps({"parts": {"part-1": got}}))
        P.collect(type("Args", (), {"sandbox_dir": sandboxes, "out_dir": out,
                                    "exclude": list(exclude)})())
        return json.loads((out / "render-manifest.json").read_text())

    manifest = run()
    assert sorted(manifest["parts"]["x-y-z"]) == sorted(S.F + S.G)
    assert set(manifest["sha256"]["x-y-z"]) == set(S.F + S.G)

    def other_spec(got):            # the recorded arguments no longer make G1
        _spec(sandbox / "out" / "part-1" / "G1.spec.json", "pr12", 31)

    def lower_case(got):            # a factory name spelled otherwise than on disk
        got["factory"][0]["preset"] = got["factory"][0]["preset"].lower()

    def one_amp(got):
        got["factory"] = [{"label": f"F{i}", "preset": n}
                          for i, n in enumerate(by_amp["PR12"][:4], 1)]

    def template_flag(got):
        got["generated"][0]["apply_spec_args"] = ["--template", "x.xml"]

    def only_reverb_differs(got):   # G2 re-made as G1 with its reverb on: alike under R
        spec = json.loads((sandbox / "out" / "part-1" / "G1.spec.json").read_text())
        spec["parameters"].append({"module": "reverb", "key": "reverbActive", "value": True})
        (sandbox / "out" / "part-1" / "G2.spec.json").write_text(json.dumps(spec))
        subprocess.run([sys.executable, str(ROOT / "scripts" / "apply_spec.py"), "--template",
                        str(ROOT / P.TEMPLATE), "--out", str(sandbox / "out" / "part-1" / "G2.xml"),
                        "--force", "--spec", "out/part-1/G2.spec.json"],
                       check=True, capture_output=True, cwd=sandbox)

    for change in (lower_case, one_amp, template_flag, only_reverb_differs, other_spec):
        with pytest.raises(SystemExit):
            run(change)
    assert run(exclude=["song"])["excluded"] == {"song": ["x-y-z"]}
    for i, (amp, volume) in ((1, ("pr12", 30)), (2, ("pr12", 50))):       # restore G1, G2
        _spec(sandbox / "out" / "part-1" / f"G{i}.spec.json", amp, volume)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "apply_spec.py"), "--template",
                        str(ROOT / P.TEMPLATE), "--out", str(sandbox / "out" / "part-1" / f"G{i}.xml"),
                        "--force", "--spec", f"out/part-1/G{i}.spec.json"],
                       check=True, capture_output=True, cwd=sandbox)
    assert run()["parts"]["x-y-z"]
    (sandbox / "plugin" / "samples" / "extra.xml").write_text("x")     # the plugin edited
    with pytest.raises(SystemExit):
        run()


def test_the_audit_flags_reads_outside_the_sandbox_and_answers_in_results(tmp_path):
    import audit_shortlist_runs as U

    sandbox = "/Users/someone/shortlist-sandboxes/song"

    def use(name, args):
        return {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": name, "input": args}]}}

    def result(text):
        return {"type": "user", "message": {"content": [
            {"type": "tool_result", "content": [{"type": "text", "text": text}]}]}}

    blocked = ["github.com", "githubusercontent.com"]
    writes = [use("Bash", {"command": f"cd {sandbox} && python plugin/scripts/apply_spec.py "
                                      f"--template plugin/samples/Example_Clean_PR12.xml "
                                      f"--spec out/part-1/G{i}.spec.json --out out/part-1/G{i}.xml"})
              for i in range(1, 5)]
    fine = [use("Bash", {"command": f"cd {sandbox} && python plugin/scripts/show.py x.xml "
                                    "--data-dir data 2>/dev/null"}),
            use("Bash", {"command": f"cd '{sandbox}' && bin/python-audio plugin/scripts/"
                                    "fingerprint.py excerpts/part-1.wav --regime mix --text"}),
            use("Bash", {"command": f"cd {sandbox} && {U.PYTHON} -c \"import json; "
                                    "print(json.load(open('out/result.json')))\""}),
            use("Read", {"file_path": f"{sandbox}/plugin/skills/generate/SKILL.md"}),
            use("Read", {"file_path": f"{sandbox}/plugin/skills/generate/../../reference/x.md"}),
            use("Write", {"file_path": f"{sandbox}/out/part-1/G1.spec.json", "content": "{}"}),
            use("WebSearch", {"query": "band song guitar amp", "blocked_domains": blocked}),
            use("WebSearch", {"query": "Morgan Amps Suite PR12", "blocked_domains": blocked}),
            result("Traceback: /Users/yoavbz/projects/neuraldsp-preset-generator/.venv/lib/x.py"),
            result("ok\nShell cwd was reset to /Users/yoavbz/projects/neuraldsp-preset-generator"
                   "/.claude/worktrees/plugin-local-install-a397e5"),
            result("<persisted-output>\nOutput too large (73.9KB). Full output saved to: /Users/"
                   "yoavbz/.claude/projects/-Users-yoavbz-projects-neuraldsp-preset-generator--x/"
                   "tool-results/b.txt"),
            use("Bash", {"command": f"cd {sandbox} && python -c \"print(m.get('a','')+'/'+k)\""}),
            use("Grep", {"pattern": "/selectedAmp", "path": f"{sandbox}/plugin/packs/morgan"}),
            use("Grep", {"pattern": "range.*0..100", "path": f"{sandbox}/plugin/reference"}),
            *writes,
            use("Read", {"file_path": f"{U.FACTORY}/Neural DSP/Blue Hotel.xml"}),
            use("Glob", {"pattern": "**/*.xml", "path": U.FACTORY}),
            use("Glob", {"pattern": f"{U.FACTORY}/**/*.xml"}),
            use("Bash", {"command": f'cd {sandbox} && python plugin/scripts/show.py '
                                    f'"{U.FACTORY}/Neural DSP/Blue Hotel.xml" --text'}),
            use("Bash", {"command": f'cd {sandbox} && ls "{U.FACTORY}/Neural DSP"'}),
            use("Bash", {"command": f"cd {sandbox} && {U.PYTHON} -c \"print(open('{U.FACTORY}"
                                    "/Artists/Mark Johnston/It's Boosted.xml').read())\""})]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in fine))
    assert U.audit(path, sandbox) == []
    bad = [use("Bash", {"command": "cat docs/reach-sets.json"}),
           use("Bash", {"command": f"cd {sandbox} && cat ~/ndsp-presets/runs/kill/amp-reach.json"}),
           use("Bash", {"command": f"cd {sandbox} && ls .."}),
           use("Bash", {"command": f"cd {sandbox} && ls ../../"}),
           use("Bash", {"command": f"cd {sandbox} && cd - && cat docs/x.md"}),
           use("Bash", {"command": f"cd {sandbox} && find / -name '*.wav'"}),
           use("Bash", {"command": f"cd {sandbox} && ls $HOME"}),
           use("Bash", {"command": f"cd {sandbox} && curl -O https://example.com/stems.zip"}),
           use("Bash", {"command": f"cd {sandbox} && python -c \"open('/Users/x/data.json')\""}),
           use("Bash", {"command": f"cd {sandbox} && python -c \"open('../../x/data.json')\""}),
           use("Grep", {"pattern": "PR12"}),
           use("Glob", {"pattern": "../../**/*.json", "path": sandbox}),
           use("Read", {"file_path": f"{sandbox}/../../ndsp-presets/runs/x.json"}),
           use("Read", {"file_path": f"{U.FACTORY}/User/mine.xml"}),
           use("Write", {"file_path": "/tmp/spec.json", "content": "{}"}),
           use("WebSearch", {"query": "band song amp"}),
           use("Bash", {"command": "ls"}),
           use("Bash", {"command": f"cd {sandbox} && python -c \"import os; print(os.listdir('/'))\""}),
           use("Bash", {"command": f"cd {sandbox} && python -c \"import pathlib; "
                                   "print(list(pathlib.Path.home().iterdir()))\""}),
           use("Bash", {"command": f"cd {sandbox} && cat out/x >/Users/x/y"}),
           use("Bash", {"command": f"cd {sandbox} && ls '{U.FACTORY.lower()}/user'"}),
           use("Bash", {"command": f"cd {sandbox} && for i in 1 2; do ls out/G$i.xml; done"}),
           use("WebFetch", {"url": "https://github.com/YoavBZ/neuraldsp-preset-generator"}),
           use("Skill", {"skill": "neuraldsp-preset-generator:generate"}),
           result("see github.com/YoavBZ/neuraldsp-preset-generator for amp-reach results")]
    for entry in bad:
        path.write_text(json.dumps(entry))
        assert U.audit(path, sandbox), entry
    harmless = "bash uses a harmless $ (a regex anchor or a loop's own variable)"
    for command in (f'cd {sandbox} && for f in G1 G2; do echo "== $f"; done',
                    f'cd {sandbox} && python plugin/scripts/show.py out/x.xml | grep -E "Amp$|Gain"'):
        path.write_text(json.dumps(use("Bash", {"command": command})))
        assert [k for k, _, _ in U.audit(path, sandbox)] == [harmless], command
    for command in (f"cd {sandbox} && ls $HOME", f"cd {sandbox} && for f in a; do cat $g; done",
                    f"cd {sandbox} && ls ${{HOME}}"):
        path.write_text(json.dumps(use("Bash", {"command": command})))
        assert "bash uses shell expansion" in [k for k, _, _ in U.audit(path, sandbox)], command
    order = ["factory opened before every G was written"]
    early = [use("Read", {"file_path": f"{U.FACTORY}/Neural DSP/Blue Hotel.xml"}), *writes]
    path.write_text("\n".join(json.dumps(e) for e in early))
    assert [k for k, _, _ in U.audit(path, sandbox)] == order
    late = [*writes[:1], use("Read", {"file_path": f"{U.FACTORY}/x.xml"}), *writes[1:]]
    path.write_text("\n".join(json.dumps(e) for e in late))
    assert [k for k, _, _ in U.audit(path, sandbox)] == order
    chained = [use("Bash", {"command": f"cd {sandbox} && python plugin/scripts/apply_spec.py "
                                       f"--spec s.json --dry-run && python plugin/scripts/"
                                       f"apply_spec.py --spec s.json --out out/part-1/G{i}.xml"})
               for i in range(1, 5)] + [use("Read", {"file_path": f"{U.FACTORY}/x.xml"})]
    path.write_text("\n".join(json.dumps(e) for e in chained))
    assert U.audit(path, sandbox) == []
    planning = [use("TodoWrite", {"todos": [{"content": f"then F1-F4 from {U.FACTORY}"}]}), *writes,
                use("Read", {"file_path": f"{U.FACTORY}/x.xml"})]
    path.write_text("\n".join(json.dumps(e) for e in planning))
    assert U.audit(path, sandbox) == []
    repo = "/Users/someone/projects/neuraldsp-preset-generator"
    no_cd = {"type": "assistant", "cwd": repo, "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "cat docs/amp-reach-results.md"}}]}}
    path.write_text(json.dumps(no_cd))
    assert "bash path outside the sandbox: docs/amp-reach-results.md" in [
        k for k, _, _ in U.audit(path, sandbox)]
