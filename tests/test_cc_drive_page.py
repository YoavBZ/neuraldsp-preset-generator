import hashlib
import json

import pytest

from learn import audibility_measure as AM
from learn import build_ear_page as BEP
from learn import cc_audibility as CA
from learn import cc_drive_page as D
from learn import full_space as F
from learn import local_objective as LO

PLAYING = {"drums": -20.0, "bass": -22.0, "all": -15.0}


def _x(i=1, ratio=-3.0, mode="factory"):
    return {"i": i, "draw": {"ratio_db": ratio, "vocals_drawn": False}, "others": [], "amp_tracks": [],
            "band": "BKS", "mode": mode, "base": "crunch", "cls": "crunch",
            "stems": {"v": ["01_Kick.wav", "09_Bass.wav"], "n": ["01_Kick.wav", "09_Bass.wav"]}}


def test_the_pedals_and_the_checks():
    assert {e: v[0] for e, v in D.DRIVES.items()} == {"drive1": "drive1/drive1Active", "drive2": "drive2/drive2Active"}
    assert all(v[0] in F.SW for v in D.DRIVES.values())
    assert set(D.LABEL) >= set(D.DRIVES) | {e for _, e in D.CHECKS}
    assert D.CHECKS == ((800877, "reverb"), (802682, "sw50r spring"))           # step 4's loudest of each
    assert len({D.SEED, D.PAGE_SEED, CA.SEED, CA.PAGE_SEED, AM.SEED, AM.PAGE_SEED}) == 6
    assert D.N_MAX == 30 and D.NEAR == 3 and D.CATCH == 3 and D.XFADE_S == 0.01


def test_runaway_targets_are_out_before_step_4s_rule():
    assert len(D.RUNAWAY) == 64 and 900215 in D.RUNAWAY                       # the 2026-10-30 scan, clear + likely
    assert D.qualifies(_x(i=900215), lambda _: PLAYING) == (False, "a runaway-flagged target")
    assert D.qualifies(_x(i=1), lambda _: PLAYING) == (True, None)
    assert D.qualifies(_x(i=1, ratio=-9.0), lambda _: PLAYING)[1] == "not exposed"      # step 4's rule otherwise
    assert all(i not in D.RUNAWAY for i, _ in D.CHECKS)


def test_drives_on_reads_the_masked_switches():
    s, m = [0.0] * len(F.SW), [1.0] * len(F.SW)
    s[F.SW.index("drive2/drive2Active")] = 1.0
    assert D.drives_on([None, None, s, m]) == ["drive2"]
    m[F.SW.index("drive2/drive2Active")] = 0.0                                 # masked out: not counted
    assert D.drives_on([None, None, s, m]) == []


def test_step_4s_r_on_is_reused_and_its_repeat_kept():
    chosen = {"drive1": [1, 2], "drive2": [2]}
    group = {1: ("s1", "pr12"), 2: ("s2", "ac20")}
    jobs, reps = D.jobs_for(chosen, group, {1})
    got = [(j["i"], j["what"]) for j in jobs]
    assert (1, AM.ON) not in got and (2, AM.ON) in got                          # 1's r_on' is step 4's
    assert (1, AM.REPEAT) in got and (2, AM.REPEAT) in got and len(reps) == 2
    assert sorted(got) == sorted([(1, AM.REPEAT), (1, "drive1"), (2, AM.ON), (2, AM.REPEAT), (2, "drive1"),
                                  (2, "drive2")])
    assert got.index((2, AM.ON)) < got.index((2, AM.REPEAT)) < got.index((2, "drive1"))


def test_files_resolve_to_step_4_for_reused_renders(tmp_path):
    flac = D.flac_for({1})
    assert flac(tmp_path, 1, AM.ON) == CA.flac_of(tmp_path, 1, AM.ON)
    assert flac(tmp_path, 2, AM.ON) == D.flac_of(tmp_path, 2, AM.ON)
    assert flac(tmp_path, 1, AM.REPEAT) == D.flac_of(tmp_path, 1, AM.REPEAT)
    assert flac(tmp_path, 1, "drive1") == D.flac_of(tmp_path, 1, "drive1")
    assert flac(tmp_path, 1, "reverb") == CA.flac_of(tmp_path, 1, "reverb")      # a check's off render
    assert D.out_dir(tmp_path) != CA.out_dir(tmp_path)


