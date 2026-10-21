"""learn/direct_stems.py: the pure parts of gate 1 (docs/direct-model-stems-plan.md)."""

import math
import random

import pytest

np = pytest.importorskip("numpy")

from learn import direct_stems as DS  # noqa: E402


def _o(logpi, mu, ls=None, sw=(0.0,), cats=((1.0, 0.0),)):
    mu = np.asarray(mu, float)
    return (np.log(np.asarray(logpi, float)), mu, np.zeros_like(mu) if ls is None else np.asarray(ls, float),
            np.asarray(sw, float), [np.asarray(c, float) for c in cats])


def test_musdb_filter_matches_slugs():
    assert DS.is_musdb("cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3")
    assert DS.is_musdb("cambridge-femme-elecgtr5")
    assert DS.is_musdb("cambridge-Signs-ElecGtr3")
    assert not DS.is_musdb("cambridge-Passing_Ships-ElecGtr2")
    assert not DS.is_musdb("cambridge-designs-gtr")             # whole words only


def test_leak_draws_are_seeded_sorted_and_in_range():
    a = DS.leak_draws(["k2", "k1"])
    b = DS.leak_draws(["k1", "k2"])
    assert a == b and len(a["k1"]) == DS.N_LEAK
    assert all(0.0 <= v <= 6.0 for vs in a.values() for v in vs)


def test_training_stem_sets_the_leak_below_the_guitar():
    def lufs(x):                                                   # a power meter stand-in
        return 10 * math.log10(float(np.mean(np.asarray(x) ** 2)) + 1e-20)

    rng = np.random.default_rng(0)
    ref, back = rng.normal(size=4800), 3.0 * rng.normal(size=4800)
    st = DS.training_stem(ref, back, 4.0, lufs)
    leak = st - ref
    assert math.isclose(lufs(ref) - lufs(leak), 4.0, abs_tol=1e-9)
    assert np.allclose(leak / back, leak[0] / back[0])           # a scaled copy of the backing


def test_leak_gain_caps_a_silent_backing():
    assert DS.leak_gain_db(-20.0, -100.0, 3.0) == -20.0 - 3.0 - (-60.0)


def test_derangement_respects_groups_and_avoid():
    keys = list(range(12))
    p = DS.derangement_avoid(keys, lambda k: k % 2, lambda a, b: a == b, 7)
    assert sorted(p) == keys and sorted(p.values()) == keys
    assert all(a != b and a % 2 == b % 2 for a, b in p.items())
    assert p == DS.derangement_avoid(keys, lambda k: k % 2, lambda a, b: a == b, 7)
    with pytest.raises(SystemExit):
        DS.derangement_avoid([1], lambda k: 0, lambda a, b: a == b, 1, max_tries=5)


def test_movement_uses_top_components_and_masks():
    x = _o([0.7, 0.3], [[0.2, 0.5, 0.9], [0.0, 0.0, 0.0]], sw=(1.0, -1.0), cats=((2.0, 0.0),))
    y = _o([0.1, 0.9], [[0.9, 0.9, 0.9], [0.4, 0.5, 0.1]], sw=(1.0, 1.0), cats=((0.0, 2.0),))
    d, sw, mic = DS.movement(x, y, [1, 1, 0], [1, 1], [1])
    assert math.isclose(d, (0.2 + 0.0) / 2)                      # dims 0, 1 of x's comp 0 vs y's comp 1
    assert sw == 0.5 and mic == 0.0
    d0, _, _ = DS.movement(x, x, [1, 1, 1], [1, 1], [1])
    assert d0 == 0.0


def test_likelihood_shift_is_zero_on_itself_and_positive_otherwise():
    x = _o([0.5, 0.5], [[0.2, 0.2], [0.8, 0.8]], ls=[[-2, -2], [-2, -2]])
    y = _o([0.9, 0.1], [[0.5, 0.5], [0.8, 0.8]])
    assert DS.likelihood_shift(x, x, [1, 1]) == 0.0
    assert DS.likelihood_shift(x, y, [1, 1]) > 0


def test_mixture_logp_single_gaussian():
    o = _o([1.0], [[0.5, 0.5]], ls=[[0.0, 0.0]])
    lp = DS.mixture_logp(o, [0.5, 1.5], [1, 0])                  # only dim 0 counts
    assert math.isclose(lp, -0.5 * math.log(2 * math.pi))


def test_band_weighted_averages_parts_then_bands():
    rows = [("A", "p1", 1.0), ("A", "p1", 3.0), ("A", "p2", 0.0), ("B", "q", 10.0)]
    m, bm = DS.band_weighted(rows)
    assert bm == {"A": 1.0, "B": 10.0} and m == 5.5


def test_bootstrap_interval_contains_mean_and_is_seeded():
    rows = [(f"b{k}", "p", float(k)) for k in range(8)]
    s = DS.bootstrap(rows, n=500)
    assert s["lo90"] <= s["mean"] <= s["hi90"] and s["bands"] == 8
    assert s == DS.bootstrap(rows, n=500)
    assert DS.bootstrap([("b", "p", 1.0)])["lo90"] is None


def test_gate1_rules_on_toy_tables():
    pos = {"mean": 0.02, "lo90": 0.01, "hi90": 0.03}
    tie = {"mean": 0.0, "lo90": -0.01, "hi90": 0.01}
    none = {"d(a',b)-null": {"all": tie, "unseen_by_part_c": tie}, "d(a,b)-null": {"all": tie, "unseen_by_part_c": tie}}
    assert DS.gate1(none, tie) == ("MIX-ONLY", [])
    assert DS.gate1(none, pos) == ("STEM", ["audit (iii)-(i)"])
    one = {**none, "d(a,b)-null": {"all": tie, "unseen_by_part_c": pos}}
    assert DS.gate1(one, tie) == ("STEM", ["d(a,b)-null on unseen_by_part_c"])
    # an interval touching 0 is not "entirely above"
    assert DS.gate1(none, {"mean": 0.01, "lo90": 0.0, "hi90": 0.02})[0] == "MIX-ONLY"


# --- 1c, the pilot build and the pilot (amendment 1) ---------------------------------------------------

F_BANDS = {"Stage F Band"}


def _sec(sid, band, split="train", es=False, path=None, source="cambridge", stage_f_session=False):
    return {"id": sid, "di": sid.split("@")[0], "band": band, "split": split, "early_stop": es, "source": source,
            "path": path or f"cambridge/{band.replace(' ', '')}_Song_Full/01_ElecGtrDI.wav",
            "stage_f_session": stage_f_session}


def _row(i, band, sec, split="train", es=False, amp="pr12", base="clean"):
    return {"i": i, "band": band, "section": sec, "split": split, "early_stop": es, "amp": amp, "base": base}


def _toy_pool():
    secs = {s["id"]: s for s in (_sec("a@1", "Band A"), _sec("b@1", "Band B", es=True), _sec("f@1", "Stage F Band"),
                                 _sec("k@1", "Rebecca Haviland"), _sec("v@1", "Val Band", split="val"))}
    rows = [_row(0, "Band A", "a@1"), _row(1, "Band B", "b@1", es=True), _row(2, "Stage F Band", "f@1"),
            _row(3, "Rebecca Haviland", "k@1"), _row(1_000_000, "Val Band", "v@1", split="val")]
    return rows, secs


