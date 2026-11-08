"""H4a's side read on N12's units (`learn/score_ear.py` h4-*, `bakeoff_render.fold_nets`), with fakes: no nets, no renders."""
import argparse
import json
import math

import pytest

from learn import pipeline_fix as P
from learn import score_ear as E


def _ledger(monkeypatch, have=(E.WIDE, E.H4, P.H4_EXCL), sha="x"):
    seen = []

    def require(key):
        seen.append(key)
        if key not in have:
            raise SystemExit(f"the ledger has no {key}")
        return {}
    monkeypatch.setattr(P, "require", require)
    monkeypatch.setattr(P, "h4_exclusions", lambda: (require(P.H4), require(P.H4_EXCL), {"sha256": sha})[-1])
    return seen


def test_the_side_read_takes_only_h4_tags():
    assert E.h4_tags("P2b-ftmf,P2b-ftmc") == ["P2b-ftmf", "P2b-ftmc"]
    for bad in ("P2b-ftm", "P2b-ftmf,FTm", "", "P2b-ftmf50"):
        with pytest.raises(SystemExit, match="H4's tags only"):
            E.h4_tags(bad)


def _rec(nm, sd, arm=None, sha="x"):
    r = {"test": nm, "seed": sd, "inner": False, "E": 5, "epochs_run": 5,
         "models": {"final": "m", "best": "m"}, "model_sha256": {"final": "h", "best": "h"}}
    if arm:
        r["h4"] = {"arm": arm, "exclusions_sha256": sha}
    return r


def test_fold_nets_load_each_ft_k_through_the_h4_read_check(monkeypatch):
    pytest.importorskip("numpy")
    from learn import bakeoff_render as BR

    _ledger(monkeypatch)
    loaded = []

    def load_run(nm, sd, which):
        loaded.append((nm, sd, which))
        return f"net-{nm}-{sd}", _rec(nm, sd, "gentle")
    monkeypatch.setattr(P, "load_run", load_run)
    got = BR.fold_nets("P2b-ftmg")
    assert got == {k: [f"net-P2b-ftmg-k{k}-{sd}" for sd in P.SEEDS] for k in range(P.REAL_FOLDS)}
    assert {(nm, w) for nm, _, w in loaded} == {(f"P2b-ftmg-k{k}", "best") for k in range(P.REAL_FOLDS)}
    monkeypatch.setattr(P, "load_run", lambda nm, sd, w: (None, _rec(nm, sd)))          # no h4 field
    with pytest.raises(SystemExit, match="not an H4 run"):
        BR.fold_nets("P2b-ftmg")
    monkeypatch.setattr(P, "load_run", lambda nm, sd, w: (None, _rec(nm, sd, "full")))  # another arm's run
    with pytest.raises(SystemExit, match="not an H4 run"):
        BR.fold_nets("P2b-ftmg")
    monkeypatch.setattr(P, "load_run", lambda nm, sd, w: (None, dict(_rec(nm, sd, "gentle"), inner=True)))
    with pytest.raises(SystemExit, match="read checkpoint"):
        BR.fold_nets("P2b-ftmg")
    with pytest.raises(SystemExit, match="not an H4 tag"):
        BR.fold_nets("P2b-ftm")
    _ledger(monkeypatch, have=(E.WIDE,))
    with pytest.raises(SystemExit, match=E.H4):
        BR.fold_nets("P2b-ftmg")


def _wide_fakes(tmp_path, monkeypatch, stored_ok=True):
    """`wide_answers`' world: one read unit for the control, two N12 units, fake nets that echo their tag."""
    pytest.importorskip("numpy")
    from learn import bakeoff_render as BR
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(BR, "read_units", lambda: [("goat", {"unit": "g"})] * 13)
    monkeypatch.setattr(BR, "net_answers", lambda folds, some: {w: {"k": folds[0][0]} for w in BR.SETS})
    monkeypatch.setattr(BR, "stored_answers", lambda w, tag: {"k": f"net-{tag}" if stored_ok else "other"})
    units = [{"unit": f"u{j}", "amp": "pr12", "cls": "clean"} for j in range(2)]
    recs = {u["unit"]: {"search": "AB"[j]} for j, u in enumerate(units)}
    monkeypatch.setattr(E, "wide_units", lambda: (units, recs, []))
    monkeypatch.setattr(P, "A_menu_S", lambda: {"pr12": {"clean": ("sel", {"S": 1})}})
    monkeypatch.setattr(P, "dfix_backed", lambda unit: {"A": ("backed", -20.0), "B": ("backed", -20.0)})
    monkeypatch.setattr(DS, "model_input", lambda s8, s8b, ls, lsb, search, amp, cls, kind: (s8, None))
    monkeypatch.setattr(F, "run_nets", lambda nets, xs, cs: [[nets[0]]])
    monkeypatch.setattr(F, "readout", lambda outs: {"a2": outs[0], "sw_p": None, "mics": None})
    monkeypatch.setattr(F, "answer_settings", lambda amp, S, a2, sw, mics: {"net": a2})
    monkeypatch.setattr(P, "hold_outside_space", lambda st, S, amp: {**st, "held": True})
    monkeypatch.setattr(LO, "sdict", dict)


