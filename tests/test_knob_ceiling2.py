"""Knob ceiling 2's pure parts (`learn/knob_ceiling2.py`) and `knob_search`'s `canon`."""

import pytest

pytest.importorskip("numpy")

from learn import knob_ceiling as K  # noqa: E402
from learn import knob_ceiling2 as K2  # noqa: E402


def test_canon_none_leaves_knob_search_unchanged():
    dims = [K.Dim("a", "x", "cont"), K.Dim("a", "y", "cont")]
    x0 = {("a", "x"): "0.1", ("a", "y"): "0.9"}
    f = lambda x: abs(float(x[("a", "x")]) - 0.6) + abs(float(x[("a", "y")]) - 0.3)
    assert K.knob_search(dims, x0, f, 80, 0)[:2] == K.knob_search(dims, x0, f, 80, 0, canon=None)[:2]


def test_canon_makes_moves_of_an_off_pedal_free():
    dims = [K.Dim("drive1", "drive1Active", "switch", values=("false", "true")),
            K.Dim("drive1", "drive1Drive", "cont"), K.Dim("a", "x", "cont")]
    x0 = {("drive1", "drive1Active"): "false", ("drive1", "drive1Drive"): "0.3",
          ("drive1", "drive1Level"): "0.5", ("drive1", "drive1Tone"): "0.5", ("a", "x"): "0.1"}
    seen = []

    def f(x):
        seen.append(dict(x))
        on = x[("drive1", "drive1Active")] == "true"
        return abs(float(x[("a", "x")]) - 0.6) + (0.0 if not on else 0.5)
    K.knob_search(dims, x0, f, 60, 0, canon=K2.canon_pedals)
    # with the pedal off, its drive knob is always at the neutral value when rendered
    assert all(x[("drive1", "drive1Drive")] == "0.3" for x in seen if x[("drive1", "drive1Active")] == "false")


def test_stage1_space_holds_the_mics_and_widens_input_gain():
    start = {("cabParameters", "leftCabActive"): "true"}
    dims = K2.stage1_space("sw50r", start)
    names = {d.name for d in dims}
    assert not any(d.kind == "cat" for d in dims)
    gain = next(d for d in dims if d.key == "inputGain")
    assert (gain.lo, gain.hi) == (-24.0, 12.0)
    assert {"drive1/drive1Active", "compressor/compressorMix", "sw50rEQ/sw50rEQBand5"} <= names


def test_effects_canon_forces_free_sync_and_neutral_off_effects():
    c = K2.make_canon_effects("pr12")
    y = c({("delay", "delayActive"): "false", ("delay", "delaySync"): "1", ("delay", "delayTime"): "900",
           ("reverb", "reverbActive"): "true", ("reverb", "reverbMix"): "0.7",
           ("tremolo", "tremoloActive"): "false", ("spring", K2.SPRING_SWITCH): "false"})
    assert y[("delay", "delaySync")] == "0" and y[("delay", "delayTime")] == "350"
    assert y[("reverb", "reverbMix")] == "0.7"                      # on: left alone
    assert K2.plugin_settings(y, "pr12")[("pr12Amp", "pr12Reverb")] == "0"
    assert ("spring", K2.SPRING_SWITCH) not in K2.plugin_settings(y, "pr12")


def test_best_amp_uses_the_search_half_only():
    run = lambda s, h: {"EQ": {"search": s, "held": h}}
    cells = {("p", "pr12"): {"runs": {"A": run(3.0, 1.0), "B": run(2.0, 9.0)}},
             ("p", "ac20"): {"runs": {"A": run(2.5, 9.0), "B": run(4.0, 1.0)}}}
    assert K2.best_amp(cells, "p", "A") == "ac20" and K2.best_amp(cells, "p", "B") == "pr12"
