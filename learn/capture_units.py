"""L1a's units, and L1b's and L1c's (`docs/pipeline-fix-plan.md`, ledger `phase_l1a`; `docs/full-controls-plan.md`, `phase_l1c`): which capture plays which DI at which level.

The pure rules run anywhere; the worker runs in `tools/nam-venv` and reads the captures as data:

    ~/ndsp-presets/tools/nam-venv/bin/python -I ~/ndsp-presets/tools/nam-tools/nam_notk.py learn/capture_units.py PLAN OUT

PLAN (`capture_labels dis`): {seed, plan: [{capture, path, sha256, level_dbu}], players: {player: [item]}, dis: npz}. Each
capture's candidates go through the level rule and the pool's classifier, and each amp takes its DI (`walk`). -> OUT:
units.json (every candidate's class and gain, the units taken), renders.npz (the units' audio).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
import sys

REFERENCE_DBU = 9.0                 # the level rule's reference: a free choice the data do not determine
MAX_INPUT_PEAK = 1.0                # the top of the range a capture was trained on
DI_CAP = 3                          # units a DI may play in the batch
TRIES = 9                           # candidates per capture
AMPS = ("pr12", "sw50r", "ac20")
SR = 48000
TRIM_S = 0.25                       # the sections' lead (`pretrain_set.TRIM_S`), left out of the class measure


def level_gain_db(level_dbu, peak):
    """The level rule: 9 − the stored level, 0 dB where none is stored, and the input's peak never past 1.0.
    peak: the levelled DI's. -> (gain in dB, held)."""
    import math

    want = 0.0 if level_dbu is None else REFERENCE_DBU - level_dbu
    most = -20 * math.log10(peak / MAX_INPUT_PEAK)
    return (most, True) if want > most else (want, False)


def seeded(xs, seed):
    xs = sorted(xs)
    random.Random(seed).shuffle(xs)
    return xs


def amps_balanced(captures, seed, amps=AMPS):
    """L1b: one forced amp per capture, balanced and seeded. -> {capture: amp}."""
    order = seeded(captures, f"{seed}|amps")
    return {c: amps[j % len(amps)] for j, c in enumerate(order)}


def walk(captures, players, class_of, seed, amps=AMPS, cap=DI_CAP, tries=TRIES, after=None, amp_of=None, prefer=None):
    """The DI walk. Captures run in a seeded order, each with a seeded amp order and first player; its `tries` candidates
    take the players in turn, items cycling within a player, skipping a DI at the cap or already this capture's. Each amp
    takes the next candidate giving crunch if there is one, otherwise the next giving clean; other classes play nothing.
    class_of(capture, item) -> class. players: {player: [item]}. `after(capture, {amp: item})` runs after each capture.
    `amp_of`, {capture: amp}: that capture plays that amp alone (L1b). `prefer`, {capture: "clean" | "crunch"}: that capture
    takes that class first, then the other (L1c: the capture's own tag).
    -> ({capture: {amp: item}}, {capture: [item]})."""
    order = {p: seeded(v, f"{seed}|{p}") for p, v in players.items()}
    pos, used, taken, tried = {p: 0 for p in order}, {}, {}, {}
    names = sorted(order)

    def nxt(p, own):
        for _ in range(len(order[p])):                 # one lap at most
            it = order[p][pos[p] % len(order[p])]
            pos[p] += 1
            if used.get(it, 0) < cap and it not in own:
                return it
        return None

    for c in seeded(captures, f"{seed}|captures"):
        rng = random.Random(f"{seed}|{c}")
        amp_order = list(amps)
        rng.shuffle(amp_order)
        if amp_of:
            amp_order = [amp_of[c]]
        start = rng.randrange(len(names))
        turn, own, dry = names[start:] + names[:start], [], set()
        while len(own) < tries and len(dry) < len(turn):
            for p in turn:
                if len(own) == tries:
                    break
                it = nxt(p, own)
                if it is None:
                    dry.add(p)
                else:
                    own.append(it)
        tried[c] = own
        by = {k: [it for it in own if class_of(c, it) == k] for k in ("crunch", "clean")}
        first = (prefer or {}).get(c, "crunch")
        if first not in by:
            raise SystemExit(f"{c}: no class {first!r} to take first")
        second = "clean" if first == "crunch" else "crunch"
        taken[c] = {}
        for amp in amp_order:
            pick = by[first].pop(0) if by[first] else by[second].pop(0) if by[second] else None
            if pick is not None:
                taken[c][amp] = pick
                used[pick] = used.get(pick, 0) + 1
        if after:
            after(c, taken[c])
    return taken, tried


def sha256_file(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def checked(c):
    """A plan row's path, once the file on disk is the one the manifest names. c: {path, sha256}."""
    if sha256_file(c["path"]) != c["sha256"]:
        raise SystemExit(f"{c['path']}: not the manifest's file")
    return c["path"]


def worker(plan_path, out_dir):
    """Every capture's candidates rendered and classed; the walk; the units' audio kept."""
    import numpy as np
    import torch

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    sys.path.insert(0, str(pathlib.Path.home() / "ndsp-presets/references/datasets-set3/_tools"))
    import classify as C
    import gainmeasure as GM
    from nam_load import load

    spec = json.loads(pathlib.Path(plan_path).read_text())
    if spec.get("threads"):                             # L1c: beside the plugin's render shards
        torch.set_num_threads(int(spec["threads"]))
    dis = dict(np.load(spec["dis"]))
    keep = int(TRIM_S * SR)
    done, audio = {}, {}

    def play(m, level, item):
        d = dis[item]
        gain, held = level_gain_db(level, float(np.abs(d).max()))
        with torch.no_grad():
            y = m(torch.tensor(d * 10 ** (gain / 20), dtype=torch.float32), pad_start=True).numpy().ravel()
        gm = GM.measures(np.asarray(y[keep:], np.float64), np.asarray(d[keep:], np.float64), SR)
        return y, {"gain_db": gain, "held": held, "class": C.classify(gm)[0] if gm else None,
                   "split": C.classify(gm)[3] if gm else None, "gain_measures": gm}

    byname = {c["capture"]: c for c in spec["plan"]}
    models = {}

    def class_of(name, item):
        if (name, item) not in done:
            if name not in models:
                models.clear()                          # one capture in memory at a time
                models[name] = load(checked(byname[name]))[0]
            audio[(name, item)], done[(name, item)] = play(models[name], byname[name]["level_dbu"], item)
        return done[(name, item)]["class"]

    kept = {}

    def keep_units(name, amps):                         # the units' audio stays, the other candidates' goes
        for amp, item in amps.items():
            kept[f"{name}|{amp}"] = audio[(name, item)].astype(np.float32)
        for k in [k for k in audio if k[0] == name]:
            del audio[k]

    taken, tried = walk(sorted(byname), spec["players"], class_of, spec["seed"], after=keep_units, amp_of=spec.get("amp_of"),
                        prefer=spec.get("prefer"))
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / "renders.npz", **kept)
    (out / "units.json").write_text(json.dumps({
        "seed": spec["seed"], "taken": taken, "tried": tried,
        "candidates": {f"{a}|{b}": r for (a, b), r in done.items()}}, indent=1) + "\n")
    print(f"CAPTURE-UNITS DONE: {sum(len(v) for v in taken.values())} units from {len(taken)} captures")


if __name__ == "__main__":
    worker(sys.argv[1], sys.argv[2])