def test_an_h4_tag_answers_n12s_units_by_ftms_path_after_its_control(tmp_path, monkeypatch):
    _wide_fakes(tmp_path, monkeypatch)
    from learn import bakeoff_render as BR

    seen = _ledger(monkeypatch)
    monkeypatch.setattr(BR, "fold_nets", lambda tag: {k: [f"net-{tag}"] * 2 for k in range(P.REAL_FOLDS)})
    E.cmd_h4_answers(argparse.Namespace(tags="P2b-ftmf,P2b-ftmc"))
    assert E.WIDE in seen and E.H4 in seen
    for t in ("P2b-ftmf", "P2b-ftmc"):
        d = json.loads((tmp_path / E.WIDE_DIR / "answers" / f"{t}.json").read_text())
        assert d["tag"] == t
        assert d["answers"] == {"u0": {"A": {"select": "sel", "settings": {"net": f"net-{t}", "held": True}}},
                                "u1": {"B": {"select": "sel", "settings": {"net": f"net-{t}", "held": True}}}}
    assert not (tmp_path / E.WIDE_DIR / "answers" / "FTm.json").exists()
    _ledger(monkeypatch, have=(E.WIDE,))
    with pytest.raises(SystemExit, match=E.H4):
        E.cmd_h4_answers(argparse.Namespace(tags="P2b-ftmf"))


def test_the_control_refuses_before_any_answer_is_written(tmp_path, monkeypatch):
    _wide_fakes(tmp_path, monkeypatch, stored_ok=False)
    from learn import bakeoff_render as BR

    _ledger(monkeypatch)
    monkeypatch.setattr(BR, "fold_nets", lambda tag: {k: [f"net-{tag}"] * 2 for k in range(P.REAL_FOLDS)})
    with pytest.raises(SystemExit, match="control"):
        E.cmd_h4_answers(argparse.Namespace(tags="P2b-ftmg"))
    assert not (tmp_path / E.WIDE_DIR / "answers").exists()


def test_ftms_own_answers_are_written_as_before(tmp_path, monkeypatch):
    _wide_fakes(tmp_path, monkeypatch)
    from learn import bakeoff_render as BR

    _ledger(monkeypatch, have=(E.WIDE,))                              # FTm's path needs no H4 key
    monkeypatch.setattr(P, "load_run", lambda nm, sd, w: (f"net-{BR.FTM}", None))
    E.cmd_answers(None)
    d = json.loads((tmp_path / E.WIDE_DIR / "answers" / "FTm.json").read_text())
    assert list(d) == ["tag", "time", "answers"] and d["tag"] == "FTm"
    assert d["answers"]["u0"] == {"A": {"select": "sel", "settings": {"net": f"net-{BR.FTM}", "held": True}}}


def _units():
    units = [{"unit": f"u{j}", "player": f"band{j % 3}", "di": f"d{j}"} for j in range(6)]
    recs = {u["unit"]: {"held": "B", "s_judge": {"B": 4.0}} for u in units}
    return units, recs


