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


def test_amendment_2_in_force_step_3_and_4_default_to_xlance_g():
    assert DS.AMENDMENT2_IN_FORCE and DS.STEP_SEP == "xlance_g" and DS.PILOT_SEP == "mega53"
    assert DS.full_stem_sep(None) == "xlance_g"
    assert DS.full_stem_sep("mega53") == "mega53"                 # the fallback, only when asked for
    with pytest.raises(SystemExit):
        DS.full_stem_sep("htdemucs")


def test_step_sep_follows_d():
    stem = {"decision": "STEM", "augmentation_kept": True}
    assert DS.step_sep(stem, None) == "xlance_g"
    assert DS.step_sep(stem, "mega53") == "mega53"
    assert DS.step_sep({"decision": "MIX"}, None) == "mega53"     # D_mix reads no stems: default names


def test_full_runs_carry_the_build_separator(tmp_path):
    # D0 reads no separated stem but drops the xlance_g stem stage's refusals: its own name, too
    assert DS.run_path(tmp_path, "D0", "full", 20261042, "xlance_g").name == "D0-full-20261042-xlance_g.json"
    assert DS.run_path(tmp_path, "Dstem", "full", 20261042, "xlance_g").parent.name == "runs"
    assert DS.run_path(tmp_path, "D0", "full", 20261042).name == "D0-full-20261042.json"


def test_full_models_refuse_runs_from_another_separator(tmp_path, monkeypatch):
    DS._save(tmp_path / "pilot" / "pilot-report.json", {"decision": "STEM", "augmentation_kept": True})
    rec = {"dropped_refused": [], "train": 10, "seed": 1}
    monkeypatch.setattr(DS, "load_full_runs", lambda root, arm, smoke=False, seeds=None, stem_sep="mega53":
                        ([object()], [{**rec, "arm": arm, "stem_sep": "mega53" if arm == "D0" else stem_sep}]))
    monkeypatch.setattr(DS, "load_nets", lambda: [])
    with pytest.raises(SystemExit, match="stems mega53, not xlance_g"):
        DS.full_models(tmp_path)
    _, _, _, bad = DS.full_models(tmp_path, smoke=True)
    assert bad == ["D0-1: stems mega53, not xlance_g"]


def test_stem_stage_defaults():
    assert DS.stem_stage_sep("rest", None) == "xlance_g"
    assert DS.stem_stage_sep("pilot", None) == "mega53" and DS.stem_stage_sep("vsep", None) == "mega53"
    assert DS.stem_stage_sep("pilot", "xlance_g") == "xlance_g"
    assert DS.stem_stage_sep("rest", "mega53") == "mega53"
    assert DS.stem_stage_sep("vsep", "htdemucs") == "htdemucs"


def test_step4_records_per_separator(tmp_path):
    assert DS.stems_manifest_path(tmp_path, "mega53") == tmp_path / "step4" / "stems" / "stems.json"
    assert DS.stems_manifest_path(tmp_path, "xlance_g") == tmp_path / "step4" / "stems" / "xlance_g" / "stems.json"
    assert DS.parity_path(tmp_path).name == "parity.json"
    assert DS.parity_path(tmp_path, "xlance_g").name == "parity-xlance_g.json"
    DS.save_parity(tmp_path, {"ok": True, "time": "2026-10-21 12:00:00"}, "xlance_g")
    DS.save_parity(tmp_path, {"ok": False, "time": "2026-10-21 13:00:00"}, "xlance_g")
    assert DS._load(tmp_path / "step4" / "parity-xlance_g-2026-10-21T120000.json")["ok"]
    assert not DS._load(DS.parity_path(tmp_path, "xlance_g"))["ok"]
    assert DS._load(DS.parity_path(tmp_path)) is None              # Mega-53's record untouched


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
    DS.require_amendment2("xlance_g", "train --n 5000")            # in force
    DS.require_amendment2("mega53", "build --stage stem")
    DS.require_amendment2("htdemucs", "build --stage stem")
    monkeypatch.setattr(DS, "AMENDMENT2_IN_FORCE", False)
    with pytest.raises(SystemExit):
        DS.require_amendment2("xlance_g", "train --n 5000")
    with pytest.raises(SystemExit):
        DS.full_stem_sep(None)


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


