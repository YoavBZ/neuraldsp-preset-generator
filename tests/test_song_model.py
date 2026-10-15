"""Arm B's label layout and encoding (`learn/song_model.py`)."""

import pytest

np = pytest.importorskip("numpy")

from learn import song_model as M  # noqa: E402


def test_layout_covers_every_amp_space():
    from learn import knob_ceiling as K

    for amp in K.AMPS:
        for d in K.space(amp):
            assert d.name in M.CONT + M.SW + M.CAT, d.name


def test_encode_masks_settings_the_amp_lacks():
    c, cm, s, sm, k, km = M.encode({"parameters/inputGain": 0.25, "cabParameters/leftMicType": "7",
                                    "sw50rAmp/sw50rBright": "true"})
    assert cm.sum() == 1 and c[M.CONT.index("parameters/inputGain")] == 0.25
    assert sm.sum() == 1 and s[M.SW.index("sw50rAmp/sw50rBright")] == 1.0
    assert km[M.CAT.index("cabParameters/leftMicType")] == 1 and k[M.CAT.index("cabParameters/leftMicType")] == 7
