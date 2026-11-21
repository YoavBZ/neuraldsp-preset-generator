import itertools

import pytest

np = pytest.importorskip("numpy")

from learn import window_count as W  # noqa: E402


def test_windows_and_mean_match_the_locator():
    from learn import locator_truth as T

    x = np.random.default_rng(1).random(437)
    s = W.windows(437)
    assert np.array_equal(s, T._windows(437))
    assert np.allclose(W.win_mean(x, s), T._win_mean(x, s))


def test_conf_frames():
    hop = 2048 / 44100
    t = np.arange(40) * hop
    c = np.zeros(40)
    c[[3, 10, 11]] = [0.5, 0.49, 0.9]
    a = W.conf_frames(t, c, 20)
    want = np.zeros(20, bool)
    want[int(3 * hop / 0.1)] = True          # exactly at the threshold counts
    want[int(11 * hop / 0.1)] = True         # 0.49 does not
    assert np.array_equal(a, want)
    assert W.conf_frames(t, np.ones(40), 5).all()          # samples past the song's end are dropped


def test_active_is_relative_to_the_tracks_own_loudest_frame():
    db = np.array([-10.0, -29.0, -31.0, -50.0])
    assert W.active(db, 6, 20.0).tolist() == [True, True, False, False, False, False]
    assert W.active(db, 4, 30.0).tolist() == [True, True, True, False]


def _window_truth(target, others, tol):
    n = len(target)
    out = []
    for s in W.windows(n):
        t = target[s:s + W.WIN].mean() >= W.ACTIVE_SHARE
        u = np.zeros(W.WIN, bool)
        for o in others:
            u |= o[s:s + W.WIN]
        out.append(t and u.mean() <= tol)
    return np.array(out)


def test_alone_strict_and_tolerant_against_a_direct_loop():
    rng = np.random.default_rng(2)
    for _ in range(20):
        n = int(rng.integers(100, 400))
        target = rng.random(n) < 0.8
        others = [rng.random(n) < rng.choice([0.0, 0.005, 0.05, 0.3]) for _ in range(int(rng.integers(0, 3)))]
        for tol in (W.STRICT, W.TOLERANT, 0.3):
            assert np.array_equal(W.alone(target, others, W.windows(n), tol), _window_truth(target, others, tol))


def test_strict_refuses_a_single_frame_of_another_guitar():
    target = np.ones(100, bool)
    other = np.zeros(100, bool)
    other[57] = True
    s = W.windows(100)
    assert not W.alone(target, [other], s, W.STRICT).any()
    assert W.alone(target, [other], s, W.TOLERANT).all()
    assert W.alone(target, [], s).all()


def test_target_share_is_sixty_percent():
    t = np.zeros(100, bool)
    t[:60] = True
    assert W.alone(t, [], W.windows(100)).all()
    t[59] = False
    assert not W.alone(t, [], W.windows(100)).any()


def _brute_disjoint(hit, gap):
    idx = [i for i, h in enumerate(hit) if h]
    best = 0
    for k in range(1, len(idx) + 1):
        if any(all(b - a >= gap for a, b in zip(c, c[1:])) for c in itertools.combinations(idx, k)):
            best = k
    return best


def test_max_disjoint_matches_enumeration():
    rng = np.random.default_rng(3)
    for _ in range(40):
        hit = rng.random(int(rng.integers(1, 30))) < 0.4
        assert W.max_disjoint(hit, 4) == _brute_disjoint(hit, 4)


def test_same_part_base():
    assert W.same_part_base("ElecGtr1DT") == W.same_part_base("ElecGtr1") == W.same_part_base("elecgtr1dt")
    assert W.same_part_base("GTR 1") == W.same_part_base("gtr1")
    assert W.same_part_base("ElecGtr1") != W.same_part_base("ElecGtr2")


