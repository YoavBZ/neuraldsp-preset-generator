"""Loading, level measurement and excerpt selection."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("soundfile", reason="needs the analysis extra")

import numpy as np

from analysis import SAMPLE_RATE, io
from tests import fixtures_audio as fx


def test_load_resamples_to_the_canonical_rate(tmp_path):
    """A 44.1 kHz file arrives at 48 kHz, and says where it came from."""
    one_second_at_44k = fx.noise(seconds=1.0, sample_rate=44100)
    path = fx.write_wav(tmp_path / "a.wav", one_second_at_44k, sample_rate=44100)
    audio = io.load(path)
    assert audio.sample_rate == SAMPLE_RATE
    assert audio.source_rate == 44100
    assert audio.duration_s == pytest.approx(1.0, abs=0.01)


def test_load_preserves_channels(tmp_path):
    path = fx.write_wav(tmp_path / "s.wav", fx.stereo(fx.noise(seconds=1.0), width=0.5))
    assert io.load(path).channels == 2


def test_sha256_is_of_the_bytes_not_the_samples(tmp_path):
    """The hash identifies a reference the project must never keep a copy of."""
    import hashlib

    path = fx.write_wav(tmp_path / "a.wav", fx.noise(seconds=0.5))
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert io.load(path).sha256 == expected


def test_normalise_hits_the_target_loudness():
    audio = io.from_samples(fx.stereo(fx.noise(seconds=3.0)) * 0.01, SAMPLE_RATE)
    assert io.loudness_lufs(io.normalise(audio, -23.0)) == pytest.approx(-23.0, abs=0.1)


def test_normalise_leaves_silence_alone():
    """There is no gain that makes silence -23 LUFS, so nothing is invented."""
    silent = io.from_samples(np.zeros((SAMPLE_RATE, 2), dtype=np.float32), SAMPLE_RATE)
    assert io.loudness_lufs(silent) is None
    assert float(np.abs(io.normalise(silent).samples).max()) == 0.0


def test_true_peak_sees_between_the_samples():
    """An inter-sample peak is above the sample peak, which is the point."""
    t = np.arange(SAMPLE_RATE) / SAMPLE_RATE
    tone = np.sin(2 * np.pi * 11000 * t + 0.4) * 0.99
    audio = io.from_samples(tone, SAMPLE_RATE)
    sample_peak = 20 * np.log10(float(np.abs(tone).max()))
    assert io.true_peak_dbtp(audio) > sample_peak


def test_active_frames_exclude_the_silence():
    """Gating keeps the sound and drops the gaps, and a long gap moves the mean."""
    loud = fx.noise(seconds=1.0)
    padded = np.concatenate([loud, np.zeros(SAMPLE_RATE * 3)])
    mask = io.active_frames(padded)
    assert 0.15 < mask.mean() < 0.40
    assert mask[: len(mask) // 5].all()


def test_excerpt_picks_the_busy_part():
    """Two seconds of noise buried in nine seconds of silence is what comes back."""
    quiet = np.zeros(SAMPLE_RATE * 4)
    audio = io.from_samples(
        np.concatenate([quiet, fx.noise(seconds=2.0), quiet]), SAMPLE_RATE
    )
    chosen = io.excerpt(audio, 2.0)
    start, end = io.excerpt_bounds(audio, 2.0)
    assert chosen.frames == SAMPLE_RATE * 2
    assert float(np.abs(chosen.samples).mean()) > 0.1
    assert end - start == chosen.frames
    assert np.array_equal(chosen.samples, audio.samples[start:end])
    assert 3.9 < start / SAMPLE_RATE < 4.1


def test_excerpt_of_a_short_file_is_the_whole_file():
    audio = io.from_samples(fx.noise(seconds=1.0), SAMPLE_RATE)
    assert io.excerpt(audio, 20.0).frames == audio.frames
    assert io.excerpt_bounds(audio, 20.0) == (0, audio.frames)


def test_resample_uses_the_exact_ratio():
    """44100 to 48000 is 160/147, not a float approximation of it."""
    resampled = io.resample(fx.noise(seconds=1.0, sample_rate=44100)[:, None], 44100, 48000)
    assert len(resampled) == pytest.approx(48000, abs=2)


def test_a_compressed_reference_names_the_conversion(tmp_path):
    """`.m4a` and `.mp3` are what a reference actually arrives as.

    libsndfile decodes WAV, AIFF, FLAC and Ogg and nothing compressed, and its
    own message — "Format not recognised" — tells the person holding a phone
    recording or a stem-separation export nothing about what to do next. The
    bytes here are not a real AAC file; what is being tested is that an
    unreadable one is refused with the converter named, not that AAC is parsed.
    """
    import pytest

    from analysis import io

    path = tmp_path / "reference.m4a"
    path.write_bytes(b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 512)
    with pytest.raises(ValueError) as raised:
        io.load(path)
    message = str(raised.value)
    assert "afconvert" in message and "ffmpeg" in message
    assert "48000" in message, "the conversion has to land at the rate we measure at"
    assert "reference.m4a" in message


# --- how honestly the excerpt was chosen ----------------------------------
#
# The ranking underneath `excerpt_selection` is a broadband activity gate, so on
# a source that never stops it ranks nothing and returns the first window while
# calling itself most-continuously-active. That is how a real run measured a
# bass intro and reported it as the guitar tone, so the tie has to be reported.
#
# The harder half is not over-reporting it. The policy says only what is true of
# every case that reaches it — these windows scored the same and this is the
# earliest — because a large plateau does NOT mean the ranking failed.


def test_a_gapped_source_really_is_ranked_by_activity():
    """The case the ranking was written for still works and still says so."""
    quiet = np.zeros(SAMPLE_RATE * 4)
    audio = io.from_samples(
        np.concatenate([quiet, fx.noise(seconds=2.0), quiet]), SAMPLE_RATE
    )
    sel = io.excerpt_selection(audio, 2.0)
    start, end, policy, fraction = sel.start, sel.end, sel.policy, sel.active_fraction
    assert policy == "most_continuously_active"
    assert 3.9 < start / SAMPLE_RATE < 4.1
    assert end - start == SAMPLE_RATE * 2
    assert fraction < 0.5, "most of this source is silence"


def test_a_continuously_active_source_reports_the_tie():
    """Nothing distinguishes any window, so `argmax` is picking the first one."""
    audio = io.from_samples(fx.noise(seconds=10.0), SAMPLE_RATE)
    sel = io.excerpt_selection(audio, 2.0)
    start, policy, fraction = sel.start, sel.policy, sel.active_fraction
    assert policy == "activity_tie"
    assert fraction > 0.9
    assert start == 0, "which is the start of the file, not a chosen section"


def test_an_explicit_window_is_taken_as_given():
    audio = io.from_samples(fx.noise(seconds=10.0), SAMPLE_RATE)
    sel = io.excerpt_selection(audio, 2.0, start_s=6.0)
    start, end, policy = sel.start, sel.end, sel.policy
    assert policy == "explicit_window"
    assert start == SAMPLE_RATE * 6
    assert end - start == SAMPLE_RATE * 2


def test_an_explicit_window_past_the_end_is_clamped_and_says_so():
    """Measuring a shorter window than asked for would silently change the
    measurement, so the length is kept and the start moves. But the move is
    reported: `--excerpt-start 300` on a 60 s file measured the last 20 s and
    called them the window the user named, which is a whole match budget spent
    on a window nobody chose."""
    audio = io.from_samples(fx.noise(seconds=10.0), SAMPLE_RATE)
    sel = io.excerpt_selection(audio, 2.0, start_s=999.0)
    assert sel.policy == "explicit_window_clamped"
    assert sel.end == audio.frames
    assert sel.end - sel.start == SAMPLE_RATE * 2


def test_a_window_that_fits_is_not_reported_as_clamped():
    """The distinction has to survive: a clamp caveat on every honoured request
    would be noise, and noise is how a real one gets skipped."""
    audio = io.from_samples(fx.noise(seconds=10.0), SAMPLE_RATE)
    assert io.excerpt_selection(audio, 2.0, start_s=8.0).policy == "explicit_window"
    assert io.excerpt_selection(audio, 2.0, start_s=8.1).policy == (
        "explicit_window_clamped"
    ), "8.1 s + 2 s does not fit in 10 s"


def test_excerpt_bounds_still_returns_a_pair():
    """Its two callers are unchanged; the extra reporting is additive."""
    audio = io.from_samples(fx.noise(seconds=10.0), SAMPLE_RATE)
    assert io.excerpt_bounds(audio, 2.0) == io.excerpt_selection(audio, 2.0)[:2]


def test_a_short_source_reports_that_it_could_not_honour_the_window():
    """Start 5 s into a 3 s file and there is nothing to select — but dropping
    the request silently would report `full_source` for a run the caller
    believes was windowed, which is the whole failure this flag exists to fix."""
    audio = io.from_samples(fx.noise(seconds=3.0), SAMPLE_RATE)
    sel = io.excerpt_selection(audio, 20.0, start_s=5.0)
    start, end, policy = sel.start, sel.end, sel.policy
    assert (start, end) == (0, audio.frames)
    assert policy == "explicit_window_ignored_short_source"


def test_a_short_source_with_no_window_request_is_just_the_full_source():
    """No request, nothing ignored: the ordinary case keeps its ordinary name."""
    audio = io.from_samples(fx.noise(seconds=3.0), SAMPLE_RATE)
    assert io.excerpt_selection(audio, 20.0).policy == "full_source"
    assert io.excerpt_selection(audio, 20.0, start_s=0.0).policy == "full_source", (
        "starting at zero is what a full source already is"
    )


def test_a_long_plateau_is_not_mistaken_for_a_failed_ranking():
    """The ranking found the music; the caveat must not say otherwise.

    Ten seconds of silence then fifty of playing. Every window that sits inside
    the music ties — 31 of 41 of them — so a plain tie-share test calls this
    degenerate. It is not: `argmax` lands on the first note, which is exactly
    the job. An earlier version reported "the excerpt was NOT chosen by
    activity ... every candidate window scored the same and the earliest one was
    taken" two lines under a start of 9.96 s, all three claims false.
    """
    lead_in = np.zeros(SAMPLE_RATE * 10)
    audio = io.from_samples(
        np.concatenate([lead_in, fx.band_limited(seconds=50.0)]), SAMPLE_RATE
    )
    sel = io.excerpt_selection(audio, 20.0)
    assert 9.5 < sel.start / SAMPLE_RATE < 10.5, "the silence was excluded"
    assert sel.tied_windows > 0.5 * sel.candidate_windows, (
        "the plateau really is large — this is the shape that used to be "
        "misreported, not a case that avoids the threshold"
    )
    assert sel.policy == "activity_tie"


def test_the_tie_counts_are_reported_so_a_caveat_can_be_specific():
    audio = io.from_samples(fx.noise(seconds=10.0), SAMPLE_RATE)
    sel = io.excerpt_selection(audio, 2.0)
    assert sel.candidate_windows > 1
    assert sel.tied_windows == sel.candidate_windows, "white noise ties everywhere"


def test_a_source_barely_longer_than_the_window_is_not_worth_a_caveat():
    """Eleven candidates that overlap almost completely: saying they tied is
    true and useless, and a caveat that fires on ordinary material is how the
    ones that matter get skipped."""
    audio = io.from_samples(fx.noise(seconds=3.0), SAMPLE_RATE)
    assert io.excerpt_selection(audio, 2.0).policy == "most_continuously_active"