def test_failure_part_rows_list_xlance_failures():
    assert "telefunken-She's_Gone-GTR" in DS.XL_FAILURE_PARTS and len(DS.XL_FAILURE_PARTS) == 3
    units = [{"slug": "p", "d": {"S": 1.0, "D": math.e, "D0": 1.0}},
             {"slug": "p", "d": {"S": 1.0, "D": 1.0, "D0": None}},
             {"slug": "q", "d": {"S": 1.0, "D": 5.0, "D0": 5.0}}]
    swap = [{"slug": "p", "movement_vs_c_f": {"D": {"m_f": [[0.1, 1, 1], [0.3, 1, 1]], "b": [[0.2, 1, 1]]}}},
            {"slug": "p", "movement_vs_c_f": {"D": {"m_f": [[0.2, 1, 1], [0.2, 1, 1]], "b": [[0.0, 1, 1]]}}}]
    r = DS.failure_part_rows(units, swap, slugs=("p", "z"))
    assert r["p"]["directions"] == 2 and math.isclose(r["p"]["D-S"], 0.5)
    assert r["p"]["D0-S"] == 0.0 and r["p"]["D0 scored"] == 1
    assert math.isclose(r["p"]["movement"]["D m_f vs c_f"], 0.2) and math.isclose(r["p"]["movement"]["D b vs c_f"], 0.1)
    assert r["z"] == {"directions": 0, "D-S": None, "D scored": 0, "D0-S": None, "D0 scored": 0, "movement": {}}


def test_xlance_transfer_table_pairs_the_same_examples():
    band_of = {"1": "a", "2": "a", "3": "b", "4": "b", "5": "c"}
    keep = {"1", "2", "3", "4", "5"}
    const = {i: 0.2 for i in keep}
    m = [{"1": 0.20, "2": 0.22, "3": 0.18, "4": 0.21, "5": 0.3}, {"1": 0.22, "2": 0.20, "3": 0.20, "4": 0.19}]
    x = [{i: v - 0.01 for i, v in r.items()} for r in m]
    t = DS.xlance_transfer_table({"Dstem": x, "D0": [m[0]]}, {"Dstem": m, "D0": []}, const, band_of, keep)
    v = t["Dstem xlance_g-mega53"]
    assert math.isclose(v[0], -0.01, abs_tol=1e-12) and v[3] == 2          # "5" lacks seed 1: left out
    assert math.isclose(t["Dstem mega53-constant"][0], 0.0025, abs_tol=1e-12)
    assert math.isclose(t["Dstem xlance_g-constant"][0], -0.0075, abs_tol=1e-12)
    assert "Dstem seed 1 xlance_g-mega53" in t and t["D0 xlance_g-mega53"] is None


# --- amendment 5: the readout E rewards -------------------------------------------------------------

def _mix(w, mu, sd):
    """One row's (logpi [K], mu [K, n], ls [K, n]) from weights, means and sds."""
    mu = np.asarray(mu, float)
    return np.log(np.asarray(w, float)), mu, np.log(np.broadcast_to(np.asarray(sd, float), mu.shape))


def _true_median(w, mu, sd):
    from scipy.optimize import brentq
    from scipy.stats import norm

    def f(x):
        return sum(wk * norm.cdf((x - m) / s) for wk, m, s in zip(w, mu, sd)) - 0.5

    return brentq(f, -5, 5, xtol=1e-14)


def test_median_of_a_known_mixture():
    lp, mu, ls = _mix([0.7, 0.3], [[0.2], [0.8]], 0.05)
    m = DS.mixture_median(lp, mu, ls)
    assert m.shape == (1,) and math.isclose(m[0], _true_median([0.7, 0.3], [0.2, 0.8], [0.05, 0.05]), abs_tol=1e-9)
    assert abs(m[0] - 0.2) > 0.02                                    # not the top component's mean
    # an equal two-component mixture: the midpoint; one component: its mean; per dim, vectorised over rows
    lp2, mu2, ls2 = _mix([0.5, 0.5], [[0.3, 0.1], [0.7, 0.1]], [[0.1, 0.2], [0.1, 0.2]])
    rows = DS.mixture_median(np.stack([lp, lp2[[0, 1]]]), np.stack([np.c_[mu, mu], mu2]), np.stack([np.c_[ls, ls], ls2]))
    assert rows.shape == (2, 2)
    assert math.isclose(rows[1, 0], 0.5, abs_tol=1e-9) and math.isclose(rows[1, 1], 0.1, abs_tol=1e-9)
    # four components, unequal sds, against a root finder
    w, mus, sds = [0.1, 0.4, 0.3, 0.2], [0.05, 0.4, 0.55, 0.9], [0.3, 0.02, 0.15, 0.05]
    lp4, mu4, ls4 = _mix(w, [[m] for m in mus], [[s] for s in sds])
    assert math.isclose(DS.mixture_median(lp4, mu4, ls4)[0], _true_median(w, mus, sds), abs_tol=1e-9)
    # clipped to [0, 1]
    lp5, mu5, ls5 = _mix([1.0], [[1.3]], 0.1)
    assert DS.mixture_median(lp5, mu5, ls5)[0] == 1.0


