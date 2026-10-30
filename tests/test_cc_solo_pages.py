import inspect
import json

import pytest

from learn import audibility_measure as AM
from learn import cc_audibility as CA
from learn import cc_drive_page as D
from learn import cc_solo_pages as S
from learn import local_objective as LO
from learn import verify_tracks as V

RUN = 801136                                    # a runaway-flagged example besides 900215


def _src():
    """An in-mix key's items: a runaway anchor, a pair, a catch, another effect's pair."""
    rows = [("delay", 900215, "anchor (loudest)", 0.48, "on"), ("delay", 2, "near tau, above", 0.006, "off"),
            ("delay", 2, "same", None, "on"), ("reverb", 3, "near tau, below", 0.004, "on")]
    return [{"id": AM.item_id(e, i, k), "effect": e, "i": i, "kind": k, "a_e": a, "first": f, "band": "BKS"}
            for e, i, k, a, f in rows]


MEASURED = [{"i": 900215, "effect": "delay", "a_e": 0.48}, {"i": RUN, "effect": "delay", "a_e": 0.9},
            {"i": 803054, "effect": "delay", "a_e": 0.45}, {"i": 5, "effect": "delay", "a_e": 0.1},
            {"i": 2, "effect": "delay", "a_e": 0.006}, {"i": 3, "effect": "reverb", "a_e": 0.004},
            {"i": 7, "effect": "reverb", "a_e": 0.9}]


def test_the_runaway_anchor_is_replaced_by_the_loudest_clean_pair():
    assert 900215 in D.RUNAWAY and RUN in D.RUNAWAY and 803054 not in D.RUNAWAY
    out, swaps = S.swap_runaway([{k: it[k] for k in ("effect", "i", "kind", "a_e")} for it in _src()], MEASURED)
    assert [(it["effect"], it["i"]) for it in out] == [("delay", 803054), ("delay", 2), ("delay", 2), ("reverb", 3)]
    assert out[0]["kind"] == "anchor (loudest), in place of runaway 900215" and out[0]["a_e"] == 0.45
    assert swaps == [{"replaced": 900215, "by": 803054, "effect": "delay", "kind": "anchor (loudest)", "a_e": 0.45}]


def test_a_catch_on_a_runaway_example_is_dropped():
    out, swaps = S.swap_runaway([{"effect": "delay", "i": RUN, "kind": "same", "a_e": None}], MEASURED)
    assert out == [] and swaps == [{"dropped": RUN, "effect": "delay", "kind": "same"}]


def test_the_items_are_the_in_mix_pages_with_new_ids_order_and_ab():
    src = _src()
    items, swaps = S.solo_items(src, MEASURED)
    assert items == S.solo_items(src, MEASURED)[0]                             # seeded
    base = sorted((it["effect"], it["i"], it["kind"]) for it in src if it["i"] != 900215)
    assert sorted((it["effect"], it["i"], it["kind"]) for it in items if it["i"] != 803054) == base
    assert len(items) == len(src) and len(swaps) == 1                          # the item rule otherwise unchanged
    assert all(it["id"].startswith("solo-") for it in items)
    assert not {it["id"] for it in items} & {it["id"] for it in src}          # no answer can land on an in-mix id
    assert len({it["id"] for it in items}) == len(items)
    assert all(it["first"] in ("on", "off") for it in items)
    assert S.PAGE_SEED not in (D.PAGE_SEED, CA.PAGE_SEED, AM.PAGE_SEED)


def test_new_names_never_the_in_mix_pages_or_keys(tmp_path):
    args = type("A", (), {"out": str(tmp_path), "smoke": True})
    for part in S.PARTS:
        assert S.key_path(tmp_path, part).name == "solo-page-key.json"
        assert S.key_path(tmp_path, part).parent == S.source_dir(tmp_path, part)
        assert S.page_dir(args, part).name not in (D.PAGE_NAME, CA.PAGE_NAME)
    assert S.source_dir(tmp_path, 1) == D.out_dir(tmp_path) and S.source_dir(tmp_path, 2) == CA.out_dir(tmp_path)
    assert {p["name"] for p in S.PARTS.values()} == {"cc-drive-solo", "cc-audibility-solo"}


