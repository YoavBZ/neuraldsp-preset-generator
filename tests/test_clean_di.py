"""The clean DI library's pure parts (`learn/clean_di.py`, docs/clean-di-library-plan.md)."""

import importlib.util
import os
import pathlib

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import clean_di as C  # noqa: E402

SR = C.SR
RNG = np.random.default_rng(7)


def guitarish(seconds=10.0, f=110.0, level=0.1, sr=SR):
    """Plucked notes: decaying harmonic tones every 0.5 s (no stationary line) over a -100 dBFS
    noise floor."""
    t = np.arange(int(seconds * sr)) / sr
    x = 1e-5 * np.random.default_rng(int(f)).standard_normal(len(t))
    notes = [f, f * 1.26, f * 1.5, f * 1.68, f * 2.0]
    for i, s in enumerate(np.arange(0, seconds, 0.5)):
        m = (t >= s)
        tt = t[m] - s
        g = notes[i % len(notes)] * (1 + 0.003 * (i % 3))
        x[m] += level * np.exp(-tt * 3) * sum(np.sin(2 * np.pi * g * k * tt) / k for k in range(1, 6))
    return x


def hum_series(seconds=10.0, f0=60.0, level=1e-3, ks=(1, 3, 5), sr=SR):
    t = np.arange(int(seconds * sr)) / sr
    return sum(level / k * np.sin(2 * np.pi * f0 * k * t + k) for k in ks)


# --- sections: parity with multi_section ---------------------------------------------------------

def test_sections_match_multi_section_when_importable():
    if importlib.util.find_spec("learn.multi_section") is None:
        pytest.skip("learn.multi_section is not on this branch")
    from learn import multi_section as M

    assert (C.SEC_S, C.HOP_S, C.FRAME, C.FHOP, C.PLAY_DB, C.MIN_ACTIVE, C.MIN_ACTIVE_HALF, C.HALVES) == \
        (M.SEC_S, M.HOP_S, M.FRAME, M.FHOP, M.PLAY_DB, M.MIN_ACTIVE, M.MIN_ACTIVE_HALF, M.HALVES)
    x = guitarish(30.0)
    x[int(12 * SR):int(19 * SR)] = 0
    a, b = C.frame_db(x), M.frame_db(x)
    assert np.allclose(a, b)
    assert (C.playing(a) == M.playing(b)).all()
    assert C.grid(len(x)) == M.grid(len(x))
    for s in C.grid(len(x)):
        assert C.section_activity(C.playing(a), s) == M.section_activity(M.playing(b), s)
    assert C.disjoint([0, 5 * SR, 10 * SR, 25 * SR]) == M.disjoint([0, 5 * SR, 10 * SR, 25 * SR])


def test_activity_rule():
    x = guitarish(20.0)
    play = C.playing(C.frame_db(x))
    share, halves = C.section_activity(play, 0)
    assert C.passes(share, halves)
    y = x.copy()
    y[int(1 * SR):int(5.5 * SR)] = 0
    play = C.playing(C.frame_db(y))
    assert not C.passes(*C.section_activity(play, 0))
    assert C.disjoint([0, 5 * SR, 10 * SR, 15 * SR]) == [0, 10 * SR]


# --- screens -------------------------------------------------------------------------------------

def test_clip_runs_find_flat_tops_not_smooth_peaks():
    x = 0.5 * np.sin(2 * np.pi * 100 * np.arange(SR) / SR)
    assert len(C.clip_runs(x)) == 0                       # a smooth peak dwells near the top but moves
    low = np.sin(2 * np.pi * 82.4 * np.arange(SR) / SR)  # normalised low E: a "-Norm" file's case
    assert len(C.clip_runs(low)) == 0
    y = np.clip(1.4 * x, -0.5, 0.5)
    assert len(C.clip_runs(y)) >= 150                     # two flat tops per cycle, 100 cycles
    z = x.copy()
    z[1000:1003] = 0.5                                    # one flat run of three at the peak
    assert len(C.clip_runs(z, peak=0.5)) == 1


