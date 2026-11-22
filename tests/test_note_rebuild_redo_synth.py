"""The redo's dry guitars on made-up note lists (`learn/note_rebuild.py`: `synthesise_redo`, `rebuild_redo`,
`mute_times`, `sustain_tilt`, `apply_bend`, `snap_onsets`) and the content checks' measures
(`learn/note_transcribe.py`), with a stub note bank; then, where the stored data exist, the stage-1 arms rebuilt in
memory for two parts byte-for-byte equal to build.json's sha256. Needs numpy, scipy, noisereduce and pyloudnorm
(skipped on the light CI runner)."""
import hashlib
import io
import json

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("noisereduce")
pytest.importorskip("pyloudnorm")

from learn import note_rebuild as N  # noqa: E402
from learn import note_transcribe as T  # noqa: E402

SR = N.SR


def _tone(midi, seconds=5.0, decay=1.5, seed=0):
    t = np.arange(int(seconds * SR)) / SR
    f0 = 440 * 2 ** ((midi - 69) / 12)
    y = sum(np.sin(2 * np.pi * h * f0 * t) / h for h in range(1, 6)) * np.exp(-t / decay)
    y = np.concatenate([np.zeros(int(0.01 * SR)), y])[:len(t)]
    return 0.3 * y / np.abs(y).max() + 1e-4 * np.random.default_rng(seed).standard_normal(len(t))


class _Bank(N.Bank):
    def __init__(self):
        super().__init__(None, loader=lambda s, f: (_tone(N.OPEN_STRINGS[s] + f, seed=s * 100 + f), SR))
        self.loaded = []

    def note(self, s, f, cents):
        self.loaded.append((s, f))
        return super().note(s, f, cents)


def _n(on, pitch, off=None, bends=()):
    return {"on": on, "off": on + 0.5 if off is None else off, "pitch": pitch, "bends": list(bends)}


def _f0(y, a, b):
    seg = y[int(a * SR):int(b * SR)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 1 << 18))
    return np.fft.rfftfreq(1 << 18, 1 / SR)[int(np.argmax(spec))]


def test_repeatable_byte_for_byte():
    notes = [_n(0.5, 60), _n(0.5, 64), _n(1.5, 67, bends=[0] * 3 + [3] * 30)]
    a, ra = N.synthesise_redo(notes, 4 * SR, _Bank(), 0.0, "ring-soft")
    b, rb = N.synthesise_redo(notes, 4 * SR, _Bank(), 0.0, "ring-soft")
    assert a.tobytes() == b.tobytes() and ra == rb and ra["played"] == 3 and ra["bent"] == 1


def test_ring_variants():
    notes = [_n(0.5, 60, off=1.0)]
    soft, _ = N.synthesise_redo(notes, 4 * SR, _Bank(), 0.0, "ring-soft")
    on, rep = N.synthesise_redo(notes, 4 * SR, _Bank(), 0.0, "ring-on")
    assert np.abs(soft[int(1.16 * SR):]).max() == 0                       # the 150-ms release from the note-off
    assert np.abs(on[int(2.0 * SR):int(3.0 * SR)]).max() > 1e-3 and rep["ends"] == {"sample": 1}


def test_a_mute_ends_every_sounding_note():
    notes = [_n(0.5, 60, off=3.0), _n(0.5, 64, off=3.0)]
    y, rep = N.synthesise_redo(notes, 4 * SR, _Bank(), 0.0, "ring-on", mutes=[1.2])
    assert np.abs(y[int(1.21 * SR):]).max() == 0 and rep["ends"] == {"mute": 2}
    di = np.concatenate([0.3 * np.sin(2 * np.pi * 220 * np.arange(SR) / SR), 1e-4 * np.ones(SR)])
    got = N.mute_times(di)
    assert len(got) == 1 and 0.99 < got[0] < 1.07
    slow = 0.3 * np.sin(2 * np.pi * 220 * np.arange(2 * SR) / SR) * np.exp(-np.arange(2 * SR) / SR)
    assert N.mute_times(slow) == []                                       # a natural decay is no mute


