"""The note-versions read: at zero renders, do Basic Pitch's extra notes move the rebuilt guitar away from the real DI,
and does playing each note at its detected loudness bring it back? (note-rebuild-plan 12m; ledger `note-rebuild`
`phase_nr_1_redo_calib_amend`, then `phase_nr_1_redo_versions`.)

Versions, each built as `tr-di` is built (`note_rebuild.rebuild_redo`, finished by `song_bank.measure` as `calibrate`
finishes its development windows; `ring-soft` deciding, `ring-on` beside):

| Version | Notes | Levels |
|---|---|---|
| `nv-true` | the true notes | as today |
| `nv-asis` | Basic Pitch's notes after the clean-up | as today |
| `nv-hand` | Basic Pitch's notes that pair with a true note (`hand_notes`); nothing added | as today |
| `nv-loud` | Basic Pitch's notes, all of them | each at its detected loudness, gamma 1 |
| beside: `nv-loud2`, `nv-hand-loud` | the stronger setting (gamma 2); the hand-cleaned notes at gamma 1 | |

The distance is `floored_logmel` (each side floored 60 dB under its own loudest bin; `note_rebuild.logmel_distance`
stays as it is). It must first pass its own instrument check, `ghost_ladder`. The three numbers per set: C =
`nv-asis` - `nv-hand` (the extras' cost), G = `nv-loud` - `nv-hand` (what loudness leaves), E = `nv-hand` - `nv-true`
(the other gap); `set_reading`, `chord_guard`, `nv_code` and `recommendation` declare the rest.

The pure parts are tested in tests/test_note_versions.py on the light CI runner (no numpy).
"""

from __future__ import annotations

import math

from learn import note_rebuild as NR

VERSIONS = ("nv-true", "nv-asis", "nv-hand", "nv-loud", "nv-loud2", "nv-hand-loud")
DECIDING_RING, BESIDE_RING = "ring-soft", "ring-on"
BIN_FLOOR_DB = 60.0                      # each side floored this far under its own loudest bin (chosen after the
                                         # review's look at six windows; `ghost_ladder` is its declared test)
PLAY_FLOOR_DB = 40.0                     # J0's rule for which frames count (as `logmel_distance`)
GHOST_INTERVAL = 12                      # the instrument check's ghost: an octave above every true note
GHOST_STEPS_DB = (0.0, -6.0, -12.0, -20.0)
NEAR_MEAN, NEAR_HI, SHORT_LO = 0.25, 0.50, 0.50   # "near": G mean <= C/4 and G hi <= C/2; "short": G lo > C/2
GUARD = 0.05                             # chord and soft-note recall may fall at most this much against nv-asis
SETS = ("lists", "real", "goat")
CODES = ("NV-loud", "NV-short", "NV-none", "NV-undecided")
RECOMMENDATION = {
    "NV-loud": "adopt loudness at its gamma (already the user's decision)",
    "NV-short": "design one clean-up rule under its own declaration, fitted on fresh made-up lists; if it fails its "
                "grading, the row runs with the listening page as the guard, or the work stops; there is no second "
                "rule",
    "NV-none": "run as is, with the listening page as the guard",
    "NV-undecided": "if the lists read near at either gamma, the chord guard holds and GOAT is not decided worse: adopt "
                    "that gamma (the lists carry the read); otherwise run as is, with the listening page as the guard",
}
OTHER_GAP = "report it and go on: time, length and bend are not this amendment's subject; ring-kept and the page cover them"


# --- the distance (numpy) ----------------------------------------------------------------------------------------------