def test_part_counts_double_counts_as_another_guitar_in_the_deciding_count():
    n = 300
    target = np.ones(n, bool)
    double = np.zeros(n, bool)
    double[:150] = True
    c = W.part_counts(target, [double], [], W.windows(n))
    assert c["windows"] == 21 and c["target_windows"] == 21
    assert c["alone"] == 6 and c["alone_same_part"] == 21           # starts 150..200 only
    assert c["offers"] and c["offers_same_part"] and not c["offers_3"]
    assert c["disjoint"] == 1
    assert c["curve"]["1.0"] and c["curve"]["0.0"]


def test_w0_code():
    assert W.w0_code(0.5, 0.9) == "W-wide"
    assert W.w0_code(0.49, 0.9) == "W-some"
    assert W.w0_code(0.0, 0.2) == "W-rare"
    assert W.w0_code(0.0, 0.21) == "W-some"
    assert W.w0_code(None, None) == "incomplete"
    assert set(W.W0_TABLE) == {"W-wide", "W-some", "W-rare", "incomplete"}


def test_clustered_is_band_weighted_with_songs_once():
    r = W.clustered([("a", "s1", 1.0), ("a", "s2", 0.0), ("b", "s3", 1.0)])
    assert r["mean"] == pytest.approx(0.75)                    # band a 0.5, band b 1.0
    assert r["song_weighted"] == pytest.approx(2 / 3)
    assert r["bands"] == 2 and r["songs"] == 3


def _song(set_, band, sid, offers, single=False, **kw):
    parts = [{"part": f"p{i}", "role": None, "gain_class": kw.get("gc"), "mdb_label": kw.get("mdb"),
              "counts": {"offers": o, "offers_90": True, "offers_same_part": o, "offers_3": False,
                         "curve": {str(c): o or c >= 0.5 for c in W.CURVE}},
              **({"counts_annotation_only": {"offers": o, "offers_90": True, "offers_same_part": o,
                                             "offers_3": False, "curve": {str(c): o for c in W.CURVE}}}
                 if set_ == "medleydb" else {})}
             for i, o in enumerate(offers)]
    return {"set": set_, "id": f"{set_}:{sid}", "band": band, "single_guitar": single, "parts": parts}


def test_report_reads_each_set_alone_and_pooled():
    loc = [_song("locator", f"b{i}", f"s{i}", [True, False], gc="clean") for i in range(6)]
    mdb = [_song("medleydb", f"m{i}", f"t{i}", [i % 2 == 0], mdb="clean electric guitar") for i in range(6)]
    r = W.report({"locator": loc, "medleydb": mdb})
    assert r["locator"]["deciding"]["mean"] == pytest.approx(0.5)
    assert r["locator"]["deciding"]["lo90"] == pytest.approx(0.5)        # no spread
    assert r["locator"]["deciding"]["code"] == "W-wide"
    assert r["medleydb"]["deciding"]["mean"] == pytest.approx(0.5)
    assert r["medleydb"]["deciding"]["code"] == "W-some"
    assert r[W.POOL]["deciding"]["bands"] == 12 and r[W.POOL]["deciding"]["songs"] == 12
    assert r["headline"]["code"] == r[W.POOL]["deciding"]["code"]
    assert r["headline"]["per_set"] == {"locator": "W-wide", "medleydb": "W-some"}
    assert r["locator"]["side_90"]["mean"] == pytest.approx(1.0)
    assert r["locator"]["curve"]["1.0"]["mean"] == pytest.approx(1.0)
    assert r["locator"]["by_scope"]["in-scope"]["songs"] == 6
    assert r["medleydb"]["by_scope"]["mdb-clean"]["songs"] == 6
    assert r["medleydb"]["side_annotation_only"]["songs"] == 6
    assert r["locator"]["parts"] == 12 and r["locator"]["parts_offering"] == 6


def test_scope_of():
    assert W.scope_of({"gain_class": "crunch"}) == "in-scope"
    assert W.scope_of({"gain_class": "high-gain"}) == "high-gain"
    assert W.scope_of({"gain_class": None}) == "unlabelled"
    assert W.scope_of({"gain_class": None, "mdb_label": "distorted electric guitar"}) == "mdb-distorted"


