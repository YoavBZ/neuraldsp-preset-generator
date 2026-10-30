"""Guitar-only versions of the clean/crunch listening pages (`docs/clean-crunch-pool-plan.md`; ledger
`clean-crunch-pool-dcc`, `amendment_6`). The user, 2026-10-30: "The mixes make it harder to distinguish, please only
the guitars if possible". Part 1 is the drive page's items (`cc_drive_page`, amendment 5), part 2 step 4's
(`cc_audibility`, amendment 3), each clip the rendered guitar alone: no backing, no other guitars, no stand-ins, no
mastering. Zero renders: every clip is a stored r_on' or r_off, read hash-checked. Descriptive: it decides nothing and
relabels nothing. Outputs: new keys beside the in-mix keys (`solo-page-key.json`) and new pages
(`listening/cc-drive-solo/`, `listening/cc-audibility-solo/`); the in-mix pages, keys, plans and measurements are
read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.cc_solo_pages page --part 1          # the drive page's 17 items, the guitar alone
    $MAIN -m learn.cc_solo_pages page --part 2          # step 4's 25 items, the guitar alone (item 4 replaced)

**The items.** The in-mix page's items as its key stored them (the same pairs, kinds and catches), except a pair on a
runaway-flagged example (`cc_drive_page.RUNAWAY`): step 4's delay anchor 900215 is a self-oscillating delay, dirty
under the trusted-data rule, so it is replaced by the loudest measured pair of the same effect that is neither
runaway-flagged nor on the page (`swap_runaway`). New ids, order and A/B draw (PAGE_SEED: the listener has heard the
in-mix pages). Each clip is levelled to -23 LUFS on its own with 10-ms fades and AAC at 256 kbps
(`audibility_measure.pair_clips`), in the drive page's A/B player (`cc_drive_page.page_html`, guitar-only wording).
**Near silence.** A guitar-alone render below the pool's render floor (`trusted_data.near_silent`) stops the build,
named; none is at the declaration. Gaps where the guitar does not play are kept (both clips share them): each item's
key row records the share of its window where the guitar plays (`playing_share`), with its solo J (the measurement's
J(r_off, r_on') on the guitar alone) and the clips' magnitude-spectrogram difference (`spec_diff_db`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import time

from learn import audibility_measure as AM
from learn import cc_audibility as CA
from learn import cc_drive_page as D
from learn import verify_tracks as V

LEDGER_ID = D.LEDGER_ID                         # clean-crunch-pool-dcc
LEDGER_KEY = "amendment_6"
LEDGER_MARK = "Guitar-only listening pages"
KEY_NAME = "solo-page-key.json"                 # beside each in-mix page-key.json
PAGE_SEED = 20261119                            # the order and each item's A/B order, both parts
PLAY_DB = 40.0                                  # playing: a 100-ms frame within this of the window's loudest
PARTS = {1: {"name": "cc-drive-solo", "source": "drive page (amendment 5)"},
         2: {"name": "cc-audibility-solo", "source": "step 4's page (amendment 3)"}}

_save, _load = V._save, V._load


# --- pure ---------------------------------------------------------------------------------------------------------

def solo_id(effect, i, kind):
    return "solo-" + hashlib.sha256(f"{effect}|{i}|{kind}".encode()).hexdigest()[:12]


def swap_runaway(items, measured, runaway=D.RUNAWAY):
    """(items, swaps): each pair on a runaway-flagged example replaced by the loudest measured pair of its effect that
    is neither runaway-flagged nor on the page (kind marked); a catch on one is dropped (none on either page)."""
    on_page = {(it["effect"], it["i"]) for it in items}
    out, swaps = [], []
    for it in items:
        if it["i"] not in runaway:
            out.append(dict(it))
            continue
        if it["kind"] == "same":
            swaps.append({"dropped": it["i"], "effect": it["effect"], "kind": it["kind"]})
            continue
        rows = [m for m in measured if m["effect"] == it["effect"] and m.get("a_e") is not None
                and m["i"] not in runaway and (m["effect"], m["i"]) not in on_page]
        if not rows:
            swaps.append({"dropped": it["i"], "effect": it["effect"], "kind": it["kind"]})
            continue
        m = max(rows, key=lambda m: (m["a_e"], -m["i"]))
        kind = f"{it['kind']}, in place of runaway {it['i']}"
        out.append({"effect": it["effect"], "i": m["i"], "kind": kind, "a_e": m["a_e"]})
        on_page.add((m["effect"], m["i"]))
        swaps.append({"replaced": it["i"], "by": m["i"], "effect": it["effect"], "kind": it["kind"], "a_e": m["a_e"]})
    return out, swaps


def solo_items(src_items, measured, seed=PAGE_SEED, runaway=D.RUNAWAY):
    """(items, swaps): the in-mix page's items (effect, example, kind, A_e) with `swap_runaway` applied, new ids,
    shuffled, each item's A/B order drawn ("first": the clip with the effect on is A)."""
    rng = random.Random(seed)
    base = [{k: it[k] for k in ("effect", "i", "kind", "a_e")} for it in src_items]
    out, swaps = swap_runaway(base, measured, runaway)
    for it in out:
        it["id"] = solo_id(it["effect"], it["i"], it["kind"])
    out.sort(key=lambda it: it["id"])
    rng.shuffle(out)
    for it in out:
        it["first"] = rng.choice(("on", "off"))
    return out, swaps