def floored_logmel(a, b, rate=NR.SR, floor_db=PLAY_FLOOR_DB, bin_floor_db=BIN_FLOOR_DB):
    """`note_rebuild.logmel_distance` with one change: each side's log-mel is floored `bin_floor_db` under its own
    loudest bin before the difference. `a`: the DI. dB, lower is closer."""
    import numpy as np

    from analysis import aligned as A

    k = min(len(a), len(b))
    A1, _ = A._logmel(a[:k], 2048, rate)
    B1, _ = A._logmel(b[:k], 2048, rate)
    fa = A._frame_db(a[:k], 2048)
    m = min(len(A1), len(B1), len(fa))
    play = fa[:m] >= fa[:m].max() - floor_db
    if play.sum() < 1:
        return float("nan")
    A1, B1 = A1[:m][play], B1[:m][play]
    A1, B1 = np.maximum(A1, A1.max() - bin_floor_db), np.maximum(B1, B1.max() - bin_floor_db)
    return float(np.mean(np.abs((A1 - A1.mean()) - (B1 - B1.mean()))))


# --- the instrument check ---------------------------------------------------------------------------------------------

def ghost_notes(notes, interval=GHOST_INTERVAL):
    """(Pure.) A made-up ghost for every true note: `interval` semitones above, same onset and length, no bend."""
    return [dict(n, pitch=n["pitch"] + interval, bends=[]) for n in notes]


def ladder_passes(base, steps):
    """(Pure.) The instrument check on one window: the distance goes down at every step (0 dB to -6, -12, -20) and the
    -20 dB version is not below the plain true-notes rebuild. steps: distances in GHOST_STEPS_DB order."""
    return all(x > y for x, y in zip(steps, steps[1:])) and steps[-1] >= base


def ghost_ladder(di, notes, bank, finish, ring=DECIDING_RING, rate=NR.SR):
    """One window's ladder: the true-notes rebuild, and the ghosts built as their own track by the same synthesis,
    scaled as the rebuild's plain synthesis was, added at each step. -> {base, steps, passes}."""
    import numpy as np

    n = len(di)
    base, _ = NR.rebuild_redo("tr-di", notes, n, bank, di, ring, finish=finish)
    pad = n + int(round(NR.END_PAD_S * rate))
    G, grep = NR.synthesise_redo(ghost_notes(notes), pad, bank, 0.0, ring, (), 0.0, None, rate)
    P, _ = NR.synthesise_redo(notes, pad, bank, 0.0, ring, (), 0.0, None, rate)
    k = float(np.sqrt(np.mean(base ** 2)) / (np.sqrt(np.mean(P[:n] ** 2)) + 1e-12))
    b = floored_logmel(di, base, rate)
    steps = [floored_logmel(di, base + 10 ** (db / 20) * k * G[:n], rate) for db in GHOST_STEPS_DB]
    return {"base": b, "steps": steps, "passes": ladder_passes(b, steps), "ghosts": grep["notes"],
            "ghosts_played": grep["played"]}    # ghosts above the bank's range are not played (recorded)


def ladder_outcome(lists, real):
    """(Pure.) The instrument check's outcome: any list failing stops the work (to the user); every list passing and a
    real window failing makes the real set reported only. lists, real: {window: passes}. -> (go, real_reported_only)."""
    if not lists or not all(lists.values()):
        return False, None
    return True, not all(real.values())


# --- the versions (pure) ------------------------------------------------------------------------------------------------

def hand_pairs(est, truth, onset_s=0.050):
    """(Pure.) The one-to-one pairs of `match_notes` (same pitch, onsets within `onset_s`, closest first). -> [(truth
    index, est index)]."""
    pairs = sorted((abs(r["on"] - e["on"]), i, j) for i, r in enumerate(truth) for j, e in enumerate(est)
                   if r["pitch"] == e["pitch"] and abs(r["on"] - e["on"]) <= onset_s)
    ui, uj, out = set(), set(), []
    for _, i, j in pairs:
        if i not in ui and j not in uj:
            ui.add(i)
            uj.add(j)
            out.append((i, j))
    return sorted(out)


def hand_notes(est, truth):
    """(Pure.) `nv-hand`: Basic Pitch's notes that pair with a true note; unpaired notes dropped, nothing added, each
    kept note as Basic Pitch gave it (time, length, bend, amplitude)."""
    keep = {j for _, j in hand_pairs(est, truth)}
    return [dict(e) for j, e in enumerate(est) if j in keep]