def test_the_rows_are_each_tag_less_ftm_by_band():
    pytest.importorskip("numpy")                                     # pretrain_set's t90
    units, recs = _units()
    n12 = lambda slug: {"judge": {"FTm": 2.0}}                          # noqa: E731
    vals = {E.slug_of(u["unit"]): (1.0 if int(u["unit"][1]) % 3 else 2.0) for u in units}   # band0 ties FTm, others halve
    judged = lambda t, slug: {"judge": vals[slug]}                     # noqa: E731
    rows, refused = E.h4_rows(units, recs, ["P2b-ftmf"], judged, n12)
    r = rows["P2b-ftmf less FTm"]
    assert r["clusters"] == 3 and r["cards"] == 6
    assert r["mean"] == pytest.approx((0 + 4 * math.log(0.5)) / 6)
    assert rows["P2b-ftmf less S"]["mean"] == pytest.approx((2 * math.log(0.5) + 4 * math.log(0.25)) / 6)
    assert refused["P2b-ftmf less FTm"] == refused["P2b-ftmf less S"] == 0 and not any(refused.values())
    assert rows["P2b-ftmf less FTm (W's DIs, apart)"] is None                          # no apart units: no row
    assert rows["P2b-ftmf less FTm (all units)"] == r
    vals[E.slug_of("u1")] = math.inf                                   # a refused judge: dropped and counted
    rows, refused = E.h4_rows(units, recs, ["P2b-ftmf"], judged, n12)
    assert rows["P2b-ftmf less FTm"]["cards"] == 5 and refused["P2b-ftmf less FTm"] == 1
    with pytest.raises(SystemExit, match="renders missing"):
        E.h4_rows(units, recs, ["P2b-ftmf"], lambda t, slug: None if slug == E.slug_of("u3") else judged(t, slug), n12)


