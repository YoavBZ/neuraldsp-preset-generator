"""The audition page plays every clip at one loudness, as it will be heard."""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audition as A  # noqa: E402

np = pytest.importorskip("numpy", reason="needs the analysis extra")
sf = pytest.importorskip("soundfile", reason="needs the analysis extra")
pytest.importorskip("pyloudnorm", reason="needs the analysis extra")

RATE = 48000


def _tone(seconds=4.0, freq=220.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * RATE)) / RATE
    return (0.2 * np.sin(2 * np.pi * freq * t) + 0.01 * rng.standard_normal(len(t))
            ).astype(np.float32)


def test_a_mono_clip_plays_as_two_identical_channels():
    x = _tone()
    played = A.as_played(x)
    assert played.shape == (len(x), 2)
    assert np.array_equal(played[:, 0], played[:, 1])
    assert A.as_played(x[:, None]).shape == (len(x), 2)


def test_a_two_channel_clip_is_left_as_it_is():
    stereo = np.stack([_tone(seed=1), _tone(seed=2, freq=330.0)], axis=1)
    assert np.array_equal(A.as_played(stereo), stereo)


def test_more_than_two_channels_is_refused():
    with pytest.raises(ValueError):
        A.as_played(np.zeros((100, 3)))


def _page(tmp_path, song, render):
    raw = tmp_path / "raw"
    raw.mkdir()
    sf.write(str(raw / "song.wav"), song, RATE, subtype="FLOAT")
    sf.write(str(raw / "A-riff-1.wav"), render, RATE, subtype="FLOAT")
    record = {"candidates": [{"renders": {"riff-1": "A-riff-1.wav"}}]}
    A.level_page(tmp_path, record)
    return {name: sf.read(str(tmp_path / name))[0] for name in ("song.wav", "A-riff-1.wav")}


def test_a_mono_song_and_a_render_of_the_same_signal_play_at_one_level(tmp_path):
    x = _tone()
    clips = _page(tmp_path, x, np.stack([x, x], axis=1))       # a mono song, a render
    for clip in clips.values():
        assert clip.ndim == 2 and clip.shape[1] == 2
    rms = {n: np.sqrt((c ** 2).mean(axis=0)) for n, c in clips.items()}
    assert np.allclose(rms["song.wav"], rms["A-riff-1.wav"], rtol=0.01)


def test_a_decorrelated_stereo_render_keeps_its_channels(tmp_path):
    left, right = _tone(seed=3), _tone(seed=4, freq=330.0)
    clips = _page(tmp_path, _tone(seed=5), np.stack([left, right], axis=1))
    render = clips["A-riff-1.wav"]
    gain = np.sqrt((render[:, 0] ** 2).mean() / (left ** 2).mean())
    assert np.allclose(render[:, 0], left * gain, atol=2e-4)       # PCM_16 rounding
    assert np.allclose(render[:, 1], right * gain, atol=2e-4)


def test_re_levelling_a_page_with_a_mono_raw_song_is_stable(tmp_path):
    x = _tone()
    _page(tmp_path, x, np.stack([x, x], axis=1))
    record = {"candidates": [{"renders": {"riff-1": "A-riff-1.wav"}}]}
    A.level_page(tmp_path, record)                  # as --add does, from the raw files
    first = dict(record["gain_db"])
    A.level_page(tmp_path, record)
    assert record["gain_db"] == first
    assert sf.info(str(tmp_path / "raw" / "song.wav")).channels == 1     # raw kept as is


def test_a_song_with_more_than_two_channels_is_refused_before_anything_is_written(
        tmp_path, monkeypatch):
    song = tmp_path / "surround.wav"
    sf.write(str(song), np.zeros((RATE * 12, 3), dtype=np.float32), RATE)
    out = tmp_path / "page"
    monkeypatch.setattr(sys, "argv", ["audition.py", "--song", str(song), "--start", "0",
                                      "--out-dir", str(out), "--preset",
                                      str(ROOT / "samples" / "Example_Clean_PR12.xml")])
    with pytest.raises(SystemExit):
        A.main()
    assert not out.exists() or not any(out.iterdir())


def test_the_phone_page_holds_every_clip_inside_it(tmp_path):
    import shutil

    if shutil.which("afconvert") is None:
        pytest.skip("the phone page needs macOS's afconvert")
    sf.write(str(tmp_path / "song.wav"), np.stack([_tone()] * 2, axis=1), RATE, subtype="PCM_16")
    sf.write(str(tmp_path / "A-riff-1.wav"), np.stack([_tone(seed=1)] * 2, axis=1), RATE,
             subtype="PCM_16")
    (tmp_path / "index.html").write_text(
        '<audio src="song.wav"></audio><audio src="A-riff-1.wav"></audio><p>keep me</p>')
    phone = A.write_phone_page(tmp_path)
    text = phone.read_text()
    assert text.count('src="data:audio/mp4;base64,') == 2
    assert ".wav" not in text and "<p>keep me</p>" in text


def test_without_afconvert_there_is_no_phone_page_and_no_error(tmp_path, monkeypatch, capsys):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda name: None)
    (tmp_path / "index.html").write_text('<audio src="song.wav"></audio>')
    assert A.write_phone_page(tmp_path) is None
    assert not (tmp_path / "phone.html").exists()
    assert "afconvert" in capsys.readouterr().err