def test_a2_averages_the_medians_over_seeds_and_halves():
    one = _mix([1.0], [[0.2, 0.6]], 0.1)
    two = _mix([1.0], [[0.4, 0.2]], 0.1)
    s0 = [one + (None, None), two + (None, None), one + (None, None)]       # rows: example 7 (A, B), example 8
    s1 = [two + (None, None), two + (None, None), two + (None, None)]
    meds, ans = DS.median_answers([s0, s1], [7, 7, 8])
    assert len(meds) == 2 and meds[0].shape == (3, 2)
    assert np.allclose(ans[7], np.mean([[0.2, 0.6], [0.4, 0.2], [0.4, 0.2], [0.4, 0.2]], axis=0))    # the mean of the medians
    assert np.allclose(ans[8], [0.3, 0.4])


def test_pull_fit_is_0_for_an_uninformative_model_and_1_for_a_perfect_one():
    c = 0.5
    labels = np.array([0.2, 0.5, 0.8, 0.2, 0.5, 0.8])
    noise = np.array([-0.2, -0.2, -0.2, 0.2, 0.2, 0.2])                     # independent of the label
    assert DS.fit_pull(noise, labels - c) == (0.0, 0.0)
    assert DS.fit_pull(labels - c, labels - c) == (1.0, 1.0)                # the answer is the label
    assert DS.fit_pull(np.zeros(6), labels - c) == (0.0, 0.0)              # never leaves the constant
    b, bu = DS.fit_pull(0.5 * (labels - c), labels - c)                     # spread too narrow for its correlation
    assert b == 1.0 and math.isclose(bu, 2.0)
    b, bu = DS.fit_pull(-(labels - c), labels - c)                          # anti-informative
    assert b == 0.0 and bu < 0


def test_pull_fit_can_only_tie_or_beat_the_constant_and_a1a2_on_its_fitting_set():
    rng = np.random.default_rng(5)
    for _ in range(50):
        n = int(rng.integers(5, 80))
        c = float(rng.uniform(0.2, 0.8))
        theta = rng.uniform(0, 1, n)
        pred = np.clip(rng.uniform(0, 1) * theta + rng.normal(0, rng.uniform(0.01, 0.5), n) + rng.normal(0, 0.1), 0, 1)
        b, bu = DS.fit_pull(pred - c, theta - c)
        assert 0.0 <= b <= 1.0
        e = np.abs(c + b * (pred - c) - theta).sum()
        assert e <= np.abs(c - theta).sum() + 1e-9 and e <= np.abs(pred - theta).sum() + 1e-9
        grid = min(np.abs(c + g * (pred - c) - theta).sum() for g in np.linspace(0, 1, 201))
        assert e <= grid + 1e-9                                             # the exact minimum over [0, 1]