def test_a_restruck_pitch_never_reuses_its_last_sample():
    bank = _Bank()
    notes = [_n(0.5, 64, off=0.6), _n(1.0, 64, off=1.1), _n(3.5, 64, off=3.6)]
    _, rep = N.synthesise_redo(notes, 5 * SR, bank, 0.0, "ring-soft")
    assert bank.loaded == [(1, 0), (2, 5), (1, 0)] and rep["variety_swaps"] == 1   # within 2 s: the next source
    bank = _Bank()                                       # ring-on: the high E still rings, so the placing rule moves
    _, rep = N.synthesise_redo(notes, 5 * SR, bank, 0.0, "ring-on")
    assert bank.loaded == [(1, 0), (2, 5), (3, 9)] and rep["variety_swaps"] == 0
    bank = _Bank()
    _, rep = N.synthesise_redo([_n(0.5, 64, off=0.8), _n(1.0, 65, off=1.3)], 3 * SR, bank, 0.0, "ring-on")
    assert bank.loaded == [(1, 0), (2, 6)]                               # the high E still rings: another string


def test_a_repluck_cuts_the_ringing_note():
    bank = _Bank()
    notes = [_n(0.5, 64, off=0.8), _n(3.0, 65, off=3.3)]
    y, rep = N.synthesise_redo(notes, 5 * SR, bank, 0.0, "ring-on")
    assert rep["ends"] == {"sample": 2} and bank.loaded == [(1, 0), (2, 6)]   # 64 rings on string 1: 65 on string 2
    y, rep = N.synthesise_redo([_n(0.5, 40, off=0.8), _n(1.0, 41, off=1.3)], 3 * SR, _Bank(), 0.0, "ring-on")
    assert rep["ends"]["repluck"] == 1                                     # E2 and F2 only on the low E


def test_a_bend_raises_the_pitch():
    plain, _ = N.synthesise_redo([_n(0.5, 64, off=2.0)], 3 * SR, _Bank(), 0.0, "ring-on")
    bent, _ = N.synthesise_redo([_n(0.5, 64, off=2.0, bends=[0] * 10 + [6] * 120)], 3 * SR, _Bank(), 0.0,
                                "ring-on")
    f_plain, f_bent = _f0(plain, 1.0, 1.6), _f0(bent, 1.0, 1.6)
    assert 1200 * np.log2(f_bent / f_plain) == pytest.approx(200, abs=15)      # 6 steps: a whole tone
    assert abs(_f0(bent, 0.51, 0.6) - _f0(plain, 0.51, 0.6)) < 3.0             # unbent before the bend


def test_sustain_tilt():
    notes = [_n(0.5, 60), _n(1.5, 62), _n(2.5, 64), _n(3.5, 65)]
    plain, _ = N.synthesise_redo(notes, 5 * SR, _Bank(), 0.0, "ring-on")
    tilt, rep = N.sustain_tilt(notes, plain, plain)
    assert tilt == pytest.approx(0.0, abs=1e-6) and rep["isolated_groups"] == 4
    t = np.arange(len(plain)) / SR
    faster = plain * 10 ** (-np.clip(t - 0.5, 0, None) % 1.0 * 10 / 20)       # 10 dB/s more decay after each onset
    tilt, _ = N.sustain_tilt(notes, plain, faster)
    assert tilt == pytest.approx(-10.0, abs=1.0)
    tilt, rep = N.sustain_tilt(notes, plain, plain * 10 ** (-np.clip(t - 0.5, 0, None) % 1.0 * 40 / 20))
    assert tilt == -N.TILT_MAX_DB_S and rep["clamped"]
    tilt, rep = N.sustain_tilt(notes[:2], plain, faster)
    assert tilt == 0.0 and not rep["applied"]                               # under 3 isolated groups
    y, _ = N.synthesise_redo(notes, 5 * SR, _Bank(), 0.0, "ring-on", tilt_db_s=-10.0)
    late = lambda x: 20 * np.log10(N.span_rms(x, int(0.8 * SR), int(1.0 * SR)))       # noqa: E731
    assert late(y) - late(plain) == pytest.approx(-10 * 0.4, abs=0.6)


def test_snap_onsets_at_fifty_ms_is_refine_onsets():
    rng = np.random.default_rng(3)
    di = 1e-3 * rng.standard_normal(3 * SR)
    for t in (0.515, 1.485, 2.2):
        di[int(t * SR):int(t * SR) + 4800] += 0.3 * rng.standard_normal(4800)
    notes = [_n(0.5, 60), _n(1.5, 62), _n(2.25, 64)]
    a = N.refine_onsets(notes, di)
    b = N.snap_onsets(notes, di, window=N.REFINE_S)
    assert a == b
    snapped, shifts = N.snap_onsets(notes, di)
    assert abs(snapped[0]["on"] - 0.515) < 0.003 and abs(snapped[1]["on"] - 1.485) < 0.003
    assert shifts[2] == 0.0 and abs(a[0][2]["on"] - 2.2) < 0.003            # 50 ms: only stage 1's +-50 ms reaches