def test_pool_leaves_out_stage_f_and_known_answer_bands_and_val():
    rows, secs = _toy_pool()
    pool = DS.pool_examples(rows, secs, F_BANDS)
    assert [r["i"] for r in pool] == [0, 1]
    vs = DS.vsep_examples(rows, secs, F_BANDS)
    assert [r["i"] for r in vs] == [1_000_000]
    c = DS.counts(pool)
    assert c == {"examples": 2, "train": 1, "early_stop": 1, "sections": 2, "bands": 2,
                 "per_band": {"Band A": 1, "Band B": 1}}
    DS.check_counts(c, {"examples": 2, "bands": 2}, "toy")
    with pytest.raises(SystemExit):
        DS.check_counts(c, {"examples": 3}, "toy")


@pytest.mark.parametrize("bad", [
    {"split": "reserve"},                                             # part C's reserve of stage F DIs
    {"source": "guitar-techs"},
    {"path": "guitar-techs/P3_music/x.wav"},                          # Guitar-TECHS P3
    {"stage_f_session": True},
    {"band": "Other Band"},                                           # row and section disagree
    {"early_stop": True},                                             # flag differs from the row's
])
def test_every_exclusion_is_asserted(bad):
    rows, secs = _toy_pool()
    secs["a@1"].update(bad)
    with pytest.raises(SystemExit):
        DS.pool_examples(rows, secs, F_BANDS)


def test_held_out_material_and_bands_are_refused():
    rows, secs = _toy_pool()

    def refuse(sec):
        if sec["id"] == "b@1":
            raise ValueError("held out")

    with pytest.raises(ValueError):
        DS.pool_examples(rows, secs, F_BANDS, refuse=refuse)
    with pytest.raises(SystemExit):
        DS.pool_examples(rows, secs, F_BANDS, held_bands={"Band A"})
    rows.append(_row(1_000_001, "Rebecca Haviland", "v@1", split="val"))
    with pytest.raises(SystemExit):                                   # a known-answer band in V_sep is a bug, not a filter
        DS.vsep_examples(rows, secs, F_BANDS)


def test_known_answer_and_musdb_lists_match_their_sources():
    from learn import clean_di as CD
    from learn import locator_truth as LT

    assert set(CD.KNOWN_ANSWER) == DS.KNOWN_ANSWER_BANDS
    assert (set(LT.MUSDB_TRAIN), set(LT.MUSDB_TEST), set(LT.MUSDB_ARTIST)) == (DS.MUSDB_TRAIN, DS.MUSDB_TEST,
                                                                              DS.MUSDB_ARTIST)


def test_musdb_tags():
    assert DS.musdb_tag("Bannockburn", "Cnoc An Tursa") == "musdb_train"
    assert DS.musdb_tag("Ill Fate", "Hollow Ground") == "musdb_test"
    assert DS.musdb_tag("Drag", "The Long Wait") == "musdb_artist"
    assert DS.musdb_tag("Some Song", "Eggy") is None


def test_stratified_pick_is_proportional_seeded_and_exact():
    rows = [_row(i, f"B{i % 3}", f"s{i % 7}@1", amp=("pr12", "sw50r", "ac20")[i % 2]) for i in range(300)]
    a = DS.stratified_pick(rows, 100, seed=5)
    assert len(a) == 100 and len({r["i"] for r in a}) == 100
    assert [r["i"] for r in a] == [r["i"] for r in DS.stratified_pick(list(reversed(rows)), 100, seed=5)]
    from collections import Counter
    full, got = Counter((r["band"], r["amp"]) for r in rows), Counter((r["band"], r["amp"]) for r in a)
    assert all(abs(got[k] - 100 * v / 300) < 1 for k, v in full.items())
    with pytest.raises(SystemExit):
        DS.stratified_pick(rows, 301)


def test_split_parts_pilot_rest_and_es():
    rows = [_row(i, f"B{i % 3}", f"s{i % 5}@1", es=(i % 10 == 0)) for i in range(200)]
    p = DS.split_parts(rows, [], n_pilot=50)
    es = [r for r in rows if r["early_stop"]]
    assert sum(not r["early_stop"] for r in p["pilot"]) == 50
    assert {r["i"] for r in es} <= {r["i"] for r in p["pilot"]}
    assert not ({r["i"] for r in p["pilot"]} & {r["i"] for r in p["rest"]})
    assert len(p["rest"]) == 200 - len(es) - 50 and not any(r["early_stop"] for r in p["rest"])


def test_match_share_counts_one_step():
    a = np.array([[10, 10, 10, 10]], np.uint8)
    b = np.array([[10, 11, 9, 13]], np.uint8)
    assert DS.match_share(a, b) == 0.75
    assert DS.match_share(np.zeros((2, 2), np.uint8), np.full((2, 2), 255, np.uint8)) == 0.0


def test_half_features_of_a_failed_separation():
    """A separator that returns silence: -70 LUFS (song_aug.lufs) and every cell at the floor."""
    pytest.importorskip("pyloudnorm")
    pytest.importorskip("scipy")
    mels, lu, floor = DS.half_features(np.zeros(480_000))
    assert lu == {"A": -70.0, "B": -70.0}
    assert floor == 1.0 and all(m.dtype == np.uint8 and not m.any() for m in mels.values())
    rng = np.random.default_rng(1)
    mels, lu, floor = DS.half_features(0.1 * rng.normal(size=480_000))
    assert all(-40 < v < 0 for v in lu.values()) and floor == 0.0
    assert mels["A"].shape == (96, 446)


def test_master_draw_is_seeded_by_index():
    a, b = DS.master_draw(17), DS.master_draw(17)
    assert a[0] == b[0] and a[1].random() == b[1].random()
    share = np.mean([DS.master_draw(i)[0] for i in range(2000)])
    assert 0.45 < share < 0.55


def test_sepcheck_rule():
    assert DS.sepcheck_rule((-1.0, -2.0, 0.0, 6)) == "fast"           # reaches 0
    assert DS.sepcheck_rule((0.5, -0.2, 1.0, 6)) == "fast"
    assert DS.sepcheck_rule((-1.0, -2.0, -0.1, 6)) == "stored"        # entirely below 0
    assert math.isclose(DS.snr_db(np.array([1.0, 1.0]), np.array([1.0, 0.0])), 0.0, abs_tol=1e-12)


def test_disk_guard_logic():
    assert DS.disk_guard("pilot") == (31.0, None)
    assert DS.disk_guard("rest", 35) == (35.0, None)
    g, note = DS.disk_guard("pilot", 26)
    assert g == 26.0 and note == "user, 2026-10-20: pilot build only, stop below 26 GB"
    assert DS.disk_guard("vsep", 28)[1] == note
    with pytest.raises(SystemExit):
        DS.disk_guard("rest", 26)                                     # the full build keeps 31 GB
    with pytest.raises(SystemExit):
        DS.disk_guard("pilot", 25)
    assert DS.disk_stop(25.9, 26.0) and not DS.disk_stop(26.0, 26.0)
    assert DS.disk_start_ok("pilot", 27.0, 26.0) and not DS.disk_start_ok("pilot", 25.0, 26.0)
    assert not DS.disk_start_ok("rest", 33.0, 31.0) and DS.disk_start_ok("rest", 34.0, 31.0)