def version_notes(true_notes, est):
    """(Pure.) Each version's notes and loudness: {version: (notes, gamma or None)}."""
    hand = hand_notes(est, true_notes)
    return {"nv-true": (true_notes, None), "nv-asis": (est, None), "nv-hand": (hand, None),
            "nv-loud": (est, NR.LOUD_GAMMA[0]), "nv-loud2": (est, NR.LOUD_GAMMA[1]),
            "nv-hand-loud": (hand, NR.LOUD_GAMMA[0])}


ROUND_TRIP = ("nv-asis", "nv-loud", "nv-loud2")   # Basic Pitch again on these (the chord and soft-note guard)


def build_versions(di, true_notes, est, bank, finish, rings=(DECIDING_RING, BESIDE_RING), which=VERSIONS,
                   keep=ROUND_TRIP):
    """Every version's dry guitar and its distance to the DI, for each ring variant, with the beside figures
    (envelope correlation; energy above 2 kHz less the DI's). true_notes may be None (GOAT: no usable truth; only
    nv-asis, nv-loud, nv-loud2). -> ({ring: {version: distance}}, {ring: {version: beside}}, {version: audio} for
    `keep` on the deciding ring)."""
    import numpy as np

    d, side, audio = {}, {}, {}
    vn = version_notes(true_notes or [], est)
    for ring in rings:
        d[ring], side[ring] = {}, {}
        for v, (notes, gamma) in vn.items():
            if v not in which or (true_notes is None and v in ("nv-true", "nv-hand", "nv-hand-loud")):
                continue
            y, _ = NR.rebuild_redo("tr-di", notes, len(di), bank, di, ring, finish=finish, loud=gamma)
            d[ring][v] = floored_logmel(di, y)
            side[ring][v] = {"env_corr": NR.envelope_corr(np.asarray(di, np.float64), y),
                             "above2k_less_di": NR.share_above(y) - NR.share_above(np.asarray(di, np.float64))}
            if ring == rings[0] and v in keep:
                audio[v] = y
    return d, side, audio


def differences(d):
    """(Pure.) One window's three numbers (and nv-loud2's, nv-hand-loud's beside) from its distances {version: dB}."""
    def diff(a, b):
        return d[a] - d[b] if a in d and b in d else None
    return {"C": diff("nv-asis", "nv-hand"), "G": diff("nv-loud", "nv-hand"), "G2": diff("nv-loud2", "nv-hand"),
            "E": diff("nv-hand", "nv-true"), "loud_less_asis": diff("nv-loud", "nv-asis"),
            "loud2_less_asis": diff("nv-loud2", "nv-asis"), "hand_loud_less_hand": diff("nv-hand-loud", "nv-hand")}


def t90(df):
    """(Pure.) The two-sided 90% t quantile (`pipeline_fix.t95`, as the project's other 90% intervals)."""
    from learn import pipeline_fix as P

    return P.t95(df)


def set_numbers(rows, field):
    """(Pure.) A set's number: the mean over clusters of each cluster's mean, with its 90% t interval (clusters - 1
    degrees of freedom). rows: [(cluster, {field: value})]. -> {mean, lo90, hi90, clusters} or None."""
    by = {}
    for c, r in rows:
        v = r.get(field)
        if v is not None and math.isfinite(v):
            by.setdefault(c, []).append(v)
    means = [sum(v) / len(v) for v in by.values()]
    n = len(means)
    if n < 2:
        return {"mean": means[0] if means else None, "lo90": None, "hi90": None, "clusters": n}
    m = sum(means) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in means) / (n - 1))
    h = t90(n - 1) * sd / math.sqrt(n)
    return {"mean": m, "lo90": m - h, "hi90": m + h, "clusters": n}


def clear_of_zero(iv):
    return bool(iv) and iv.get("lo90") is not None and (iv["lo90"] > 0 or iv["hi90"] < 0)