def test_zero_renders():
    cmd = "/x/.venv/bin/python -m learn.cc_solo_pages page --part 1"
    assert not LO.is_render_process(cmd)
    src = inspect.getsource(S)
    assert not any(w in src for w in ("new_renderer", "render_shard", "fresh_render", "new_process"))


def test_the_solo_wording_and_the_unchanged_drive_page():
    items = [{"id": "solo-x", "effect": "delay", "i": 1, "kind": "same", "a_e": None, "first": "on"},
             {"id": "solo-y", "effect": "drive1", "i": 1, "kind": "same", "a_e": None, "first": "on"}]
    clips = {f"{it['id']}-{k}": "AAAA" for it in items for k in (1, 2)}
    mix = D.page_html(items, clips, "b")
    assert "<title>Drive pedal check</title>" in mix and "the same 10 seconds of a song as A and B" in mix
    assert "very same mix as A and B" in mix and "guitar part" not in mix
    solo = D.page_html(items, clips, "b", name="cc-audibility-solo", part=2, solo=True)
    assert "<title>Guitar-only check</title>" in solo and "played alone (no band)" in solo
    assert "very same clip as A and B" in solo and "of a song" not in solo
    data = json.loads(solo.split('<script id="data" type="application/json">')[1].split("</script>")[0])
    assert data["page"] == "cc-audibility-solo" and data["part"] == 2
    assert [it["title"] for it in data["items"]] == ["Listen for: delay", "Listen for: drive pedal 1"]


def test_runs_refuse_without_the_declaration(tmp_path, monkeypatch):
    led = tmp_path / "ledger.json"
    led.write_text(json.dumps({"tests": [{"test_id": S.LEDGER_ID}]}))
    assert not S.ledger_declared(led)
    led.write_text(json.dumps({"tests": [{"test_id": S.LEDGER_ID, S.LEDGER_KEY: f"{S.LEDGER_MARK} (...)"}]}))
    assert S.ledger_declared(led)
    monkeypatch.setattr(S, "ledger_declared", lambda path=None: False)
    with pytest.raises(SystemExit, match="runs refuse"):
        S.main(["page", "--part", "1", "--smoke", "--out", str(tmp_path)])


def test_the_ledger_declares_the_pages():
    assert S.ledger_declared()


def test_spectrogram_difference_and_playing_share():
    np = pytest.importorskip("numpy")
    y = np.random.default_rng(1).standard_normal(48000)
    assert S.spec_diff_db(y, y) == float("-inf")
    assert S.spec_diff_db(y, 0.5 * y) == pytest.approx(-6.02, abs=0.01)
    assert S.playing_share(np.r_[y, np.zeros(48000)], 48000) == pytest.approx(0.5)
    assert S.playing_share(np.zeros(4800), 48000) == 0.0


