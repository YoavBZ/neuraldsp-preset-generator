"""ROADMAP step (c)'s measurement (`learn/audibility_measure.py`): the draw, the effect-off edit, A_e, the A_e
subsets, the page's pairs, the render count, the mix rebuild, the render-slot list, the CLI and the chain. Fakes only:
no data files, no renders."""

import math
import pathlib
import re

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import audibility_measure as A  # noqa: E402
from learn import full_space as F  # noqa: E402
from learn import local_objective as LO  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHAIN = ROOT / "docs" / "audibility-measure-chain.sh"


# --- the effects and the draw --------------------------------------------------------------------------------------

def test_effects_are_the_tone_probes_switches_and_proxies():
    from learn import tone_info_probe as P

    assert {sw: px for sw, _, px in A.EFFECTS.values()} == P.AUDIBLE
    for sw, (path, off), px in A.EFFECTS.values():
        assert sw in F.SW and px in F.CONT
        assert off in ("false", "0")
    for amp, path in F.SPRING.items():                    # a spring is switched off by its level, written as 0
        assert A.EFFECTS[f"{amp} spring"][1] == (path, "0")


def _enc(on=(), scored=None):
    n = len(F.SW)
    s, sm = np.zeros(n), np.zeros(n)
    for e in (scored if scored is not None else A.EFFECTS):
        sm[F.SW.index(A.EFFECTS[e][0])] = 1.0
    for e in on:
        s[F.SW.index(A.EFFECTS[e][0])] = 1.0
    return (None, None, s, sm)


def test_on_effects_needs_the_switch_scored_and_on():
    assert A.on_effects(_enc(on=("delay", "tremolo"))) == ["delay", "tremolo"]
    assert A.on_effects(_enc(on=("delay",), scored=("reverb",))) == []        # on but masked: not scored
    assert A.on_effects(_enc()) == []


def test_select_keeps_all_under_the_cap_and_draws_seeded_above():
    ids = list(range(500, 0, -1))
    out = A.select({"delay": ids, "reverb": [3, 1, 2]}, n_max=200)
    assert out["reverb"] == [1, 2, 3]
    assert len(out["delay"]) == 200 and out["delay"] == sorted(out["delay"]) and set(out["delay"]) <= set(ids)
    assert out == A.select({"delay": list(reversed(ids)), "reverb": [1, 2, 3]}, n_max=200)   # order-free, seeded
    assert A.select({"delay": ids}, n_max=200, seed=1)["delay"] != out["delay"]


def test_repeats_and_jobs_render_r_on_first_for_every_id():
    group_of = {1: ("s1", "pr12"), 2: ("s1", "pr12"), 3: ("s1", "ac20"), 4: ("s2", "pr12")}
    chosen = {"delay": [2, 3, 4], "reverb": [1, 2], "tremolo": []}
    reps = A.repeats(chosen, group_of)
    assert reps == {("s1", "pr12"): 1, ("s1", "ac20"): 3, ("s2", "pr12"): 4}
    jobs = A.jobs_of(chosen, reps, group_of)
    assert len(jobs) == 4 + 3 + 5                                                     # r_on' per id, repeats, offs
    keys = [(j["section"], j["amp"]) for j in jobs]
    assert len({k for k in keys}) == 3 and all(keys[n] == keys[n + 1] or keys[n + 1] not in keys[:n + 1]
                                               for n in range(len(keys) - 1))          # groups contiguous
    for i in group_of:
        whats = [j["what"] for j in jobs if j["i"] == i]
        assert whats[0] == A.ON                                                       # r_on' before its repeat
    assert [j["what"] for j in jobs if j["i"] == 1] == [A.ON, A.REPEAT, "reverb"]
    assert [j["what"] for j in jobs if j["i"] == 2] == [A.ON, "delay", "reverb"]      # EFFECTS order within an id