def test_rebuild_redo_both_arms():
    rng = np.random.default_rng(5)
    notes = [_n(0.5 + 0.7 * k, 55 + (k * 5) % 12, off=0.5 + 0.7 * k + 0.6) for k in range(10)]
    di, _ = N.synthesise_redo(notes, int(10.25 * SR), _Bank(), 0.0, "ring-soft")
    di = di * (1 + 0.5 * rng.random(len(di)))
    out = {}
    for arm in N.REDO_ARMS:
        y, rep = N.rebuild_redo(arm, notes, len(di), _Bank(), di, "ring-soft")
        assert len(y) == len(di) and np.isfinite(y).all() and rep["ring"] == "ring-soft"
        assert N.loudness(y) == pytest.approx(N.ASSUMED_LUFS, abs=0.02)
        out[arm] = y
    assert out["tr-di"].tobytes() != out["tr-plain"].tobytes()
    with pytest.raises(ValueError):
        N.rebuild_redo("nr-plain", notes, len(di), _Bank(), di, "ring-soft")


# --- the checks' measures --------------------------------------------------------------------------------------------------

def _plucks(onsets, seconds=5.25, seed=7):
    """A stand-in DI: a broadband decaying burst at each onset (a pick attack), ringing on over the next ones."""
    rng = np.random.default_rng(seed)
    x = 1e-5 * rng.standard_normal(int(seconds * SR))
    t = np.arange(int(2.0 * SR)) / SR
    for o in onsets:
        a = int(o * SR)
        seg = 0.3 * rng.standard_normal(len(t)) * np.exp(-t / 0.4)
        x[a:a + len(t)] += seg[:len(x) - a]
    return x


def test_the_note_checks_find_missed_notes_under_ringing_ones():
    notes = [_n(0.5 + 0.5 * k, 60 + k, off=0.5 + 0.5 * k + 1.5) for k in range(8)]
    di = _plucks([n["on"] for n in notes])
    att = T.attack_times(di, 6.0)
    assert len(att) == 8
    full = T.onsets_found(notes, di, 6.0)
    assert full["found"] == 8 and T.onsets_found_pass(full)
    missed = T.onsets_found(notes[::2], di, 6.0)                 # every other note missing, the rest still ringing
    assert missed["found"] == 4 and not T.onsets_found_pass(missed)
    ringing = [dict(n, off=n["off"] + 1.0) for n in notes[::2]]
    assert T.playing_covered_pass(T.playing_covered(ringing, di))   # frame coverage alone cannot see them
    assert not T.onsets_found_pass(T.onsets_found(ringing, di, 6.0))


def test_the_audio_checks_on_the_true_di_and_a_gap():
    notes = [_n(0.6 + 0.6 * k, 55 + (k * 7) % 12, off=0.6 + 0.6 * k + 0.5) for k in range(14)]
    di, _ = N.synthesise_redo(notes, int(10.25 * SR), _Bank(), 0.0, "ring-soft")
    di = N.at_lufs(di, N.ASSUMED_LUFS)
    fig = T.judge_accepts(di, di, 0, "A")
    assert T.judge_accepts_pass(fig) and fig["judge_finite"] is None
    holed = di.copy()
    holed[int(3.0 * SR):int(3.4 * SR)] = 0.0
    assert T.longest_gap_s(holed, di) > 0.25 and not T.judge_accepts_pass(T.judge_accepts(holed, di, 0, "A"))
    rk = T.ring_kept(di, di, [n["on"] for n in notes])
    assert rk["env_corr"] == pytest.approx(1.0) and T.ring_kept_pass(rk)


def test_transcriber_input():
    x = 0.1 * np.sin(2 * np.pi * 440 * np.arange(SR) / SR)
    y = T.transcriber_input(x)
    assert y.dtype == np.float32 and len(y) == 22050
    assert 20 * np.log10(np.abs(y).max()) == pytest.approx(-1.0, abs=1e-4)


def test_the_known_audio_stops_each_note_at_its_note_off():
    """After the amendment each known note stops at its declared note-off: the scale's audio is silent between one
    note's off and the next attack (the first gate's lists rang on under ring-on, so the transcriber heard notes the
    truth did not list)."""
    y = T.known_audio("scale-c-major", _Bank())
    for n in T.KNOWN_NOTES["scale-c-major"][:-1]:
        assert np.abs(y[int((n["off"] + 0.001) * SR):int((n["on"] + 0.497) * SR)]).max() == 0


