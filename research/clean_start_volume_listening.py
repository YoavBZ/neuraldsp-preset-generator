"""Are the turned-down clean starts closer by ear? (docs/clean-start-volume-listening-plan.md)

    build   render each clean part's DI through each amp's clean start as shipped and turned
            down (after a reproduction check), choose the reversed-taste controls by rule,
            cut half B, level, write the trial files and the private key; prints the key's
            SHA-256, committed before the first sitting
    phone   one self-contained phone page per sitting
    score   check the key's and the answer sheet's committed hashes, then compute the
            declared readings into docs/clean-start-volume-listening-results.json

The parts are the starting-preset check's (development only; nothing held out, nothing
from sets 5 or 6).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import secrets
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "learn"))

import generate_routing as GR  # noqa: E402
import starting_preset_listening as SPL  # noqa: E402

OUT = pathlib.Path.home() / "ndsp-presets" / "listening" / "clean-start-volume"
PLAN = ROOT / "docs" / "clean-start-volume-listening-plan.md"
REPEATS_PER_AMP = 1
AMPS = ("pr12", "sw50r", "ac20")
# The turned-down volume per amp (the plan's table).
DOWN = {"pr12": ("pr12Amp", "pr12Volume", 35.0),
        "sw50r": ("sw50rAmp", "sw50rVolume", 15.0),
        "ac20": ("ac20Amp", "ac20Volume", 10.0)}
REVERSED_MARGIN = 0.15        # the judge prefers the shipped start by more than this
REVERSED_N = 2
SAME_SONG = ({"cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1",
              "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2"},
             {"telefunken-First_Offering-GTR_1", "telefunken-First_Offering-GTR_2"})


def _parts():
    chosen = json.loads(SPL.PARTS.read_text())
    main = [dict(slug=r["slug"], band=r["band"], set=r["set"]) for b in ("C", "X") for r in chosen[b]]
    controls = [dict(slug=r["slug"], band=r["band"], set=r["set"], block=r["block"])
                for r in chosen["controls"]]
    by_slug = {p["slug"]: p for p in json.loads(GR.PARTS.read_text())["parts"]}
    crunch = [dict(slug=s, band=by_slug[s]["band"], set=by_slug[s]["set"])
              for s in chosen["spare_crunch"]]
    crunch += [dict(slug=r["slug"], band=r["band"], set=r["set"]) for r in chosen["K"]]
    return main, controls, crunch


def rebuild_measfix(parts):
    """The set 1-2 and 12 parts' measfix DIs, removed in the approved 2026-10-20 cleanup,
    rebuilt the way `learn.confirm_run.build_di("measfix", ...)` makes them (the crop's DI
    EQ'd to the average guitar spectrum, at -22.9 LUFS) into this check's own folder, and
    `songs_check` pointed there; learn/ is not touched. The reproduction check then confirms
    they match the stored scores."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import songs_check as SC
    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    folder = OUT / "measfix"
    avg = np.load(CR.AVERAGE)
    for p in parts:
        if p["set"] == 3:
            continue
        target = folder / p["slug"] / "di.npy"
        if not target.exists():
            part = SC.parts()[p["slug"]]
            di = CR.mono(part["crop"] / "di.wav")
            own = smoothed_spectrum(di)
            target.parent.mkdir(parents=True, exist_ok=True)
            np.save(target, to_lufs(eq_to(di, avg - (own - own.mean()))))
    SC.OUT = OUT                       # kind_dir("measfix", slug, part) -> OUT/measfix/slug


def driven_margin(entries, slug):
    """How driven the record is, from stored scores only: the mean over amps and halves of
    log d(clean start) - log d(crunch start). Higher means the crunch start sat closer."""
    vals = [math.log(GR._raw(entries, slug, a, GR.BASELINES["clean"][a], h))
            - math.log(GR._raw(entries, slug, a, GR.BASELINES["crunch"][a], h))
            for a in AMPS for h in "AB"]
    return sum(vals) / len(vals)


def _options(amp, folder):
    """(shipped xml, turned-down xml) for an amp: the clean baseline made dry, then the
    same with the amp's volume set."""
    shipped = SPL._dry_xml(GR.BASELINES["clean"][amp], amp, folder)
    down = folder / f"{shipped.stem}-down.xml"
    if not down.exists():
        module, key, value = DOWN[amp]
        spec = folder / f"{amp}-down.json"
        spec.write_text(json.dumps({"parameters": [{"module": module, "key": key, "value": value}]}))
        GR._apply(["--template", str(shipped), "--spec", str(spec), "--out", str(down)], folder)
    return shipped, down


def build(isolate: bool):
    import numpy as np

    import build_avg_listening as L
    import render_preset_panel as RP
    from analysis.aligned import aligned_distance
    from learn import phase2_set3 as P
    from learn import rescore as R
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    main, controls, crunch = _parts()
    rebuild_measfix(main + controls + crunch)
    listen, private = OUT / "listen", OUT / "private"
    for folder in (listen, private):
        if folder.exists() and any(folder.iterdir()):
            raise SystemExit(f"{folder} is not empty; the trials are built once")
        folder.mkdir(parents=True, exist_ok=True)
    entries = GR._distances()
    pack = load_pack("morgan")
    seed = secrets.randbits(64)           # kept in the private key only
    rng = random.Random(seed)

    class OptionRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["key"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    renderer = OptionRenderer("morgan", process_policy="reuse", isolate=isolate)
    rendered, check = {}, []
    state = {"amp": None}

    def render(r, amp):
        shipped, down = _options(amp, OUT / "presets")
        ref, di, lag = GR._context(r["slug"], r["set"])
        d32 = np.asarray(di, dtype=np.float32)
        for role, xml in (("shipped", shipped), ("down", down)):
            key = f"{r['slug']}|{amp}|{role}"
            if key in rendered:
                continue
            OptionRenderer.commands[key] = RP.preset_edits(xml, pack, renderer, amp, False)
            if amp != state["amp"]:
                renderer.render(d32, {"key": key})            # priming after an amp change
                state["amp"] = amp
            y = np.asarray(renderer.render(d32, {"key": key}).audio, np.float64)
            y = y.mean(axis=1) if y.ndim > 1 else y
            halves = {h: aligned_distance(ref, y, di, lag=lag, render_latency=P.LATENCY,
                                          start_s=a, end_s=b).distance
                      for h, (a, b) in R.HALVES.items()}
            rendered[key] = (y, halves)
            if role == "shipped":
                stored = {h: GR._raw(entries, r["slug"], amp, GR.BASELINES["clean"][amp], h)
                          for h in "AB"}
                if all(stored.values()):
                    check.append(dict(slug=r["slug"], amp=amp, **{
                        h: round(abs(math.log(halves[h]) - math.log(stored[h])), 5) for h in "AB"}))

    def ratio(r, amp):
        return (math.log(rendered[f"{r['slug']}|{amp}|down"][1]["B"])
                - math.log(rendered[f"{r['slug']}|{amp}|shipped"][1]["B"]))

    practice = [c for c in controls if c["block"] == "practice"]
    hidden = [c for c in controls if c["block"] == "hidden"]
    jobs = [(r, amp, "main") for amp in AMPS for r in main]
    jobs += [(c, "pr12", "practice") for c in practice]
    jobs += [(c, amp, "hidden") for c, amp in zip(hidden, ("sw50r", "ac20"))]
    reversed_jobs = []
    try:
        for amp in AMPS:
            for r, a, _ in jobs:
                if a == amp:
                    render(r, amp)
        # Reversed taste: crunch development parts, in the parts file's order, on SW50R then
        # AC20, where the judge prefers the shipped start on half B by more than the margin.
        for amp in ("sw50r", "ac20"):
            for r in crunch:
                if len(reversed_jobs) >= REVERSED_N or any(j[0]["slug"] == r["slug"] for j in reversed_jobs):
                    continue
                render(r, amp)
                if ratio(r, amp) > REVERSED_MARGIN:
                    reversed_jobs.append((r, amp, "reversed"))
                    break
    finally:
        renderer.close()
    worst_b = max(c["B"] for c in check) if check else None
    worst_a = max(c["A"] for c in check) if check else None
    if worst_b is None or worst_b >= 0.005:
        bad = [c for c in check if c["B"] >= 0.005]
        raise SystemExit(f"reproduction check failed on half B (isolate={isolate}): worst "
                         f"|Δ log| {worst_b}; {bad}\nIf isolate is the cause, rerun with --no-isolate.")
    jobs += reversed_jobs

    trials = []
    for r, amp, block in jobs:
        trials.append(dict(block=block, slug=r["slug"], band=r["band"], amp=amp, set=r["set"],
                           driven_margin=round(driven_margin(entries, r["slug"]), 4)
                           if block == "main" else None,
                           judge_log_ratio_down_over_shipped_halfB=round(ratio(r, amp), 4),
                           _y={"down": rendered[f"{r['slug']}|{amp}|down"][0],
                               "shipped": rendered[f"{r['slug']}|{amp}|shipped"][0]}))
    # Sittings balanced by amp: each amp's 13 parts split 6/7 at random, alternating which
    # sitting gets 7; A/B balanced within each amp and sitting.
    s1, s2 = [], []
    for i, amp in enumerate(AMPS):
        ts = [t for t in trials if t["block"] == "main" and t["amp"] == amp]
        rng.shuffle(ts)
        k = 7 if i % 2 == 0 else 6
        for part, sitting in ((ts[:k], s1), (ts[k:], s2)):
            lead = set(id(t) for t in rng.sample(part, len(part) // 2 + (rng.random() < 0.5 if len(part) % 2 else 0)))
            for t in part:
                t["down_is"] = "A" if id(t) in lead else "B"
            sitting.extend(part)
    for t in trials:
        t.setdefault("down_is", "A" if rng.random() < 0.5 else "B")
    repeats = [rng.choice([t for t in s1 if t["amp"] == amp]) for amp in AMPS for _ in range(REPEATS_PER_AMP)]
    hid = [t for t in trials if t["block"] == "hidden"]
    prac = [t for t in trials if t["block"] == "practice"]
    rev = [t for t in trials if t["block"] == "reversed"]
    s1 = s1 + hid[:1] + rev[:1]
    s2 = s2 + hid[1:2] + rev[1:2] + [dict(t, block="repeat", down_is="B" if t["down_is"] == "A" else "A")
                                     for t in repeats]

    def spread(seq):
        for _ in range(2000):
            rng.shuffle(seq)
            if all(seq[i]["slug"] != seq[i + 1]["slug"] for i in range(len(seq) - 1)):
                return seq
        raise SystemExit("could not order a sitting without the same part twice in a row")

    sittings = [prac + spread(s1), spread(s2)]
    rows, clips = [], []
    for sitting, seq in enumerate(sittings, 1):
        for t in seq:
            ref, _, lag = GR._context(t["slug"], t["set"])
            a = t["_y"]["down"] if t["down_is"] == "A" else t["_y"]["shipped"]
            b = t["_y"]["shipped"] if t["down_is"] == "A" else t["_y"]["down"]
            rr, aa, bb = L.excerpt(ref, a, b, lag)
            if t["block"] == "hidden":           # one option is the reference itself
                if t["down_is"] == "A":
                    aa = rr.copy()
                else:
                    bb = rr.copy()
            clips += [L.fade(rr), L.fade(aa), L.fade(bb)]
            row = {k: v for k, v in t.items() if k != "_y"}
            row.update(trial=len(rows) + 1, sitting=sitting)
            if t["block"] == "hidden":
                row["reference_is"] = t["down_is"]
            if t["block"] == "repeat":
                row["repeat_of"] = next(x["trial"] for x in rows if x["slug"] == t["slug"]
                                        and x["block"] == "main" and x["amp"] == t["amp"])
            rows.append(row)
    target, levelled, _ = L.level(clips)
    gains = [20 * math.log10(float(np.sqrt(np.mean(np.square(after)))) /
                             max(float(np.sqrt(np.mean(np.square(before)))), 1e-12))
             for before, after in zip(clips, levelled)]
    for k, row in enumerate(rows):
        rr, aa, bb = levelled[3 * k: 3 * k + 3]
        g = gains[3 * k: 3 * k + 3]
        row["levelling_gain_db"] = {x: round(float(v), 2) for x, v in zip("RAB", g)}
        n = f"{row['trial']:02d}"
        L.write(listen / f"trial-{n}.flac", L.montage(rr, aa, bb))
        for label, x in zip("RAB", (rr, aa, bb)):
            L.write(listen / f"trial-{n}-{label}.flac", x)
    key = {"schema": "clean-start-volume-listening-key-v1", "plan": PLAN.name, "seed": seed,
           "isolate": isolate, "down": {a: v[2] for a, v in DOWN.items()},
           "reproduction": {"worst_dlog_halfB": worst_b, "worst_dlog_halfA": worst_a,
                            "per_part": check},
           "target_lufs": round(target, 3),
           "sittings": {s + 1: [r["trial"] for r in rows if r["sitting"] == s + 1]
                        for s in range(2)},
           "trials": rows}
    text = json.dumps(key, indent=1) + "\n"
    (private / "key.json").write_text(text)
    (listen / "sittings.json").write_text(json.dumps(key["sittings"]) + "\n")
    print(f"built {len(rows)} trials (isolate={isolate}); reproduction worst |Δ log| half B "
          f"{worst_b:.5f}, half A {worst_a:.5f}; reversed controls: {len(rev)}")
    print(f"key sha256 {hashlib.sha256(text.encode()).hexdigest()}")


def phone():
    """The starting-preset check's phone pages, pointed at this check's trials (same
    format, same check that no preset or amp is named), retitled so answers from the two
    checks cannot be confused."""
    SPL.OUT = OUT
    SPL.phone()
    for f in sorted((OUT / "listen").glob("sitting-*-phone.html")):
        text = f.read_text()
        for old, new in (("Listening check S", "Listening check V"), ('"start-', '"check-v-')):
            if old not in text:
                raise SystemExit(f"{f.name}: {old!r} not found")
            text = text.replace(old, new)
        f.write_text(text)


KEY_SHA = "c73ef0f023e9fcb75de3b204dafee0b425a9fef5e09237826bd9cb1dc89afe5b"  # before the first sitting
ANSWERS = ROOT / "docs" / "clean-start-volume-listening-answers.txt"
ANSWERS_SHA = None      # committed before the key is read
RESULTS = ROOT / "docs" / "clean-start-volume-listening-results.json"


def _sign_p_two(k, n):
    tail = sum(math.comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def _interval(k, n):
    """Exact (Clopper-Pearson) 95% interval for a share."""
    from scipy.stats import beta

    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return [round(lo, 3), round(hi, 3)]


def score():
    import re

    if not KEY_SHA or not ANSWERS_SHA:
        raise SystemExit("commit the key's and the answer sheet's hashes first")
    key_bytes = (OUT / "private" / "key.json").read_bytes()
    if hashlib.sha256(key_bytes).hexdigest() != KEY_SHA:
        raise SystemExit("the key does not match its committed hash")
    if hashlib.sha256(ANSWERS.read_bytes()).hexdigest() != ANSWERS_SHA:
        raise SystemExit("the answer sheet does not match its committed hash")
    key = json.loads(key_bytes)
    answers = {}
    for n, a in re.findall(r"(\d+)([AB?])", ANSWERS.read_text()):
        if int(n) in answers:
            raise SystemExit(f"trial {n} answered twice")
        answers[int(n)] = a
    trials = {t["trial"]: t for t in key["trials"]}
    extra = sorted(set(answers) - set(trials))
    if extra:
        raise SystemExit(f"answers for trials that do not exist: {extra}")

    def chose_down(t):
        a = answers.get(t["trial"])
        return None if a in (None, "?") else a == t["down_is"]

    out = {"plan": PLAN.name, "key_sha256": KEY_SHA, "answers_sha256": ANSWERS_SHA,
           "unanswered": sorted(set(trials) - set(answers))}
    hidden = [t for t in trials.values() if t["block"] == "hidden"]
    # An unanswered or missed hidden reference voids its sitting.
    out["hidden_reference"] = {f"sitting {t['sitting']}": answers.get(t["trial"]) == t["reference_is"]
                               for t in hidden}
    void = {t["sitting"] for t in hidden if answers.get(t["trial"]) != t["reference_is"]}
    out["void_sittings"] = sorted(void)
    main = [t for t in trials.values() if t["block"] == "main" and t["sitting"] not in void]

    def reading(ts):
        decided = [chose_down(t) for t in ts if chose_down(t) is not None]
        k, n = sum(decided), len(decided)
        return {"chose_turned_down": k, "decided": n, "cant_tell": len(ts) - n,
                "share": round(k / n, 3) if n else None,
                "interval_95": _interval(k, n) if n else None,
                "p_two_sided": round(_sign_p_two(k, n), 4) if n else None}

    out["per_amp"] = {a: reading([t for t in main if t["amp"] == a]) for a in AMPS}
    out["pooled_descriptive"] = reading(main)
    same = set().union(*SAME_SONG)
    out["pooled_without_same_song_pairs"] = reading([t for t in main if t["slug"] not in same])
    # The cleaner and the more driven records (the stored-score margin, split at the median).
    margins = sorted({t["slug"]: t["driven_margin"] for t in main}.items(), key=lambda x: x[1])
    cleaner = {s for s, _ in margins[: len(margins) // 2]}
    out["per_amp_cleaner_records"] = {a: reading([t for t in main if t["amp"] == a and t["slug"] in cleaner])
                                      for a in AMPS}
    out["per_amp_more_driven_records"] = {a: reading([t for t in main if t["amp"] == a
                                                      and t["slug"] not in cleaner]) for a in AMPS}
    by_part = {}
    for t in main:
        c = chose_down(t)
        by_part.setdefault(t["slug"], {})[t["amp"]] = None if c is None else ("down" if c else "shipped")
    out["by_part"] = by_part
    counts = [sum(v == "down" for v in d.values()) for d in by_part.values()]
    out["parts_by_turned_down_picks"] = {n: counts.count(n) for n in range(4)}
    decision = {}
    if void == {1, 2}:
        decision = {a: "no reading; no change" for a in AMPS}
    else:
        for a in ("sw50r", "ac20"):
            s = out["per_amp"][a]["share"]
            decision[a] = ("no reading; no change" if s is None else
                           "keep the turned-down rule" if s >= 0.5 else
                           "revert to 'may break up', no volume change")
        s = out["per_amp"]["pr12"]["share"]
        decision["pr12"] = ("no reading; no change" if s is None else
                            "set pr12Volume 35 for a fully clean part" if s > 0.5 else "no change")
    out["decision"] = decision
    agree = {"all": [], "margin_over_0.15": [], "margin_at_most_0.15": []}
    for t in main:
        c = chose_down(t)
        if c is None:
            continue
        r = t["judge_log_ratio_down_over_shipped_halfB"]
        hit = c == (r < 0)
        agree["all"].append(hit)
        agree["margin_over_0.15" if abs(r) > 0.15 else "margin_at_most_0.15"].append(hit)
    out["ear_judge_agreement"] = {k: [sum(v), len(v)] for k, v in agree.items()}
    out["judge_chose_turned_down"] = {
        a: [sum(t["judge_log_ratio_down_over_shipped_halfB"] < 0 for t in main if t["amp"] == a),
            sum(1 for t in main if t["amp"] == a)] for a in AMPS}
    out["reversed_taste_control"] = [{"amp": t["amp"], "answer": answers.get(t["trial"]),
                                      "chose_shipped_as_judge_prefers": None if chose_down(t) is None
                                      else not chose_down(t)}
                                     for t in trials.values() if t["block"] == "reversed"]
    reps = []
    for t in trials.values():
        if t["block"] == "repeat" and t["sitting"] not in void:
            o = trials[t["repeat_of"]]
            a, b = chose_down(t), chose_down(o)
            if a is not None and b is not None and o["sitting"] not in void:
                reps.append({"trial": t["trial"], "of": o["trial"], "consistent": a == b})
    out["repeats"] = reps
    gap = {a: [] for a in AMPS}
    for t in main:
        g = t["levelling_gain_db"]
        down, ship = (g["A"], g["B"]) if t["down_is"] == "A" else (g["B"], g["A"])
        gap[t["amp"]].append(down - ship)
    out["levelling_gain_down_minus_shipped_db_median"] = {
        a: round(sorted(v)[len(v) // 2], 2) if v else None for a, v in gap.items()}
    out["per_trial"] = [{"trial": t["trial"], "block": t["block"], "amp": t["amp"],
                         "answer": answers.get(t["trial"]), "down_is": t["down_is"],
                         "judge_log_ratio": t["judge_log_ratio_down_over_shipped_halfB"]}
                        for t in sorted(trials.values(), key=lambda x: x["trial"])]
    RESULTS.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("void_sittings", "hidden_reference", "per_amp",
                                          "pooled_descriptive", "decision", "per_amp_cleaner_records",
                                          "per_amp_more_driven_records", "parts_by_turned_down_picks",
                                          "ear_judge_agreement", "reversed_taste_control",
                                          "repeats")}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=["build", "phone", "score"])
    ap.add_argument("--no-isolate", action="store_true",
                    help="render without isolate (only if half B fails to reproduce with it)")
    args = ap.parse_args()
    if args.step == "build":
        build(isolate=not args.no_isolate)
    else:
        {"phone": phone, "score": score}[args.step]()


if __name__ == "__main__":
    main()
