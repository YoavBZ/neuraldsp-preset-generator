import json

import pytest

from learn import audibility_measure as AM
from learn import cc_audibility as C
from learn import local_objective as LO

PLAYING = {"drums": -20.0, "bass": -22.0, "all": -15.0}


def _x(ratio=-3.0, vocals=False, others=1, stands=0, stems=("01_Kick.wav", "09_Bass.wav"), band="BKS",
       mode="factory", base="clean", cls="clean"):
    return {"draw": {"ratio_db": ratio, "vocals_drawn": vocals}, "others": [{}] * others,
            "amp_tracks": [{}] * stands, "band": band, "mode": mode, "base": base, "cls": cls,
            "stems": {"v": list(stems) + ["20_LeadVox.wav"], "n": list(stems)}}


def _q(x, levels=PLAYING):
    return C.qualifies(x, lambda _: levels)


def test_the_page_rule():
    assert _q(_x()) == (True, None)
    assert _q(_x(ratio=-7.0))[1] == "not exposed"                             # the earlier exposed page's rule
    assert _q(_x(vocals=True))[1] == "not exposed"
    assert _q(_x(others=3))[1] == "not exposed"
    assert _q(_x(stems=("01_Kick.wav",)))[1] == "no drums or no bass track in the backing"
    assert _q(_x(band="Storm Of Particles"))[1] == "a heavy band"
    assert _q(_x(mode="wide"))[1] == "an atypical tone (part C's wide draw)"
    assert _q(_x(mode="start"))[0]
    assert _q(_x(base="crunch"))[1] == "the drawn class is not the section's"
    assert _q(_x(base="crunch", cls="crunch"))[0]
    assert AM.EXPOSED == {"min_ratio_db": -6.0, "vocals": False, "max_others": 2}


def test_stand_ins_count_as_other_guitars():
    # the review: this pool's backing also sums recorded amp-track stand-ins; they are other guitars too
    assert _q(_x(others=1, stands=1))[0]
    assert _q(_x(others=1, stands=2))[1] == "not exposed"
    assert _q(_x(others=0, stands=3))[1] == "not exposed"


def test_drums_and_bass_must_play_in_the_window():
    assert C.plays({"drums": -35.0, "bass": -30.0, "all": -15.0})                      # both within 20 dB
    assert not C.plays({"drums": -37.0, "bass": -30.0, "all": -15.0})                  # drums 22 dB under (802402)
    assert not C.plays({"bass": -20.0, "all": -15.0})                                  # no drums at all (802742)
    assert _q(_x(), {"drums": -40.0, "bass": -20.0, "all": -15.0})[1] == "drums or bass not playing in the window"
    assert C.PLAYS_WITHIN_DB == 20.0
    calls = []
    assert C.qualifies(_x(ratio=-9.0), lambda x: calls.append(x) or PLAYING)[1] == "not exposed"
    assert not calls                                                                  # the audio is read last


def test_backing_classes_read_the_drawn_vocal_variant():
    x = _x(vocals=True)
    assert "vocal" in C.backing_classes(x) and "vocal" not in C.backing_classes(_x())


def test_the_recipe_and_effects_are_the_audibility_pages():
    assert C.N_MAX == 30 and C.SEED != AM.SEED and C.PAGE_SEED != AM.PAGE_SEED
    assert AM.RECIPE == "fresh" and set(AM.EFFECTS) == {"delay", "reverb", "tremolo", "pr12 spring", "sw50r spring"}


def test_renders_are_in_the_machine_cap():
    assert LO.is_render_process("/x/bin/python3 -u -m learn.cc_audibility render --shard 0/3")
    assert not LO.is_render_process("/x/bin/python3 -m learn.cc_audibility plan")
    assert not LO.is_render_process("/bin/zsh -c 'python -m learn.cc_audibility render'")   # a shell, not python


def test_runs_refuse_without_the_declaration(tmp_path, monkeypatch):
    led = tmp_path / "ledger.json"
    led.write_text(json.dumps({"tests": [{"test_id": C.LEDGER_ID}]}))
    assert not C.ledger_declared(led)
    led.write_text(json.dumps({"tests": [{"test_id": C.LEDGER_ID, C.LEDGER_KEY: f"{C.LEDGER_MARK} (...)"}]}))
    assert C.ledger_declared(led)
    monkeypatch.setattr(C, "ledger_declared", lambda path=None: False)
    with pytest.raises(SystemExit, match="runs refuse"):
        C.main(["render", "--shard", "0/3"])