def test_memory_guard_and_render_slots():
    assert DS.mem_stop(10.0, 0.0) is None and DS.mem_stop(None, None) is None
    assert "free memory" in DS.mem_stop(3.9, 0.0)
    assert "swap" in DS.mem_stop(10.0, 300.0)
    assert DS.render_slot_free(2, 2) and not DS.render_slot_free(3, 0) and not DS.render_slot_free(0, 3)


def test_half_of_matches_part_c_draw():
    from learn import pretrain_set as PS

    for i in (0, 5, 1_000_003):
        for ep in (-1, 0, 7):
            assert DS.half_of(i, ep) == int(random_half(PS, i, ep))


def random_half(PS, i, ep):
    import random

    return random.Random(PS.seed_int(PS.SEED, "half", i, ep)).random() < 0.5


def test_zeroing_is_exact_per_arm():
    x = np.ones((3, 2, 4, 5), np.float32)
    c = np.ones((3, 7), np.float32)
    DS.zero_inputs(x, c, "Dmix")
    assert not x[:, 0].any() and x[:, 1].all() and not c[:, -2].any() and c[:, -1].all() and c[:, :-2].all()
    x, c = np.ones((3, 2, 4, 5), np.float32), np.ones((3, 7), np.float32)
    for arm in ("Dstem", "Dstem-noaug"):
        DS.zero_inputs(x, c, arm)
        assert x[:, 0].all() and not x[:, 1].any() and c[:, -2].all() and not c[:, -1].any()
    x, c = np.ones((3, 2, 4, 5), np.float32), np.ones((3, 7), np.float32)
    DS.zero_inputs(x, c, "D0")
    assert x.all() and c.all()
    with pytest.raises(ValueError):
        DS.zero_inputs(x, c, "Dsep")


def test_zero_is_minus_60_db_after_the_mask():
    from learn import song_model as SM

    assert SM.norm_feat(np.array([-60.0]))[0] == 0.0                  # the zeroed channel reads -60 dB


def test_separator_failure_sets_stem_to_mix_and_moves_lufs_by_the_same_offset():
    mix = np.full((96, 446), -30.0, np.float32)
    rng = np.random.default_rng(0)
    stem, lu = DS.sep_failure(mix, -14.0, rng)
    off = stem[0, 0] + 30.0
    assert -6.0 <= off <= 0.0 and np.allclose(stem, mix + off) and math.isclose(lu, -14.0 + off, abs_tol=1e-5)
    low, _ = DS.sep_failure(np.full((2, 2), -111.0, np.float32), -60.0, np.random.default_rng(1))
    assert low.min() >= DS.Q_FLOOR_DB


def test_merge_adds_in_the_power_domain_at_the_drawn_gain():
    st = np.full((2, 3), -20.0)
    out = DS.merge_guitar(st, np.full((2, 3), -30.0), 10.0)            # equal powers: +3.01 dB
    assert np.allclose(out, -20.0 + 10 * math.log10(2), atol=1e-5)
    assert DS.merge_gain_db(-30.0, 12.0, -25.0, -6.0) == -30.0 + 12.0 + 25.0 - 6.0


def test_dropouts_attenuate_one_to_three_segments():
    st = np.full((96, 446), -20.0, np.float32)
    for seed in range(20):
        out = DS.dropouts(st, np.random.default_rng(seed))
        hit = (out < -20.0 + 1e-6).all(axis=0) & (out < -29.99).all(axis=0)
        assert hit.any() and (out <= st).all() and (out >= DS.Q_FLOOR_DB).all()
        assert hit.sum() <= 3 * 100                                    # at most 3 segments of 1 s
        assert np.allclose(out[:, ~hit], -20.0)
        assert np.ptp(out, axis=0).max() == 0.0                       # whole frames, all mels


def test_darkening_attenuates_only_above_the_corner():
    st = np.full((96, 10), -20.0, np.float32)
    c = DS.mel_centres_hz()
    assert len(c) == 96 and c[0] > 30 and c[-1] < 16000
    out = DS.darken(st, np.random.default_rng(3), c)
    low = c < 3000
    assert np.allclose(out[low], -20.0) and (out[c > 8000] <= -20.0).all()
    att = -20.0 - out[:, 0]
    assert att.max() <= 15.0 and len(set(np.round(att[att > 0], 5))) <= 1


def test_augment_order_seeding_and_lufs():
    stem = np.full((96, 446), -25.0, np.float32)
    mix = np.full((96, 446), -15.0, np.float32)
    calls = []

    def draw(rng):
        calls.append(1)
        return np.full((96, 446), -40.0, np.float32), 0.0

    c = DS.mel_centres_hz()
    seen = {}
    for i in range(400):
        s, lu, ap = DS.augment(i, 0, stem, -20.0, mix, -10.0, draw, c)
        s2, lu2, ap2 = DS.augment(i, 0, stem, -20.0, mix, -10.0, draw, c)
        assert ap == ap2 and np.array_equal(s, s2) and lu == lu2   # SeedSequence([20261074, i, epoch])
        assert ap == [a for a in ("fail", "merge", "drop", "dark") if a in ap]
        for a in ap:
            seen[a] = seen.get(a, 0) + 1
        if "fail" in ap:
            assert -16.0 <= lu <= -10.0                              # the mix LUFS + the offset
        else:
            assert lu == -20.0                                         # merge, drop-outs, darkening keep it
        if not ap:
            assert np.array_equal(s, stem)
        if ap == ["fail"]:
            assert np.allclose(s, mix + (lu + 10.0))                  # stem := mix, offset as the LUFS
    assert all(k in seen for k in ("fail", "merge", "drop", "dark"))
    assert 0.0 < seen["fail"] / 400 < 0.12 and 0.2 < seen["drop"] / 400 < 0.4
    assert len(calls) == seen["merge"] * 2
    a = DS.augment(1, 0, stem, -20.0, mix, -10.0, draw, c)
    b = DS.augment(1, 1, stem, -20.0, mix, -10.0, draw, c)
    assert a[2] != b[2] or not np.array_equal(a[0], b[0]) or not a[2]   # epochs draw anew


def test_failure_comes_before_the_merge_and_dropouts_last_before_darkening():
    """Order: a failed stem is the mix, then merged, then drop-outs, then darkening."""
    stem = np.full((96, 446), -25.0, np.float32)
    mix = np.full((96, 446), -15.0, np.float32)
    c = DS.mel_centres_hz()
    for i in range(3000):
        rng_gate = DS.aug_rng(i, 0).random(4)
        if rng_gate[0] < DS.P_FAIL and rng_gate[1] < DS.P_MERGE:
            s, lu, ap = DS.augment(i, 0, stem, -20.0, mix, -10.0, lambda r: (np.full((96, 446), -15.0, np.float32), 0.0), c)
            off = lu + 10.0
            expect = DS.merge_guitar(mix + off, np.full((96, 446), -15.0), 0.0)
            if ap == ["fail", "merge"]:
                assert np.allclose(s, expect, atol=1e-4)
                return
    pytest.skip("no example drew failure and merge alone")


