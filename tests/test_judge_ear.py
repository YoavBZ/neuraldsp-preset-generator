import json

import pytest

from learn import judge_ear as J
from learn import knob_ceiling as K


def _S(amp="pr12", treble="0.5", gain="0", dist="0.1", mic="0"):
    """A minimal starting preset: every key a step reads, effects off, the spring off."""
    x = {("parameters", "inputGain"): gain, (f"{amp}Amp", f"{amp}Treble"): treble,
         ("cabParameters", "leftCabDistance"): dist, ("cabParameters", "leftMicType"): mic,
         ("reverb", "reverbActive"): "false", ("reverb", "reverbMix"): "0.2", ("reverb", "reverbDecay"): "9",
         ("delay", "delayActive"): "false", ("delay", "delayMix"): "0.3", ("delay", "delaySync"): "1",
         ("delay", "delayTime"): "500", ("delay", "delayFeedback"): "0.5",
         (f"{amp}Amp", f"{amp}Reverb"): "0", ("pr12Amp", "pr12Dwell"): "0.8",
         ("parameters", "outputGain"): "3"}
    return x


DEFAULTS = {("reverb", "reverbDecay"): "1.48034", ("delay", "delaySync"): "1", ("delay", "delayTime"): "500",
            ("delay", "delayFeedback"): "0.304266"}


def test_declared_constants():
    assert J.GROUPS == ("drive", "tone", "cab", "reverb", "delay", "spring") and J.SIZES == ("small", "large")
    assert J.STEPS["drive"] == (4.0, 10.0) and J.STEPS["tone"] == (0.15, 0.35)
    assert J.STEPS["reverb"] == J.STEPS["delay"] == (0.15, 0.40) and J.STEPS["spring"] == (0.2, 0.5)
    assert J.PRESETS == (("clean", "pr12"), ("crunch", "sw50r"))
    assert J.LEDGER_KEY == "phase_judge_ear" and J.DI_START_S == 110.0 and J.DI_LUFS == -22.9
    assert J.RATINGS == ("same", "barely", "clearly", "very") and J.CONFS == ("sure", "unsure")


@pytest.mark.parametrize("amp", ["pr12", "sw50r"])
def test_each_pair_differs_from_S_only_in_its_groups_keys(amp):
    S = _S(amp)
    pairs = J.preset_pairs("x", amp, S, DEFAULTS)
    assert len(pairs) == 13 and sum(p["group"] == J.CATCH for p in pairs) == 1
    for p in pairs:
        x = J.tdict(p["settings"])
        assert set(x) == set(S)
        diff = {k for k in S if x[k] != S[k]}
        if p["group"] == J.CATCH:
            assert not diff and p["null"]
            continue
        assert diff, p["pair"]
        assert diff <= J.group_keys(amp, p["group"], DEFAULTS), p["pair"]
        assert set(p["changes"]) == {f"{a}/{b}" for a, b in diff}


def test_step_values_and_sizes_ordered():
    S = _S("pr12", treble="0.5", gain="0", dist="0.1", mic="3")
    get = {s: {g: J.step_settings("pr12", S, g, s, DEFAULTS)[0] for g in J.GROUPS} for s in J.SIZES}
    sm, lg = get["small"], get["large"]
    assert sm["drive"][("parameters", "inputGain")] == "4" and lg["drive"][("parameters", "inputGain")] == "10"
    t = ("pr12Amp", "pr12Treble")
    assert float(sm["tone"][t]) == pytest.approx(0.65) and float(lg["tone"][t]) == pytest.approx(0.85)
    assert float(sm["cab"][("cabParameters", "leftCabDistance")]) == pytest.approx(0.35)
    assert sm["cab"][("cabParameters", "leftMicType")] == "3"           # small moves the distance only
    assert lg["cab"][("cabParameters", "leftMicType")] == "4"           # large: the next mic
    assert lg["cab"][("cabParameters", "leftCabDistance")] == "0.1"
    for g in ("reverb", "delay"):
        assert sm[g][(g, f"{g}Active")] == lg[g][(g, f"{g}Active")] == "true"
        assert float(sm[g][(g, f"{g}Mix")]) == 0.15 and float(lg[g][(g, f"{g}Mix")]) == 0.4
    assert sm["reverb"][("reverb", "reverbDecay")] == "1.48034"          # the plugin's default, not S's
    assert sm["delay"][("delay", "delaySync")] == "0" and sm["delay"][("delay", "delayTime")] == "500"
    assert sm["delay"][("delay", "delayFeedback")] == "0.304266"
    sp = ("pr12Amp", "pr12Reverb")
    assert sm["spring"][sp] == "0.2" and lg["spring"][sp] == "0.5"
    assert sm["spring"][("pr12Amp", "pr12Dwell")] == "0.8"              # the dwell stays at S's
    for g, k in (("drive", ("parameters", "inputGain")), ("tone", t), ("spring", sp)):
        assert float(S[k]) < float(sm[g][k]) < float(lg[g][k])