def test_flags_belong_to_their_commands(tmp_path):
    with pytest.raises(SystemExit):
        C.main(["plan", "--shard", "1/3"])
    with pytest.raises(SystemExit):
        C.main(["measure", "--force"])
    with pytest.raises(SystemExit, match="scratch --out"):
        C.main(["page", "--smoke"])
    with pytest.raises(SystemExit, match="smoke runs only"):
        C.main(["page", "--out", str(tmp_path)])


def test_a_smoke_page_never_touches_the_real_page(tmp_path):
    import argparse

    real = C.page_dir(argparse.Namespace(out=None, smoke=False))
    smoke = C.page_dir(argparse.Namespace(out=str(tmp_path), smoke=True))
    assert smoke == tmp_path / "listening" / C.PAGE_NAME and smoke != real


def test_the_ledger_declares_the_page_before_any_render():
    assert C.ledger_declared()


def test_render_opens_a_new_primed_process_per_job(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    on = {("delay", "delayActive"): "true", ("pr12Amp", "pr12Gain"): "0.4"}
    js = F.SW.index(AM.EFFECTS["delay"][0])
    jobs = [{"i": 1, "section": "s1", "amp": "pr12", "what": AM.ON},
            {"i": 1, "section": "s1", "amp": "pr12", "what": AM.REPEAT},
            {"i": 1, "section": "s1", "amp": "pr12", "what": "delay"}]
    od = C.out_dir(tmp_path)
    od.mkdir(parents=True)
    (od / "plan.json").write_text(json.dumps({"recipe": AM.RECIPE, "jobs": jobs}))
    processes = []

    class Proc:
        def __init__(self):
            self.calls, self.closed = [], False
            processes.append(self)

        def render(self, di, sel, x):
            self.calls.append(dict(x))
            return np.full(int((PS.TRIM_S + PS.SEC_S) * PS.SR) + 10, 0.5 if x[("delay", "delayActive")] == "true"
                           else 0.25)

        def close(self):
            self.closed = True

        def menu(self):
            return {}

    class Menus:
        dried = {}

        def gate_thresholds(self):
            return []

    def encode(x, amp):
        s = [0.0] * len(F.SW)
        s[js] = 1.0 if x[("delay", "delayActive")] == "true" else 0.0
        return [None, None, s, [1.0] * len(F.SW)]

    monkeypatch.setattr(C, "require_declared", lambda: None)
    monkeypatch.setattr(C, "new_process", Proc)
    monkeypatch.setattr(CB, "new_renderer", Proc)
    monkeypatch.setattr(CB, "load_plan", lambda args: {"gate_cap": {"unit": 0.5}})
    monkeypatch.setattr(CB, "ctx_for", lambda args: type("X", (), {"sections": {"s1": {"path": "/x", "start_s": 0.0}}}))
    monkeypatch.setattr(T, "rows_of", lambda root, stage, prefix: {1: {"settings": LO.sdict(on), "target": {}}})
    monkeypatch.setattr(T, "lufs_or_none", lambda y: -20.0)
    monkeypatch.setattr(T3, "Menus", Menus)
    monkeypatch.setattr(T3, "check_menu", lambda live, dried: None)
    monkeypatch.setattr(T3, "full_twin", lambda i, menus: ("pr12", "factory", "clean", "SEL", dict(on), {}, "c", 1))
    monkeypatch.setattr(F, "gate_cap_u", lambda thr: (0.5, -60.0))
    monkeypatch.setattr(F, "encode", encode)
    monkeypatch.setattr(LO, "_wait_cap", lambda: None)
    monkeypatch.setattr(PS, "free_gb", lambda: 100.0)
    monkeypatch.setattr(PS, "section_audio", lambda path, start: np.zeros(10))
    monkeypatch.setattr(B, "measure", lambda x: x)
    monkeypatch.setattr(DS, "swap_mb", lambda: 0)
    monkeypatch.setattr(DS, "_guards", lambda *a: None)
    monkeypatch.setattr(G, "write_flac", lambda path, y, sr: (1.0, "sha"))
    C.main(["render", "--smoke", "--out", str(tmp_path)])
    rows = [json.loads(line) for line in (od / "rows" / "render-0of1.jsonl").read_text().splitlines()]
    assert [r["what"] for r in rows] == [AM.ON, AM.REPEAT, "delay"]
    menu_check, *per_job = processes
    assert menu_check.calls == [] and menu_check.closed               # the menu check renders nothing
    assert len(per_job) == 3 and all(p.closed for p in per_job)      # a new process per job
    for p, r in zip(per_job, rows):
        assert len(p.calls) == 2 and p.calls[0] == on                # primed with the example's own setting
        assert p.calls[1][("delay", "delayActive")] == ("false" if r["what"] == "delay" else "true")
        assert r["renders"] == 2 and r["primes"] == 1
    assert rows[1]["repeat_exact"] is True
