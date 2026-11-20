"""The family check's declared rule, table, shrink, shuffle and readings (`learn/gear_family.py`,
`docs/family-class-checks-plan.md` part A). Pure: runs on the light CI runner (no numpy)."""
import math

import pytest

from learn import gear_family as G


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


# --- the table -------------------------------------------------------------------------------------------------------------

def test_gf_table_is_whole_as_declared():
    G.table_guard()
    want = {(True, True, True): "GF-go", (True, False, True): "GF-go",
            (True, True, False): "GF-stop", (False, True, False): "GF-stop",
            (False, False, True): "GF-thin", (False, False, False): "GF-thin",
            (False, True, True): "GF-thin", (True, False, False): "GF-thin"}
    assert {k: G.gf_cell(*k)[0] for k in want} == want


@pytest.mark.parametrize("cut", [slice(0, -1), slice(1, None)])
def test_the_guard_refuses_a_broken_table(monkeypatch, cut):
    monkeypatch.setattr(G, "GF_TABLE", G.GF_TABLE[cut])
    with pytest.raises(SystemExit):
        G.table_guard()


def test_thin_offers_the_render_read_without_running_it():
    nxt = G.gf_cell(False, False, False)[1]
    assert "render read" in nxt and "not run without a yes" in nxt
    assert "nothing renders before the user's yes" in G.gf_cell(True, False, True)[1]


# --- the rule --------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("pack,fam", [
    ("fender-blues-junior-iii-ltd-gain-95-sm57-78177", "fender"),
    ("fender-tweed-deluxe-5e3-1", "tweed"),                    # tweed's row comes first
    ("vox-ac30-top-boost", "vox"), ("some-ac15-clone", "vox"),
    ("marshall-jtm45-x", "marshall"), ("plexi-1987x", "marshall"),
    ("hiwatt-dr103-fane-speakers-sm57-full-rig-2711", "hiwatt"),
    ("prototype-amp-hiwatt-sovtek-sound-city-57315", "hiwatt"),   # the review's oddity, kept by the rule
    ("orange-or15", "orange"), ("two-rock-classic", "two-rock"), ("tworock-x", "two-rock"),
    ("63-silvertone-1472-jensen-1x12-ver-21-108164", "none"), ("", "none"), (None, "none")])
def test_family_rule(pack, fam):
    assert G.family_of(pack) == fam


def test_odd_pack_prefix_matches_the_rule_oddity():
    assert "prototype-amp-hiwatt-sovtek-sound-city-57315".startswith(G.ODD_PACK)


# --- the shrink and the power bar --------------------------------------------------------------------------------------------

def test_shrink():
    assert G.shrink(0) == 0.0 and G.shrink(2) == 0.5 and G.shrink(8) == 0.8


@pytest.mark.parametrize("n", [1, 2, 3, 6, 20])
def test_shrunk_centre_breaks_even_at_one_over_n_plus_five(n):
    assert G.expected_ratio(1 / (n + 5), n) == pytest.approx(1.0)
    assert G.expected_ratio(1.5 / (n + 5), n) < 1.0 < G.expected_ratio(0.5 / (n + 5), n)


def test_captures_needed():
    assert G.captures_needed(None) is None
    assert G.captures_needed(0.1) is None                     # below 0.19 no n reaches a 10% RMS gain
    n = G.captures_needed(0.5)
    assert n is not None and math.sqrt(G.expected_ratio(0.5, n)) <= 0.9 < math.sqrt(G.expected_ratio(0.5, n - 1))


def test_icc():
    assert G.icc({"a": [1.0, 1.0], "b": [3.0, 3.0]}) == pytest.approx(1.0)
    assert G.icc({"a": [0.0, 2.0], "b": [0.0, 2.0]}) == 0.0
    assert G.icc({"a": [1.0, 2.0]}) is None


# --- the centre and the distance ----------------------------------------------------------------------------------------------