def _page(tmp_path, monkeypatch, quiet=False):
    """cmd_page on a fake part 2: the in-mix key's items, synthetic renders, pair_clips captured."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    from learn import build_data_review as BDR

    t = np.arange(10 * BDR.SR) / BDR.SR
    audio = {(i, AM.ON): 0.1 * np.sin(2 * np.pi * (110 + i % 50) * t) for i in (803054, 2, 3)}
    audio.update({(i, e): (0 if quiet else 0.05) * np.sin(2 * np.pi * 220 * t) for i, e in
                  ((803054, "delay"), (2, "delay"), (3, "reverb"))})
    src = {"build": "inmix", "items": _src()}
    pairs = {(m["i"], m["effect"]): dict(m, solo=1.5) for m in MEASURED}
    sd = S.source_dir(tmp_path, 2)
    sd.mkdir(parents=True)
    (sd / "page-key.json").write_text(json.dumps(src))
    seen = []

    def clips(a, b, cache):
        seen.append((a, b))
        return "A", "B"

    monkeypatch.setattr(S, "require_declared", lambda: None)
    monkeypatch.setattr(S, "sources", lambda root, part: (src, pairs, lambda i, what: audio[(i, what)].copy()))
    monkeypatch.setattr(AM, "pair_clips", clips)
    S.main(["page", "--part", "2", "--smoke", "--out", str(tmp_path)])
    return audio, seen, json.loads(S.key_path(tmp_path, 2).read_text()), sd


def test_the_page_plays_the_renders_alone_and_writes_only_its_own_files(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    audio, seen, key, sd = _page(tmp_path, monkeypatch)
    assert json.loads((sd / "page-key.json").read_text())["build"] == "inmix"     # the in-mix key untouched
    assert key["solo"] is True and key["part"] == 2 and key["source_build"] == "inmix"
    assert key["swaps"] == [{"replaced": 900215, "by": 803054, "effect": "delay", "kind": "anchor (loudest)",
                             "a_e": 0.45}]
    by_order = sorted(key["items"], key=lambda it: it["id"])
    assert len(seen) == len(by_order) == 4
    for it, (a, b) in zip(by_order, seen):                                     # the clips are the renders, no backing
        on = audio[(it["i"], AM.ON)]
        off = on if it["kind"] == "same" else audio[(it["i"], it["effect"])]
        first, second = (on, off) if it["first"] == "on" else (off, on)
        assert np.array_equal(a, first) and np.array_equal(b, second)
        assert it["playing_on"] == 1.0 and it["playing_off"] == 1.0 and it["lufs_on"] < -10 and it["lufs_off"] < -10
        if it["kind"] == "same":
            assert it["solo_j"] is None and it["spec_diff_db"] is None
        else:
            assert it["solo_j"] == 1.5 and np.isfinite(it["spec_diff_db"])
    page = (tmp_path / "listening" / "cc-audibility-solo" / "index.html").read_text()
    assert "played alone (no band)" in page and key["build"] in page
    with pytest.raises(SystemExit, match="exists"):                             # no silent rebuild over answers
        S.main(["page", "--part", "2", "--smoke", "--out", str(tmp_path)])


def test_clips_are_levelled_apart():
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    from learn import build_data_review as BDR
    from learn import trusted_data as T

    t = np.arange(10 * BDR.SR) / BDR.SR
    a, b = AM.level_free(0.3 * np.sin(2 * np.pi * 200 * t), 0.01 * np.sin(2 * np.pi * 300 * t))
    assert T.lufs_or_none(a) == pytest.approx(-23.0, abs=0.1) and T.lufs_or_none(b) == pytest.approx(-23.0, abs=0.1)


def test_a_near_silent_guitar_stops_the_build(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="near-silent"):
        _page(tmp_path, monkeypatch, quiet=True)
    assert not S.key_path(tmp_path, 2).exists()


def test_the_real_parts_when_present():
    root = V.out_root(type("A", (), {"out": None}))
    if not (S.source_dir(root, 1) / "page-key.json").exists() or not (S.source_dir(root, 2) / "page-key.json").exists():
        pytest.skip("the in-mix pages' keys are not on this machine")
    for part, n, swap in ((1, 17, []), (2, 25, [(900215, 803054)])):
        sd = S.source_dir(root, part)
        src = json.loads((sd / "page-key.json").read_text())
        meas = json.loads((sd / "measure.json").read_text())["pairs"]
        if part == 1:
            s4 = json.loads((S.source_dir(root, 2) / "measure.json").read_text())["pairs"]
            meas = meas + [p for p in s4 if (p["i"], p["effect"]) in D.CHECKS]
        items, swaps = S.solo_items(src["items"], meas)
        assert len(items) == n and [(s["replaced"], s["by"]) for s in swaps] == swap
        assert not any(it["i"] in D.RUNAWAY for it in items)