def test_plan_unchanged_ignores_the_time_only():
    a = {"recipe": A.RECIPE, "seed": 1, "n_max": 200, "tau": 0.005, "chosen": {"delay": [1]}, "jobs": [{"i": 1}],
         "time": "then"}
    assert A.plan_unchanged(a, {**a, "time": "now"})
    assert not A.plan_unchanged(a, {**a, "chosen": {"delay": [2]}})
    assert not A.plan_unchanged(a, {**a, "jobs": []})
    assert not A.plan_unchanged({k: v for k, v in a.items() if k != "recipe"}, a)      # the first run's plan


# --- the fresh-process recipe (amendment 5's fix) ------------------------------------------------------------------------

class _FakeRenderer:
    """Output depends on the render's position in its process, as Morgan's modulated effects do."""

    def __init__(self, log):
        self.log, self.n, self.closed = log, 0, False

    def render(self, di, sel, x):
        self.n += 1
        self.log.append((self.n, x))
        if x == "boom":
            raise RuntimeError("render failed")
        return np.full(4, 100.0 * self.n + {"on": 1.0, "off": 2.0}.get(x, 0.0))

    def close(self):
        self.closed = True


def test_fresh_render_primes_once_with_r_on_then_keeps_one_render_and_closes():
    made = []

    def make():
        made.append(_FakeRenderer([]))
        return made[-1]

    on = A.fresh_render(make, None, "amp", "on", "on")
    rep = A.fresh_render(make, None, "amp", "on", "on")
    off = A.fresh_render(make, None, "amp", "on", "off")
    assert [r.log for r in made] == [[(1, "on"), (2, "on")], [(1, "on"), (2, "on")], [(1, "on"), (2, "off")]]
    assert all(r.closed for r in made) and len(made) == 3                             # a new process per render
    assert np.array_equal(on, rep) and A.audio_sha(on) == A.audio_sha(rep)            # same position: bit-identical
    assert on[0] == 201.0 and off[0] == 202.0                                         # both at position 2
    with pytest.raises(RuntimeError):
        A.fresh_render(make, None, "amp", "on", "boom")
    assert made[-1].closed                                                            # closed on a failure too


def test_audio_sha_is_exact():
    y = np.linspace(-1, 1, 1000)
    z = y.copy()
    assert A.audio_sha(y) == A.audio_sha(z)
    z[500] = np.nextafter(z[500], 2.0)
    assert A.audio_sha(y) != A.audio_sha(z)


def test_clean_pair_looks_at_the_other_modulated_effects_only():
    s = {"delay/delayActive": "true", "reverb/reverbActive": "false", "tremolo/tremoloActive": "false",
         "pr12Amp/pr12Reverb": "0.4"}
    assert A.clean_pair(s, "delay")                                                    # only delay: clean
    assert not A.clean_pair(s, "reverb")                                               # delay still on in r_off
    assert not A.clean_pair(s, "pr12 spring")
    assert A.clean_pair({**s, "delay/delayActive": "false"}, "pr12 spring")            # springs do not run on
    assert set(A.MODULATED) == {"delay", "reverb", "tremolo"}


def test_consistency_counts_tau_crossings_on_clean_pairs():
    old = {("delay", 1): 0.004, ("delay", 2): 0.02, ("delay", 3): 0.1, ("reverb", 4): 0.01, ("reverb", 5): None}
    new = {("delay", 1): 0.006, ("delay", 2): 0.021, ("delay", 3): 0.09, ("reverb", 4): 0.03, ("reverb", 5): 0.2}
    clean = {("delay", 1), ("delay", 2), ("delay", 3), ("reverb", 5)}
    c = A.consistency(old, new, clean)
    assert c["delay"]["n"] == 3 and c["delay"]["crossed_tau"] == 1
    assert c["delay"]["median_abs_diff"] == pytest.approx(0.002)
    assert c["reverb"]["n"] == 0 and c["all"]["n"] == 3                                # a None is left out
    assert c["delay"]["spearman"] is None                                              # fewer than 5 pairs