def test_merge_partners_come_from_the_training_pool_only():
    rows = [_row(0, "A", "s1@1", base="clean"), _row(1, "A", "s1@1", base="clean"), _row(2, "A", "s2@1", base="clean"),
            _row(3, "A", "s3@1", es=True, base="clean"), _row(4, "A", "s4@1", base="crunch"),
            _row(1_000_000, "V", "v@1", split="val", base="clean")]
    cands = DS.merge_candidates(rows)
    assert sorted(p for p, _ in cands["clean"]) == [0, 1, 2] and [p for p, _ in cands["crunch"]] == [4]
    rng = np.random.default_rng(0)
    for _ in range(50):
        p = DS.merge_partner(rng, cands["clean"], "s1@1")
        assert p == 2                                                 # another section, never ES or V_sep
    with pytest.raises(SystemExit):
        DS.merge_partner(rng, cands["crunch"], "s4@1", tries=10)


def _iv(m, lo, hi):
    return (m, lo, hi, 4)


def test_pilot_rules_on_toy_tables():
    neg, tie, pos = _iv(-0.01, -0.02, -0.001), _iv(0.0, -0.01, 0.01), _iv(0.01, 0.001, 0.02)
    # rule 1: neither beats D0 -> STOP
    d, aug, _ = DS.pilot_rules({"Dstem-D0|R_out": tie, "Dmix-D0|R_out": pos, "Dmix-Dstem|R_in": neg,
                                "Dstem-Dstem-noaug|R_in": tie})
    assert d == "STOP" and aug
    # rule 2: D_mix beat D0 and is clearly better than D_stem -> MIX
    d, _, _ = DS.pilot_rules({"Dstem-D0|R_out": neg, "Dmix-D0|R_out": neg, "Dmix-Dstem|R_in": neg,
                              "Dstem-Dstem-noaug|R_in": tie})
    assert d == "MIX"
    # a tie between D_mix and D_stem keeps D_stem (amendment 1)
    d, _, _ = DS.pilot_rules({"Dstem-D0|R_out": neg, "Dmix-D0|R_out": neg, "Dmix-Dstem|R_in": tie,
                              "Dstem-Dstem-noaug|R_in": tie})
    assert d == "STEM"
    # D_mix clearly better on R_in but did not beat D0: STEM (rule 2 needs both)
    d, _, _ = DS.pilot_rules({"Dstem-D0|R_out": neg, "Dmix-D0|R_out": tie, "Dmix-Dstem|R_in": neg,
                              "Dstem-Dstem-noaug|R_in": tie})
    assert d == "STEM"
    # rule 1 passes through D_mix alone, D_mix not clearly better: STEM
    d, _, _ = DS.pilot_rules({"Dstem-D0|R_out": tie, "Dmix-D0|R_out": neg, "Dmix-Dstem|R_in": tie,
                              "Dstem-Dstem-noaug|R_in": tie})
    assert d == "STEM"
    # rule 4: augmentation dropped only if D_stem is clearly worse than noaug
    assert not DS.pilot_rules({"Dstem-D0|R_out": neg, "Dmix-D0|R_out": tie, "Dmix-Dstem|R_in": tie,
                               "Dstem-Dstem-noaug|R_in": pos})[1]
    assert DS.pilot_rules({"Dstem-D0|R_out": neg, "Dmix-D0|R_out": tie, "Dmix-Dstem|R_in": tie,
                           "Dstem-Dstem-noaug|R_in": neg})[1]
    # missing contrasts never pass a rule
    assert DS.pilot_rules({})[0] == "STOP"


def test_paired_contrast_is_band_clustered():
    a = {"1": 0.2, "2": 0.3, "3": 0.1, "4": 0.4}
    b = {"1": 0.1, "2": 0.1, "3": 0.1, "4": 0.1}
    band = {"1": "x", "2": "x", "3": "y", "4": "z"}
    m, lo, hi, n = DS.paired(a, b, band, {"1", "2", "3", "4"})
    assert n == 3 and math.isclose(m, (0.15 + 0.0 + 0.3) / 3)
    assert DS.paired(a, b, band, {"1", "2"})[3] == 1
    assert DS.paired(a, {}, band, set(a)) is None


# --- code review fixes (2026-10-20) --------------------------------------------------------------------

def test_priming_once_per_section_and_amp_group():
    rows = [_row(i, "A", f"s{i % 2}@1", amp=("pr12", "ac20")[i % 3 == 0]) for i in range(12)]
    order = DS.render_order(rows)
    keys = [(r["section"], r["amp"]) for r in order]
    assert keys == sorted(keys)                                        # groups contiguous
    last, primes = None, 0
    for k in keys:
        primes += DS.needs_priming(last, k)
        last = k
    assert primes == len(set(keys)) == 4
    assert DS.render_count(order) == 12 + 4
    assert DS.needs_priming(None, ("s", "pr12")) and not DS.needs_priming(("s", "pr12"), ("s", "pr12"))
    assert [r["i"] for r in DS.render_order(rows, reverse=True)] == [r["i"] for r in reversed(order)]


def test_primer_discards_one_render_per_change():
    class RR:
        def __init__(self):
            self.n = 0

        def render(self, di, sel, x):
            self.n += 1
            return np.zeros(4)

    p = DS.Primer(RR())
    for key in [("a", 1), ("a", 1), ("b", 1), ("b", 2), ("b", 2)]:
        p.render(key, None, None, None)
    assert p.primes == 3 and p.renders == 8 and p.rr.n == 8


def test_shard_sections_keeps_sections_whole_and_balanced():
    rows = [_row(i, "A", f"s{i % 7}@1") for i in range(70)] + [_row(100 + i, "A", "big@1") for i in range(15)]
    sh = DS.shard_sections(rows, 3)
    assert set(sh.values()) == {0, 1, 2} and sh == DS.shard_sections(list(reversed(rows)), 3)
    loads = [sum(1 for r in rows if sh[r["section"]] == k) for k in range(3)]
    assert max(loads) - min(loads) <= 15


def test_rest_needs_a_real_pilot_stem_or_mix_decision():
    with pytest.raises(SystemExit):
        DS.rest_allowed(None, "mix")
    with pytest.raises(SystemExit):
        DS.rest_allowed({"decision": "STEM", "smoke": True}, "mix")
    with pytest.raises(SystemExit):
        DS.rest_allowed({"decision": "STOP"}, "mix")
    with pytest.raises(SystemExit):
        DS.rest_allowed({"decision": "MIX"}, "stem")
    assert DS.rest_allowed({"decision": "MIX"}, "mix") == "MIX"
    assert DS.rest_allowed({"decision": "STEM"}, "stem") == "STEM"