def test_pull_table_is_per_knob_and_cell_and_respects_masks():
    ans = {1: np.array([0.9, 0.3]), 2: np.array([0.1, 0.3]), 3: np.array([0.6, 0.6])}
    lab = {1: (np.array([0.9, 0.0]), np.array([1.0, 0.0])), 2: (np.array([0.1, 0.0]), np.array([1.0, 0.0])),
           3: (np.array([0.5, 0.5]), np.array([1.0, 1.0]))}
    cell_of = {1: ("pr12", "clean"), 2: ("pr12", "clean"), 3: ("ac20", "crunch")}
    med = {("pr12", "clean"): np.array([0.5, 0.5]), ("ac20", "crunch"): np.array([0.5, 0.5])}
    t = DS.fit_pull_table(ans, lab, cell_of, med)
    assert t[("pr12", "clean")]["b"][0] == 1.0 and math.isnan(t[("pr12", "clean")]["b"][1])
    assert t[("pr12", "clean")]["examples"] == 2 and t[("ac20", "crunch")]["b"][0] == 0.0
    back = DS.table_from_json(DS.table_json(t))
    assert back[("pr12", "clean")]["b"][0] == 1.0 and math.isnan(back[("pr12", "clean")]["b"][1])
    assert np.allclose(DS.pull([0.9, 0.2], [0.5, 0.5], [0.25, np.nan]), [0.6, 0.2])     # NaN b: unchanged
    b, gaps = DS.cell_b(t, ("pr12", "clean"), [1, 1])
    assert gaps == 1 and b[1] == 0.0
    assert DS.cell_b(t, ("sw50r", "clean"), [1, 0])[1] == 1
    with pytest.raises(SystemExit):
        DS.fit_pull_table(ans, lab, cell_of, {**med, ("pr12", "clean"): np.array([np.nan, 0.5])})


def test_score_medians_reads_a1_a2_and_the_pull():
    s0 = [_mix([1.0], [[0.2]], 0.1) + (None, None)] * 2
    s1 = [_mix([1.0], [[0.6]], 0.1) + (None, None)] * 2
    Y = [np.array([[0.5]] * 2), np.ones((2, 1))]
    med = {("pr12", "clean"): np.array([0.3])}
    table = {("pr12", "clean"): {"b": np.array([0.5]), "b_unconstrained": np.array([0.5]), "examples": 1}}
    sc, ans, lab, gaps = DS.score_medians([s0, s1], [7, 7], Y, {7: ("pr12", "clean")}, med, table)
    assert math.isclose(sc["A1"][0][7], 0.3) and math.isclose(sc["A1"][1][7], 0.1)
    assert math.isclose(ans[7][0], 0.4) and math.isclose(sc["A1+A2"][7], 0.1)
    assert math.isclose(sc["A1+A2+A3"][7], 0.15) and gaps == 0                # 0.3 + 0.5 (0.4 - 0.3) = 0.35


def _per(model_vals):
    """{model: {tag: {i: E}}} with every tag at the same values."""
    return {m: {t: dict(v) for t in DS.READOUT_TAGS} for m, v in model_vals.items()}


def test_the_e_check_reads_the_declared_answer():
    band_of = {i: "abcd"[i % 4] for i in range(8)}
    const = {i: 0.20 for i in range(8)}
    better = {i: 0.18 + 0.001 * (i % 4) for i in range(8)}
    worse = {i: 0.22 + 0.001 * (i % 4) for i in range(8)}
    per = _per({"D": worse, "D0": worse})
    per["D"]["A1+A2+A3"] = better                                           # the declared answer beats the constant
    con = DS.readout_contrasts(per, const, band_of, set(const))
    assert DS.E_CHECK in con and DS.model_stop(con[DS.E_CHECK]) == "OK"
    assert DS.model_stop(con["D-constant [top]"]) == "STOP"                  # the old readout would stop
    assert "D-D0 [A1+A2+A3]" in con and con["D-D0 [A1+A2+A3]"][0] < 0
    per = _per({"D": better, "D0": better})
    per["D"]["A1+A2+A3"] = worse                                            # only the old readouts beat it
    con = DS.readout_contrasts(per, const, band_of, set(const))
    assert DS.model_stop(con[DS.E_CHECK]) == "STOP" and DS.model_stop(con["D-constant [top]"]) == "OK"
    assert "A1+A2's (no pull)" in DS.ensemble_flag("OK", con["D-constant [A1+A2+A3]"], "A1+A2's (no pull)")


def test_band_crossfit_scores_each_band_with_the_others_weights():
    band_of = {i: "ab"[i % 2] for i in range(8)}
    cell_of = {i: ("pr12", "clean") for i in range(8)}
    med = {("pr12", "clean"): np.array([0.5])}
    lab = {i: (np.array([0.1 * i]), np.array([1.0])) for i in range(8)}
    ans = {i: np.array([0.1 * i]) for i in range(8)}                         # perfect: b = 1 everywhere
    e, gaps = DS.band_crossfit(ans, lab, cell_of, med, band_of)
    assert gaps == 0 and all(math.isclose(v, 0.0, abs_tol=1e-12) for v in e.values()) and len(e) == 8