def test_archive_moves_the_first_run_and_its_page(tmp_path):
    od, pd = tmp_path / "audibility", tmp_path / "listening"
    (od / "rows").mkdir(parents=True)
    (od / "renders").mkdir()
    for n in ("plan.json", "measure.json"):
        (od / n).write_text("{}")
    pd.mkdir()
    (pd / "index.html").write_text("<html>")
    moves = A.archive_moves(od, pd)
    a = od / A.ARCHIVE
    assert (od / "plan.json", a / "plan.json") in moves and (od / "rows", a / "rows") in moves
    assert (pd / "index.html", a / "page" / "index.html") in moves
    assert (od / "read.json", a / "read.json") not in moves                           # only what exists
    assert all(a in d.parents for _, d in moves)                                       # all under the archive


def test_render_count_sums_each_rows_process(tmp_path):
    d = tmp_path / "rows"
    d.mkdir()
    row = '"recipe": "fresh", "renders": 2, "primes": 1}\n'
    (d / "render-0of3.jsonl").write_text('{"i": 1, "what": "on", ' + row + '{"i": 1, "what": "delay", ' + row)
    (d / "render-1of3.jsonl").write_text('{"i": 2, "what": "on", ' + row)
    assert A.render_count(tmp_path) == {"renders": 6, "priming": 3}


# --- the waits: the shards never wait on each other ------------------------------------------------------------------

def _ps(*extra):
    rows = [(1, 0, "launchd"), (50, 1, "zsh docs/audibility-measure-chain.sh"),
            (100, 50, "/x/.venv/bin/python -u -m learn.audibility_measure render --shard 0/3"),
            (101, 50, "/x/.venv/bin/python -u -m learn.audibility_measure render --shard 1/3"),
            (102, 50, "/x/.venv/bin/python -u -m learn.audibility_measure render --shard 2/3"),
            (200, 100, "/tmp/au-bounded-1/au_render_server"),
            (201, 101, "/tmp/au-bounded-2/au_render_server"),
            (210, 202, "/tmp/au-bounded-3/au_render_server"), (202, 102, "/bin/sh -c wrapper")]
    return rows + list(extra)


def test_sibling_shards_servers_are_not_waited_for():
    rows = _ps()
    assert A.outside_servers(rows) == []                                              # a wrapper in between too
    assert A.job_wait_reason(rows, own=(100, 50)) is None


def test_other_jobs_and_separations_are_waited_for():
    other = (300, 299, "/tmp/au-bounded-9/au_render_server")
    rows = _ps((299, 1, "/x/.venv/bin/python -u -m learn.xlance_finetune vreal-render --shard 0/3"), other)
    assert A.outside_servers(rows) == [300]
    assert "render server" in A.job_wait_reason(rows, own=(100, 50))
    sep = _ps((400, 1, "/x/.venv/bin/python -u -m learn.xlance_finetune separate --worker 0/2"))
    assert "separation" in A.job_wait_reason(sep, own=(100, 50))                       # step (b)'s, registered


def test_archive_moves_the_plan_last(tmp_path):
    od, pd = tmp_path / "audibility", tmp_path / "listening"
    (od / "rows").mkdir(parents=True)
    for n in ("plan.json", "measure.json", "read.json"):
        (od / n).write_text("{}")
    pd.mkdir()
    (pd / "index.html").write_text("<html>")
    moves = A.archive_moves(od, pd)
    assert moves[-1][0] == od / "plan.json" and moves[0][0] == pd / "index.html"


def test_off_settings_switches_only_the_effect():
    x = {("delay", "delayActive"): "true", ("delay", "delayMix"): "0.3", ("pr12Amp", "pr12Reverb"): "0.2"}
    y = A.off_settings(x, "delay")
    assert y[("delay", "delayActive")] == "false" and y[("delay", "delayMix")] == "0.3"
    assert x[("delay", "delayActive")] == "true"                                      # a copy
    z = A.off_settings(x, "pr12 spring")
    assert z[("pr12Amp", "pr12Reverb")] == "0" and z[("delay", "delayActive")] == "true"
    with pytest.raises(ValueError):
        A.off_settings(y, "delay")
    with pytest.raises(ValueError):
        A.off_settings({("pr12Amp", "pr12Reverb"): "0"}, "pr12 spring")
    with pytest.raises(ValueError):
        A.off_settings(x, "reverb")                                                   # not in the setting