def test_rows_decide_built_and_refusals_and_run_parity():
    items = [{"i": i} for i in range(5)]
    mix = {0: {}, 1: {"refused": "x"}, 2: {}, 3: {}}
    stem = {0: {}, 2: {"refused": "y"}}
    assert DS.refusals(mix, stem, {0, 1, 2, 3, 4}) == {1, 2}
    assert DS.pilot_unbuilt(items, mix, stem) == [3, 4]                 # 1 refused at mix needs no stem row
    runs = [{"arm": "D0", "seed": 1, "dropped_refused": [1, 2], "train": 3},
            {"arm": "Dmix", "seed": 1, "dropped_refused": [1], "train": 4}]
    bad = DS.check_run_parity(runs, {1, 2}, 3)
    assert len(bad) == 2 and all(b.startswith("Dmix") for b in bad)
    assert DS.check_run_parity(runs[:1], {1, 2}, 3) == []


# --- amendment 2: X-LANCE gtr_mss as a stem separator ---------------------------------------------------

def test_xl_single_chunk_exact():
    import numpy as np

    a = np.random.default_rng(0).standard_normal((2, DS.XL_CHUNK))
    assert np.allclose(DS.xl_run_chunked(lambda c: 2 * c, a), 2 * a)


def test_xl_crossfade_identity_on_long_input():
    import numpy as np

    a = np.random.default_rng(1).standard_normal((2, 1_323_000))
    assert len(DS.xl_chunk_starts(a.shape[1])) > 1
    assert np.allclose(DS.xl_run_chunked(lambda c: c, a), a)


def test_xl_short_input_pads():
    import numpy as np

    assert np.allclose(DS.xl_run_chunked(lambda c: c + 1, np.zeros((2, 500))), 1.0)


def test_cost_verdict():
    assert DS.cost_verdict([10, 10], [15, 15]) == (1.5, True)
    assert DS.cost_verdict([10, 10], [16, 15]) == (1.55, False)


def test_run_path_keeps_mega53_runs(tmp_path):
    assert DS.run_path(tmp_path, "Dstem", "5000", 1).name == "Dstem-5000-1.json"
    assert DS.run_path(tmp_path, "Dstem", "5000", 1, "xlance_g").name == "Dstem-5000-1-xlance_g.json"


def test_readout_kinds():
    assert DS.readout_kinds() == (("R_in", "mega53"), ("R_out", "htdemucs"))
    assert DS.readout_kinds("xlance_g") == (("R_in", "xlance_g"), ("R_out", "htdemucs"))
    with pytest.raises(SystemExit):
        DS.readout_kinds("htdemucs")


def test_xlance_g_paths_separate(tmp_path):
    assert DS.ex_path(tmp_path, 1234, "xlance_g") != DS.ex_path(tmp_path, 1234, "mega53")


def test_train_stem_sep():
    assert DS.train_stem_sep("D0", None) == "mega53"
    assert DS.train_stem_sep("Dstem", "xlance_g") == "xlance_g"
    with pytest.raises(SystemExit):
        DS.train_stem_sep("D0", "xlance_g")
    with pytest.raises(SystemExit):
        DS.train_stem_sep("Dstem", "htdemucs")


# --- step 3: the full models -----------------------------------------------------------------------------

def test_d_arm_follows_the_pilot_verdict():
    assert DS.d_arm({"decision": "STEM", "augmentation_kept": True}) == "Dstem"
    assert DS.d_arm({"decision": "STEM", "augmentation_kept": False}) == "Dstem-noaug"
    assert DS.d_arm({"decision": "MIX"}) == "Dmix"
    for bad in (None, {"decision": "STOP"}, {"decision": "STEM", "smoke": True}):
        with pytest.raises(SystemExit):
            DS.d_arm(bad)
    assert DS.d_arm({"decision": "STEM", "smoke": True}, smoke=True) == "Dstem"


def test_full_stems_are_mega53_while_amendment_2_is_a_draft():
    assert not DS.AMENDMENT2_IN_FORCE
    assert DS.full_stem_sep("Dstem", None) == "mega53" and DS.full_stem_sep("D0", None) == "mega53"
    with pytest.raises(SystemExit):
        DS.full_stem_sep("Dstem", "xlance_g")
    with pytest.raises(SystemExit):
        DS.full_stem_sep("D0", "xlance_g")


def test_full_build_state_and_counts():
    items = [{"i": i} for i in range(4)]
    mix = {0: {}, 1: {"refused": "x"}, 2: {}}
    stem = {0: {}}
    assert DS.full_unbuilt(items, mix, stem, True) == [2, 3]
    assert DS.full_unbuilt(items, mix, {}, False) == [3]                 # D_mix: the mix stage only
    rows = {i: {"i": i, "early_stop": i >= 8} for i in range(10)}
    kept = [rows[i] for i in (0, 1, 2, 3, 4, 8)]
    assert DS.full_counts_ok(kept, [5, 6, 7, 9], rows, n_train=8, n_es=2) == []
    assert len(DS.full_counts_ok(kept, [5, 6], rows, n_train=8, n_es=2)) == 2


def test_full_runs_have_their_own_folder(tmp_path):
    assert DS.run_path(tmp_path, "D0", "full", 20261044).parent == tmp_path / "full" / "runs"
    assert DS.run_path(tmp_path, "D0", "5000", 20261042).parent == tmp_path / "pilot" / "runs"
    assert DS.FULL_SEEDS == (20261042, 20261043, 20261044)


def test_seed_vs_ensemble_and_ensemble_error():
    o = _o([0.8, 0.2], [[0.2, 0.4, 0.9], [0.0, 0.0, 0.0]], sw=(1.0, -1.0), cats=((2.0, 0.0),))
    d, sw, mic = DS.seed_vs_ensemble(o, [0.3, 0.4, 0.0], [True, True], [1], [1, 1, 0], [1, 1], [1])
    assert math.isclose(d, 0.05) and sw == 0.5 and mic == 0.0
    d, sw, mic = DS.seed_vs_ensemble(o, [0.3, 0.4, 0.0], [True, True], [0], [0, 0, 0], [0, 0], [0])
    assert math.isnan(d) and math.isnan(sw) and math.isnan(mic)
    assert math.isclose(DS.ensemble_error([0.5, 0.5, 1.0], [0.4, 0.7, 0.0], [1, 1, 0]), 0.15)


def test_score_readout_pools_seeds_like_direct_existing():
    # two rows (the halves of example 7); seed 0 is confident in comp 0, seed 1 in comp 1
    s0 = _o([0.9, 0.1], [[0.2, 0.2], [0.8, 0.8]])
    s1 = _o([0.4, 0.6], [[0.5, 0.5], [0.6, 0.6]])
    outs = [[s0, s0], [s1, s1]]
    Y = [np.array([[0.3, 0.3]] * 2), np.ones((2, 2)), np.zeros((2, 1)), np.ones((2, 1)), np.zeros((2, 1), int),
         np.ones((2, 1))]
    sc = DS.score_readout(outs, [7, 7], Y)
    assert math.isclose(sc["ensemble"][7], 0.1)                        # seed 0's comp 0 (pooled weight 0.45)
    assert math.isclose(sc["per_seed"][0][7], 0.1) and math.isclose(sc["per_seed"][1][7], 0.3)
    assert math.isclose(sc["vs"][0][7][0], 0.0) and math.isclose(sc["vs"][1][7][0], 0.4)


