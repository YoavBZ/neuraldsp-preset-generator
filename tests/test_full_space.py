"""T3's label space (`learn/full_space.py`): the layout, the draw, the masked encoding, the written answer, the
output-gain fit; the network and loss where torch is installed. No renders, no data files."""

import json
import math
import pathlib
import random

import pytest

np = pytest.importorskip("numpy")

from learn import every_control as EC  # noqa: E402
from learn import full_space as F  # noqa: E402
from learn import song_model as SM  # noqa: E402

MANIFEST = json.loads((pathlib.Path(__file__).resolve().parents[1] / "packs/morgan/manifest.json").read_text())["parameters"]


def _neutral_setting(amp="pr12"):
    """Every table control at its neutral value (a stand-in for S): sections on, both cabs on."""
    x = {c.path: c.neutral for c in EC.table("morgan") if c.neutral is not None}
    x[F.AMP] = EC.MORGAN_AMPS[amp]
    x[F.OUTPUT] = "3"
    return x


# --- the layout ---------------------------------------------------------------------------------------------

def test_layout_counts_match_amendment_2():
    assert len(F.space_controls()) == 115
    assert len(F.learned_controls()) == 113                    # less the amp choice and output gain
    assert (len(F.CONT), len(F.SW), len(F.CAT)) == (85, 28, 2)  # 86 continuous less output gain; 26 + 2 springs
    assert sum(1 for n in F.SW if n.endswith("/" + F.SPRING_KEY)) == 2
    assert len(F.new_paths()) == 113 - 25
    names = {d.name for d in F.dims().values()}
    assert F.TODAY <= names and len(F.TODAY) == 25


def test_kinds_and_ranges_agree_with_the_manifest():
    for p, d in F.dims().items():
        spec = MANIFEST["/".join(p)]
        if d.kind == "switch":
            assert spec["kind"] == "switch", p
        elif d.kind == "cat":
            assert spec.get("enum") == "internalMic", p
        else:
            assert spec["kind"] in ("rotation", "fraction", "metered"), p
            lo, hi = spec.get("min", 0.0), spec.get("max", 1.0)
            assert lo <= d.lo < d.hi <= hi, (p, d.lo, d.hi, lo, hi)


def test_todays_dims_keep_part_cs_ranges():
    from learn import knob_ceiling as K

    D = F.by_name()
    for amp in F.AMPS:
        for d in K.space(amp):
            assert (D[d.name].lo, D[d.name].hi, D[d.name].kind) == (d.lo, d.hi, d.kind)


def test_cell_masks_follow_the_amp():
    cm, swm, km = F.cell_masks("pr12")
    names = dict(zip(F.CONT, cm))
    assert names["pr12Amp/pr12Volume"] and not names["sw50rAmp/sw50rVolume"]
    assert names["pr12EQ/pr12EQBand1"] and not names["ac20EQ/ac20EQBand1"]
    assert names["reverb/reverbMix"]
    sws = dict(zip(F.SW, swm))
    assert sws["pr12Amp/springOn"] and not sws["sw50rAmp/springOn"]
    assert km.all()
    assert not dict(zip(F.SW, F.cell_masks("ac20")[1]))["pr12Amp/springOn"]


# --- the encoding -------------------------------------------------------------------------------------------

def _enc(x, amp):
    c, cm, s, sm, k, km, a = F.encode(x, amp)
    return dict(zip(F.CONT, zip(c, cm))), dict(zip(F.SW, zip(s, sm))), dict(zip(F.CAT, zip(k, km))), a


def test_encoding_masks_switched_off_features():
    x = _neutral_setting()
    x[("drive1", "drive1Active")] = "false"
    x[("reverb", "reverbActive")] = "true"
    x[("pr12EQ", "pr12EQActive")] = "true"
    cont, sw, cat, a = _enc(x, "pr12")
    assert a == F.AMPS.index("pr12")
    assert cont["drive1/drive1Drive"][1] == 0 and sw["drive1/drive1Active"][1] == 1      # the switch is scored
    assert cont["reverb/reverbMix"][1] == 1 and cont["pr12EQ/pr12EQBand3"][1] == 1
    assert cont["sw50rAmp/sw50rVolume"][1] == 0 and cont["sw50rEQ/sw50rEQBand3"][1] == 0   # other amps
    assert sw["sw50rAmp/sw50rBright"][1] == 0