# --- A_e ----------------------------------------------------------------------------------------------------------

def test_a_e_is_the_halves_mean_log_ratio_unsigned():
    r = A.a_e({"A": 1.0, "B": 2.0}, {"A": math.e, "B": 2.0})
    assert r["signed"] == pytest.approx(0.5) and r["a_e"] == pytest.approx(0.5)
    r = A.a_e({"A": 2.0, "B": 2.0}, {"A": 1.0, "B": 1.0})
    assert r["signed"] == pytest.approx(-math.log(2)) and r["a_e"] == pytest.approx(math.log(2))
    assert A.a_e({"A": 1.0, "B": 1.0}, {"A": math.inf, "B": 1.0}) is None             # a refused half
    assert A.a_e({"A": 0.0, "B": 1.0}, {"A": 1.0, "B": 1.0}) is None
    assert A.a_e({"A": 1.0}, {"A": 1.0, "B": 1.0}) is None


def test_solo_is_the_mean_distance():
    assert A.solo({"A": 1.0, "B": 3.0}) == 2.0
    assert A.solo({"A": 1.0, "B": math.inf}) is None


def test_thirds_and_subsets():
    assert A.thirds([1.0, None, float("nan")]) is None
    t1, t2 = A.thirds([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    assert 1.0 < t1 < 2.0 < 3.0 < t2 < 4.0
    on = np.array([False, False, True, True, True, True, True])
    ae = np.array([np.nan, np.nan, 0.001, 0.004, 0.02, 0.5, np.nan])
    cuts = (0.003, 0.03)
    keep = {w: A.subset(on, ae, w, cuts, tau=0.005).tolist() for w in A.WHICH}
    off = [True, True]
    assert keep["all on"] == off + [True] * 5
    assert keep["measured"] == off + [True, True, True, True, False]
    assert keep["bottom third"] == off + [True, False, False, False, False]
    assert keep["middle third"] == off + [False, True, True, False, False]
    assert keep["top third"] == off + [False, False, False, True, False]
    assert keep["below tau"] == off + [True, True, False, False, False]
    assert keep["at or above tau"] == off + [False, False, True, True, False]
    assert A.subset(on, ae, "top third", None).tolist() == off + [False] * 5
    with pytest.raises(ValueError):
        A.subset(on, ae, "loud", cuts)


def test_quantiles_skip_missing():
    q = A.quantiles([1.0, None, 3.0, float("inf")])
    assert q["0"] == 1.0 and q["100"] == 3.0
    assert A.quantiles([None]) == {}


def test_spearman_needs_five_pairs():
    assert A.spearman([1, 2, 3, 4], [1, 2, 3, 4]) == (None, 4)
    rho, n = A.spearman([1, 2, 3, 4, 5, None], [2, 4, 6, 8, 10, 1])
    assert rho == pytest.approx(1.0) and n == 5


# --- the page -----------------------------------------------------------------------------------------------------

def _measured():
    out = []
    for k, e in enumerate(A.EFFECTS):
        for j, a in enumerate((0.0001, 0.003, 0.0045, 0.0049, 0.0051, 0.006, 0.02, 0.4)):
            out.append({"i": 100 * k + j, "effect": e, "a_e": a})
    out.append({"i": 999, "effect": "delay", "a_e": None})
    return out


def test_page_items_pick_near_tau_an_anchor_and_catches():
    items = A.page_items(_measured(), tau=0.005)
    assert items == A.page_items(_measured(), tau=0.005)                               # seeded
    for e in A.EFFECTS:
        mine = {it["kind"]: [] for it in items if it["effect"] == e}
        for it in items:
            if it["effect"] == e:
                mine[it["kind"]].append(it["a_e"])
        assert sorted(mine["near tau, below"]) == [0.0045, 0.0049]
        assert sorted(mine["near tau, above"]) == [0.0051, 0.006]
        assert mine["anchor (loudest)"] == [0.4]
    same = [it for it in items if it["kind"] == "same"]
    assert len(same) == A.CATCH and len({it["effect"] for it in same}) == A.CATCH
    assert len(items) == 5 * len(A.EFFECTS) + A.CATCH
    assert len({it["id"] for it in items}) == len(items)
    assert {it["first"] for it in items} <= {"on", "off"}
    assert all(it["i"] != 999 for it in items)


def test_page_html_is_blind():
    pytest.importorskip("soundfile")
    items = A.page_items(_measured(), tau=0.005)
    clips = {f"{it['id']}-{k}": "AAAA" for it in items for k in (1, 2)}
    page = A.page_html(items, clips, "b123")
    assert page.count('class="item"') == len(items)
    for word in ("near tau", "anchor", "a_e", '"kind"', '"first":'):
        assert word not in page                                                         # the key stays in page-key.json
    assert 'name="viewport"' in page and A.PAGE_NAME in page


def test_reproduce_check_refuses_rather_than_skips():
    stored = {"read": {"delay/delayActive": {"all on": {"b": {"point": 0.66}}}}}
    assert A.reproduce_fail(stored, "delay/delayActive", "b", 0.66) is None
    assert "not the stored" in A.reproduce_fail(stored, "delay/delayActive", "b", 0.67)
    assert "missing" in A.reproduce_fail(None, "delay/delayActive", "b", 0.66)
    assert A.reproduce_fail(stored, "reverb/reverbActive", "b", 0.6)                    # a switch it lacks
    assert A.reproduce_fail(stored, "delay/delayActive", "c", 0.6)                      # an input it lacks
    assert A.reproduce_fail(stored, "delay/delayActive", "b", None)
    with pytest.raises(SystemExit):
        A.read_rows({"pairs": [], "refused": []}, None)                                 # before any refit


def test_page_clips_are_level_free():
    pytest.importorskip("pyloudnorm")
    from analysis import io

    from learn import build_data_review as BDR

    rng = np.random.default_rng(1)
    a = rng.normal(0, 0.1, 48000 * 3)
    for b in (0.25 * a, 3.0 * a):                                                      # quieter, and loud enough to peak-cut
        ya, yb = A.level_free(a, b)
        la = io.loudness_lufs(io.from_samples(ya.reshape(-1, 1), BDR.SR))
        lb = io.loudness_lufs(io.from_samples(yb.reshape(-1, 1), BDR.SR))
        assert la == pytest.approx(lb, abs=0.1)
        assert la <= BDR.TARGET_LUFS + 0.1


def test_render_rows_skip_a_torn_line_and_repair_only_their_own(tmp_path):
    d = tmp_path / "rows"
    d.mkdir()
    mine, other = d / "render-0of3.jsonl", d / "render-1of3.jsonl"
    mine.write_text('{"i": 1, "what": "delay", "recipe": "fresh"}\n{"i": 2, "wh')
    other.write_text('{"i": 3, "what": "reverb", "recipe": "fresh"}\n{"i": 4, "wh')
    rows = A.render_rows(tmp_path, own=mine)
    assert [(r["i"], r["what"]) for r in rows] == [(1, "delay"), (3, "reverb")]
    assert mine.read_text() == '{"i": 1, "what": "delay", "recipe": "fresh"}\n'         # repaired
    assert other.read_text().endswith('{"i": 4, "wh')                                   # another shard's: untouched
    assert A.render_rows(tmp_path / "none") == []


def test_render_rows_refuse_the_first_runs_rows(tmp_path):
    d = tmp_path / "rows"
    d.mkdir()
    (d / "render-0of3.jsonl").write_text('{"i": 1, "what": "delay", "recipe": "fresh"}\n'
                                         '{"i": 2, "what": "repeat", "renders_so_far": 3}\n')
    with pytest.raises(SystemExit, match="archive"):
        A.render_rows(tmp_path)


def test_the_key_is_outside_the_listening_folder():
    root = pathlib.Path("/data")
    assert A.key_path(root) == root / A.OUT_DIR / "page-key.json"
    assert A.page_dir() not in A.key_path(A.V.OUT).parents


# --- the render count and the mix -----------------------------------------------------------------------------------

def test_run_totals_add_each_process_run():
    assert A.run_totals([]) == (0, 0)
    assert A.run_totals([(3, 1), (4, 1), (6, 2)]) == (6, 2)
    assert A.run_totals([(3, 1), (5, 1), (2, 1), (3, 1)]) == (8, 2)                    # resumed once


def test_mix_with_rebuilds_the_self_built_mix():
    pytest.importorskip("pyloudnorm")
    from learn import direct_stems as DS
    from learn import trusted_data as T

    rng = np.random.default_rng(0)
    y = rng.normal(0, 0.1, 48000 * 2)
    oth, st = rng.normal(0, 0.05, len(y)), rng.normal(0, 0.05, len(y))
    seen = set()
    for i in range(40):
        mastered = DS.master_draw(i)[0]
        if mastered in seen:
            continue
        seen.add(mastered)
        x = {"i": i, "draw": {"ratio_db": -6.0, "leak_db": -30.0, "target_lufs": -14.0, "mastered": mastered}}
        m, gains, _ = T.self_built_mix(y, oth, st, x)
        assert np.allclose(A.mix_with(y, oth, st, gains, i, mastered), m)
        with pytest.raises(SystemExit):
            A.mix_with(y, oth, st, gains, i, not mastered)
    assert seen == {True, False}


# --- the render slots, the ledger, the CLI and the chain -----------------------------------------------------------------

def test_render_is_a_render_process_and_nothing_else_is():
    assert any(re.search(p, "python -u -m learn.audibility_measure render --shard 0/3") for p in LO.RENDERS)
    for cmd in ("archive", "plan", "measure", "read", "page"):
        assert not any(re.search(p, f"python -m learn.audibility_measure {cmd}") for p in LO.RENDERS)


def test_the_ledger_declares_it_and_its_fix():
    assert A.ledger_declared()
    assert A.ledger_declared(A.FIX_KEY, A.FIX_MARK)
    assert not A.ledger_declared(A.FIX_KEY, "something never declared")


def test_cli_flags():
    with pytest.raises(SystemExit):
        A.main(["measure", "--shard", "0/3"])
    with pytest.raises(SystemExit):
        A.main(["render", "--force"])


def _code_lines():
    return [ln.split("#", 1)[0].rstrip() for ln in CHAIN.read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def test_chain_never_waits_bare_on_caffeinate():
    lines = _code_lines()
    caf = [ln for ln in lines if "caffeinate" in ln]
    assert caf and all(ln.rstrip().endswith("&!") for ln in caf)
    waits = [m for ln in lines for m in re.findall(r"\bwait\b[^;&|]*", ln)]
    assert waits and all(re.fullmatch(r"wait \$\w+", w.strip()) for w in waits)


def test_chain_order_and_guards():
    text = CHAIN.read_text()
    assert "setopt no_bg_nice" in text and A.LEDGER_MARK in text and A.FIX_MARK in text
    order = [" archive ", " plan ", "render --shard", " measure ", " read ", " page "]
    pos = [text.index(f"${{AM[@]}}{o}" if o.startswith(" ") else o) for o in order]
    assert pos == sorted(pos)
    assert "--shard $k/3" in text and "for k in 0 1 2" in text                       # at most 3 render processes
    assert "--force" not in text                                                      # a plan is never rewritten here
