"""The note-rebuild's re-synthesis on made-up note lists (`learn/note_rebuild.py`, P4): byte-for-byte repeatable,
notes placed at their onsets, equal onset groups, the mute rules, the level arms, the oracle onset step, the global
tuning and the figures. Needs numpy, scipy, noisereduce and pyloudnorm (skipped on the light CI runner)."""
import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("noisereduce")
pytest.importorskip("pyloudnorm")

from learn import note_rebuild as N  # noqa: E402

SR = N.SR


def _tone(midi, seconds=5.0, cents=0.0, decay=1.5, delay=0.01, seed=0):
    """A plucked-string stand-in: harmonics of the pitch with an exponential decay, a little noise, a short delay."""
    t = np.arange(int(seconds * SR)) / SR
    f0 = 440 * 2 ** ((midi - 69 + cents / 100) / 12)
    y = sum(np.sin(2 * np.pi * h * f0 * t) / h for h in range(1, 6)) * np.exp(-t / decay)
    y = np.concatenate([np.zeros(int(delay * SR)), y])[:len(t)]
    return 0.3 * y / np.abs(y).max() + 1e-4 * np.random.default_rng(seed).standard_normal(len(t))


def _bank():
    return N.Bank(None, loader=lambda s, f: (_tone(N.OPEN_STRINGS[s] + f, seed=s * 100 + f), SR))


def _notes():
    return [{"on": 0.5, "off": 1.4, "pitch": 55, "string": 3, "fret": 0, "arts": []},
            {"on": 0.5, "off": 1.4, "pitch": 59, "string": 2, "fret": 0, "arts": []},
            {"on": 1.0, "off": 2.0, "pitch": 64, "string": 1, "fret": 0, "arts": []},
            {"on": 2.2, "off": 3.0, "pitch": 62, "string": None, "fret": None, "arts": []}]


def test_repeatable_byte_for_byte():
    a, ra = N.synthesise(_notes(), 4 * SR, _bank())
    b, rb = N.synthesise(_notes(), 4 * SR, _bank())
    assert a.tobytes() == b.tobytes() and ra == rb
    assert ra["played"] == 4 and ra["from_tab"] == 3 and ra["groups"] == 3


def test_note_at_its_onset_and_silent_before():
    notes = [{"on": 1.0, "off": 1.5, "pitch": 60, "string": 2, "fret": 1, "arts": []}]
    y, _ = N.synthesise(notes, 3 * SR, _bank())
    assert np.abs(y[:int(0.99 * SR)]).max() == 0
    first = int(np.argmax(np.abs(y) > 0.1 * np.abs(y).max()))
    assert abs(first / SR - 1.0) < 0.005
    assert np.abs(y[int(1.53 * SR):]).max() == 0                         # ended at note-off with its 20 ms fade


def test_onset_groups_equally_loud():
    one = [{"on": 0.5, "off": 1.0, "pitch": 55, "string": 3, "fret": 0, "arts": []}]
    chord = one + [{"on": 0.5, "off": 1.0, "pitch": 59, "string": 2, "fret": 0, "arts": []},
                   {"on": 0.5, "off": 1.0, "pitch": 64, "string": 1, "fret": 0, "arts": []},
                   {"on": 0.5, "off": 1.0, "pitch": 67, "string": 1, "fret": 3, "arts": []}]
    a, _ = N.synthesise(one, 2 * SR, _bank())
    b, _ = N.synthesise(chord, 2 * SR, _bank())
    ra, rb = (np.sqrt(np.mean(x[int(0.5 * SR):int(0.8 * SR)] ** 2)) for x in (a, b))
    assert abs(20 * np.log10(rb / ra)) < 3.0


def test_repluck_cuts_the_string():
    notes = [{"on": 0.2, "off": 2.0, "pitch": 55, "string": 3, "fret": 0, "arts": []},
             {"on": 1.0, "off": 2.0, "pitch": 57, "string": 3, "fret": 2, "arts": []}]
    y, _ = N.synthesise(notes, 3 * SR, _bank())
    only_first, _ = N.synthesise(notes[:1], 3 * SR, _bank())
    # just before the second pluck the first note is fading or gone
    seg = slice(int(0.995 * SR), int(1.0 * SR))
    assert np.abs(y[seg]).max() <= np.abs(only_first[int(0.95 * SR):int(0.96 * SR)]).max()