def spec_diff_db(a, b, n=2048, hop=512):
    """The magnitude-spectrogram difference of b against a, in dB re a's (Hann frames of n, hop): -inf for the same
    clip."""
    import numpy as np

    w = np.hanning(n)

    def mag(y):
        k = 1 + max(0, (len(y) - n) // hop)
        idx = np.arange(n)[None, :] + hop * np.arange(k)[:, None]
        return np.abs(np.fft.rfft(np.pad(y, (0, max(0, n - len(y))))[idx] * w, axis=1))

    m = min(len(a), len(b))
    A, B = mag(np.asarray(a[:m], float)), mag(np.asarray(b[:m], float))
    d, r = float(np.sqrt(((A - B) ** 2).sum())), float(np.sqrt((A ** 2).sum()))
    return float("-inf") if d == 0 or r == 0 else 20 * float(np.log10(d / r))


def playing_share(y, sr, within=PLAY_DB, frame_s=0.1):
    """The share of 100-ms frames within `within` dB of the window's loudest frame: where the guitar plays."""
    import numpy as np

    f = int(sr * frame_s)
    k = len(y) // f
    if k == 0:
        return 0.0
    rms = np.sqrt((np.asarray(y[:k * f], float).reshape(k, f) ** 2).mean(1))
    if rms.max() <= 0:
        return 0.0
    lv = 20 * np.log10(np.maximum(rms, 1e-12) / rms.max())
    return float((lv > -within).mean())


# --- I/O ------------------------------------------------------------------------------------------------------------

def source_dir(root, part):
    """The in-mix page's trusted-data folder: the drive page's (part 1) or step 4's (part 2)."""
    return D.out_dir(root) if part == 1 else CA.out_dir(root)


def key_path(root, part):
    return source_dir(root, part) / KEY_NAME


def page_dir(args, part):
    """~/ndsp-presets/listening/<part's name>; under --out for a smoke run."""
    return (pathlib.Path(args.out) / "listening" if args.smoke else V.HOME / "listening") / PARTS[part]["name"]


def ledger_declared(path=None):
    d = json.loads(pathlib.Path(path or V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require_declared():
    if not ledger_declared():
        raise SystemExit(f"the ledger's {LEDGER_ID} has no {LEDGER_KEY} declaring '{LEDGER_MARK}': runs refuse")


def sources(root, part):
    """(the in-mix key, the measured pairs the items come from {(i, effect): pair}, read(i, what))."""
    sd = source_dir(root, part)
    src = _load(sd / "page-key.json")
    meas = _load(sd / "measure.json")
    if not src or not meas:
        raise SystemExit(f"{sd}: the in-mix page's key and measure.json are needed")
    pairs = {(p["i"], p["effect"]): p for p in meas["pairs"]}
    if part == 1:
        s4 = _load(CA.out_dir(root) / "measure.json")
        pairs.update({(p["i"], p["effect"]): p for p in s4["pairs"] if (p["i"], p["effect"]) in D.CHECKS})
        return src, pairs, D.reader(root, _load(sd / "plan.json"))
    return src, pairs, CA.reader(root)


# --- commands ---------------------------------------------------------------------------------------------------------

def cmd_page(args):
    """One part's guitar-only page and its key (beside the in-mix key, under a new name); zero renders."""
    require_declared()                              # before any import: the light CI has no numpy
    from learn import build_data_review as BDR
    from learn import trusted_data as T

    part = args.part
    root = V.out_root(args)
    src, pairs, read = sources(root, part)
    refused = {r["i"] for r in (_load(source_dir(root, part) / "measure.json") or {}).get("refused", [])}
    items, swaps = solo_items(src["items"], [p for p in pairs.values() if p["i"] not in refused])
    pd, kp = page_dir(args, part), key_path(root, part)
    if kp.exists() and not args.force:
        raise SystemExit(f"{kp} exists: a rebuild hides the listener's stored answers (--force)")
    clips = {}
    for it in sorted(items, key=lambda it: it["id"]):
        i = it["i"]
        on = read(i, AM.ON)
        off = on.copy() if it["kind"] == "same" else read(i, it["effect"])
        for what, y in (("on", on), ("off", off)):
            why = T.near_silent(T.lufs_or_none(y))
            if why:
                raise SystemExit(f"{it['effect']} {i} {what}: the guitar alone is a {why}")
        a, b = (on, off) if it["first"] == "on" else (off, on)
        lon, loff = AM.level_free(on, off)
        p = pairs.get((i, it["effect"]))
        it.update(solo_j=None if it["kind"] == "same" or p is None else p.get("solo"),
                  spec_diff_db=None if it["kind"] == "same" else round(spec_diff_db(lon, loff), 2),
                  playing=round(playing_share(on, BDR.SR), 3), lufs_on=round(T.lufs_or_none(on), 2))
        clips[it["id"] + "-1"], clips[it["id"] + "-2"] = AM.pair_clips(a, b, pd / "cache")
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    _save(kp, {"page": PARTS[part]["name"], "part": part, "source": PARTS[part]["source"],
               "source_build": src.get("build"), "solo": True, "seed": PAGE_SEED, "tau": AM.TAU, "build": build,
               "swaps": swaps, "items": items, "player": "A/B", "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    pd.mkdir(parents=True, exist_ok=True)
    out = pd / "index.html"
    out.write_text(D.page_html(items, clips, build, name=PARTS[part]["name"], part=part, solo=True))
    print(f"PAGE DONE part {part}: {len(items)} items ({swaps or 'no swaps'}), {out.stat().st_size / 1e6:.1f} MB "
          f"-> {out}")


COMMANDS = {"page": cmd_page}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cc_solo_pages", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--part", type=int, choices=sorted(PARTS), required=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args(argv)
    CA.require_run(args)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
