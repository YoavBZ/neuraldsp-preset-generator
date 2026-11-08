import pytest

from learn import heavy_cleanup as H


def setting(**on):
    s = {"reverb/reverbActive": "false", "delay/delayActive": "false", "tremolo/tremoloActive": "false",
         "parameters/doublerActive": "false", "pr12Amp/pr12Reverb": "0", "sw50rAmp/sw50rReverb": "0.3",
         "cabParameters/leftRoomActive": "false", "cabParameters/leftCabActive": "true",
         "cabParameters/rightRoomActive": "true", "cabParameters/rightCabActive": "false", "pr12Amp/pr12Gain": "0.5"}
    s.update(on)
    return s


def test_switches_count_a_room_only_on_an_active_cab_and_the_rows_own_spring():
    assert H.switches(setting(), "pr12") == []                                    # sw50r's spring: another amp
    assert H.switches(setting(), "sw50r") == ["spring"]
    assert H.switches(setting(**{"cabParameters/leftRoomActive": "true"}), "ac20") == ["room"]
    assert H.switches(setting(**{"reverb/reverbActive": "true", "parameters/doublerActive": "true"}), "ac20") == ["reverb", "doubler"]


def test_the_dry_twin_changes_only_declared_keys():
    x = {tuple(k.split("/")): v for k, v in setting(**{"delay/delayActive": "true", "pr12Amp/pr12Reverb": "0.4"}).items()}
    y = H.dry(x, "pr12")
    assert y[("delay", "delayActive")] == "false" and y[("pr12Amp", "pr12Reverb")] == "0"
    assert y[("sw50rAmp", "sw50rReverb")] == "0.3"                                # the other amp's knob stays
    assert y[("cabParameters", "rightRoomActive")] == "false" and y[("pr12Amp", "pr12Gain")] == "0.5"
    H.check_dry(x, y)
    with pytest.raises(SystemExit):
        H.check_dry(x, {**y, ("pr12Amp", "pr12Gain"): "0.6"})
    with pytest.raises(SystemExit):
        H.check_dry(x, {**y, ("new", "key"): "1"})


def test_draw_is_disjoint_and_per_family():
    rows = []
    i = 0
    for fam, on in (("reverb", {"reverb/reverbActive": "true"}), ("delay", {"delay/delayActive": "true"}),
                    ("doubler", {"parameters/doublerActive": "true"}), ("tremolo", {"tremolo/tremoloActive": "true"}),
                    ("spring", {}), ("room", {"cabParameters/leftRoomActive": "true"}), ("none", {})):
        for _ in range(12):
            i += 1
            amp = "sw50r" if fam == "spring" else "pr12"
            rows.append({"i": i, "amp": amp, "settings": {**setting(**on), "cabParameters/rightRoomActive": "false"}})
    items = H.draw(rows)
    assert len(items) == 6 * H.PER_FAMILY + H.N_SAME + H.N_ON
    assert len({it["i"] for it in items}) == len(items)
    assert {it["family"] for it in items if it["kind"] == "dry"} == set(H.FAMILIES)
    assert items == H.draw(rows)                                                    # seeded


def test_margin_takes_the_worst_negative_shift_when_larger():
    assert H.margin([0.2, 1.0]) == 0.5
    assert H.margin([-0.8, 1.0]) == 0.8
    assert H.residual_db(__import__("numpy").ones(4), __import__("numpy").ones(4)) == float("-inf")