def test_section_folds_keep_sections_whole_and_are_seeded():
    rows = [{"i": i, "section": f"s{i // 3}"} for i in range(30)]
    f = DS.section_folds(rows)
    assert f == DS.section_folds(list(reversed(rows))) and set(f.values()) == {0, 1}
    for s in {r["section"] for r in rows}:
        assert len({f[r["i"]] for r in rows if r["section"] == s}) == 1
    assert sum(1 for r in rows if f[r["i"]] == 0) == 15                      # 5 of 10 sections
    assert DS.READOUT_CHECK_SEED == 20261086


def test_silent_knobs_leave_e_when_the_right_cab_is_off():
    from learn import song_model as SM

    on = {"cabParameters/rightCabActive": "true", "cabParameters/rightCabPosition": 0.3,
          "cabParameters/rightCabDistance": 0.4, "cabParameters/rightCabMicLevel": 0.5, "cabParameters/rightMicType": "2",
          "cabParameters/leftCabPosition": 0.1, "parameters/inputGain": 0.6}
    off = {**on, "cabParameters/rightCabActive": "false"}
    gated = [SM.CONT.index(n) for n in DS.SILENT_GATES["cabParameters/rightCabActive"] if n in SM.CONT]
    assert len(gated) == 3
    _, cm_on, *_, km_on = DS.encode_audible(on)
    _, cm_off, *_, km_off = DS.encode_audible(off)
    assert all(cm_on[j] == 1 for j in gated) and all(cm_off[j] == 0 for j in gated)
    keep = [SM.CONT.index("cabParameters/leftCabPosition"), SM.CONT.index("parameters/inputGain")]
    assert all(cm_off[j] == 1 for j in keep)
    r = SM.CAT.index("cabParameters/rightMicType")
    assert km_on[r] == 1 and km_off[r] == 0
    no_switch = {k: v for k, v in on.items() if k != "cabParameters/rightCabActive"}
    assert all(DS.encode_audible(no_switch)[1][j] == 1 for j in gated)       # an unlabelled switch masks nothing
    # stacked labels, the inputs untouched; E of a toy answer drops the silent knobs only
    Y = [np.stack(z) for z in zip(SM.encode(on), SM.encode(off))]
    Ym = DS.silent_masks(Y)
    assert Y[1][1, gated[0]] == 1 and Ym[1][1, gated[0]] == 0 and Ym[1][0, gated[0]] == 1
    c, cm = SM.encode(off)[:2]
    guess = np.where(np.arange(len(c)) == gated[0], 1.0, c)                 # wrong only on a silent knob
    assert DS.ensemble_error(guess, c, cm) > 0 and DS.ensemble_error(guess, c, Ym[1][1]) == 0


def test_silent_gates_match_the_labelled_space_and_song_relabel():
    from learn import knob_ceiling as K
    from learn import song_model as SM
    from learn import song_relabel as SR

    (switch, gated), = DS.SILENT_GATES.items()
    assert switch == SR.RIGHT_ACTIVE and set(gated) == set(SR.RIGHT_GATED) | {SR.RIGHT_MIC}
    assert switch in SM.SW and all(n in SM.CONT or n in SM.CAT for n in gated)
    names = {d.name for d in K.space("pr12")}
    assert switch in names and set(gated) <= names
    assert DS.audible("cabParameters/rightCabMicLevel", {"cabParameters/rightCabActive": "false"}) is False
    assert DS.audible("cabParameters/rightCabMicLevel", {"cabParameters/rightCabActive": "true"}) is True
    assert DS.audible("pr12Amp/pr12Volume", {"cabParameters/rightCabActive": "false"}) is True


def test_constant_medians_skip_silent_labels():
    rows = [{"amp": "pr12", "base": "clean", "label": {"cabParameters/rightCabActive": a,
                                                         "cabParameters/rightCabPosition": v, "parameters/inputGain": v}}
            for a, v in (("true", 0.1), ("true", 0.2), ("false", 0.9), ("false", 0.95), ("false", 0.99))]
    from learn import song_model as SM

    m = DS.label_medians(rows, DS.encode_audible)[("pr12", "clean")]
    j, g = SM.CONT.index("cabParameters/rightCabPosition"), SM.CONT.index("parameters/inputGain")
    assert math.isclose(m[j], 0.15, rel_tol=1e-6) and math.isclose(m[g], 0.9, rel_tol=1e-6)   # audible labels only
    assert math.isclose(DS.label_medians(rows, SM.encode)[("pr12", "clean")][j], 0.9, rel_tol=1e-6)