# the failed gate's transcriber input for `scale-c-major` (sha256 of its float32 samples, read from the stored
# work/install-gate/known/007-scale-c-major.wav that the pre-amendment `known_audio` wrote, 2026-11-22)
OLD_SCALE_INPUT_SHA = "ffe4297ecb01f1788bc6213e8d68c69c3ab438faea6dd6cd6843b9d30956e8a7"


def test_the_default_synthesis_reproduces_the_pre_amendment_audio():
    """Without `cut`, the real bank's `scale-c-major` through the old path (ring-on, no mutes or tilt, -22.9 LUFS, the
    transcriber's input) is sample for sample the input the failed gate stored: the amendment changes nothing else."""
    import hashlib

    if not N.EGFX.exists() or not (N.OUT / "notes.json").exists():
        pytest.skip("no stored note bank")
    bank = N.Bank(N.load_notes_doc())
    y, _ = N.synthesise_redo(T.KNOWN_NOTES["scale-c-major"], int(round(10.25 * SR)), bank, 0.0, "ring-on", (), 0.0,
                             None)
    x = T.transcriber_input(N.at_lufs(y, N.ASSUMED_LUFS))
    assert hashlib.sha256(np.ascontiguousarray(x, np.float32).tobytes()).hexdigest() == OLD_SCALE_INPUT_SHA
    z = T.transcriber_input(T.known_audio("scale-c-major", bank))
    assert hashlib.sha256(np.ascontiguousarray(z, np.float32).tobytes()).hexdigest() != OLD_SCALE_INPUT_SHA


def test_known_lists_play():
    for name in ("chords-six", "bend", "let-ring-arpeggio"):
        y = T.known_audio(name, _Bank())
        assert len(y) == int(round(10.25 * SR)) and np.isfinite(y).all()


# --- the stage-1 arms unchanged, by their stored hashes (where the stored data exist) ---------------------------------------

def test_two_parts_old_arms_rebuild_to_build_jsons_sha256():
    """Section 12's proof without reading a result: two parts' stage-1 dry guitars rebuilt in memory through the
    unchanged code (as `note_rebuild_s1 build` built them) hash to build.json's sha256, in stage1/ or set aside. It
    reads build.json's dry-guitar hashes only, never a render's distance, pick or score (plan section 12a)."""
    from learn import di_robustness as DR
    from learn import knob_ceiling as K
    from learn import note_rebuild_s1 as S1
    from learn import note_replay as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as SB

    bp = next((p for p in (S1.build_path(), T.SET_ASIDE / "build.json") if p.exists()), None)
    if bp is None or not S1.subset_path().exists() or not R.draw_path().exists() or not N.EGFX.exists():
        pytest.skip("no stored stage-1 data")
    build = json.loads(bp.read_text())
    sub = json.loads(S1.subset_path().read_text())
    if build["subset_sha256"] != N.file_sha(S1.subset_path()):
        pytest.fail("build.json was made from another subset")
    draw = json.loads(R.draw_path().read_text())
    sd = R.Stored()
    by = {p["pkey"]: p for p in draw["parts"]}
    by_sec = {}
    for p in draw["parts"]:
        by_sec.setdefault(p["section"], sd.units[(p["set"], p["unit"], p["amp"])]["prt"])
    cache = {}

    def sec(s):
        if s not in cache:
            cache[s] = np.asarray(R.di_section(by_sec[s]), np.float64)
        return cache[s]
    bank = N.Bank(N.load_notes_doc())
    trim = int(PS.TRIM_S * PS.SR)
    for k in sorted(sub["parts"], key=lambda q: q["pkey"])[:2]:
        p = by[k["pkey"]]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di = sec(p["section"])
        n = len(di)
        notes = N.window_notes(S1.load_item_notes(k), k["window_s"] - PS.TRIM_S, n / PS.SR)
        refined, _ = N.refine_onsets(N.shifted_notes(notes, N.coarse_offset(notes, di)), di)
        clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        ref = S1.ref_on_section(np.asarray(clean, np.float64), n, trim, K.P.LATENCY + p["lag"])
        others = {s: [sec(x) for x in xs] for s, xs in R.others_for(p, draw["parts"]).items()}
        for arm in N.ARMS:
            y, _ = N.rebuild_dry(arm, refined, n, bank, ref, di=di,
                                 finish=lambda y, o=others: DR.average_balance(SB.measure(y), o))
            buf = io.BytesIO()
            np.save(buf, np.asarray(y, np.float32))
            assert hashlib.sha256(buf.getvalue()).hexdigest() == build["parts"][k["pkey"]]["arms"][arm]["sha256"], \
                (k["pkey"], arm)
