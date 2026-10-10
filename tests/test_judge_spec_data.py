"""The judge's specification (`docs/judge-spec.md`) on stored set-3 development renders.

Local only: skipped where `~/ndsp-presets` is absent (CI). Development data only: the
fixed-level measure renders (`learn/direc/gap-split/measfix`) and their stored distances
(`learn/direc/rescore/distances*.json`, written by `learn/rescore.py`). No held-out data.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

np = pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("pyloudnorm", reason="needs the analysis extra")
sf = pytest.importorskip("soundfile", reason="needs the analysis extra")
stats = pytest.importorskip("scipy.stats", reason="needs the analysis extra")

from analysis.aligned import aligned_distance  # noqa: E402

ROOT = pathlib.Path("~/ndsp-presets").expanduser()
MEASFIX = ROOT / "learn/direc/gap-split/measfix"
RESCORE = ROOT / "learn/direc/rescore"
CROPS = ROOT / "references/validation-crops-set3"
pytestmark = pytest.mark.skipif(
    not ((RESCORE / "distances.json").exists() and MEASFIX.exists() and CROPS.exists()),
    reason="set-3 development renders not on this machine")

SR, LATENCY = 48000, 52
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}
AMPS = ("pr12", "sw50r", "ac20")
ILL_FATE = "cambridge-ill-fate-elecgtr1"
WALL_OF_DOOM = "factory:Artists/Royce Whittaker/Wall Of Doom"

# Judge name -> (aligned_distance options, distances file tag, judge key in that file).
JUDGES = {"default": ({}, "", "flat"), "v2": ({"bands": "fixed"}, "fixed", "fixed"),
          "v3": ({"bands": "fixed", "floor": "symmetric"}, "v3", "v3")}
KNOWN = {
    ("default", "ill_fate_treble"):
        "Ill Fate 1 scores 8 of 64 bands, none above 400 Hz: treble changes cost 0",
    ("v2", "ill_fate_treble"):
        "all bands are scored, but the per-frame floor, 40 dB under the fundamental, still "
        "clamps the recording above about 700 Hz: +3 dB at 1.6 kHz costs 0.03 against 0.81",
}


def judges(prop):
    return [pytest.param(j, marks=pytest.mark.xfail(strict=True, reason=KNOWN[(j, prop)]))
            if (j, prop) in KNOWN else j for j in JUDGES]


def _mono(path):
    path = pathlib.Path(path)
    if not path.exists():
        path = path.with_suffix(".flac")
    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    assert sr == SR
    return x.mean(axis=1)


def _render(slug, amp, name):
    return _mono(MEASFIX / slug / amp / f"{hashlib.sha1(name.encode()).hexdigest()[:12]}.wav")


def _lags():
    from learn import set3

    return {p["slug"]: p["judge_lag_samples"] for p in set3.parts("development")}


def _stored(tag):
    path = RESCORE / ("distances.json" if not tag else f"distances-{tag}.json")
    if not path.exists():
        pytest.skip(f"{path.name} not scored on this machine")
    return json.loads(path.read_text())


def _distance(judge, slug, render, half, **extra):
    a, b = HALVES[half]
    return aligned_distance(_mono(CROPS / slug / "reference.wav"), render,
                            np.load(MEASFIX / slug / "di.npy"), lag=_lags()[slug],
                            render_latency=LATENCY, start_s=a, end_s=b,
                            **JUDGES[judge][0], **extra)


@pytest.mark.parametrize("judge", judges("reproduces"))
def test_stored_distances_reproduce_from_the_audio(judge):
    """The judge as stored is the judge as coded."""
    options, tag, key = JUDGES[judge]
    stored = _stored(tag)
    for slug in (ILL_FATE, "cambridge-magilla-elecgtr1", "cambridge-the-well-elecgtr01"):
        for amp, name in (("sw50r", WALL_OF_DOOM), ("pr12", "template+R")):
            render = _render(slug, amp, name)
            for half in HALVES:
                d = _distance(judge, slug, render, half)
                # Equal to float rounding (summation order varies with the BLAS build).
                assert (d.distance, d.tonal, d.temporal) == pytest.approx(tuple(
                    stored[slug][f"{key}|{amp}|measfix_{half}"][name]), rel=1e-12, abs=0), (
                    slug, amp, half)


@pytest.mark.parametrize("judge", judges("halves"))
def test_the_halves_rank_the_menus_alike(judge):
    """Half A (1–5.5 s) and half B (5.5–10 s) rank each part's menu alike: median
    Spearman ρ at least 0.95 and the 10th percentile at least 0.7 over the 99
    part × amp menus (the default judge: 0.984 and 0.826)."""
    _, tag, key = JUDGES[judge]
    stored = _stored(tag)
    rho = []
    for slug, rows in stored.items():
        for amp in AMPS:
            a, b = rows[f"{key}|{amp}|measfix_A"], rows[f"{key}|{amp}|measfix_B"]
            names = [n for n in a if a[n][0] and b.get(n) and b[n][0]]
            rho.append(stats.spearmanr([a[n][0] for n in names],
                                       [b[n][0] for n in names]).statistic)
    assert len(rho) == 99
    assert np.median(rho) >= 0.95 and np.percentile(rho, 10) >= 0.7, (
        np.median(rho), np.percentile(rho, 10))


def _fgain(x, fn):
    n = len(x)
    size = 1 << int(np.ceil(np.log2(n)))
    f = np.fft.rfftfreq(size, 1 / SR)
    return np.fft.irfft(np.fft.rfft(x, size) * 10 ** (fn(f) / 20), size)[:n]


@pytest.mark.parametrize("judge", judges("ill_fate_treble"))
def test_treble_changes_count_on_ill_fate(judge):
    """On the most bass-heavy development part, a treble change applied to the recording
    itself costs at least half what it costs on a balanced part (The Well 1), half B."""
    def cost(slug, change):
        x = _mono(CROPS / slug / "reference.wav")
        a, b = HALVES["B"]
        # The recording against a changed copy of itself: lag 0, the DI as for a render.
        return aligned_distance(x, change(x), np.load(MEASFIX / slug / "di.npy"), lag=0,
                                render_latency=_lags()[slug] + LATENCY, start_s=a, end_s=b,
                                **JUDGES[judge][0]).distance

    changes = {
        "+3 dB octave at 1.6 kHz":
            lambda x: _fgain(x, lambda f: 3 * np.exp(-0.5 * (np.log2(np.maximum(f, 1) / 1600) / 0.5) ** 2)),
        "+12 dB shelf over 5 kHz":
            lambda x: _fgain(x, lambda f: 12 / (1 + np.exp(-6 * np.log2(np.maximum(f, 1) / 5000)))),
        "-12 dB shelf over 5 kHz":
            lambda x: _fgain(x, lambda f: -12 / (1 + np.exp(-6 * np.log2(np.maximum(f, 1) / 5000)))),
    }
    for name, change in changes.items():
        heavy, balanced = cost(ILL_FATE, change), cost("cambridge-the-well-elecgtr01", change)
        assert heavy >= 0.5 * balanced, (name, heavy, balanced)