def test_the_page_rule():
    measured = [{"i": 100 + k, "effect": e, "a_e": a} for k, (e, a) in enumerate(
        [("drive1", a) for a in (0.001, 0.002, 0.003, 0.004, 0.006, 0.007, 0.02, 0.03, 0.5)]
        + [("drive2", a) for a in (0.004, 0.01, 0.2)])]
    items = D.items_of(measured, [(800877, "reverb", 0.64), (802682, "sw50r spring", 0.03)])
    kinds = [it["kind"] for it in items]
    d1 = [it for it in items if it["effect"] == "drive1" and it["kind"] != "same"]
    assert len(d1) == 7                                                         # 3 below, 3 above, the loudest
    assert max(it["a_e"] for it in d1) == 0.5
    same = [it for it in items if it["kind"] == "same"]
    assert len(same) == 5 and len({it["i"] for it in same}) == 5                # 3 drive catches, 2 under check titles
    assert {(it["i"], it["effect"]) for it in same} >= {(800877, "reverb"), (802682, "sw50r spring")}
    assert kinds.count("check (step 4's loudest)") == 2
    assert len(items) == 7 + 3 + 3 + 2 + 2                                     # drive2 has 3 measured pairs here
    assert len({it["id"] for it in items}) == len(items) and all(it["first"] in ("on", "off") for it in items)
    assert items == D.items_of(measured, [(800877, "reverb", 0.64), (802682, "sw50r spring", 0.03)])   # seeded


def test_the_ab_page_keeps_the_ear_pages_answers_and_export():
    items = [{"id": "aud-x", "effect": "drive1", "i": 1, "kind": "anchor (loudest)", "a_e": 0.1, "first": "on"},
             {"id": "aud-y", "effect": "reverb", "i": 2, "kind": "check (step 4's loudest)", "a_e": 0.6, "first": "off"}]
    clips = {f"{it['id']}-{k}": "AAAA" for it in items for k in (1, 2)}
    page = D.page_html(items, clips, "b123")
    js = page.split("<script>")[-1]
    assert BEP.JS_HEAD in js and BEP.JS_ANSWERS in js and BEP.JS_PLAYER not in js
    assert "<audio" not in page                                                 # Web Audio, not one player element
    for need in ("async function play(", "function stop()", "s.loop = true", "linearRampToValueAtTime",
                 "const XF = 0.01;", 'k === "s"', "decodeAudioData"):
        assert need in js
    assert page.count('class="play main"') == 2 and page.count('class="ab"') == 4 and page.count('class="sw"') == 2
    data = json.loads(page.split('<script id="data" type="application/json">')[1].split("</script>")[0])
    assert data["page"] == D.PAGE_NAME and data["build"] == "b123"
    assert [i["title"] for i in data["items"]] == ["Listen for: drive pedal 1", "Listen for: reverb"]
    assert set(data["secs"].values()) == {D.ITEM_S}


def test_the_ear_pages_own_script_is_unchanged():
    assert BEP.JS == BEP.JS_HEAD + BEP.JS_PLAYER + BEP.JS_ANSWERS
    assert hashlib.sha256(BEP.JS.encode()).hexdigest() == (
        "5c91f94b901708c4cd007eb73115096a73052f82379942632af43c07fd7f198e")


def test_renders_are_in_the_machine_cap():
    assert LO.is_render_process("/x/bin/python3 -u -m learn.cc_drive_page render --shard 0/3")
    assert not LO.is_render_process("/x/bin/python3 -m learn.cc_drive_page plan")


def test_runs_refuse_without_the_declaration(tmp_path, monkeypatch):
    led = tmp_path / "ledger.json"
    led.write_text(json.dumps({"tests": [{"test_id": D.LEDGER_ID}]}))
    assert not D.ledger_declared(led)
    led.write_text(json.dumps({"tests": [{"test_id": D.LEDGER_ID, D.LEDGER_KEY: f"{D.LEDGER_MARK} (...)"}]}))
    assert D.ledger_declared(led)
    monkeypatch.setattr(D, "ledger_declared", lambda path=None: False)
    for cmd in ("plan", "measure", "page"):
        with pytest.raises(SystemExit, match="runs refuse"):
            D.main([cmd])
    with pytest.raises(SystemExit, match="runs refuse"):
        D.main(["render", "--shard", "0/3"])


def test_the_ledger_declares_the_page_before_any_render():
    assert D.ledger_declared()