def test_dropouts_and_hard_cuts():
    sr = 44100
    x = 0.1 * np.sin(2 * np.pi * 220 * np.arange(5 * sr) / sr)
    pl = C.db(np.mean(x ** 2))
    y = x.copy()
    y[sr:sr + 441] = 0                            # 10 ms gap inside playing
    d, c = C.dropouts(y, sr, pl)
    assert len(d) == 1 and not c
    z = x.copy()
    z[2 * sr:] = 0                                # an edit: hard cut to silence
    d, c = C.dropouts(z, sr, pl)
    assert not d and len(c) == 1
    w = x.copy()
    w[sr:sr + sr // 2] = 0                        # 500 ms: an edit, not a dropout
    d, c = C.dropouts(w, sr, pl)
    assert not d and len(c) == 1


def test_hum_lines_found_and_not_confused_by_a_note_near_120():
    x = guitarish(20.0) + hum_series(20.0, 60.0, 3e-3)
    f, fs = C.floor_spectrum(x)
    assert {1, 3, 5} <= set(C.hum_lines(f, fs, 60.0))
    clean = guitarish(20.0, f=123.5)              # B2: partials near 120/240/360 Hz, decaying
    f, fs = C.floor_spectrum(clean)
    assert C.hum_lines(f, fs, 60.0) == []
    assert abs(C.mains_f0(hum_series(20.0, 59.97, 3e-3), 60.0, [1, 3, 5]) - 59.97) < 0.02


def test_session_mains_and_rest_check():
    assert C.session_mains({50.0: [(4, 1e-6)], 60.0: [(4, 1e-7), (3, 1e-7)]}) == 60.0
    assert C.session_mains({50.0: [(2, 1e-6)], 60.0: [(2, 1e-7)]}) == 50.0
    g = guitarish(10.0)
    quiet = np.concatenate([g, np.zeros(5 * SR)]) + 1e-6 * RNG.standard_normal(15 * SR)
    hummed = quiet + hum_series(15.0, 60.0, 1e-4)
    for x, want in ((hummed, "yes"), (quiet, "no")):
        f, rs, n = C.rest_spectrum(x)
        assert n >= C.MIN_REST_SPEC
        assert C.rest_confirms(f, rs, 60.0, n) == want
    f, rs, n = C.rest_spectrum(guitarish(10.0))
    assert C.rest_confirms(f, rs, 60.0, 0) == "unconfirmed"


def test_hum_level_tracks_the_line_power():
    g = guitarish(10.0)
    lo = g + hum_series(10.0, 60.0, 1e-4)
    hi = g + hum_series(10.0, 60.0, 1e-3)
    f, fs_hi = C.floor_spectrum(hi)
    mains, ks = 60.0, [1, 3, 5]
    assert set(ks) <= set(C.hum_lines(f, fs_hi, 60.0))
    _, fs_lo = C.floor_spectrum(lo)
    p_hi, p_lo = C.line_power(f, fs_hi, mains, ks), C.line_power(f, fs_lo, mains, ks)
    assert 17 < C.db(p_hi) - C.db(p_lo) < 23     # 20 dB apart


def test_hiss_band_reads_noise_not_the_guitar():
    g = guitarish(10.0)
    n = 1e-4 * RNG.standard_normal(len(g))
    f, a = C.floor_spectrum(g + n)
    _, b = C.floor_spectrum(g + 10 * n)
    d = C.db(C.band_power_sum(f, b, *C.HISS_BAND)) - C.db(C.band_power_sum(f, a, *C.HISS_BAND))
    assert 17 < d < 23                           # 20 dB more hiss reads about 20 dB


def test_coherence_sees_crosstalk_and_not_independent_noise():
    n = 16000 * 20
    other = RNG.standard_normal(n)
    di = 1e-3 * RNG.standard_normal(n)
    bled = di + 0.05 * other
    X, Y, Z = C.stft16(bled), C.stft16(other), C.stft16(di)
    rows = np.ones(len(X), bool)
    bins = C.bleed_bins()
    msc, bias = C.coherence(X, Y, rows, bins)
    assert msc - bias > C.BLEED_MSC
    msc0, bias0 = C.coherence(Z, Y, rows, bins)
    assert msc0 - bias0 < 0.01
    rel = C.bleed_rel(X, Y, rows, [slice(0, len(X))], bins)[0]
    assert -1.0 < rel < 0.5                      # the bleed is most of this signal


def test_section_flags():
    track = {"near_fs": True}
    ok = {"hum_rel_db": -80.0, "hiss_rel_db": -90.0, "clip_runs": 0, "dropouts": 0, "hard_cuts": 0,
          "dc_rel_db": -60.0, "bleed_rel_db": None, "bleed_status": "measured"}
    assert C.section_flags(ok, track) == ([], [])
    bad = {**ok, "hum_rel_db": -50.0, "hiss_rel_db": -70.0, "clip_runs": 1, "dropouts": 1, "hard_cuts": 1,
           "dc_rel_db": -20.0, "bleed_rel_db": -30.0}
    flags, tags = C.section_flags(bad, {**track, "hum_rest_check": "unconfirmed", "rest_hiss_2_6k_rel_db": -50.0})
    assert set(flags) == {"hum", "clipping", "dropout", "bleed"}
    assert set(tags) == {"slight_hiss", "hard_cut", "dc", "hum_unconfirmed_on_rests", "rest_hiss"}
    assert "clipping" not in C.section_flags({**ok, "clip_runs": 2}, {"near_fs": False})[0]
    assert "clipping" in C.section_flags({**ok, "clip_runs": 3}, {"near_fs": False})[0]
    assert C.section_flags({**ok, "hum_rel_db": None}, track) == ([], [])
    assert C.section_flags({**ok, "bleed_status": "unmeasured"}, track) == ([], ["bleed_unread"])
    assert C.bleed_status(10, 0, 0, True) == "no_rest_frames"
    assert C.bleed_status(100, 0, 5, True) == "unmeasured"
    assert C.bleed_status(100, 3, 5, True) == "partial"
    assert C.bleed_status(100, 5, 5, True) == "measured"
    assert C.bleed_status(100, 0, 0, False) == "no_session"


def test_notch_leaves_a_tone_between_harmonics_alone():
    t = np.arange(10 * SR) / SR
    tone = 0.1 * np.sin(2 * np.pi * 110 * t)
    band, removed, _ = C.fix_effect(tone, 60.0, [1, 2, 3, 5])
    assert band < 0.05 and removed < -50          # a 1-Hz notch 10 Hz away: about -52 dB
    hum = hum_series(10.0, 60.0, 1e-2, (1, 3))
    y = C.notch(tone + hum, 60.0, [1, 3])
    assert C.db(np.mean((y - tone)[SR:-SR] ** 2)) < C.db(np.mean(hum ** 2)) - 25


def test_broadband_signal_passes_the_collateral_rule():
    rng = np.random.default_rng(3)
    x = 0.05 * rng.standard_normal(20 * SR)          # hum-free, broadband: the notches hit no partial
    ks = list(range(1, 41))
    ref = C.noise_reference(60.0, ks)
    assert ref.max() > C.FIX_MAX_BAND_DB              # the raw band limit alone could never be met
    assert C.excess_collateral(C.band_changes(x, 60.0, ks), ref) <= C.FIX_MAX_BAND_DB
    t = np.arange(20 * SR) / SR
    on_line = x + 0.5 * np.sin(2 * np.pi * 120.0 * t)   # a partial sitting on a notch is hit
    assert C.excess_collateral(C.band_changes(on_line, 60.0, ks), ref) > C.FIX_MAX_BAND_DB


def test_fix_adoption_rule():
    assert C.fix_adopted([0.05], [-70.0], None) is None          # measured fine, not heard
    assert C.fix_adopted([0.05], [-70.0], ["no", "no"]) is True
    assert C.fix_adopted([0.05], [-70.0], ["no", "little"]) is False
    assert C.fix_adopted([0.2], [-70.0], None) is False
    assert C.fix_adopted([0.05], [-50.0], ["no"]) is False


def test_style_and_onsets():
    assert C.style(1.0) == "sparse" and C.style(3.0) == "medium" and C.style(6.0) == "dense"
    assert 1.0 < C.onset_rate(guitarish(10.0)) < 3.5            # a note every 0.5 s


# --- the inventory's guards ---------------------------------------------------------------------

def test_names_read_as_guitar_dis():
    for n in ("14_ElecGtr5DI.wav", "GTR 1 DI_TDP-1.wav", "12_ElecGtr1DTDI.wav", "GTR DI.04_02.wav",
              "17_ElecGtr2MicDI.wav", "Keys GTR DI 2_TDP-1.wav"):
        assert C.is_guitar_di(n), n
    for n in ("18_BassDI.wav", "Bass DI TDA-1.wav", "KEY 3 Bass DIRECT.wav", "22_ElecGtr1Amp1.wav",
              "DRUM Hats ELA M 260 hypercardioid.wav", "Keys Bass DI_TDA-1.wav"):
        assert not C.is_guitar_di(n), n


def test_own_tracks_do_not_take_a_longer_part_number():
    files = ["20_ElecGtr1DI.wav", "21_ElecGtr1Amp.wav", "22_ElecGtr10Amp.wav", "23_ElecGtr1DT.wav"]
    assert C.own_tracks("ElecGtr1", files, "20_ElecGtr1DI.wav") == ["21_ElecGtr1Amp.wav", "23_ElecGtr1DT.wav"]


def test_band_of_set_1_sessions():
    assert C.band_of({"path": "telefunken/Rebecaa Haviland - Collide With Me"}) == "Rebecca Haviland"
    assert C.band_of({"path": "cambridge/ChrisColtraine_HeatherJane_Full"}) == "Chris Coltraine"
    assert C.band_of({"path": "x", "group": "Eggy"}) == "Eggy"


@pytest.mark.skipif(not C.SET3_CATALOG.is_file(), reason="the set-3 catalogue is not on this machine")
def test_undeclared_sessions_were_never_eligible_for_a_held_out_draw():
    import json

    from learn import set3

    cat = json.loads(C.SET3_CATALOG.read_text())
    unpaired = {u["session"] for u in cat["unpaired"]}
    strata = set(set3.load()["band_strata"])
    for key, (band, _, _) in C.UNDECLARED.items():
        assert key in unpaired, key
        assert band not in strata, band
    assert {"Rebecca Haviland", "Chris Coltraine"} <= C._held_out_names()


def test_training_downloads_are_training_only_and_not_held_out():
    import json

    assert not set(C.TRAINING_DOWNLOADS) & set(C.RESERVED_NEW)
    assert all(split == "library" for _, split, _ in C.TRAINING_DOWNLOADS.values())
    ledger = json.loads((C.PLUGIN_ROOT / "docs/dev-test-ledger.json").read_text())
    entry = next(t for t in ledger["tests"] if t["test_id"] == "cambridge-new-training-bands-2026-10-25")
    assert all(key in json.dumps(entry) for key in C.TRAINING_DOWNLOADS)
    for key, (band, _, _) in C.TRAINING_DOWNLOADS.items():
        C.refuse_held_out({"set": "cambridge-new", "band": band, "path": str(C.CAMBRIDGE_NEW / key / "x_ElecGtrDI.wav")})
    with pytest.raises(ValueError):
        C.refuse_held_out({"set": "cambridge-new", "band": "Rebecca Haviland", "path": "/nowhere/x.wav"})


def test_held_out_paths_are_refused():
    root = os.path.expanduser("~/ndsp-presets/references/datasets")
    rec = {"set": 2, "band": "Forkupines", "path": f"{root}/cambridge/Forkupines_Semantics_Full/x.wav"}
    with pytest.raises(ValueError):
        C.refuse_held_out(rec)
    with pytest.raises(ValueError):
        C.refuse_held_out({"set": 1, "band": "x", "path": f"{root}/guitar-techs/P3_music/x.wav"})
    with pytest.raises(ValueError):
        C.refuse_held_out({"set": "undeclared", "band": "V.M.GY", "path": "/nowhere/x.wav"})
    s3 = os.path.expanduser("~/ndsp-presets/references/datasets-set3")
    with pytest.raises(ValueError):
        C.refuse_held_out({"set": 3, "band": "Silona",
                           "path": f"{s3}/cambridge/Silona_LearningHowToFly_Full/x/1.wav"})
    C.refuse_held_out({"set": 2, "band": "Starnes And Shah",
                       "path": f"{root}/cambridge/StarnesAndShah_Prodigal_Full/14_ElecGtr5DI.wav"})


def test_training_guard():
    man = {"dis": [{"path": "/a.wav", "split": "library", "training_ok": True, "notes": []},
                   {"path": "/b.wav", "split": "known_answer", "training_ok": False, "notes": []},
                   {"path": "/c.wav", "split": "library", "training_ok": False,
                    "notes": ["band has a held-out song"]}]}
    C.assert_training_ok(["/a.wav"], man)
    for p in ("/b.wav", "/c.wav"):
        with pytest.raises(ValueError):
            C.assert_training_ok([p], man)
    with pytest.raises(KeyError):
        C.assert_training_ok(["/d.wav"], man)


@pytest.mark.skipif(not (C.SETS_1_2_ROOT / "cambridge").is_dir(), reason="the datasets are not on this machine")
def test_inventory_on_disk():
    dis, excluded = C.inventory()
    assert all(r["split"] == "known_answer" for r in dis if r["band"] in C.KNOWN_ANSWER)
    assert not any("P3_music" in r["path"] for r in dis)
    assert all(r["split"] == "known_answer" and not r["training_ok"]
               for r in dis if r["band"] in ("Rebecca Haviland", "Chris Coltraine"))
    assert not any("keys" in r["id"].lower() for r in dis)
    assert all(not r["training_ok"] for r in dis if any(n.startswith("catalogue:") for n in r["notes"]))
    assert any("Crucial Taunt" in e["why"] or "CrucialTaunt" in e["what"] for e in excluded)


# --- the listening check ---------------------------------------------------------------------------

def _rows():
    rows = []
    for i in range(60):
        for start in (0.0, 5.0, 10.0):
            hum = -90.0 + i * 1.0                      # spans every stratum of the hum screen
            hiss = -100.0 + i * 1.0
            flags = [f for f, v, lvl in (("hum", hum, C.HUM_FLAG_DB), ("hiss", hiss, C.HISS_FLAG_DB)) if v >= lvl]
            if i in (3, 4, 5):
                flags.append("clipping")
            tags = ["hard_cut"] if i in (6, 7, 8) else []
            rows.append({"di": f"d{i}", "path": f"/p{i}.wav", "start_s": start, "flags": flags, "tags": tags,
                         "clean": not flags, "source": ("cambridge", "telefunken", "guitar-techs")[i % 3],
                         "measures": {"hum_rel_db": hum, "hiss_rel_db": hiss}})
    return rows


def test_draw_strata_blinding_and_repeats():
    p1, p2 = C.draw(_rows())
    scr = [t for t in p1 if t["kind"] == "screen"]
    for s_ in ("hum", "hiss"):
        for st in C.STRATA:
            got = [t for t in scr if t["screen"] == s_ and t["stratum"] == st]
            assert len(got) <= C.PER_STRATUM
            for t in got:
                key, tag, flag = C.CONTINUOUS[s_]
                assert C.stratum(t["value"], tag, flag) == st
    assert sum(t["screen"] == "clipping" for t in scr) == 2
    assert sum(t["screen"] == "hard_cut" for t in scr) <= 2
    assert sum(t["kind"] == "clean" for t in p1) == C.N_CLEAN
    reps = [t for t in p1 if t["kind"] == C.REPEAT]
    assert len(reps) == 2
    singles = [t for t in p1 if t["kind"] != C.REPEAT]
    assert len({t["di"] for t in singles}) == len(singles)        # one per DI
    for i, t in enumerate(p1):
        if t["kind"] == C.REPEAT:
            j = next(j for j, u in enumerate(p1) if u["kind"] != C.REPEAT and C._same(u, t))
            assert i > 0 and abs(i - j) > 1
    ab = [t for t in p2 if t["kind"] == "hum_ab"]
    assert len(ab) == 6 and sum(t["letters"]["A"] == "notched" for t in ab) == 3
    assert sum(t["kind"] == "null" for t in p2) == 1
    assert (p1, p2) == C.draw(_rows())


def test_amend_rule():
    F = -55.0
    assert C.amend([(-80, False), (-60, False), (-50, True), (-40, True)], F) == (F, "stays")
    assert C.amend([(-80, False), (-62, True), (-58, True), (-50, True)], F) == (-71.0, "lowered")
    assert C.amend([(-62, True), (-58, True)], F) == (-67.0, "lowered")
    assert C.amend([(-50, False), (-45, False), (-35, True)], F) == (-40.0, "raised")
    assert C.amend([(-50, False), (-45, False)], F) == (-40.0, "raised")
    assert C.amend([(-62, True), (-58, True), (-50, False), (-45, False)], F) == (F, "conflict")


def test_parse_and_score():
    p1, p2 = C.parse_answers("1ok 2hum+hiss 3? H1A-no H2same-little H3?-?")
    assert p1 == {"1": {"ok"}, "2": {"hum", "hiss"}, "3": None}
    assert p2 == {"1": ("A", "no"), "2": ("same", "little"), "3": (None, None)}
    with pytest.raises(SystemExit):
        C.parse_answers("1loud")
    t = lambda di, kind, scr, st, v: {"di": di, "start_s": 0.0, "kind": kind, "screen": scr, "stratum": st,  # noqa: E731
                                      "value": v}
    key = {"part1": {"1": t("a", "screen", "hum", "just_over", -50.0),
                     "2": t("b", "clean", None, None, None),
                     "3": t("a", C.REPEAT, "hum", "just_over", -50.0),
                     "4": t("c", "screen", "hum", "tag_to_flag", -60.0),
                     "5": t("d", "screen", "hum", "tag_to_flag", -58.0),
                     "6": t("e", "screen", "clipping", "flagged", None),
                     "7": t("f", "screen", "clipping", "flagged", None)},
           "part2": {"1": {"di": "a", "kind": "hum_ab", "letters": {"A": "notched", "B": "original"}},
                     "2": {"di": "a", "kind": "null", "letters": {"A": "original", "B": "original"}}}}
    rep = C.score_key(key, C.parse_answers("1hum 2hiss 3ok 4hum 5hum 6ok 7ok H1A-no H2same-no"))
    assert rep["per_screen"]["hum"]["just_over"] == {"clips": 1, "named": 1, "heard_ok": 0}
    assert rep["proposals"]["hum"] == {"flag": -65.0, "reason": "lowered", "tag": -80.0}
    assert rep["proposals"]["clipping"] == {"reason": "becomes a tag"}
    assert rep["passing"]["any_problem"] == 1 and rep["passing"]["named"] == {"hiss": 1}
    assert rep["repeats"] == [{"repeat": 3, "source": 1, "repeat_heard": ["ok"], "source_heard": ["hum"]}]
    assert rep["hum_summary"]["notched_less_hum"] == 1 and rep["hum_summary"]["guitar"] == {"no": 1}


def test_page_template_formats():
    page = C.PAGE.format(part1=C.section1(1, "data:audio/mp4;base64,AAAA"),
                         part2_block=C.PART2.format(trials=C.section2(1, [("A", "data:x"), ("B", "data:y")])),
                         build="abc")
    assert 'data-trial="1"' in page and "H1" in page and pathlib.Path  # noqa: B015


# --- amendment 3: the mains fundamental is never refuted by the rest check ----------------------------

def test_mains_line_hz_reads_hum_and_not_a_nearby_note():
    x = guitarish(30.0) + hum_series(30.0, 59.97, 3e-3)
    hz, prom = C.mains_line_hz(x, 60.0)
    assert abs(hz - 59.97) < 0.05 and prom >= C.LINE_PROM_DB
    assert C.fundamental_overrides([1, 3, 5], hz, 60.0)
    t = np.arange(30 * SR) / SR                     # a steady B1 (61.74 Hz): near 60 Hz, not at it
    note = guitarish(30.0) + 3e-3 * np.sin(2 * np.pi * 61.74 * t)
    hz, _ = C.mains_line_hz(note, 60.0)
    assert abs(hz - 61.74) < 0.1
    assert not C.fundamental_overrides([1, 3, 5], hz, 60.0)
    assert not C.fundamental_overrides([3, 5], 60.0, 60.0)        # the fundamental must be a line
    assert not C.fundamental_overrides([1, 3], None, 60.0)


def test_measure_di_keeps_a_mains_fundamental_the_rests_cannot_show():
    # Hum present throughout but buried in the rests by gated silence (exact zeros there), so the
    # rest check has nothing to read and says "no"; amendment 3 keeps the lines.
    g = guitarish(40.0)
    hum = hum_series(40.0, 60.0, 3e-3, (1, 3, 5, 7))
    x = g + hum
    rest = np.zeros(3 * SR)                                     # 7% of frames: under the 10th percentile
    rest += 1e-7 * RNG.standard_normal(len(rest))                # a gate's residual floor, no hum
    y = np.concatenate([x, rest])
    track, rows = C.measure_di(y, SR, 60.0)
    assert track["hum_rest_check"] == "kept_fundamental" and 1 in track["hum_harmonics"]
    assert track["hum_harmonics_refuted"] == [] and track["hum_amendment"] == C.HUM_AMENDMENT
    assert any(r.get("hum_rel_db") is not None for r in rows if r["passes_activity"])


def _rows3(n=20):
    v1, v2 = [], []
    ids = [f"d{i}" for i in range(n)] + [f"guitar-techs/P1-downloads/P1_chords/c{j}.wav" for j in range(3)]
    for i, di in enumerate(ids):
        kind = "kept" if di.startswith("guitar-techs") else ("kept", "refuted", "hum", "quiet")[i % 4]
        for start in (0.0, 5.0):
            base = {"di": di, "path": f"/p{i}.wav", "start_s": start, "source": "cambridge"}
            m = {"hum_rel_db": None, "hum_rel_db_refuted": None}
            flags, tags = [], []
            if kind == "kept":
                m["hum_rel_db"] = -45.0
                flags, tags = ["hum"], ["hum_kept_by_fundamental"]
            elif kind == "refuted":
                m["hum_rel_db_refuted"] = -50.0
            elif kind == "hum":
                m["hum_rel_db"] = -30.0
                flags = ["hum"]
            v2.append({**base, "flags": flags, "tags": tags, "clean": not flags, "measures": m})
            v1.append({**base, "flags": ["hum"] if kind == "hum" else [], "tags": [], "clean": kind != "hum",
                       "measures": {"hum_rel_db": -30.0 if kind == "hum" else None}})
    return v1, v2


def test_draw_hum_strata_and_repeats():
    v1, v2 = _rows3()
    clips = C.draw_hum(v1, v2, page1_dis={"d1"})
    kinds = [t["kind"] for t in clips]
    kept = [t for t in clips if t["kind"] == "kept"]
    assert len(kept) == 5 + C.N_PER_UNIT                          # 5 single-DI units, Guitar-TECHS P1 as one
    assert sum(t["unit"] == "guitar-techs-P1" for t in kept) == C.N_PER_UNIT
    assert kinds.count("refuted") == 4 and "d1" not in {t["di"] for t in clips if t["kind"] == "refuted"}
    assert kinds.count("anchor_hum") == kinds.count("anchor_clean") == C.N_ANCHOR
    assert kinds.count(C.REPEAT) == 2
    singles = [t for t in clips if t["kind"] != C.REPEAT]
    assert len({t["di"] for t in singles}) == len(singles)
    for i, t in enumerate(clips):
        if t["kind"] == C.REPEAT:
            j = next(j for j, u in enumerate(clips) if u["kind"] != C.REPEAT and C._same(u, t))
            assert i > 0 and abs(i - j) > 1
    assert clips == C.draw_hum(v1, v2, page1_dis={"d1"})


def test_score_hum_rule():
    def key(spec):
        return {"clips": {str(i): {"di": f"d{i}", "start_s": 0.0, "kind": k, "unit": u, "value": None,
                                   "value_refuted": None} for i, (k, u) in enumerate(spec, 1)}}
    k = key([("kept", "g"), ("kept", "g"), ("kept", "a"), ("kept", "b"), ("refuted", None), ("refuted", None),
             ("refuted", None), ("refuted", None), ("anchor_clean", None), ("anchor_clean", None)])
    rep = C.score_hum(k, C.parse_answers("1hum 2hum 3hum 4ok 5ok 6ok 7ok 8ok 9ok 10ok"))
    assert rep["decision"] == "amendment 3 stands" and rep["kept"]["units_reverted"] == ["b"]
    rep = C.score_hum(k, C.parse_answers("1ok 2ok 3ok 4hum 5ok 6ok 7ok 8ok 9ok 10ok"))
    assert rep["decision"] == "amendment 3 withdrawn" and rep["kept"]["units_reverted"] == ["a", "g"]
    rep = C.score_hum(k, C.parse_answers("1ok 2hum 3hum 4hum 5ok 6ok 7ok 8ok 9ok 10ok"))
    assert rep["kept"]["units_reverted"] == []                   # 1 of 2 in unit g: not more than half
    rep = C.score_hum(k, C.parse_answers("1hum 2hum 3hum 4hum 5hum 6hum 7ok 8ok 9ok 10ok"))
    assert rep["decision"] == "amendment 3 stands; rest refutation suspended"
    assert rep["refuted"]["restored_dis"] == ["d5", "d6"]
    rep = C.score_hum(k, C.parse_answers("1hum 2hum 3hum 4hum 5hum 6hum 7ok 8ok 9hum 10hum"))
    assert not rep["suspend"]                                    # no more than the clean anchors
    rep = C.score_hum(k, C.parse_answers("1hum 2hum 3hum 4hum 5hum 6ok 7ok 8ok 9ok 10ok"))
    assert not rep["suspend"] and rep["refuted"]["restored_dis"] == ["d5"]
    rep = C.score_hum(k, C.parse_answers("1ok 2ok 3ok 4hum 5hum 6hum 7ok 8ok 9ok 10ok"))
    assert rep["decision"].startswith("conflict") and not rep["withdraw"] and not rep["suspend"]