def test_fam_centre_shrinks_and_clips():
    cen = {"x": 0.5, "y": 0.9, "z": 0.2}
    fam = G.fam_centre(cen, {"x": [0.2, 0.4], "y": [0.6], "q": [0.1]})
    assert fam["x"] == pytest.approx(0.5 + 0.5 * 0.3) and fam["y"] == 1.0 and fam["z"] == 0.2 and "q" not in fam
    assert G.fam_centre(cen, {"x": [0.2]}, w_fn=lambda n: 1.0)["x"] == pytest.approx(0.7)


def test_record_d_uses_heads_in_all_three():
    grp = {"a": "drive", "b": "drive", "c": "tone"}.get
    lab, cen = {"a": 0.0, "b": 0.0, "c": 1.0}, {"a": 0.4, "b": 0.4, "c": 0.5}
    d = G.record_d(lab, cen, {"a": 0.0, "b": 0.4, "c": 0.5}, grp)
    assert d["drive"][1] == pytest.approx(0.4)
    assert d["drive"][0] == pytest.approx(math.sqrt(0.08) - 0.4)
    assert d["tone"][0] == pytest.approx(0.0)
    assert set(G.record_d(lab, cen, {"a": 0.1}, grp)) == {"drive"}    # an answer missing b and c: a alone


def test_cluster_t_and_wider():
    t = G.cluster_t({"c1": [-0.1, -0.3], "c2": [-0.2], "c3": [0.0]})
    assert t["mean"] == pytest.approx(-0.4 / 3) and t["clusters"] == 3 and t["lo90"] < t["mean"] < t["hi90"]
    one = G.cluster_t({"c1": [0.1]})
    assert one["lo90"] is None and one["hi90"] is None
    assert G.wider(_iv(0, -0.1, 0.1), _iv(0, -0.2, 0.2))["lo90"] == -0.2
    assert G.wider(_iv(0, -0.1, 0.1), _iv(0, None, None))["lo90"] is None


# --- the readings -----------------------------------------------------------------------------------------------------------

def _rows(ivs):
    return dict(zip(G.DECIDING, ivs))


def test_readings_nearer_ruled_out_and_p():
    cen = {g: 0.2 for g in G.DECIDING}                        # a tenth is 0.02
    t = _rows([_iv(-0.01, -0.015, -0.005), _iv(0, -0.01, 0.01), _iv(0, -0.01, 0.01)])
    assert G.readings(t, t, cen, 0.01) == (True, True, True)
    wide = _rows([_iv(-0.01, -0.05, 0.03), _iv(0, -0.01, 0.01), _iv(0, -0.01, 0.01)])
    assert G.readings(t, wide, cen, 0.2) == (True, False, False)      # the family interval is the wider one
    assert G.readings(wide, wide, cen, None) == (False, False, False)
    assert G.readings({}, {}, cen, 0.5) == (False, False, False)


def test_joint_p_uses_the_minimum_standardised_group():
    shuf = [{"drive": x, "tone": -x, "cab": 0.01 * x} for x in (-1.0, -0.5, 0.0, 0.5, 1.0)] * 4
    p, stat, norm = G.joint_p({"drive": -2.0, "tone": 0.0, "cab": 0.0}, shuf)
    assert p == 0.0 and set(norm) == set(G.DECIDING) and stat < -2
    p2, _, _ = G.joint_p({"drive": 0.0, "tone": 0.0, "cab": 0.0}, shuf)
    assert 0 < p2 <= 1
    assert G.joint_p({"drive": None}, shuf)[0] is None


def test_shuffle_tags_is_a_seeded_permutation():
    tags = {f"p{i}": ("none" if i < 4 else f"f{i % 3}") for i in range(12)}
    a, b = G.shuffle_tags(tags, 3), G.shuffle_tags(tags, 3)
    assert a == b and set(a) == set(tags) and sorted(a.values()) == sorted(tags.values())
    assert any(G.shuffle_tags(tags, j) != tags for j in range(5))
    assert G.shuffle_tags(tags, 4) != a


def test_tags_content_refuses_other_counts():
    units = {"cap/x#ac20": {"pack": "fender-a", "creator": "c", "capture": "x"}}
    with pytest.raises(SystemExit):
        G.tags_content([("cap/x#ac20", "ac20")], units)