def test_level_gains_follow_the_reference_and_clamp():
    notes = [{"on": t, "off": t + 0.4, "pitch": 60, "string": 2, "fret": 1, "arts": []} for t in (0.5, 1.0, 1.5)]
    ref = np.zeros(2 * SR)
    for t, a in zip((0.5, 1.0, 1.5), (1.0, 0.1, 0.001)):
        ref[int(t * SR):int((t + 0.05) * SR)] = a
    g = N.level_gains(notes, ref)
    assert g[1] == pytest.approx(0.0)
    assert g[0] == pytest.approx(N.LEVEL_CLAMP_DB)
    assert g[2] == pytest.approx(-N.LEVEL_CLAMP_DB)


def test_oracle_gains_match_the_true_di():
    notes = [{"on": t, "off": t + 0.4, "pitch": 60, "string": 2, "fret": 1, "arts": []} for t in (0.5, 1.0, 1.5)]
    plain, _ = N.synthesise(notes, 2 * SR, _bank())
    di = plain.copy()
    di[int(1.0 * SR):int(1.45 * SR)] *= 0.5                                 # the middle note 6 dB softer
    g = N.oracle_gains(notes, plain, di)
    assert g[1] - g[0] == pytest.approx(-6.02, abs=0.1)


def test_refine_snaps_to_the_true_rise():
    di = np.zeros(3 * SR)
    di[int(1.03 * SR):] = 0.1 * np.random.default_rng(1).standard_normal(len(di) - int(1.03 * SR))
    notes = [{"on": 1.0, "off": 1.5, "pitch": 60}]
    out, shifts = N.refine_onsets(notes, di)
    assert abs(out[0]["on"] - 1.03) < 0.003 and out[0]["off"] == pytest.approx(1.5 + shifts[0])
    far = [{"on": 2.0 + 0.5, "off": 2.9, "pitch": 60}]                       # no rise within 50 ms: kept
    out2, sh2 = N.refine_onsets(far, di)
    assert sh2 == [0.0] and out2[0]["on"] == 2.5


def test_global_tuning():
    x = _tone(57, seconds=3.0, cents=20.0, decay=5.0)
    assert abs(N.global_tuning_cents(x) - 20.0) < 3.0
    assert abs(N.global_tuning_cents(_tone(57, seconds=3.0, decay=5.0))) < 3.0


def test_rebuild_dry_arms_and_level():
    notes = _notes()
    ref = _tone(55, seconds=4.0, decay=1.0)
    y, rep = N.rebuild_dry("nr-plain", notes, 4 * SR, _bank(), ref)
    assert abs(N.loudness(y) - N.ASSUMED_LUFS) < 0.05 and rep["played"] == 4
    y2, _ = N.rebuild_dry("nr-plain", notes, 4 * SR, _bank(), ref)
    assert y.tobytes() == y2.tobytes()
    di = 0.5 * ref
    yo, ro = N.rebuild_dry("nr-oracle", notes, 4 * SR, _bank(), ref, di=di)
    assert abs(N.loudness(yo) - N.loudness(di)) < 0.05
    with pytest.raises(ValueError):
        N.rebuild_dry("nr-oracle", notes, 4 * SR, _bank(), ref)
    with pytest.raises(ValueError):
        N.rebuild_dry("plain", notes, 4 * SR, _bank(), ref)


def test_figures_on_identical_signals():
    x = _tone(60, seconds=3.0)
    f = N.figures(x, x)
    assert f["crest_diff_db"] == pytest.approx(0.0)
    assert f["env_corr"] == pytest.approx(1.0)
    assert f["logmel"] == pytest.approx(0.0, abs=1e-9)
    assert all(v["agree"] == 1.0 for v in f["mask"].values())


def test_check_note_flags():
    x = _tone(64, seconds=5.0)
    ok = N.check_note(x, SR, 1, 0)
    assert ok["ok"], ok["why"]
    wrong = N.check_note(_tone(66, seconds=5.0), SR, 1, 0)
    assert not wrong["ok"]
    clipped = x.copy()
    clipped[1000] = 1.0
    assert "clipped" in " ".join(N.check_note(clipped, SR, 1, 0)["why"])
    short = N.check_note(x[:SR], SR, 1, 0)
    assert any("length" in w for w in short["why"])
