"""T0x (`learn/fx_t0x.py`): its level and its reuse of T0's and T1x's parts."""

from learn import fx_t0x as X


def test_t0x_reads_at_minus_three_db_with_t0s_parts():
    from learn import fx_t0 as T0
    from learn import fx_t1x as T1X

    assert X.RATIO_DB == -3.0 and X.RATIO_DB in T1X.RATIOS
    assert set(T0.EFFECTS) == {"reverb", "delay", "tremolo"} and callable(T0.read_effect) and callable(T0.passes)