def test_step4_needs_amendment_5s_readout_from_the_same_models():
    recs = {"D": [{"seed": 1, "model_sha256": "a"}], "D0": [{"seed": 1, "model_sha256": "b"}]}
    models = {"D": (None, "Dstem", recs["D"]), "D0": (None, "D0", recs["D0"]), "D_existing": (None, "D0", [])}
    t = DS.table_json({("pr12", "clean"): {"b": np.array([0.5]), "b_unconstrained": np.array([0.5]), "examples": 3}})
    ro = {"readout_rule": DS.READOUT_RULE, "models": {"D": {"1": "a"}, "D0": {"1": "b"}},
          "pull": {"D": t, "D0": t, "D_existing": t}, "constant": DS.medians_json({("pr12", "clean"): np.array([0.4])})}
    pulls, cmed = DS.step4_pulls(ro, models)
    assert pulls["D"][("pr12", "clean")]["b"][0] == 0.5 and cmed[("pr12", "clean")][0] == 0.4
    with pytest.raises(SystemExit):
        DS.step4_pulls(None, models)
    with pytest.raises(SystemExit):
        DS.step4_pulls({**ro, "readout_rule": None}, models)
    with pytest.raises(SystemExit):
        DS.step4_pulls({**ro, "models": {"D": {"1": "x"}, "D0": {"1": "b"}}}, models)
    with pytest.raises(SystemExit):
        DS.step4_pulls({**ro, "smoke": True}, models)


def test_step4_renders_wait_for_amendment_6s_gate(tmp_path):
    ok, why = DS.step3_gate(tmp_path)                                       # the E check never opens step 4
    assert ok is False and "amendment 6" in why and DS.STEP3_GATE == "amendment 6"