def _render(tmp_path, monkeypatch, step4_sha):
    """cmd_render with a fake plugin: example 1's r_on' is step 4's (sha `step4_sha`), so only its repeat and its
    drive1-off render are rendered here."""
    np = pytest.importorskip("numpy")
    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    on = {("drive1", "drive1Active"): "true", ("pr12Amp", "pr12Gain"): "0.4"}
    js = F.SW.index(D.DRIVES["drive1"][0])
    jobs = [{"i": 1, "section": "s1", "amp": "pr12", "what": AM.REPEAT},
            {"i": 1, "section": "s1", "amp": "pr12", "what": "drive1"}]
    od = D.out_dir(tmp_path)
    od.mkdir(parents=True)
    (od / "plan.json").write_text(json.dumps({"recipe": AM.RECIPE, "jobs": jobs, "reused_on": [1]}))
    processes, written = [], []

    class Proc:
        def __init__(self):
            self.calls = []
            processes.append(self)

        def render(self, di, sel, x):
            self.calls.append(dict(x))
            return np.full(int((PS.TRIM_S + PS.SEC_S) * PS.SR) + 10,
                           0.5 if x[("drive1", "drive1Active")] == "true" else 0.25)

        def close(self):
            pass

        def menu(self):
            return {}

    class Menus:
        dried = {}

        def gate_thresholds(self):
            return []

    def encode(x, amp):
        s = [0.0] * len(F.SW)
        s[js] = 1.0 if x[("drive1", "drive1Active")] == "true" else 0.0
        return [None, None, s, [1.0] * len(F.SW)]

    monkeypatch.setattr(D, "require_declared", lambda: None)
    monkeypatch.setattr(D, "step4_on_rows", lambda root: {1: {"audio_sha256": step4_sha}})
    monkeypatch.setattr(CA, "new_process", Proc)
    monkeypatch.setattr(CB, "new_renderer", Proc)
    monkeypatch.setattr(CB, "load_plan", lambda args: {"gate_cap": {"unit": 0.5}})
    monkeypatch.setattr(CB, "ctx_for", lambda args: type("X", (), {"sections": {"s1": {"path": "/x", "start_s": 0.0}}}))
    monkeypatch.setattr(T, "rows_of", lambda root, stage, prefix: {1: {"settings": LO.sdict(on), "target": {}}})
    monkeypatch.setattr(T, "lufs_or_none", lambda y: -20.0)
    monkeypatch.setattr(T3, "Menus", Menus)
    monkeypatch.setattr(T3, "check_menu", lambda live, dried: None)
    monkeypatch.setattr(T3, "full_twin", lambda i, menus: ("pr12", "factory", "crunch", "SEL", dict(on), {}, "c", 1))
    monkeypatch.setattr(F, "gate_cap_u", lambda thr: (0.5, -60.0))
    monkeypatch.setattr(F, "encode", encode)
    monkeypatch.setattr(LO, "_wait_cap", lambda: None)
    monkeypatch.setattr(PS, "free_gb", lambda: 100.0)
    monkeypatch.setattr(PS, "section_audio", lambda path, start: np.zeros(10))
    monkeypatch.setattr(B, "measure", lambda x: x)
    monkeypatch.setattr(DS, "swap_mb", lambda: 0)
    monkeypatch.setattr(DS, "_guards", lambda name, *a: written.append(name) and None)
    monkeypatch.setattr(G, "write_flac", lambda path, y, sr: written.append(path) or (1.0, "sha"))
    D.main(["render", "--smoke", "--out", str(tmp_path)])
    rows = [json.loads(line) for line in (od / "rows" / "render-0of1.jsonl").read_text().splitlines()]
    return rows, processes, written, on


def test_render_checks_the_reused_r_on_bit_for_bit(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    from learn import pretrain_set as PS

    n = int((PS.TRIM_S + PS.SEC_S) * PS.SR) - int(PS.TRIM_S * PS.SR)
    rows, processes, written, on = _render(tmp_path, monkeypatch, AM.audio_sha(np.full(n, 0.5)))
    assert [r["what"] for r in rows] == [AM.REPEAT, "drive1"] and rows[0]["repeat_exact"] is True
    assert rows[1]["off"] == {"path": "drive1/drive1Active", "value": "false"}
    _, *per_job = processes
    for p, r in zip(per_job, rows):
        assert len(p.calls) == 2 and p.calls[0] == on                          # primed with the example's own setting
        assert p.calls[1][("drive1", "drive1Active")] == ("false" if r["what"] == "drive1" else "true")
    guards = [w for w in written if isinstance(w, str)]
    assert guards and set(guards) == {"cc-drive-page-render"}                  # the guard names this page's runs
    files = [w for w in written if not isinstance(w, str)]
    assert len(files) == 2 and all(D.out_dir(tmp_path) in p.parents for p in files)   # nothing into step 4's folder


def test_render_refuses_when_the_reused_r_on_does_not_repeat(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="not bit-identical"):
        _render(tmp_path, monkeypatch, "not-step-4s-sha")