def test_spring_is_a_derived_switch_and_its_level():
    x = _neutral_setting()
    x[("pr12Amp", "pr12Reverb")] = "0"
    cont, sw, _, _ = _enc(x, "pr12")
    assert sw["pr12Amp/springOn"] == (0.0, 1.0)                  # off, scored
    assert cont["pr12Amp/pr12Reverb"][1] == 0 and cont["pr12Amp/pr12Dwell"][1] == 0
    assert sw["sw50rAmp/springOn"][1] == 0                         # the other amp's spring never sounds on pr12
    x[("pr12Amp", "pr12Reverb")] = "0.3"
    cont, sw, _, _ = _enc(x, "pr12")
    assert sw["pr12Amp/springOn"] == (1.0, 1.0)
    assert cont["pr12Amp/pr12Reverb"] == (pytest.approx(0.3), 1.0) and cont["pr12Amp/pr12Dwell"][1] == 1


def test_cab_masks_mono():
    x = _neutral_setting()
    x[("cabParameters", "rightCabActive")] = "false"
    cont, sw, cat, _ = _enc(x, "pr12")
    assert cat["cabParameters/rightMicType"][1] == 0 and cat["cabParameters/leftMicType"][1] == 1
    assert cont["cabParameters/leftCabPan"][1] == 0                # pans and phase only with both cabs on
    assert sw["cabParameters/leftCabPhase"][1] == 0
    x[("cabParameters", "rightCabActive")] = "true"
    cont, sw, cat, _ = _enc(x, "pr12")
    assert cont["cabParameters/leftCabPan"][1] == 1 and sw["cabParameters/leftCabPhase"][1] == 1


def test_label_roundtrip():
    x = _neutral_setting("sw50r")
    lab = F.label_of(x, "sw50r")
    assert json.loads(json.dumps(lab)) == lab
    a, b = F.encode_label(lab), F.encode(x, "sw50r")[:6]
    assert all(np.array_equal(u, v) for u, v in zip(a, b))


# --- the draw -------------------------------------------------------------------------------------------------

def _core(amp="pr12", right="true"):
    x = _neutral_setting(amp)
    x[("cabParameters", "rightCabActive")] = right
    x[("delay", "delaySync")] = "1"
    x[("parameters", "inputGain")] = "4.5"
    return x


def test_draw_keeps_the_core_and_writes_sync_off_and_sections_on():
    core = _core()
    S = dict(core)
    x, tries = F.draw_new(7, "wide", core, S, S, 0.36)
    assert x == F.draw_new(7, "wide", core, S, S, 0.36)[0]          # deterministic per example
    assert x != F.draw_new(8, "wide", core, S, S, 0.36)[0]
    today = {p for p in core if "/".join(p) in F.TODAY}
    assert all(x[p] == core[p] for p in today)
    assert x[F.OUTPUT] == core[F.OUTPUT] and x[F.AMP] == core[F.AMP]
    assert x[("delay", "delaySync")] == "0" and x[("tremolo", "tremoloSync")] == "false"
    assert all(x[(s, "sectionActive")] == "true" for s in F.SECTIONS)


def test_wide_draws_redraw_both_cabs_off_and_cap_the_gate():
    core = _core(right="false")
    cap = 0.36
    lefts = []
    for i in range(200):
        x, tries = F.draw_new(i, "wide", core, core, core, cap)
        assert F.cabs_ok(x)
        lefts.append(tries)
        assert F.dims()[F.GATE_THR].to_unit(x[F.GATE_THR]) <= cap + 1e-6
    assert max(lefts) > 1                                           # some draws were redrawn