def test_constant_predictor_medians_per_amp_and_class():
    def enc(label):
        c = np.array([label.get("a", 0.0), label.get("b", 0.0)])
        return c, np.array(["a" in label, "b" in label], float)

    rows = [{"amp": "pr12", "base": "clean", "label": {"a": v}} for v in (0.1, 0.2, 0.9)]
    rows += [{"amp": "pr12", "base": "crunch", "label": {"a": 0.5, "b": 0.3}}]
    med = DS.label_medians(rows, enc)
    assert med[("pr12", "clean")][0] == 0.2 and math.isnan(med[("pr12", "clean")][1])
    assert math.isclose(DS.const_error(med[("pr12", "clean")], [0.4, 0.0], [1, 0]), 0.2)
    with pytest.raises(SystemExit):
        DS.const_error(med[("pr12", "clean")], [0.4, 0.4], [1, 1])


def test_model_stop_rule():
    assert DS.model_stop((-0.02, -0.03, -0.01, 4)) == "OK"
    assert DS.model_stop((-0.02, -0.03, 0.001, 4)) == "STOP"
    assert DS.model_stop((0.02, 0.01, 0.03, 4)) == "STOP"
    assert DS.model_stop(None) == "STOP" and DS.model_stop((-0.1, -math.inf, math.inf, 1)) == "STOP"


def test_model_input_masks_conditions_and_zeroes():
    from learn import pretrain_set as PS

    s8 = np.full((96, 446), 100, np.uint8)
    m8 = np.full((96, 446), 120, np.uint8)
    xA, cA = DS.model_input(s8, m8, -20.0, -15.0, "A", "pr12", "clean", "Dstem")
    assert not xA[:, :, :PS.MASK_A_FRAMES].any() and xA[0, :, PS.MASK_A_FRAMES:].all()
    assert not xA[1].any() and cA[-1] == 0 and cA[-2] == 0.0             # (-20 + 20) / 10 is 0 too
    xB, cB = DS.model_input(s8, m8, -10.0, -15.0, "B", "pr12", "clean", "D0")
    assert xB.all() and math.isclose(cB[-2], 1.0) and math.isclose(cB[-1], 0.5)
    assert math.isclose(float(xB[0, 0, 0]), (PS.dequant(100) + 60) / 30, rel_tol=1e-6)
    xm, cm = DS.model_input(s8, m8, -10.0, -15.0, "B", "pr12", "clean", "Dmix")
    assert not xm[0].any() and xm[1].all() and cm[-2] == 0


def test_step4_half_applies_one_gain_to_both_channels():
    rng = np.random.default_rng(3)
    mix = 0.05 * rng.standard_normal(480_000)
    stem = 0.5 * mix
    s0, m0, ls0, lm0 = DS.step4_half(stem, mix, "B", 0.0)
    s6, m6, ls6, lm6 = DS.step4_half(stem, mix, "B", 6.0)
    assert math.isclose(ls6 - ls0, 6.0, abs_tol=0.01) and math.isclose(lm6 - lm0, 6.0, abs_tol=0.01)
    assert math.isclose(lm0 - ls0, 20 * math.log10(2), abs_tol=0.01)
    assert DS.match_share(m6.astype(int) - 12, m0) > 0.99                 # +6 dB is 12 grid steps


# --- step 4: renders, parity, report ---------------------------------------------------------------------

def test_step4_render_counts_and_cap():
    assert DS.step4_expected() == 63 + 126 * 2 + 6 == 321
    assert DS.step4_expected() <= DS.STEP4_CAP == 400
    assert DS.step4_group_renders(False) == 5 and DS.step4_group_renders(True) == 6
    groups = [(f"p{i}", a) for i in range(21) for a in ("pr12", "sw50r", "ac20")]
    assert sum(DS.step4_group_renders(False) for _ in groups) + 6 == 321
    rep = DS.step4_repeat_groups(groups)
    assert len(rep) == 6 and rep == DS.step4_repeat_groups(list(reversed(groups)))
    assert rep == sorted(random.Random(20261077).sample(sorted(groups), 6))


class _RR:
    def __init__(self):
        self.count, self.calls = 0, []

    def render(self, di, sel, x):
        self.count += 1
        self.calls.append(x)
        return np.zeros(8)


def _g():
    return {"sel": 0, "S": "S", "di": None, "di32": None, "ref": None, "lag": 0}


def _settings():
    return {a: {h: f"{a}{h}" for h in "AB"} for a in ("D", "D0")}


def test_run_group_primes_once_and_renders_each_arm_once():
    rr = _RR()
    rec = DS.run_group(rr, _g(), _settings(), False, None, lambda ref, y, di, lag: {"A": 1.0, "B": 2.0})
    assert rr.calls == ["S", "DA", "DB", "D0A", "D0B"] and rec["primes"] == 1 and rec["renders"] == 5
    assert set(rec["judge"]) == {"D|A", "D|B", "D0|A", "D0|B"} and rec["status"] == "done"
    rr = _RR()
    rec = DS.run_group(rr, _g(), _settings(), True, {"A": 1.0, "B": 2.0}, lambda ref, y, di, lag: {"A": 1.0, "B": 2.0})
    assert rr.calls == ["S", "S", "DA", "DB", "D0A", "D0B"] and rec["renders"] == 6 and rec["repeat"]["dev"] == 0


def test_run_group_repeat_miss_stops_before_any_arm():
    rr = _RR()
    rec = DS.run_group(rr, _g(), _settings(), True, {"A": 1.0, "B": 2.0},
                       lambda ref, y, di, lag: {"A": 1.0, "B": 2.0 * math.exp(2e-3)})
    assert rec["status"] == "stopped" and rr.calls == ["S", "S"] and not rec["judge"]
    rr = _RR()
    rec = DS.run_group(rr, _g(), _settings(), True, {"A": 1.0, "B": 2.0},
                       lambda ref, y, di, lag: {"A": 1.0, "B": math.inf})
    assert rec["status"] == "stopped"


def test_deviation_matches_local_objective():
    from learn import local_objective as LO

    for a, b in ((1.0, 1.1), (math.inf, 1.0), (math.inf, math.inf), (0.5, 0.5)):
        assert DS.deviation(a, b) == LO.deviation(a, b)


def test_parity_rule():
    assert DS.parity_ok([0.995, 1.0], [0.0, 0.009])
    assert not DS.parity_ok([0.989, 1.0], [0.0])
    assert not DS.parity_ok([1.0], [0.011])
    assert not DS.parity_ok([], [])


def test_refused_answer_scores_as_s_and_unrendered_stays_none():
    units = [{"d": {"S": 2.0}}, {"d": {"S": 3.0}}, {"d": {"S": 4.0}}]
    vals = [1.0, math.inf, None]
    n = DS.add_step4_arm(units, "D", lambda u: vals[units.index(u)])
    assert n == 1 and [u["d"]["D"] for u in units] == [1.0, 3.0, None]