def test_h4_wide_reads_the_stored_renders_under_phase_h4(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    units, recs = _units()
    monkeypatch.setattr(E, "wide_units", lambda: (units, recs, []))
    monkeypatch.setattr(E, "w_dis", lambda: frozenset({"d0"}))
    for u in units:
        slug = E.slug_of(u["unit"])
        d = tmp_path / E.WIDE_DIR / "renders" / slug
        d.mkdir(parents=True)
        (d / "rec.json").write_text(json.dumps({"judge": {"FTm": 2.0, "M-pcs": 3.0}}))
        h = tmp_path / E.WIDE_DIR / E.H4_DIR / "P2b-ftmc"
        h.mkdir(parents=True, exist_ok=True)
        (h / f"{slug}.json").write_text(json.dumps({"judge": 1.0}))
    _ledger(monkeypatch)
    out = tmp_path / "h4-n12.json"
    E.cmd_h4_wide(argparse.Namespace(out=str(out), tags="P2b-ftmc"))
    rep = json.loads(out.read_text())
    assert rep["phase"] == E.H4 and rep["units"] == 6 and rep["bands"] == 3
    assert rep["rows"]["P2b-ftmc less FTm"]["mean"] == pytest.approx(math.log(0.5))
    assert rep["w_di_units"] == ["u0"] and rep["rows"]["P2b-ftmc less FTm"]["cards"] == 5
    assert rep["rows"]["P2b-ftmc less FTm (all units)"]["cards"] == 6
    _ledger(monkeypatch, have=(E.WIDE,))
    with pytest.raises(SystemExit, match=E.H4):
        E.cmd_h4_wide(argparse.Namespace(out=str(out), tags="P2b-ftmc"))


def test_h4_render_refuses_without_phase_h4_or_on_another_tag(monkeypatch):
    pytest.importorskip("numpy")
    _ledger(monkeypatch, have=(E.WIDE,))
    with pytest.raises(SystemExit, match=E.H4):
        E.cmd_h4_render(argparse.Namespace(tags="P2b-ftmf", shard="0/3"))
    _ledger(monkeypatch)
    with pytest.raises(SystemExit, match="H4's tags only"):
        E.cmd_h4_render(argparse.Namespace(tags="M-pcs", shard="0/3"))


def _render_world(tmp_path, monkeypatch, n12_lag=7, n12_held="B", n12_sha="sha-1.0", s_sha="sha-0.5", clips=("u0",)):
    """`cmd_h4_render`'s world: 2 N12 units held on B at lag 7, N12's clips kept for `clips` only, stored readers whose settings
    tag their renders (S 0.5, FTm 1.0, the H4 tag 2.0; sample j adds j / 100), a 16-sample second and halves of half a second,
    and fakes for every audio step. -> the list of renders made."""
    np = pytest.importorskip("numpy")
    from learn import arm_a_levers as AL
    from learn import audibility_measure as AM
    from learn import ear_vreal as EV
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import rescore as R
    from learn import song_bank as B

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    _ledger(monkeypatch)
    units = [{"unit": f"u{j}", "amp": "pr12", "cls": "clean", "player": "band", "di_path": "di", "start_s": 0.0, "sd": None,
              "track": None, "di": "d"} for j in range(2)]
    recs = {u["unit"]: {"search": "A", "held": "B", "lag": 7, "s_render_sha256": s_sha} for u in units}
    monkeypatch.setattr(E, "wide_units", lambda: (units, recs, []))
    val = {"FTm": 1.0, "P2b-ftmf": 2.0}
    monkeypatch.setattr(E, "stored_reader", lambda t: {u["unit"]: {"A": {"select": "sel", "settings": {"v": val[t]}}}
                                                        for u in units})
    monkeypatch.setattr(AL, "menu_S", lambda: {"pr12": {"clean": ("sel", {"v": 0.5})}})
    for u in units:
        d = tmp_path / E.WIDE_DIR / "renders" / E.slug_of(u["unit"])
        d.mkdir(parents=True)
        (d / "rec.json").write_text(json.dumps({"lag": n12_lag, "held": n12_held, "sha": {"FTm": n12_sha}, "judge": {}}))
        if u["unit"] in clips:
            np.savez(d / "clips.npz", ref=np.zeros(8, np.float32))
    monkeypatch.setattr(LO, "_wait_cap", lambda: None)
    monkeypatch.setattr(LO, "tdict", dict)
    monkeypatch.setattr(LO, "sdict", dict)
    monkeypatch.setattr(PS, "free_gb", lambda: 1e9)
    monkeypatch.setattr(PS, "TRIM_S", 0.0)
    monkeypatch.setattr(PS, "SEC_S", 1.5)
    monkeypatch.setattr(PS, "SR", 16)
    monkeypatch.setattr(EV, "SR", 16)
    monkeypatch.setattr(R, "HALVES", {"A": (0.0, 0.5), "B": (0.5, 1.0)})      # B: samples 8 to 16
    monkeypatch.setattr(PS, "section_audio", lambda path, start: np.zeros(24))
    monkeypatch.setattr(B, "measure", lambda x: x)
    monkeypatch.setattr(P, "real_amp_track", lambda sd, track, start: np.arange(24) / 1000)
    made = []

    def fresh_render(make, di, sel, st, st2):
        made.append(st["v"])
        return st["v"] + np.arange(24) / 100
    monkeypatch.setattr(AM, "fresh_render", fresh_render)
    monkeypatch.setattr(AM, "audio_sha", lambda y: f"sha-{float(y[0])}")
    monkeypatch.setattr(K, "judge", lambda ref, y, di, lag: {"A": 1.0, "B": 2.0} if lag == 7 else {})
    return made


def test_h4_render_judges_the_held_half_and_keeps_every_clip_once(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    made = _render_world(tmp_path, monkeypatch)
    E.cmd_h4_render(argparse.Namespace(tags="P2b-ftmf", shard="0/1"))
    # u0 (N12 kept its clips): FTm as the shard's control, then the tag; u1 (none kept): FTm and S, then the tag
    assert made == [1.0, 2.0, 1.0, 0.5, 2.0]
    h4 = tmp_path / E.WIDE_DIR / E.H4_DIR
    for u in ("u0", "u1"):
        r = json.loads((h4 / "P2b-ftmf" / f"{E.slug_of(u)}.json").read_text())
        assert r["judge"] == 2.0 and r["held"] == "B" and r["lag"] == 7 and r["sha"] == "sha-2.0" and r["window"] == [8, 16]
        z = np.load(h4 / "P2b-ftmf" / f"{E.slug_of(u)}.npz")
        assert np.allclose(z["clip"], 2.0 + np.arange(1, 9) / 100) and list(z["window"]) == [8, 16]   # render[s0 - lag:s1 - lag]
    assert sorted(q.name for q in h4.iterdir()) == ["P2b-ftmf", "base"]                # FTm and S only as base clips
    b0, b1 = (np.load(h4 / "base" / f"{E.slug_of(u)}.npz") for u in ("u0", "u1"))
    assert sorted(b0.files) == ["FTm", "ref", "window"] and sorted(b1.files) == ["FTm", "S", "ref", "window"]
    assert np.allclose(b1["S"], 0.5 + np.arange(1, 9) / 100) and np.allclose(b1["FTm"], 1.0 + np.arange(1, 9) / 100)
    assert np.allclose(b1["ref"], np.arange(8, 16) / 1000) and list(b1["window"]) == [8, 16]
    E.cmd_h4_render(argparse.Namespace(tags="P2b-ftmf", shard="0/1"))
    assert len(made) == 5                                                              # a second run: nothing left to render
    (h4 / "P2b-ftmf" / f"{E.slug_of('u1')}.json").unlink()                             # one tag record gone: only that unit
    E.cmd_h4_render(argparse.Namespace(tags="P2b-ftmf", shard="0/1"))
    assert made[5:] == [1.0, 2.0]                                                      # its control, then the tag; S kept


@pytest.mark.parametrize("world, why", [({"n12_sha": "sha-other"}, "FTm's render differs"),
                                        ({"s_sha": "sha-other", "clips": ("u0", "u1")}, None),
                                        ({"s_sha": "sha-other"}, "S's render differs"),
                                        ({"n12_lag": 8}, "lag or half differs"),
                                        ({"n12_held": "A"}, "lag or half differs")])
def test_h4_render_refuses_on_each_gate(tmp_path, monkeypatch, world, why):
    made = _render_world(tmp_path, monkeypatch, **world)
    if why is None:                                                    # N12 kept every unit's clips: S is never rendered
        E.cmd_h4_render(argparse.Namespace(tags="P2b-ftmf", shard="0/1"))
        assert 0.5 not in made
        return
    with pytest.raises(SystemExit, match=why):
        E.cmd_h4_render(argparse.Namespace(tags="P2b-ftmf", shard="0/1"))
    assert not (tmp_path / E.WIDE_DIR / E.H4_DIR / "P2b-ftmf" / f"{E.slug_of('u1')}.json").exists()


def test_the_w_di_units_are_reported_apart_and_left_out_of_the_primary():
    pytest.importorskip("numpy")
    units = [{"unit": f"u{j}", "player": f"band{j % 3}", "di": "w-di" if j < 2 else f"d{j}"} for j in range(6)]
    recs = {u["unit"]: {"held": "B", "s_judge": {"B": 4.0}} for u in units}
    vals = {E.slug_of(u["unit"]): (4.0 if u["di"] == "w-di" else 1.0) for u in units}  # W's DIs read worse than FTm
    rows, refused = E.h4_rows(units, recs, ["P2b-ftmg"], lambda t, slug: {"judge": vals[slug]},
                              lambda slug: {"judge": {"FTm": 2.0}}, frozenset({"w-di"}))
    assert rows["P2b-ftmg less FTm"]["cards"] == 4 and rows["P2b-ftmg less FTm"]["mean"] == pytest.approx(math.log(0.5))
    assert rows["P2b-ftmg less FTm (W's DIs, apart)"]["cards"] == 2
    assert rows["P2b-ftmg less FTm (W's DIs, apart)"]["mean"] == pytest.approx(math.log(2.0))
    assert rows["P2b-ftmg less FTm (all units)"]["cards"] == 6
    assert set(refused) == set(rows) and len(rows) == 6                 # 2 bases x 3 groups


def test_w_dis_are_the_sections_dis_of_ws_training_rows(monkeypatch):
    pytest.importorskip("numpy")                                     # bakeoff imports numpy
    from learn import bakeoff as BK

    monkeypatch.setattr(BK, "plugin_set", lambda: ([{"section": "a/B_Full/16_ElecGtr1DI.wav@40.0"},
                                                    {"section": "a/B_Full/16_ElecGtr1DI.wav@80.0"},
                                                    {"section": "c/D_Full/15_ElecGtr04DI.wav@5.0"}], None))
    assert E.w_dis() == {"a/B_Full/16_ElecGtr1DI.wav", "c/D_Full/15_ElecGtr04DI.wav"}


def test_a_base_file_without_s_does_not_count_as_done(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    made = _render_world(tmp_path, monkeypatch)
    d = tmp_path / E.WIDE_DIR / E.H4_DIR / "base"
    d.mkdir(parents=True)
    np.savez(d / f"{E.slug_of('u1')}.npz", FTm=np.zeros(8, np.float32))       # u1 has no N12 clips and no S kept yet
    assert not E.h4_base_done(E.slug_of("u1")) and E.h4_base_done(E.slug_of("u0"))
    E.cmd_h4_render(argparse.Namespace(tags="P2b-ftmf", shard="0/1"))
    assert 0.5 in made and "S" in np.load(d / f"{E.slug_of('u1')}.npz").files