def test_wide_spring_is_a_fair_switch_with_a_level_above_zero():
    core = _core()
    on = 0
    for i in range(300):
        x, _ = F.draw_new(i, "wide", core, core, core, 1.0)
        v = float(x[("pr12Amp", "pr12Reverb")])
        if v > 0:
            on += 1
            assert v >= F.SPRING_MIN
        else:
            assert x[("pr12Amp", "pr12Reverb")] == "0"
    assert 100 < on < 200


def test_factory_and_start_spring_follows_the_centre():
    core = _core()
    off, on = dict(core), dict(core)
    off[("pr12Amp", "pr12Reverb")] = "0"
    on[("pr12Amp", "pr12Reverb")] = "0.4"
    for i in range(50):
        assert F.draw_new(i, "factory", core, off, core, 1.0)[0][("pr12Amp", "pr12Reverb")] == "0"
        assert float(F.draw_new(i, "factory", core, on, core, 1.0)[0][("pr12Amp", "pr12Reverb")]) > 0
        assert F.draw_new(i, "start", core, on, off, 1.0)[0][("pr12Amp", "pr12Reverb")] == "0"   # start: S's


def test_factory_centre_section_off_switches_its_features_off():
    centre = _core()
    centre[("fxParameters", "sectionActive")] = "false"
    centre[("reverb", "reverbActive")] = "true"
    y = F.sections_on(centre)
    assert y[("fxParameters", "sectionActive")] == "true" and y[("reverb", "reverbActive")] == "false"
    # with the keep probability most draws keep the centre's switch
    kept = sum(F.draw_new(i, "factory", _core(), centre, _core(), 1.0)[0][("reverb", "reverbActive")] == "false"
               for i in range(200))
    assert kept > 140


def test_positive_settings_are_the_core_with_sync_and_sections_written():
    core = _core()
    x = F.positive_settings(core, core)
    diff = {p for p in x if x[p] != core.get(p)}
    assert diff <= set(F.FREE) | {(s, "sectionActive") for s in F.SECTIONS}


def test_gate_cap_nearest_rank():
    u, v = F.gate_cap_u([-80, -70, -60, -50] * 5)
    assert v == -50 and u == pytest.approx((-50 + 96) / 96)
    u, v = F.gate_cap_u(list(range(-96, -76)))                     # 20 values: the 19th
    assert v == -78


# --- the written answer -------------------------------------------------------------------------------------

def _heads(amp, S, sw_on=()):
    D = F.by_name()
    cont = np.array([D[n].to_unit(S.get((D[n].module, D[n].key), D[n].lo)) for n in F.CONT])
    sw = np.array([1.0 if n in sw_on else 0.0 for n in F.SW])
    mics = [3, 4]
    return cont, sw, mics


def test_answer_neutralises_off_features_and_keeps_output_gain():
    S = _core()
    S[("drive1", "drive1Drive")] = "0.9"
    cont, sw, mics = _heads("pr12", S, sw_on={"cabParameters/rightCabActive", "cabParameters/leftCabActive"})
    cont[F.CONT.index("drive1/drive1Drive")] = 0.8
    x = F.answer_settings("pr12", S, cont, sw, mics)
    assert x[("drive1", "drive1Active")] == "false"
    assert x[("drive1", "drive1Drive")] == EC.table("morgan")[[c.path for c in EC.table("morgan")].index(
        ("drive1", "drive1Drive"))].neutral                        # off -> neutral
    assert x[F.OUTPUT] == S[F.OUTPUT]
    assert x[("pr12Amp", "pr12Reverb")] == "0"                       # spring switch off -> level 0
    assert x[("cabParameters", "leftMicType")] == "3"