def test_p_reading():
    assert DS.p_reading({"lo90": -0.1, "hi90": -0.01}) == "closer"
    assert DS.p_reading({"lo90": -0.1, "hi90": 0.01}) == "not shown"
    assert DS.p_reading({"lo90": 0.01, "hi90": 0.1}) == "worse"
    assert DS.p_reading(None) == "incomplete"


def test_step4_contrast_on_a_toy_table():
    # 4 bands x 1 part x 2 amps x 2 directions; D = S * e^(band effect); one D refused -> S (log 0)
    effect = {"b0": -0.2, "b1": -0.1, "b2": 0.0, "b3": -0.1}
    units = []
    for b, e in effect.items():
        for amp in ("pr12", "ac20"):
            for sh, held in (("A", "B"), ("B", "A")):
                d = {"S": 1.0, "H": 1.0, "M": 1.0, "D0": 1.0}
                units.append({"slug": f"p-{b}", "band": b, "cls": "clean" if b < "b2" else "crunch", "amp": amp,
                              "search": sh, "held": held, "d": d})
    vals = {id(u): math.exp(effect[u["band"]]) for u in units}
    vals[id(units[0])] = math.nan                                      # refused: scores as S
    DS.add_step4_arm(units, "D", lambda u: vals[id(u)])
    filters = {r: (lambda u: True) for r in DS.STEP4_ROWS}
    filters["unseen_by_part_c"] = lambda u: u["band"] in ("b0", "b1")
    c = DS.step4_contrast(units, "D", "S", filters)
    allr = c["rows"]["all"]["all"]
    b0 = (-0.2 * 3 + 0.0) / 4
    assert c["directions"] == 16
    assert math.isclose(allr["band_weighted_mean"], (b0 - 0.1 + 0.0 - 0.1) / 4)
    assert allr["bands"] == 4 and allr["lo90"] < allr["band_weighted_mean"] < allr["hi90"]
    assert allr["bands_negative"] == 3 and len(allr["leave_one_band_out"]) == 4
    assert math.isclose(c["rows"]["unseen_by_part_c"]["all"]["band_weighted_mean"], (b0 - 0.1) / 2)
    assert set(c["rows"]["all"]["per_class"]) == {"clean", "crunch"}
    units[1]["d"]["H"] = None                                          # an unscored fixed arm drops the direction
    assert DS.step4_contrast(units, "D", "S", filters)["directions"] == 15


def test_renders_of_this_step_are_counted_machine_wide():
    import re

    from learn import local_objective as LO

    for c in ("python -m learn.direct_stems render --shard 0/3", "python -m learn.direct_stems parity --device cpu",
              "python -m learn.direct_stems build --part rest --stage mix"):
        assert any(re.search(p, c) for p in LO.RENDERS)
    assert not any(re.search(p, "python -m learn.direct_stems report") for p in LO.RENDERS)


def test_known_answer_items():
    assert DS.KA_ITEM == {"s1": 1, "s2": 1, "s3": 3, "s4": 3}


# --- the code review's fixes (2026-10-21) ----------------------------------------------------------------

def test_step4_reads_only_when_complete():
    done = ["done"] * 63
    assert DS.step4_complete(126, done, False)
    assert not DS.step4_complete(125, done, False)
    assert not DS.step4_complete(126, done, True)                      # STOP.json present
    assert not DS.step4_complete(126, done[:-1] + ["stopped"], False)
    assert not DS.step4_complete(126, done[:-1], False)                # a group record missing


def test_ensemble_flag_only_when_ok_but_ensemble_does_not_clear():
    assert DS.ensemble_flag("OK", (-0.02, -0.03, -0.01, 4)) is None
    assert "does not clear" in DS.ensemble_flag("OK", (-0.02, -0.04, 0.001, 4))
    assert "n/a" in DS.ensemble_flag("OK", None)
    assert DS.ensemble_flag("STOP", (0.1, 0.0, 0.2, 4)) is None


def test_xlance_g_needs_amendment_2_in_force(monkeypatch):
    with pytest.raises(SystemExit):
        DS.require_amendment2("xlance_g", "train --n 5000")
    DS.require_amendment2("mega53", "build --stage stem")
    DS.require_amendment2("htdemucs", "build --stage stem")
    monkeypatch.setattr(DS, "AMENDMENT2_IN_FORCE", True)
    DS.require_amendment2("xlance_g", "train --n 5000")


def test_xl_unload_restores_path_and_forgets_its_modules(tmp_path):
    import types

    code = str(tmp_path / "code")
    (tmp_path / "code").mkdir()
    path = ["/x", code, "/y", code]
    mods = {"utils": types.SimpleNamespace(__file__=f"{code}/utils.py"),
            "models.a": types.SimpleNamespace(__file__=f"{code}/models/a.py"),
            "msst_utils": types.SimpleNamespace(__file__="/elsewhere/utils.py"), "builtin": types.SimpleNamespace()}
    assert DS.xl_unload(code, path, mods) == ["models.a", "utils"]
    assert path == ["/x", "/y"] and set(mods) == {"msst_utils", "builtin"}


def test_training_procs_counts_others_only():
    from learn import local_objective_1c as C

    ps = [(1, "python -m learn.direct_stems train --arm D0 --n full --seed 20261042"),
          (2, "python -m learn.direct_stems time-mps --device mps"), (3, "python -m learn.direct_stems train --arm X")]
    assert DS.training_procs(ps, {3}, C.is_training) == [1]


def test_lufs_medians_of_the_stored_training_mixes():
    rows = {1: {"target_lufs": -12.0, "lufs_mA": -13.0, "lufs_mB": -11.0}, 2: {"target_lufs": -14.0, "lufs_mA": -15.0,
            "lufs_mB": -14.0}, 3: {"refused": "x", "target_lufs": 0.0}}
    m = DS.lufs_medians(rows)
    assert m == {"examples": 2, "drawn_target_median": -13.0, "stored_half_lufs_median": -13.5}


# --- amendment 3: parity's LUFS gating --------------------------------------------------------------------

def _integ(l):
    l = np.asarray(l, float)
    return float(-0.691 + 10 * np.log10(np.mean(10 ** ((l + 0.691) / 10))))


def test_gate_toggle_matches_pyloudnorm_on_audio():
    pytest.importorskip("pyloudnorm")
    from learn import song_aug as SA

    rng = np.random.default_rng(5)
    x = rng.standard_normal(216_000) * np.repeat(rng.uniform(0.001, 0.3, 45), 4800)    # a sparse, uneven signal
    g = DS.gate_toggle(DS.block_loudness(x), SA.lufs(x))
    assert g["own_diff"] < 1e-9


def test_a_knife_edge_block_explains_a_miss():
    loud = [-30.0] * 20 + [-31.0] * 10
    b = -40.0
    for _ in range(100):                                 # the block 0.009 LU above the gate it helps set
        b = _integ(loud + [b]) - 10.0 + 0.009
    blocks = loud + [b]                                  # just above the gate: counted
    stored = _integ(loud)                                # the stored run had it just below: not counted
    g = DS.gate_toggle(blocks, stored)
    assert g["own_diff"] > 0.01 and 0 < g["gate_margin"] <= 0.05
    assert g["explained"] and g["toggled_diff"] < 1e-6
    assert DS.parity_ok([1.0, 1.0], [g["own_diff"], 0.0], explained=[g["explained"], False])


