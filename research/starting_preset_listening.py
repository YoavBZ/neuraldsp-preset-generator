"""Do the starting presets sound closer by ear? (docs/starting-preset-listening-plan.md)

    parts   screen and choose the parts, write docs/starting-preset-listening-parts.json
            (no judge margin for these trials is computed before it is written)
    build   render every option through the part's measfix DI (after a reproduction
            check), cut half B, level, write the trial files and the private key;
            prints the key's SHA-256, committed before the first sitting
    phone   one self-contained phone page per sitting

Development parts only; nothing held out, nothing from sets 5 or 6.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "learn"))

import generate_routing as GR  # noqa: E402

OUT = pathlib.Path.home() / "ndsp-presets" / "listening" / "starting-presets"
PARTS = ROOT / "docs" / "starting-preset-listening-parts.json"
PLAN = ROOT / "docs" / "starting-preset-listening-plan.md"
TEMPLATE = ROOT / "samples" / "Example_Clean_PR12.xml"
SR = 48000
HALF_B = (5.5, 10.0)
ACTIVE_SHARE = 0.9            # the DI plays in at least this share of half B
LOW_SHARE = 0.25              # at most this share of the DI's energy below 200 Hz
ACTIVE_DB = -40.0             # a 20-ms frame plays if within 40 dB of the 95th percentile
ROTATION = ("pr12", "sw50r", "ac20")
SEED = 20261013
MARGIN = 0.15
REPEATS = 3
DOUBLE_TRACKS = {"cambridge-magilla-elecgtr1dt", "cambridge-magilla-elecgtr2dt"}


def _di_stats(slug, set_id):
    import numpy as np

    _, di, _ = GR._context(slug, set_id)
    x = np.asarray(di, dtype=np.float64)[int(HALF_B[0] * SR):int(HALF_B[1] * SR)]
    n = int(0.02 * SR)
    frames = x[: len(x) // n * n].reshape(-1, n)
    rms = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-12)
    active = float((rms >= np.percentile(rms, 95) + ACTIVE_DB).mean())
    spectrum = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    low = float(spectrum[freqs < 200].sum() / max(spectrum.sum(), 1e-30))
    return active, low


def choose_parts():
    if PARTS.exists():
        raise SystemExit(f"{PARTS} exists; the parts are chosen once")
    entries = GR._distances()
    doc = json.loads(GR.PARTS.read_text())
    scored = [p for p in doc["parts"]
              if all(GR._raw(entries, p["slug"], a, GR.BASELINES[c][a], h)
                     for a in GR.AMPS for c in GR.BASELINES for h in "AB")]
    rows = []
    for p in scored:
        if p["label"] not in ("clean", "crunch"):
            continue
        active, low = _di_stats(p["slug"], p["set"])
        rows.append(dict(slug=p["slug"], band=p["band"], label=p["label"], set=p["set"],
                         active=round(active, 3), low=round(low, 3),
                         passes=active >= ACTIVE_SHARE and low <= LOW_SHARE))
    order = sorted((r for r in rows if r["passes"]), key=lambda r: (-r["active"], r["slug"]))
    bands = []
    for r in order:
        if r["band"] not in bands:
            bands.append(r["band"])
    used = set()

    def take(label, band, skip=()):
        for r in order:
            if (r["label"] == label and r["band"] == band and r["slug"] not in used
                    and r["slug"] not in skip):
                used.add(r["slug"])
                return r
        return None

    C = [r for b in bands if (r := take("clean", b))][:10]
    for r in C:
        r["block"], r["amp"] = "C", "pr12"
    X = []
    for b in bands:
        if len(X) == 6:
            break
        if not any(r["band"] == b for r in C):
            continue
        r = take("clean", b, skip=DOUBLE_TRACKS)
        if r:
            X.append(r)
    for i, r in enumerate(X):
        r["block"], r["amp"] = "X", ROTATION[i % 3]
    K = []
    for b in bands:
        for _ in range(2):
            if len(K) < 10 and (r := take("crunch", b)):
                K.append(r)
    for i, r in enumerate(K):
        r["block"], r["amp"] = "K", ROTATION[i % 3]
    spare_clean = [r for r in order if r["label"] == "clean" and r["slug"] not in used
                   and r["slug"] not in DOUBLE_TRACKS]
    spare_crunch = [r for r in order if r["label"] == "crunch" and r["slug"] not in used]
    controls = []
    for i, r in enumerate(spare_clean[:3]):
        r = dict(r)
        r["block"] = "practice" if i == 0 else "hidden"
        r["amp"] = "pr12"
        controls.append(r)
        used.add(r["slug"])
    out = {"plan": PLAN.name, "screen": {"active_share": ACTIVE_SHARE, "low_share": LOW_SHARE,
                                         "active_db": ACTIVE_DB},
           "C": C, "X": X, "K": K, "controls": controls,
           "spare_crunch": [r["slug"] for r in spare_crunch],
           "k_report_only": len(K) < 8,
           "screened_out": [r["slug"] for r in rows if not r["passes"]]}
    PARTS.write_text(json.dumps(out, indent=1) + "\n")
    print(f"C {len(C)}, X {len(X)}, K {len(K)} (report only: {len(K) < 8}), controls "
          f"{len(controls)}, spare crunch {len(spare_crunch)}, screened out "
          f"{len(out['screened_out'])}")


def _options(block, amp, band):
    """(preferred, other) preset sources for a block, as factory names or the template."""
    from functools import lru_cache  # noqa: F401

    B = GR.BASELINES
    if block == "C":
        return B["clean"]["pr12"], "template"
    if block == "X":
        return B["clean"][amp], B["crunch"][amp]
    if block == "K":
        return B["crunch"][amp], B["heavier"][amp]
    if block == "reversed":
        return B["crunch"][amp], B["clean"][amp]
    if block in ("hidden", "practice"):
        return B["clean"][amp], B["crunch"][amp]
    raise ValueError(block)


def _dry_xml(source, amp, folder):
    folder.mkdir(parents=True, exist_ok=True)
    name = "template" if source == "template" else hashlib.sha1(source.encode()).hexdigest()[:10]
    xml = folder / f"{name}-{amp}.xml"
    if not xml.exists():
        template = TEMPLATE if source == "template" else GR._factory_file(source)
        GR._apply(["--template", str(template), "--recipe", f"dry/{amp}", "--strip-irs",
                   "--out", str(xml)], folder)
    return xml


def build():
    import numpy as np

    import build_avg_listening as L
    import render_preset_panel as RP
    from analysis.aligned import aligned_distance
    from learn import phase2_set3 as P
    from learn import rescore as R
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    chosen = json.loads(PARTS.read_text())
    listen, private = OUT / "listen", OUT / "private"
    for folder in (listen, private):
        if folder.exists() and any(folder.iterdir()):
            raise SystemExit(f"{folder} is not empty; the trials are built once")
        folder.mkdir(parents=True, exist_ok=True)
    entries = GR._distances()
    pack = load_pack("morgan")

    class OptionRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["key"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    jobs = [(r, b) for b in ("C", "X", "K") for r in chosen[b]]
    jobs += [(r, r["block"]) for r in chosen["controls"]]
    # The reversed-taste control: the first spare crunch part (screened) on any amp with
    # a stored margin over 0.15 for the heavier option; else the first K part on another
    # amp with one; else none. Margins are looked at for these candidates only.
    reversed_job = None
    by_slug = {p["slug"]: p for p in json.loads(GR.PARTS.read_text())["parts"]}

    def margin(slug, amp):
        crunch, clean = GR.BASELINES["crunch"][amp], GR.BASELINES["clean"][amp]
        return sum(math.log(GR._raw(entries, slug, amp, clean, h))
                   - math.log(GR._raw(entries, slug, amp, crunch, h)) for h in "AB") / 2

    for slug in chosen["spare_crunch"]:
        for amp in ROTATION:
            if margin(slug, amp) > MARGIN:
                p = by_slug[slug]
                reversed_job = (dict(slug=slug, band=p["band"], label="crunch", set=p["set"],
                                     amp=amp, block="reversed"), "reversed")
                break
        if reversed_job:
            break
    if reversed_job is None:
        for r in chosen["K"]:
            for amp in ROTATION:
                if amp != r["amp"] and margin(r["slug"], amp) > MARGIN:
                    reversed_job = (dict(r, amp=amp, block="reversed"), "reversed")
                    break
            if reversed_job:
                break
    if reversed_job:
        jobs.append(reversed_job)

    renderer = OptionRenderer("morgan", process_policy="reuse")
    rendered, check = {}, []
    last_amp = None
    try:
        for r, block in jobs:
            preferred, other = _options(block, r["amp"], r["band"])
            ref, di, lag = GR._context(r["slug"], r["set"])
            d32 = np.asarray(di, dtype=np.float32)
            for role, source in (("preferred", preferred), ("other", other)):
                xml = _dry_xml(source, r["amp"], OUT / "presets")
                key = f"{r['slug']}|{r['amp']}|{source}"
                if key in rendered:
                    continue
                OptionRenderer.commands[key] = RP.preset_edits(xml, pack, renderer, r["amp"], False)
                if r["amp"] != last_amp:
                    renderer.render(d32, {"key": key})
                    last_amp = r["amp"]
                y = np.asarray(renderer.render(d32, {"key": key}).audio, np.float64)
                y = y.mean(axis=1) if y.ndim > 1 else y
                halves = {h: aligned_distance(ref, y, di, lag=lag, render_latency=P.LATENCY,
                                              start_s=a, end_s=b).distance
                          for h, (a, b) in R.HALVES.items()}
                rendered[key] = (y, halves)
                if source != "template":
                    stored = {h: GR._raw(entries, r["slug"], r["amp"], source, h) for h in "AB"}
                    if all(stored.values()):
                        check.append(max(abs(math.log(halves[h]) - math.log(stored[h]))
                                         for h in "AB"))
    finally:
        renderer.close()
    worst = max(check) if check else None
    if worst is None or worst >= 0.005:
        raise SystemExit(f"reproduction check failed: worst |Δ log| {worst}")

    rng = random.Random(SEED)
    trials = []
    for r, block in jobs:
        preferred, other = _options(block, r["amp"], r["band"])
        yp, hp = rendered[f"{r['slug']}|{r['amp']}|{preferred}"]
        yo, ho = rendered[f"{r['slug']}|{r['amp']}|{other}"]
        trials.append(dict(block=block, slug=r["slug"], band=r["band"], amp=r["amp"],
                           set=r["set"], preferred=preferred, other=other,
                           judge_log_ratio_preferred_over_other_halfB=round(
                               math.log(hp["B"]) - math.log(ho["B"]), 4),
                           _y={"preferred": yp, "other": yo}))
    # A/B: the preferred option is A on half of each block's trials (rounded), drawn.
    for block in ("C", "X", "K"):
        idx = [i for i, t in enumerate(trials) if t["block"] == block]
        lead = set(rng.sample(idx, len(idx) // 2 + (rng.random() < 0.5 if len(idx) % 2 else 0)))
        for i in idx:
            trials[i]["preferred_is"] = "A" if i in lead else "B"
    for t in trials:
        t.setdefault("preferred_is", "A" if rng.random() < 0.5 else "B")
    main = [t for t in trials if t["block"] in ("C", "X", "K")]
    repeats = rng.sample(main, REPEATS)
    hidden = [t for t in trials if t["block"] == "hidden"]
    practice = [t for t in trials if t["block"] == "practice"]
    rev = [t for t in trials if t["block"] == "reversed"]
    rest = [t for t in main if t not in repeats]
    rng.shuffle(rest)
    half = len(main) // 2
    s1 = repeats + rest[: half - len(repeats)] + hidden[:1] + rev
    s2 = rest[half - len(repeats):] + hidden[1:2] + [dict(t, block="repeat", of=id(t),
                                                         preferred_is="B" if t["preferred_is"] == "A" else "A")
                                                    for t in repeats]

    def spread(seq):
        for _ in range(200):
            rng.shuffle(seq)
            if all(seq[i]["slug"] != seq[i + 1]["slug"] for i in range(len(seq) - 1)):
                return seq
        return seq

    sittings = [practice + spread(s1), spread(s2)]
    rows, clips = [], []
    for sitting, seq in enumerate(sittings, 1):
        for t in seq:
            ref, _, lag = GR._context(t["slug"], t["set"])
            a = t["_y"]["preferred"] if t["preferred_is"] == "A" else t["_y"]["other"]
            b = t["_y"]["other"] if t["preferred_is"] == "A" else t["_y"]["preferred"]
            rr, aa, bb = L.excerpt(ref, a, b, lag)
            if t["block"] == "hidden":           # one option is the reference itself
                if t["preferred_is"] == "A":
                    aa = rr.copy()
                else:
                    bb = rr.copy()
            clips += [L.fade(rr), L.fade(aa), L.fade(bb)]
            row = {k: v for k, v in t.items() if k not in ("_y", "of")}
            row.update(trial=len(rows) + 1, sitting=sitting)
            if t["block"] == "hidden":
                row["reference_is"] = t["preferred_is"]
            if t["block"] == "repeat":
                row["repeat_of"] = next(x["trial"] for x in rows
                                        if x["slug"] == t["slug"] and x["block"] in ("C", "X", "K")
                                        and x["amp"] == t["amp"])
            rows.append(row)
    target, levelled, after = L.level(clips)
    for k, row in enumerate(rows):
        rr, aa, bb = levelled[3 * k: 3 * k + 3]
        n = f"{row['trial']:02d}"
        L.write(listen / f"trial-{n}.flac", L.montage(rr, aa, bb))
        for label, x in zip("RAB", (rr, aa, bb)):
            L.write(listen / f"trial-{n}-{label}.flac", x)
    key = {"schema": "starting-preset-listening-key-v1", "plan": PLAN.name, "seed": SEED,
           "reproduction_worst_dlog": round(worst, 6), "target_lufs": round(target, 3),
           "sittings": {s + 1: [r["trial"] for r in rows if r["sitting"] == s + 1]
                        for s in range(2)},
           "trials": rows}
    text = json.dumps(key, indent=1) + "\n"
    (private / "key.json").write_text(text)
    (listen / "sittings.json").write_text(json.dumps(key["sittings"]) + "\n")
    print(f"built {len(rows)} trials; reproduction worst |Δ log| {worst:.5f}; "
          f"reversed control: {'yes' if rev else 'none'}")
    print(f"key sha256 {hashlib.sha256(text.encode()).hexdigest()}")


def phone():
    import tempfile

    import soundfile as sf

    import build_avg_listening as L

    listen = OUT / "listen"
    sittings = {int(k): v for k, v in json.loads((listen / "sittings.json").read_text()).items()}
    page_t = L.PHONE
    for old, new in (("Listening check L", "Listening check S"),
                     ('"avg-{build}', '"start-{build}'),
                     ("Which of A and B is closer to the Reference?",
                      "Which of A and B is closer <b>in tone</b> to the Reference? Ignore "
                      "loudness: every clip is at the same level. If a clip sounds broken or "
                      "silent, stop and say which trial.{practice}"),
                     ("Tap A or B;\nyou must choose one.",
                      "Tap A, B, or ? if you\nreally can't tell.")):
        if old not in page_t:
            raise SystemExit(f"the phone template changed: {old!r} is gone")
        page_t = page_t.replace(old, new)
    for sitting, numbers in sorted(sittings.items()):
        files = [listen / f"trial-{n:02d}{x}.flac" for n in numbers for x in ("", "-R", "-A", "-B")]
        build_id = hashlib.sha256(b"".join(f.read_bytes()[:4096] for f in files)).hexdigest()[:12]
        sections = []
        with tempfile.TemporaryDirectory() as tmp:
            for n in numbers:
                clip_s = sf.info(str(listen / f"trial-{n:02d}-R.flac")).frames / SR
                rows = [f'<div class="row"><b>Trial</b><audio class="trial" controls '
                        f'preload="none" data-clip="{clip_s:.4f}" '
                        f'src="{L.aac_data_uri(listen / f"trial-{n:02d}.flac", tmp)}"></audio></div>']
                rows += [f'<div class="row"><b>{x}</b><audio controls preload="none" '
                         f'src="{L.aac_data_uri(listen / f"trial-{n:02d}-{x}.flac", tmp)}">'
                         f'</audio></div>' for x in "RAB"]
                buttons = "".join(f'<button type="button" data-value="{x}">{x}</button>'
                                  for x in ("A", "B", "?"))
                title = f"Trial {n} (practice)" if n == 1 else f"Trial {n}"
                sections.append(f'<section><h2>{title}</h2><p class="cue"></p>'
                                f'{"".join(rows)}<div class="pick" data-trial="{n}">'
                                f'{buttons}</div></section>')
        page = page_t.format(sitting=sitting, first=numbers[0], last=numbers[-1],
                             count=len(numbers), build=build_id, gap=L.GAP_S,
                             cycle=L.CYCLE_GAP_S,
                             brk=", with a break between the sittings" if sitting == 1 else "",
                             practice=" Trial 1 is practice." if sitting == 1 else "",
                             trials="\n".join(sections))
        import re

        text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page)
        for word in ("PR12", "SW50R", "AC20", ".xml", "factory", "Royally", "Metal",
                     "Platform", "Low-Watt", "Doom", "Coil", "template"):
            if re.search(r"(?<![-\w])" + re.escape(word) + r"(?![-\w])", text, re.I):
                raise SystemExit(f"the page names {word}")
        out = listen / f"sitting-{sitting}-phone.html"
        out.write_text(page)
        print(f"{out} ({out.stat().st_size / 1e6:.1f} MB, {len(numbers)} trials)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=["parts", "build", "phone"])
    args = ap.parse_args()
    {"parts": choose_parts, "build": build, "phone": phone}[args.step]()


if __name__ == "__main__":
    main()