def test_locator_groups_follow_the_replays_backing():
    s = {"song": "x", "mix": ["03_ElecGtr1Mic1.wav", "06_AcousticGtr.wav", "07_ElecGtr3.wav", "Keys GTR Amp.wav",
                              "01_Kick.wav", "09_Click.wav"],
         "files": ["02_ElecGtr1DI.wav", "03_ElecGtr1Mic1.wav", "04_ElecGtr1Mic2.wav", "05_ElecGtr2DI.wav",
                   "06_AcousticGtr.wav", "07_ElecGtr3.wav", "08_ElecGtr4Mic1.wav", "Keys GTR Amp.wav",
                   "09_Click.wav", "10_GtrClick.wav", "01_Kick.wav", "11_BassDI.wav"],
         "parts": [{"part": "ElecGtr1", "di": "02_ElecGtr1DI.wav", "ref": "03_ElecGtr1Mic1.wav", "alts": []}]}
    parts, unowned = W.locator_groups(s)
    assert parts["ElecGtr1"]["tracks"] == ["02_ElecGtr1DI.wav", "03_ElecGtr1Mic1.wav"]   # Mic2 is not in the mix
    assert set(unowned) == {"elecgtr2", "acousticgtr", "elecgtr3", "keys gtr"}            # a DI always counts
    assert "10_GtrClick.wav" not in sum(unowned.values(), [])
    assert "08_ElecGtr4Mic1.wav" not in sum(unowned.values(), [])                         # not in the mix


def test_mdb_guitar_stems():
    meta = {"stems": {"S01": {"instrument": "electric bass", "raw": {}},
                      "S02": {"instrument": "clean electric guitar", "filename": "a",
                              "raw": {"R01": {"filename": "x_RAW_02_01.wav"}}},
                      "S03": {"instrument": ["acoustic guitar"], "raw": {}},
                      "S04": {"instrument": "lap steel guitar", "raw": {}},
                      "S05": {"instrument": "mandolin", "raw": {}},
                      "S06": {"instrument": "banjo", "raw": {}}}}
    st = W.mdb_guitar_stems(meta)
    assert sorted(st) == ["S02", "S03", "S04"]
    assert st["S02"]["electric"] and not st["S03"]["electric"] and not st["S04"]["electric"]
    assert st["S02"]["raws"] == ["x_RAW_02_01.wav"]


def test_locator_song_counts_every_other_guitar(monkeypatch):
    n = 250
    db = {"m.wav": np.zeros(n), "02_ElecGtr1DI.wav": np.zeros(n), "03_ElecGtr1Mic1.wav": np.zeros(n),
          "06_AcousticGtr.wav": np.full(n, -100.0), "05_ElecGtr1DTDI.wav": np.full(n, -100.0)}
    db["06_AcousticGtr.wav"][:100] = 0.0           # the acoustic plays the first 10 s
    db["05_ElecGtr1DTDI.wav"][200:] = 0.0          # the double the last 5 s
    s = {"song": "x", "band": "b", "source": "t", "mix": ["m.wav", "03_ElecGtr1Mic1.wav", "06_AcousticGtr.wav"],
         "files": list(db),
         "parts": [{"part": "ElecGtr1", "di": "02_ElecGtr1DI.wav", "ref": "03_ElecGtr1Mic1.wav", "alts": []},
                   {"part": "ElecGtr1DT", "di": "05_ElecGtr1DTDI.wav", "ref": None, "alts": []}]}
    r = W.locator_song(s, db, {})
    c = r["parts"][0]["counts"]
    assert r["guitars"] == ["other:acousticgtr", "part:ElecGtr1", "part:ElecGtr1DT"]
    # windows start 0..150: the acoustic blocks starts < 100; the double blocks starts > 100
    assert c["alone"] == 1 and c["alone_same_part"] == 6
    assert not r["single_guitar"]