def test_a_genuine_level_change_is_not_explained():
    blocks = [-30.0] * 20 + [-50.0] * 10                 # no block near the gate
    stored = DS.gate_toggle(blocks, 0.0)["own"]
    shifted = [v + 0.17 for v in blocks]                 # the whole half 0.17 LU louder
    g = DS.gate_toggle(shifted, stored)
    assert math.isclose(g["own_diff"], 0.17, abs_tol=1e-9) and not g["explained"]
    assert abs(g["gate_margin"]) > 0.05
    assert not DS.parity_ok([1.0, 1.0], [g["own_diff"], 0.0], explained=[g["explained"], False])
    # a block at the gate that does not account for the difference does not excuse it either
    gate = _integ(blocks) - 10.0
    g2 = DS.gate_toggle([v + 0.17 for v in blocks] + [gate + 0.17 + 0.009], stored)
    assert not g2["explained"]


def _prow(i, h, ds, dm, gs=None, gm=None):
    return {"i": i, "half": h, "share_stem": 1.0, "share_mix": 1.0, "lufs_stem_diff": ds, "lufs_mix_diff": dm,
            "gate_stem": gs or {"gate_margin": 1.0, "toggled_diff": 0.2}, "gate_mix": gm or {"gate_margin": 1.0,
                                                                                            "toggled_diff": 0.2}}


def test_parity_verdict_tolerances_and_gate():
    v = DS.parity_verdict([_prow(1, "A", 0.02, 0.005)])
    assert v["ok"] and v["worst_unexplained_lufs_diff"] == 0.02            # stem within 0.03 LU
    assert not DS.parity_verdict([_prow(1, "A", 0.0, 0.02)])["ok"]          # mix stays at 0.01 LU
    assert not DS.parity_verdict([_prow(1, "A", 0.031, 0.0)])["ok"]
    knife = _prow(2, "B", 0.171, 0.0, gs={"gate_margin": -0.0027, "toggled_diff": 0.0044})
    v = DS.parity_verdict([_prow(1, "A", 0.001, 0.0), knife])
    assert v["ok"] and v["explained_by_gate"] == ["2B stem"] and v["worst_unexplained_lufs_diff"] == 0.001
    assert v["worst_lufs_diff"] == 0.171 and "post hoc" in v["rule"]
    level = _prow(2, "B", 0.17, 0.0, gs={"gate_margin": 0.6, "toggled_diff": 0.02})     # no block at the gate
    v = DS.parity_verdict([level])
    assert not v["ok"] and v["worst_unexplained_lufs_diff"] == 0.17
    far = _prow(2, "B", 0.17, 0.0, gs={"gate_margin": 0.01, "toggled_diff": 0.04})      # toggle does not explain it
    assert not DS.parity_verdict([far])["ok"]
    assert not DS.parity_verdict([_prow(1, "A", 0.0, 0.0), {"i": 3, "refused": "x"}])["ok"]
    assert "post-hoc rule" in DS.parity_line(v) and "worst unexplained" in DS.parity_line(v)


# --- amendment 4: the learning-curve probe ---------------------------------------------------------------

def test_curve_subsets_are_nested_stratified_and_deterministic():
    rows = [_row(i, f"B{i % 4}", f"s{i % 40}@1", amp=("pr12", "sw50r", "ac20")[i % 3]) for i in range(5000)]
    rows += [_row(10_000 + i, "B0", "es@1", es=True) for i in range(100)]
    sub = DS.curve_subsets(rows)
    assert len(sub[5000]) == 5000 and len(sub[2500]) == 2500 and len(sub[1250]) == 1250
    assert sub[1250] <= sub[2500] <= sub[5000] and not any(i >= 10_000 for i in sub[5000])
    assert sub == DS.curve_subsets(list(reversed(rows)))
    by = {}
    for i in sub[1250]:
        k = (f"B{i % 4}", i % 3)
        by[k] = by.get(k, 0) + 1
    assert max(by.values()) - min(by.values()) <= 1                    # 12 equal strata, proportional


def test_curve_fit_extrapolates_per_band_on_log2_n():
    by_n = {1250: {"a": 0.04, "b": 0.03}, 2500: {"a": 0.03, "b": 0.02}, 5000: {"a": 0.02, "b": 0.01}}
    f = DS.curve_fit(by_n, x_target=math.log2(20000))
    assert math.isclose(f["per_band"]["a"][0], -0.01) and math.isclose(f["per_band"]["b"][0], -0.01)
    assert math.isclose(f["per_band"]["a"][1], 0.02 - 0.01 * 2, abs_tol=1e-12)   # two more doublings
    assert math.isclose(f["at_target"][0], (0.0 - 0.01) / 2, abs_tol=1e-12) and f["at_target"][3] == 2


def test_probe_reading():
    assert DS.probe_reading((0.02, 0.005, 0.035, 4)) == "PAUSE"
    assert DS.probe_reading((0.01, -0.005, 0.025, 4)) == "CONTINUE"
    assert DS.probe_reading((-0.01, -0.02, -0.001, 4)) == "CONTINUE"
    assert DS.probe_reading(None) == "INCOMPLETE"


def test_curve_runs_live_with_the_pilot(tmp_path):
    assert DS.run_path(tmp_path, "Dstem", "1250", 20261042).parent == tmp_path / "pilot" / "runs"
    assert DS.run_path(tmp_path, "Dstem", "full", 20261042).parent == tmp_path / "full" / "runs"


def test_amendment_4_review_epoch_caps_capped_projection_and_advisory():
    assert DS.epoch_cap(1250) == 160 and DS.epoch_cap(2500) == 80 and DS.epoch_cap(5000) == 40
    assert 1250 * 160 == 2500 * 80 == 5000 * 40                        # equal optimisation steps
    assert math.isclose(DS.capped_projection(0.03, 0.02, 1), 0.015)
    assert math.isclose(DS.capped_projection(0.03, 0.02, 2), 0.0125)
    assert math.isclose(DS.capped_projection(0.03, 0.02, 0), 0.02)
    assert DS.advisory((0.01, -0.01, 0.03, 4), (-0.01, -0.02, 0.0, 4)) == "PROJECTED ABOVE CONSTANT"
    assert DS.advisory((-0.01, -0.03, 0.01, 4), (0.0, -0.01, 0.01, 4)) == "PROJECTED ABOVE CONSTANT"
    assert DS.advisory((-0.01, -0.03, 0.01, 4), (-0.005, -0.01, 0.0, 4)) is None
    assert DS.advisory(None, None) is None


def test_merge_pool_problems():
    rows = [_row(i, "A", f"s{i % 3}@1", base="clean") for i in range(6)] + [_row(9, "A", "x@1", base="crunch")]
    assert DS.merge_pool_problems(rows) == ["crunch: 1 section(s)"]
    assert DS.merge_pool_problems(rows[:6]) == []