def set_reading(C, G):
    """(Pure.) "Lands near", declared: "cost not shown" when C's interval is not clear above zero (it reaches zero, or
    lies below it: extras that bring the rebuild closer show no cost; never a pass, never "short"); "near" when C is
    clear above zero, G's mean at most a quarter of C's mean and G's upper end at most half of C's mean; "short" when C
    is clear above zero and G's lower end above half of C's mean; else "undecided"."""
    if not C or C.get("lo90") is None or not C["lo90"] > 0:
        return "cost not shown"
    if not G or G.get("lo90") is None:
        return "undecided"
    c = C["mean"]
    if G["mean"] <= NEAR_MEAN * c and G["hi90"] <= NEAR_HI * c:
        return "near"
    if G["lo90"] > SHORT_LO * c:
        return "short"
    return "undecided"


def recall_of(found, wanted):
    """(Pure.) The share of `wanted` (indices) among `found` (a set), or None."""
    return sum(i in found for i in wanted) / len(wanted) if wanted else None


def chord_guard(rows):
    """(Pure.) The chord and soft-note guard over windows: pooled recall of truth chord notes (groups of 3 or more,
    windows with 5 or more such notes) and of soft notes in the round trip on `nv-loud`, each no more than GUARD under
    `nv-asis`'s. rows: [{chord: (found on asis, found on loud, total), soft: (asis, loud, total)}]. -> {holds, ...}."""
    out = {}
    for key in ("chord", "soft"):
        a = sum(r[key][0] for r in rows if r.get(key))
        b = sum(r[key][1] for r in rows if r.get(key))
        n = sum(r[key][2] for r in rows if r.get(key))
        out[key] = {"asis": a / n if n else None, "loud": b / n if n else None, "notes": n,
                    "holds": n == 0 or (b / n) >= (a / n) - GUARD}
    out["holds"] = out["chord"]["holds"] and out["soft"]["holds"]
    return out


def chord_indices(true_notes, size=3, min_notes=5):
    """(Pure.) The true notes in onset groups of `size` or more, on windows with `min_notes` such notes (as
    `chords-kept` defines them)."""
    idx = [k for g in NR.onset_groups(true_notes) if len(g) >= size for k in g]
    return sorted(idx) if len(idx) >= min_notes else []


def soft_indices(est, true_notes, gamma, soft_db=NR.SOFT_DB):
    """(Pure.) The true notes whose paired Basic Pitch note loudness turns down by more than 3 dB at `gamma`."""
    down = NR.note_turndown_db(est, gamma)
    return sorted(i for i, j in hand_pairs(est, true_notes) if down[j] < soft_db)


def turned_down_share(est, true_notes, gamma, soft_db=NR.SOFT_DB):
    """(Pure.) The share of truth-paired Basic Pitch notes turned down by more than 3 dB at `gamma`."""
    soft, paired = turned_down_counts(est, true_notes, gamma, soft_db)
    return soft / paired if paired else None


def turned_down_counts(est, true_notes, gamma, soft_db=NR.SOFT_DB):
    """(Pure.) (soft notes, truth-paired notes) at `gamma`, for the share pooled over windows."""
    return len(soft_indices(est, true_notes, gamma, soft_db)), len(hand_pairs(est, true_notes))


def pooled_share(counts):
    """(Pure.) A share pooled over windows from [(part, whole)]; None with no whole."""
    a, b = sum(x for x, _ in counts), sum(y for _, y in counts)
    return a / b if b else None


def found_true(round_trip, true_notes, onset_s=0.050):
    """(Pure.) The true notes found in a round trip's notes (`hand_pairs`). -> set of truth indices."""
    return {i for i, _ in hand_pairs(round_trip, true_notes, onset_s)}


def goat_not_worse(iv):
    """(Pure.) On GOAT, `nv-loud` is not decided worse than `nv-asis`: its interval is not wholly above zero."""
    return not (iv and iv.get("lo90") is not None and iv["lo90"] > 0)


# --- the code and the recommendation (pure) ----------------------------------------------------------------------------