def test_steps_clip_to_the_range():
    S = _S("sw50r", treble="1", gain="8", dist="0.9", mic="9")
    for s in J.SIZES:
        x, ch = J.step_settings("sw50r", S, "tone", s, DEFAULTS)
        assert x == S and ch == {}                                       # clipped at 1: the step equals S
    x, _ = J.step_settings("sw50r", S, "drive", "large", DEFAULTS)
    assert x[("parameters", "inputGain")] == "12"                        # 8 + 10 clipped to full_space's 12 dB
    x, _ = J.step_settings("sw50r", S, "drive", "small", DEFAULTS)
    assert x[("parameters", "inputGain")] == "12"
    x, _ = J.step_settings("sw50r", S, "cab", "small", DEFAULTS)
    assert x[("cabParameters", "leftCabDistance")] == "1"
    x, _ = J.step_settings("sw50r", S, "cab", "large", DEFAULTS)
    assert x[("cabParameters", "leftMicType")] == K.MICS[0]             # 9 wraps to 0
    pairs = J.preset_pairs("crunch", "sw50r", S, DEFAULTS)
    assert [p["pair"] for p in pairs if p["null"] and p["group"] != J.CATCH] == ["crunch-tone-small",
                                                                                   "crunch-tone-large"]


def test_render_jobs_and_the_catch():
    S = _S()
    plan = {"presets": [{"cls": "clean", "amp": "pr12", "select": 1, "S": J.sdict(S)}],
            "pairs": J.preset_pairs("clean", "pr12", S, DEFAULTS)}
    jobs = J.render_jobs(plan)
    assert [j for j, _, _ in jobs[:2]] == ["clean-S", "clean-S2"] and len(jobs) == 14
    assert len({j for j, _, _ in jobs}) == 14 and 2 * len(jobs) == 28
    by = {p["pair"]: p for p in plan["pairs"]}
    assert J.job_of(by["clean-catch"]) == "clean-S2" and J.job_of(by["clean-drive-small"]) == "clean-drive-small"


def test_page_order_is_seeded_and_complete():
    pairs = [f"x{i}" for i in range(26)]
    a, b = J.page_order(pairs), J.page_order(list(reversed(pairs)))
    assert a == b                                                         # the input order does not matter
    assert sorted(it["pair"] for it in a) == sorted(pairs)
    assert [it["page_id"] for it in a] == [f"p{n:02d}" for n in range(1, 27)]
    assert {it["a"] for it in a} == {"S", "step"}
    assert [it["pair"] for it in a] != sorted(pairs)
    assert J.page_order(pairs, seed=1) != a


def test_leaks_strip_the_audio_and_find_names():
    blob = "QUJD" * 200
    page = (f'<p>How different?</p><script id="clips" type="application/json">{{"p01-1": "drive{blob}"}}</script>'
            f'<script>let x = null; try {{}} catch (e) {{}}</script>')
    assert J.leaks(page) == []
    assert J.leaks(page + "<p>Reverb</p>") == ["reverb"]
    assert J.leaks(page + "<p>sw50r crunch</p>") == ["crunch", "sw50r"]
    assert J.leaks("<p>overdriven</p>") == []                             # whole words only
    assert J.leaks("x" + blob + "drive") == []                            # a long base64 run is stripped