def test_answer_spring_on_and_families_at_S():
    S = _core()
    S[("reverb", "reverbMix")] = "0.11"
    S[("reverb", "reverbActive")] = "false"
    on = {"pr12Amp/springOn", "reverb/reverbActive", "cabParameters/rightCabActive", "cabParameters/leftCabActive"}
    cont, sw, mics = _heads("pr12", S, sw_on=on)
    cont[F.CONT.index("pr12Amp/pr12Reverb")] = 0.5
    cont[F.CONT.index("reverb/reverbMix")] = 0.7
    x = F.answer_settings("pr12", S, cont, sw, mics)
    assert float(x[("pr12Amp", "pr12Reverb")]) == pytest.approx(0.5) and x[("reverb", "reverbActive")] == "true"
    assert float(x[("reverb", "reverbMix")]) == pytest.approx(0.7)
    y = F.answer_settings("pr12", S, cont, sw, mics, at_S=("time effects and spring",))
    assert y[("reverb", "reverbActive")] == "false" and y[("pr12Amp", "pr12Reverb")] == S[("pr12Amp", "pr12Reverb")]


def test_answer_never_has_both_cabs_off():
    S = _core()
    cont, sw, mics = _heads("pr12", S)
    sw[F.SW.index("cabParameters/leftCabActive")] = 0.3
    sw[F.SW.index("cabParameters/rightCabActive")] = 0.1
    x = F.answer_settings("pr12", S, cont, sw, mics)
    assert x[("cabParameters", "leftCabActive")] == "true" and x[("cabParameters", "rightCabActive")] == "false"


def test_output_gain_fit_is_linear_and_clamped():
    assert F.output_gain_fit(3.0, -20.0, -14.0) == (9.0, False)
    assert F.output_gain_fit(20.0, -30.0, -10.0) == (24.0, True)
    assert F.output_gain_fit(0.0, -10.0, -40.0) == (-24.0, True)
    assert "confirmed" in F.OUTPUT_FIT_STATUS


def test_readout_without_amp_head():
    rng = np.random.default_rng(0)
    n = len(SM.CONT)
    outs = [(np.log(np.full(4, 0.25)), rng.random((4, n)), np.full((4, n), -2.0), np.array([3.0, -3.0, 0, 0, 0, 0]),
             [np.eye(10)[2] * 5, np.eye(10)[7] * 5], None) for _ in range(2)]
    r = F.readout(outs)
    assert r["amp"] is None and r["mics"] == [2, 7]
    assert r["sw_p"][0] > 0.9 and r["sw_p"][1] < 0.1 and len(r["a1"]) == 2
    assert np.allclose(r["a2"], np.mean(r["a1"], axis=0))


def test_readout_amp_head_by_mean_probability():
    n = len(F.CONT)
    mk = lambda amp_logits: (np.zeros(4), np.full((4, n), 0.5), np.full((4, n), -2.0), np.zeros(len(F.SW)),  # noqa: E731
                             [np.zeros(10), np.zeros(10)], np.array(amp_logits))
    r = F.readout([mk([2.0, 0.0, 0.0]), mk([0.0, 2.5, 0.0])])
    assert r["amp"] == "sw50r" and math.isclose(sum(r["amp_p"]), 1.0)


# --- the network (torch) --------------------------------------------------------------------------------------

def test_net_and_masked_loss():
    torch = pytest.importorskip("torch")
    net = F.build_net(width=(4, 4, 4, 4))
    x = torch.zeros((3, 2, 96, 446))
    c = torch.zeros((3, len(SM.AMPS) + len(SM.CLASSES) + 2))
    out = net(x, c)
    assert out[1].shape == (3, SM.K_MIX, len(F.CONT)) and out[3].shape == (3, len(F.SW)) and out[5].shape == (3, 3)
    setting = _neutral_setting()
    y = [torch.tensor(np.stack([v] * 3)) for v in F.encode(setting, "pr12")]
    loss = F.loss_fn(out, *y)
    assert torch.isfinite(loss)
    # the amp head reads the audio only: the condition does not move it
    net.eval()
    a0 = net(x, c)[5]
    c2 = c.clone()
    c2[:, 0] = 1
    assert torch.allclose(a0, net(x, c2)[5])


def test_random_module_unused_by_draw_order():
    """The draw uses its own seeded stream: the global random state does not change it."""
    core = _core()
    random.seed(1)
    a = F.draw_new(11, "wide", core, core, core, 1.0)[0]
    random.seed(2)
    assert F.draw_new(11, "wide", core, core, core, 1.0)[0] == a