def nv_code(read):
    """(Pure.) The outcome, the first that holds. read: {gamma: {"lists": reading, "real": reading or "reported only",
    "goat_ok": bool, "guard": bool}} for both LOUD_GAMMA values. -> {code, gamma}.
    - NV-loud: near on the lists; near, cost not shown or reported only on the real DIs; GOAT not decided worse; the
      chord guard holds; gamma 1 if it qualifies, else gamma 2.
    - NV-short: short on either set at both gamma values.
    - NV-none: cost not shown on the made-up lists.
    - NV-undecided: the rest."""
    g1, g2 = NR.LOUD_GAMMA
    for g in (g1, g2):
        r = read[g]
        if (r["lists"] == "near" and r["real"] in ("near", "cost not shown", "reported only") and r["goat_ok"]
                and r["guard"]):
            return {"code": "NV-loud", "gamma": g}
    if all("short" in (read[g]["lists"], read[g]["real"]) for g in (g1, g2)):
        return {"code": "NV-short", "gamma": None}
    if read[g1]["lists"] == "cost not shown":
        return {"code": "NV-none", "gamma": None}
    return {"code": "NV-undecided", "gamma": None}


def other_gap(C, E):
    """(Pure.) The `other-gap` flag on the real DIs: E clear of zero and larger than C (the extras are not the main
    gap)."""
    return bool(E) and E.get("lo90") is not None and E["lo90"] > 0 and (not C or C.get("mean") is None
                                                                       or E["mean"] > C["mean"])


def summarise_read(windows, real_reported_only):
    """(Pure.) The read from its per-window records, once. windows: [{set ("lists" | "real" | "goat"), cluster, d: {ring:
    {version: distance}}, guard: {gamma: {chord: (asis, loud, n), soft: (asis, loud, n)}}}]; `real_reported_only`: the
    instrument check failed a real window. -> {numbers, readings, guard, code, other_gap, recommendation}."""
    g1, g2 = NR.LOUD_GAMMA
    numbers = {}
    for ring in (DECIDING_RING, BESIDE_RING):
        numbers[ring] = {}
        for st in SETS:
            rows = [(w["cluster"], differences(w["d"][ring])) for w in windows if w["set"] == st and ring in w["d"]]
            numbers[ring][st] = {f: set_numbers(rows, f) for f in ("C", "G", "G2", "E", "loud_less_asis",
                                                                    "loud2_less_asis", "hand_loud_less_hand")}
    n = numbers[DECIDING_RING]
    sets = ("lists",) if real_reported_only else ("lists", "real")     # a reported-only set enters no reading
    guard = {g: chord_guard([w["guard"][g] for w in windows if w["set"] in sets and g in w.get("guard", {})])
             for g in (g1, g2)}
    read = {}
    for g, gf, ga in ((g1, "G", "loud_less_asis"), (g2, "G2", "loud2_less_asis")):
        read[g] = {"lists": set_reading(n["lists"]["C"], n["lists"][gf]),
                   "real": "reported only" if real_reported_only else set_reading(n["real"]["C"], n["real"][gf]),
                   "goat_ok": goat_not_worse(n["goat"][ga]), "guard": guard[g]["holds"]}
    code = nv_code(read)
    return {"numbers": numbers, "readings": read, "guard": guard, "code": code,
            "other_gap": None if real_reported_only else other_gap(n["real"]["C"], n["real"]["E"]),
            "recommendation": recommendation(code, read)}


def recommendation(code, read):
    """(Pure.) The declared recommendation for a code; for NV-undecided, the gamma it would adopt, or None."""
    adopt = None
    if code["code"] == "NV-loud":
        adopt = code["gamma"]
    elif code["code"] == "NV-undecided":
        adopt = next((g for g in NR.LOUD_GAMMA if read[g]["lists"] == "near" and read[g]["guard"]
                      and read[g]["goat_ok"]), None)
    return {"text": RECOMMENDATION[code["code"]], "adopt_gamma": adopt}