def test_readout_glue_end_to_end_on_toy_models(tmp_path, monkeypatch, capsys):
    """cmd_readout with the models, rows and network outputs faked (no torch): the early-stopping fit,
    the masked and unmasked readings, the E check (descriptive) and the stored pull for step 4."""
    import types

    from learn import song_model as SM

    rng = np.random.default_rng(11)
    names = ["parameters/inputGain", "pr12Amp/pr12Volume", "cabParameters/rightCabPosition"]

    def row(i, band, base, early_stop=False):
        lab = {n: float(rng.uniform(0, 1)) for n in names}
        lab["cabParameters/rightCabActive"] = "true" if rng.random() < 0.7 else "false"
        return {"i": i, "band": band, "amp": "pr12", "base": base, "early_stop": early_stop, "label": lab}

    pool = [row(i, "t1", ("clean", "crunch")[i % 2]) for i in range(80)]
    pool += [row(100 + i, ("t1", "t2")[i % 2], ("clean", "crunch")[(i // 2) % 2], True) for i in range(40)]
    vsep = [row(1_000_000 + i, f"v{i % 4}", ("clean", "crunch")[(i // 4) % 2]) for i in range(48)]
    ctx = types.SimpleNamespace(pool=pool, parts={"vsep": vsep}, tag={r["i"]: None for r in vsep})
    recs = [{"seed": s, "model_sha256": f"h{s}", "dropped_refused": []} for s in (1, 2, 3)]
    models = {"D": (["D"] * 3, "Dstem", recs), "D0": (["D0"] * 3, "D0", recs), "D_existing": (["DE"] * 3, "D0", [])}
    by_i = {r["i"]: r for r in pool + vsep}

    def fake_rows(nets, rows, make, chunk=64, batch=128):
        outs, who, ys = [[] for _ in nets], [], []
        for r in rows:
            enc = SM.encode(r["label"])
            for _ in "AB":
                who.append(r["i"])
                ys.append(enc)
                for k, kind in enumerate(nets):
                    good = enc[0] if kind == "D" else np.full(len(SM.CONT), 0.5)
                    mu = np.stack([np.clip(good + rng.normal(0, 0.02, len(good)), 0, 1), np.full(len(good), 0.5)])
                    outs[k].append((np.log([0.8, 0.2]), mu, np.full(mu.shape, -3.0), np.zeros(len(SM.SW)),
                                    [np.zeros(len(SM.MICS)) for _ in SM.CAT]))
        return outs, who, [np.stack(z) for z in zip(*ys)]

    monkeypatch.setattr(DS, "Ctx", lambda: ctx)
    monkeypatch.setattr(DS, "full_models", lambda root, smoke, sep: (models, "Dstem", {"decision": "STEM"}, []))
    monkeypatch.setattr(DS, "step_sep", lambda report, sep, smoke=False: "xlance_g")
    monkeypatch.setattr(DS, "vsep_ready", lambda ctx, root, smoke, sep: {"R_in": vsep, "R_out": vsep})
    monkeypatch.setattr(DS, "build_rows", lambda root, part, stage: {r["i"]: {"mastered": False} for r in vsep})
    monkeypatch.setattr(DS, "vdev_rows", lambda: [dict(r) for r in vsep])
    monkeypatch.setattr(DS, "ex_path", lambda root, i, kind: tmp_path)
    monkeypatch.setattr(DS, "run_rows", fake_rows)
    DS.cmd_readout(types.SimpleNamespace(out=str(tmp_path), smoke=False, limit=None, sep=None))
    out = capsys.readouterr().out
    assert "E check (descriptive; Amendment 6 decides): OK" in out and "MODEL " not in out
    ro = DS._load(tmp_path / "full" / "readout.json")
    assert ro["decides"] == "amendment 6" and ro["e_check"] == "OK" and "decision" not in ro
    assert set(ro["pull"]) == {"D", "D0", "D_existing"} and not any(ro["gaps"].values())
    assert ro["fitting_set"]["examples"] == 40 and set(ro["contrasts"]) == {"R_in", "R_out", "V_dev"}
    assert DS.E_CHECK in ro["contrasts"]["R_in"] and DS.E_CHECK in ro["contrasts_unmasked"]["R_in"]
    assert "D-constant [A1+A2+A3, R_in band cross-fit, descriptive]" in ro["contrasts"]["R_in"]
    j = SM.CONT.index("parameters/inputGain")
    assert ro["pull"]["D"]["pr12|clean"]["b"][j] > 0.5                       # an informative model keeps its answer
    pulls, cmed = DS.step4_pulls(ro, models)                                # what step 4 reads back
    assert ("pr12", "crunch") in pulls["D_existing"] and np.isfinite(cmed[("pr12", "clean")][j])
    # the constant's medians skip silent labels: the right cab's position over audible training labels only
    k = SM.CONT.index("cabParameters/rightCabPosition")
    aud = [by_i[r["i"]]["label"]["cabParameters/rightCabPosition"] for r in pool
           if not r["early_stop"] and r["base"] == "clean" and r["label"]["cabParameters/rightCabActive"] == "true"]
    assert math.isclose(cmed[("pr12", "clean")][k], float(np.median(np.float32(aud))), rel_tol=1e-6)


def test_pull_fit_weights_each_example_by_its_scored_knobs():
    # one knob, three examples; the first scores 1 knob, the others 4 (the rest silent or unlabelled)
    d, r = [0.2, 0.2, 0.2], [0.2, -0.2, -0.2]
    assert DS.fit_pull(d, r)[0] == 0.0                                       # unweighted: two examples say 0
    assert DS.fit_pull(d, r, [1, 4, 4])[0] == 1.0                            # per-example E: the first weighs 4x
    # fit_pull_table passes each example's scored dims: the fit minimises example-mean masked E
    rng = np.random.default_rng(3)
    ans, lab = {}, {}
    for i in range(40):
        m = np.ones(4) if i % 2 else np.array([1.0, 0, 0, 0])
        theta = rng.uniform(0, 1, 4)
        ans[i] = np.clip(theta + rng.normal(0, 0.3, 4) + (0.3 if i % 2 else -0.2), 0, 1)
        lab[i] = (theta, m)
    cell_of = {i: ("pr12", "clean") for i in ans}
    med = {("pr12", "clean"): np.full(4, 0.5)}
    b = DS.fit_pull_table(ans, lab, cell_of, med)[("pr12", "clean")]["b"]

    def mean_e(bb):
        return np.mean([DS.ensemble_error(DS.pull(ans[i], med[("pr12", "clean")], bb), *lab[i]) for i in ans])

    for g in np.linspace(0, 1, 101):                                          # no other b0 does better
        assert mean_e(b) <= mean_e(np.r_[g, b[1:]]) + 1e-12
