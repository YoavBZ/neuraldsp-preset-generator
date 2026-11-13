"""A2s (`learn/amp_di_compare_s.py`): its sets and level match A2's and the product path's."""

from learn import amp_di_compare_s as S


def test_a2s_reads_a2s_sets_at_the_product_level():
    from learn import amp_di_compare_r as R
    from learn import product_path as PP

    assert set(S.SETS) == set(R.SETS) and S.MIX_LEVEL == PP.MIX_LEVEL == -12.25