def test_the_page_html_is_blind():
    html = J.page_html(["p01", "p02"], {"p01-1": "AAAA", "p01-2": "AAAA", "p02-1": "AAAA", "p02-2": "AAAA"}, "b1")
    assert J.leaks(html) == []
    assert "How different do these sound?" in html and html.count('class="item"') == 2
    for r in J.RATINGS:
        assert f'data-r="{r}"' in html
    assert 'data-c="sure"' in html and 'data-c="unsure"' in html


def _export(build, answers):
    lines = [f"judge-ear build {build} 2026-11-02T00:00:00Z", "1 p01 same sure"]
    return "\n".join(lines + [json.dumps({"page": "judge-ear", "build": build, "answers": answers})])


def test_parse_answers():
    t = _export("b1", {"p01": {"rating": "clearly", "conf": "sure", "note": "hm"},
                       "p02": {"rating": "loud", "conf": "maybe"}, "p03": {"conf": "unsure"}})
    a = J.parse_answers(t, "b1")
    assert a["p01"] == {"rating": "clearly", "conf": "sure", "note": "hm"}
    assert a["p02"] == {"rating": None, "conf": None, "note": ""}           # off-scale values dropped
    assert a["p03"]["rating"] is None and a["p03"]["conf"] == "unsure"
    with pytest.raises(ValueError, match="build"):
        J.parse_answers(t, "other")
    with pytest.raises(ValueError, match="no answers"):
        J.parse_answers("1 p01 same sure\n", "b1")
    assert J.parse_answers(t)["p01"]["rating"] == "clearly"


def _item(pid, pair, group, size, cls="clean"):
    return {"page_id": pid, "pair": pair, "group": group, "size": size, "cls": cls, "null": False}


def test_score_rows_order_and_join():
    items = [_item("p02", "clean-reverb-small", "reverb", "small"), _item("p01", "clean-drive-large", "drive", "large"),
             _item("p03", "clean-catch", J.CATCH, None), _item("p04", "clean-drive-small", "drive", "small"),
             _item("p05", "crunch-drive-small", "drive", "small", "crunch")]
    rows = J.score_rows(items, {"clean-drive-large": 0.3, "clean-reverb-small": 0.1}, {"p01": {"rating": "very",
                                                                                              "conf": "sure"}})
    assert [r["pair"] for r in rows] == ["clean-drive-small", "crunch-drive-small", "clean-drive-large",
                                         "clean-reverb-small", "clean-catch"]
    r = next(r for r in rows if r["pair"] == "clean-drive-large")
    assert r["rating"] == "very" and r["judge"] == 0.3
    assert next(r for r in rows if r["pair"] == "clean-reverb-small")["rating"] is None


def _row(pair, group, judge, rating, conf="sure"):
    return {"pair": pair, "group": group, "judge": judge, "rating": rating, "conf": conf}


def test_misweights_rule():
    ok = [_row("d1", "drive", 0.30, "very"), _row("d2", "drive", 0.20, "clearly"),
          _row("r1", "reverb", 0.05, "barely"), _row("r2", "reverb", 0.02, "same")]
    assert J.misweights(ok) == ([], {})
    bad = ok + [_row("v1", "reverb", 0.10, "clearly"), _row("t1", "tone", 0.15, "same", "unsure")]
    inv, by = J.misweights(bad)
    assert [(x["heard"], x["quiet"]) for x in inv] == [("v1", "t1")]
    assert inv[0]["unsure"] is True
    assert by == {"reverb": {"under": ["v1"], "over": []}, "tone": {"under": [], "over": ["t1"]}}


def test_misweights_ignores_same_group_ties_catches_and_gaps():
    rows = [_row("d1", "drive", 0.10, "clearly"), _row("d2", "drive", 0.30, "same"),       # same group: no
            _row("r1", "reverb", 0.10, "barely"),                                          # a tie: not below
            _row("c1", J.CATCH, 0.50, "same"), _row("c2", J.CATCH, 0.0, "very"),           # catches: outside
            _row("s1", "spring", None, "same"), _row("s2", "spring", 0.9, None),           # unjudged, unrated
            _row("s3", "spring", float("inf"), "same")]                                    # a refusal: outside
    assert J.misweights(rows) == ([], {})

