"""learn/direct_stems.py: the pure parts of gate 1 (docs/direct-model-stems-plan.md)."""

import math

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
