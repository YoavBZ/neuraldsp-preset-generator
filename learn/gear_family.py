"""The family check (`docs/family-class-checks-plan.md` part A; ledger `pipeline-fix` `phase_family_check`): does a
capture's gear family, read from its pack's name alone, place its label nearer than Cen does? Direction 2's step 1 of
the 2026-11-19 strategic review. Zero renders, CPU seconds.

    .venv/bin/python -m learn.gear_family tags     # names only -> PF/family/tags.json (its content hash is declared)
    .venv/bin/python -m learn.gear_family read     # the read and its cell -> PF/family/report.json

**The rule** (`FAMILY_RULE`): the first row whose token is in the lower-cased pack slug names the family; else "none".
**The read:** per record r (plugin amp a, class k, creator c, family f), every record of c is left out. Cen_-c is the
ladder's Cen rebuilt without c (`centre_of`, every training showing as the stored Cen counts them; with nobody left out
it must equal `ladder/centres.json` exactly). O is the mean over f's other-creator records on amp a (both classes) of
label less Cen_-c of that record's class, head by head; Fam = Cen_-c(a, k) + w O, w = n / (n + 2), clipped to [0, 1].
D_g = d_g(Fam) - d_g(Cen_-c): the RMS unit-space gap to r's own label over group g's continuous heads that sound in
both and are labelled. T_g is D_g's mean over creators with its 90% t interval (creators, and families beside).

**The shuffle** (`shuffle_tags`, `joint_p`): the 41 packs' tags (the 13 "none" too) permuted over the packs, seeded;
the record set fixed to the real read's usable records; a record whose shuffled family is "none" or has no
other-creator record on its amp has Fam = Cen_-c (D = 0). Joint statistic: min over drive, tone, cab of
(T_g - its shuffles' mean) / its shuffles' sd; p is the share of shuffles whose own statistic is at or below the real.

`GF_TABLE` (the plan's D2_TABLE: GF-go, GF-stop, GF-thin) and its guard are declared here and tested in
`tests/test_gear_family.py` before any label is read by family.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time

PLAN = "docs/family-class-checks-plan.md"
PHASE = "phase_family_check"                  # ledger pipeline-fix
OUT = "family"                                # PF/family/
FAMILY_RULE = (                               # (family, tokens), the first match wins; fixed before any label is read
    ("tweed", ("tweed", "5e3", "5d3")),
    ("fender", ("fender", "princeton", "vibroverb", "bandmaster", "twin-reverb")),
    ("vox", ("vox", "ac30", "ac15")),
    ("marshall", ("marshall", "jtm", "jmp", "1987x", "2555")),
    ("hiwatt", ("hiwatt",)),
    ("orange", ("orange",)),
    ("two-rock", ("two-rock", "tworock")))
NONE = "none"
FAMILIES = tuple(f for f, _ in FAMILY_RULE)
AT_PLANNING = {                               # (packs, creators, captures, records) per family; the tags refuse on another
    "fender": (8, 8, 12, 25), "marshall": (6, 5, 9, 18), "vox": (5, 5, 6, 9), "hiwatt": (3, 3, 4, 12),
    "tweed": (2, 2, 4, 11), "two-rock": (2, 2, 3, 9), "orange": (2, 2, 3, 6), "none": (13, 11, 19, 43)}
TOTALS = {"records": 133, "captures": 60, "packs": 41, "creators": 27}
TAGS_SHA256 = "2a64b6a189c80e4cf2361037bd36cafdbac2385d473ac2023a5135fc5a64931f"  # the tags' content hash, declared with the ledger phase
ODD_PACK = "prototype-amp-hiwatt-sovtek-sound-city"   # the review's rule oddity: a prototype read beside without it
SHRINK = 2                                    # w = n / (n + SHRINK)
SHUFFLES, SHUFFLE_SEED = 2000, 20261206
P_GO = 0.05
STOP_FRACTION = 0.10                          # GF-stop: each interval rules out a gain beyond this share of Cen's distance
DECIDING = ("drive", "tone", "cab")
GROUPS = ("drive", "tone", "cab", "eq", "pedals")

GF_TABLE = (                    # ((nearer, ruled_out, p_small) combinations, code, next): each of the 8 once
    (((True, True, True), (True, False, True)), "GF-go",
     "to the user, with the render read's declaration (family centre against Cen through the true DIs, about 530 "
     "renders, about 8 min); nothing renders before the user's yes"),
    (((True, True, False), (False, True, False)), "GF-stop",
     "the badge does not predict the label: Direction 2 ends"),
    (((False, False, True), (False, False, False), (False, True, True), (True, False, False)), "GF-thin",
     "underpowered, not failed. The write-up gives each group's interval, the share of label variance the families "
     "hold and how many captures a family would need. To the user: the render read (about 8 min, not run without a "
     "yes), fetch more named captures per family, or park"))


# --- the table (pure) ------------------------------------------------------------------------------------------------------

def table_guard():
    """Refuse unless GF_TABLE holds each (nearer, ruled_out, p_small) combination once, with the three codes."""
    for a in (True, False):
        for b in (True, False):
            for c in (True, False):
                if sum((a, b, c) in combos for combos, _, _ in GF_TABLE) != 1:
                    raise SystemExit(f"GF_TABLE holds {(a, b, c)} not once")
    if [c for _, c, _ in GF_TABLE] != ["GF-go", "GF-stop", "GF-thin"]:
        raise SystemExit("GF_TABLE's codes are not the three declared")
    if not (0 < P_GO < 1 and 0 < STOP_FRACTION < 1 and SHRINK > 0):
        raise SystemExit("the family check's constants are out of range")


def family_of(pack):
    """(Pure.) FAMILY_RULE on the lower-cased pack slug."""
    p = (pack or "").lower()
    for fam, toks in FAMILY_RULE:
        if any(t in p for t in toks):
            return fam
    return NONE


def shrink(n, k=SHRINK):
    return n / (n + k) if n > 0 else 0.0


def cluster_t(values_by_cluster):
    """(Pure.) The mean of cluster means with its 90% t interval (clusters - 1 df). -> {mean, lo90, hi90, clusters}."""
    from learn import pretrain_set as PS

    by = {k: v for k, v in values_by_cluster.items() if v}
    if not by:
        return {"mean": None, "lo90": None, "hi90": None, "clusters": 0}
    m, lo, hi, n = PS.band_t_interval(by)
    fin = lambda x: x if math.isfinite(x) else None   # noqa: E731
    return {"mean": m, "lo90": fin(lo), "hi90": fin(hi), "clusters": n}


def wider(a, b):
    """(Pure.) Of two intervals on the same mean, the one with the lower lower end (None ends count as unbounded)."""
    lo = lambda r: -math.inf if r.get("lo90") is None else r["lo90"]   # noqa: E731
    return a if lo(a) <= lo(b) else b


def readings(t_rows, stop_rows, cen_dist, p):
    """(Pure.) GF_TABLE's three readings. t_rows: {group: creator-clustered T}; stop_rows: {group: the wider of the
    creator- and family-clustered T}; cen_dist: {group: Cen's mean distance}; p: the joint shuffle p.
    nearer: on drive, tone or cab the creator interval is wholly below 0; ruled_out: on each of the three the wider
    interval's lower end is above -STOP_FRACTION x Cen's distance; p_small: p < P_GO."""
    nearer = any((t_rows.get(g) or {}).get("hi90") is not None and t_rows[g]["hi90"] < 0 for g in DECIDING)
    ruled = all((stop_rows.get(g) or {}).get("lo90") is not None and cen_dist.get(g) is not None
                and stop_rows[g]["lo90"] > -STOP_FRACTION * cen_dist[g] for g in DECIDING)
    return nearer, ruled, p is not None and p < P_GO


def gf_cell(nearer, ruled, p_small):
    table_guard()
    hit = [(c, t) for combos, c, t in GF_TABLE if (nearer, ruled, p_small) in combos]
    if len(hit) != 1:
        raise SystemExit(f"GF_TABLE has {len(hit)} rows for {(nearer, ruled, p_small)}")
    return hit[0]


def joint_p(real, shuffled, groups=DECIDING):
    """(Pure.) real: {group: T}; shuffled: [{group: T}]. Each group standardised by its shuffles' mean and sd; the
    statistic is the minimum over groups; p = share of shuffles whose own statistic is <= the real one. Groups with no
    real T, or no spread across shuffles, are left out. -> (p, real statistic, {group: (mean, sd)})."""
    norm = {}
    for g in groups:
        xs = [s[g] for s in shuffled if s.get(g) is not None]
        if real.get(g) is None or len(xs) < 2:
            continue
        m = sum(xs) / len(xs)
        sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
        if sd > 0:
            norm[g] = (m, sd)
    if not norm:
        return None, None, norm

    def stat(t):
        zs = [(t[g] - m) / sd for g, (m, sd) in norm.items() if t.get(g) is not None]
        return min(zs) if zs else math.inf

    r = stat(real)
    return sum(stat(s) <= r for s in shuffled) / len(shuffled), r, norm


def shuffle_tags(pack_tags, j, seed=SHUFFLE_SEED):
    """(Pure.) Shuffle j: the packs' tags (every pack, "none" included) permuted over the sorted packs."""
    packs = sorted(pack_tags)
    tags = [pack_tags[p] for p in packs]
    random.Random(f"{seed}:{j}").shuffle(tags)
    return dict(zip(packs, tags))


def icc(groups):
    """(Pure.) One-way ICC(1) of values grouped by family ({family: [values]}, groups of one included in the within
    term only through their n): the share of variance between families, floored at 0. None with under two families."""
    gs = [v for v in groups.values() if v]
    k, n = len(gs), sum(len(v) for v in gs)
    if k < 2 or n <= k:
        return None
    grand = sum(sum(v) for v in gs) / n
    ssb = sum(len(v) * (sum(v) / len(v) - grand) ** 2 for v in gs)
    ssw = sum((x - sum(v) / len(v)) ** 2 for v in gs for x in v)
    msb, msw = ssb / (k - 1), ssw / (n - k)
    n0 = (n - sum(len(v) ** 2 for v in gs) / n) / (k - 1)
    den = msb + (n0 - 1) * msw
    return max(0.0, (msb - msw) / den) if den > 0 else None


def expected_ratio(rho, n, k=SHRINK):
    """(Pure.) Expected squared distance of the shrunk family centre over Cen's, if a share rho of the residual variance
    sits between families and n other records feed the centre: (1-w)^2 rho + (1-rho) + w^2 (1-rho) / n."""
    w = shrink(n, k)
    return (1 - w) ** 2 * rho + (1 - rho) + (w * w * (1 - rho) / n if n else 0.0)


def captures_needed(rho, target=0.9, cap=1000):
    """(Pure.) The fewest other-creator records a family centre needs for its expected RMS distance to reach `target`
    times Cen's at share rho; None if no n up to `cap` does."""
    if rho is None:
        return None
    for n in range(1, cap + 1):
        if math.sqrt(expected_ratio(rho, n)) <= target:
            return n
    return None


def rms(a, b, heads):
    return math.sqrt(sum((a[h] - b[h]) ** 2 for h in heads) / len(heads)) if heads else None


def fam_centre(cen, offsets, w_fn=shrink):
    """(Pure.) cen: {head: unit value}; offsets: {head: [residuals]}. Fam = cen + w(n) x mean residual, clipped to [0,
    1], on the heads with any residual; the rest stay at cen."""
    out = dict(cen)
    for h, xs in offsets.items():
        if h in cen and xs:
            out[h] = min(1.0, max(0.0, cen[h] + w_fn(len(xs)) * sum(xs) / len(xs)))
    return out


def record_d(lab, cen, fam, group_of):
    """(Pure.) {group: (D_g, d_g(cen))} for one record: d_g(fam) - d_g(cen), over group g's heads sounding in all
    three (the label's labelled heads; a family centre sounds where its Cen does, a reader's answer where it does)."""
    out = {}
    for g in GROUPS:
        hs = sorted(h for h in lab if h in cen and h in fam and group_of(h) == g)
        if hs:
            out[g] = (rms(fam, lab, hs) - rms(cen, lab, hs), rms(cen, lab, hs))
    return out


# --- the data ----------------------------------------------------------------------------------------------------------------

def family_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


def sha_json(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def capture_records(st):
    """C3r's trusted capture records [(unit, amp)], sorted, with their unit records; refuses on another count."""
    recs = sorted((u, a) for (u, a) in st["sources"] if u.startswith("cap/"))
    units = {}
    for s in ("cap1", "n12"):
        units.update(st["units"][s])
    if len(recs) != TOTALS["records"] or any(u not in units for u, _ in recs):
        raise SystemExit(f"{len(recs)} trusted capture records, not {TOTALS['records']}, or one has no unit record")
    return recs, units


def tags_content(recs, units):
    """(Pure.) The tags: every record's pack, creator, capture and family, with the rule. Refuses unless the counts
    are the plan's (AT_PLANNING, TOTALS)."""
    rows = {f"{u}|{a}": {"pack": units[u]["pack"], "creator": units[u]["creator"], "capture": units[u]["capture"],
                         "family": family_of(units[u]["pack"])} for u, a in recs}
    for fam, want in AT_PLANNING.items():
        xs = [r for r in rows.values() if r["family"] == fam]
        got = (len({r["pack"] for r in xs}), len({r["creator"] for r in xs}), len({r["capture"] for r in xs}), len(xs))
        if got != want:
            raise SystemExit(f"family {fam}: (packs, creators, captures, records) {got}, not the plan's {want}")
    got = {"records": len(rows), "captures": len({r["capture"] for r in rows.values()}),
           "packs": len({r["pack"] for r in rows.values()}), "creators": len({r["creator"] for r in rows.values()})}
    if got != TOTALS:
        raise SystemExit(f"totals {got}, not {TOTALS}")
    by_pack = {}
    for r in rows.values():
        by_pack.setdefault(r["pack"], set()).add(r["creator"])
    if any(len(v) != 1 for v in by_pack.values()):
        raise SystemExit("a pack with more than one creator")
    return {"rule": [[f, list(t)] for f, t in FAMILY_RULE], "records": rows}


def cmd_tags(_args):
    """Names only (no label is read): the tags -> PF/family/tags.json, written once; refuses unless its content hash is
    the declared TAGS_SHA256."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    table_guard()
    P.require(PHASE)
    st = R.state()
    content = tags_content(*capture_records(st))
    sha = sha_json(content)
    if sha != TAGS_SHA256:
        raise SystemExit(f"the tags' content sha256 {sha} is not the declared {TAGS_SHA256}")
    path = family_dir() / "tags.json"
    if path.exists():
        raise SystemExit(f"{path} exists; never overwritten")
    P.save(path, dict(content, plan=PLAN, ledger=f"pipeline-fix {PHASE}", c3r_sha256=st["sha256"], content_sha256=sha,
                      time=time.strftime("%Y-%m-%d %H:%M:%S")))
    print(f"TAGS: {len(content['records'])} records, sha256 {sha} -> {path}")


def load_tags():
    path = family_dir() / "tags.json"
    if not path.exists():
        raise SystemExit("no tags.json: run `tags` first")
    d = json.loads(path.read_text())
    content = {"rule": d["rule"], "records": d["records"]}
    if sha_json(content) != TAGS_SHA256 or d.get("content_sha256") != TAGS_SHA256:
        raise SystemExit("tags.json's content is not the declared tags")
    return content["records"]


class Ctx:
    """The labels, the rebuilt centres and the stored fold answers (numpy)."""

    def __init__(self, st):
        import numpy as np

        from learn import full_controls_c3 as C3
        from learn import full_controls_c3r as R
        from learn import full_space as F
        from learn import local_objective as LO
        from learn import pipeline_fix as P
        from learn import preset_ladder as L

        self.np, self.F, self.LO, self.P, self.L, self.C3, self.R = np, F, LO, P, L, C3, R
        self.st = st
        self.ms, self.hold = P.A_menu_S(), R.answer_hold(st)
        self.keys_of, self.label_of = C3.keys_fn(st["sources"]), C3.label_fn(st["sources"])
        self.recs = L.training_records(st, None)
        self.cls_of = L.classes(st)
        self.creator_of = {}
        for s in ("cap1", "n12"):
            self.creator_of.update({u: p["creator"] for u, p in st["units"][s].items()})
        self._enc, self._cen = {}, {}

    def encoded(self, unit, amp):
        """A training record's label row under C3's training mask, with its knob values (labelled, sounding)."""
        k = (unit, amp)
        if k not in self._enc:
            F, LO, C3 = self.F, self.LO, self.C3
            S = self.ms[amp][self.cls_of[unit]][1]
            lab = self.label_of({"unit": unit, "amp": amp})
            c, cm, s, sm, kk, km, _ = F.encode(LO.tdict(lab["settings"]), amp)
            hc, hs, hk = C3.head_masks(self.keys_of(unit, amp, S))
            row = (c, cm * hc, s, sm * hs, kk, km * hk)
            D = F.by_name()
            kv = {n: float(c[j]) for j, n in enumerate(F.CONT)
                  if row[1][j] > 0 and self.L.knob_group(D[n].module, D[n].key)}
            sw = {n: float(s[j]) > 0.5 for j, n in enumerate(F.SW) if row[3][j] > 0}
            mic = {n: int(kk[j]) for j, n in enumerate(F.CAT) if row[5][j] > 0}
            self._enc[k] = (row, kv, sw, mic)
        return self._enc[k]

    def centre(self, amp, cls, out_creator=None):
        """Cen over the training showings of (amp, class), less every record of `out_creator`: (settings, knob values,
        switches on, mics)."""
        k = (amp, cls, out_creator)
        if k not in self._cen:
            F, LO, P, L = self.F, self.LO, self.P, self.L
            sel, S = self.ms[amp][cls]
            s_enc = F.encode(dict(S), amp)
            s_mics = [int(v) if m else None for v, m in zip(s_enc[4], s_enc[5])]
            mine = [r for r in self.recs if r["amp"] == amp and self.cls_of[r["unit"]] == cls
                    and (out_creator is None or self.creator_of.get(r["unit"]) != out_creator)]
            rows = [self.encoded(r["unit"], amp)[0] for r in mine]
            cont, swp, mics = L.centre_of(rows, len(F.CONT), len(F.SW), len(F.CAT), s_mics)
            stg = F.answer_settings(amp, S, self.np.array(cont, self.np.float64), swp, mics)
            stg = P.hold_outside_space(stg, S, amp, self.hold) if self.hold is not None else \
                P.hold_outside_space(stg, S, amp)
            settings = LO.sdict(stg)
            sw = {n: (p is not None and p > 0.5) for n, p in zip(F.SW, swp)}
            mic = dict(zip(F.CAT, mics))
            self._cen[k] = ({"select": sel, "settings": settings}, L.knob_values(settings, amp), sw, mic)
        return self._cen[k]


def stored_cen_check(cx):
    """The rebuilt Cen with nobody left out equals ladder/centres.json's cen exactly, in all six cells."""
    stored = json.loads((cx.L.ladder_dir() / "centres.json").read_text())["centres"]["cen"]
    bad = [(a, k) for a in cx.P.AMPS3 for k in ("clean", "crunch") if cx.centre(a, k)[0] != stored[a][k]]
    if bad:
        raise SystemExit(f"the rebuilt Cen differs from ladder/centres.json in {bad}")


def offsets_for(cx, r, members, centre_of_cls, same_class=False):
    """{head: [residuals]} of the family's member records (other creators, same amp) against `centre_of_cls(class)`."""
    u, a = r
    out = {}
    for q in members:
        if same_class and cx.cls_of[q[0]] != cx.cls_of[u]:
            continue
        lab = cx.encoded(*q)[1]
        cen = centre_of_cls(cx.cls_of[q[0]])
        for h, v in lab.items():
            if h in cen:
                out.setdefault(h, []).append(v - cen[h])
    return out


def members_of(r, fam, tags_by_rec, creator_of, recs):
    u, a = r
    if fam == NONE:
        return []
    return [q for q in recs if q[1] == a and tags_by_rec[q] == fam and creator_of[q[0]] != creator_of[u]]


def t_rows(per_record, cluster_key):
    """{group: T} from per-record {group: (D, cen_d)} by `cluster_key(record)`."""
    out = {}
    for g in GROUPS:
        by = {}
        for r, d in per_record.items():
            if g in d:
                by.setdefault(cluster_key(r), []).append(d[g][0])
        out[g] = cluster_t(by)
    return out


def cen_distance(per_record, cluster_key):
    out = {}
    for g in GROUPS:
        by = {}
        for r, d in per_record.items():
            if g in d:
                by.setdefault(cluster_key(r), []).append(d[g][1])
        out[g] = cluster_t(by)["mean"]
    return out


def read_family(cx, recs, tags_by_rec, w_fn=shrink, same_class=False, only=None):
    """Per usable record {group: (D_g, d_g(Cen_-c))}, and the records left out (no family or n = 0)."""
    cr = cx.creator_of
    per, out_ = {}, []
    for r in recs:
        if only is not None and r not in only:
            continue
        mem = members_of(r, tags_by_rec[r], tags_by_rec, cr, recs)
        if not mem:
            out_.append(r)
            if only is not None:            # the shuffle's fixed record set: no family centre, D = 0
                cen = cx.centre(r[1], cx.cls_of[r[0]], cr[r[0]])[1]
                per[r] = {g: (0.0, dc) for g, (_, dc) in record_d(cx.encoded(*r)[1], cen, cen, cx.L.group_of).items()}
            continue
        c = cr[r[0]]
        cen = cx.centre(r[1], cx.cls_of[r[0]], c)[1]
        offs = offsets_for(cx, r, mem, lambda k, a=r[1], c=c: cx.centre(a, k, c)[1], same_class)
        fam = fam_centre(cen, offs, w_fn)
        per[r] = record_d(cx.encoded(*r)[1], cen, fam, cx.L.group_of)
    return per, out_


def summary(per, cx, tags_by_rec):
    creator = t_rows(per, lambda r: cx.creator_of[r[0]])
    family = t_rows(per, lambda r: tags_by_rec[r])
    return {"records": len(per), "creators": len({cx.creator_of[r[0]] for r in per}),
            "T_creator": creator, "T_family": family,
            "cen_distance": cen_distance(per, lambda r: cx.creator_of[r[0]])}


def switch_mic_shares(cx, recs, tags_by_rec, usable):
    """Beside: the share of labelled switches and mics where Cen_-c differs from the label, and where the family's
    majority (other creators, same amp, both classes; a tie to Cen_-c) differs."""
    cr = cx.creator_of
    n = dc = df = 0
    for r in usable:
        _, _, sw, mic = cx.encoded(*r)
        _, _, csw, cmic = cx.centre(r[1], cx.cls_of[r[0]], cr[r[0]])
        mem = members_of(r, tags_by_rec[r], tags_by_rec, cr, recs)
        for kind, lab, cen in (("sw", sw, csw), ("mic", mic, cmic)):
            for h, v in lab.items():
                votes = [cx.encoded(*q)[2 if kind == "sw" else 3].get(h) for q in mem]
                votes = [x for x in votes if x is not None]
                if votes:
                    from collections import Counter

                    cnt = Counter(votes)
                    top = max(cnt.values())
                    tied = [x for x, c in cnt.items() if c == top]
                    maj = cen[h] if cen[h] in tied else sorted(tied, key=str)[0]
                else:
                    maj = cen[h]
                n += 1
                dc += cen[h] != v
                df += maj != v
    return {"values": n, "cen_differs": dc / n if n else None, "family_majority_differs": df / n if n else None}


def variance_share(cx, recs, tags_by_rec):
    """Per group: the mean over heads of the families' ICC(1) of label residuals against Cen_-c (each record's own
    creator out), tagged records only; and the captures a family would need for a 10% RMS gain at that share."""
    out = {}
    res = {}
    for r in recs:
        if tags_by_rec[r] == NONE:
            continue
        lab = cx.encoded(*r)[1]
        cen = cx.centre(r[1], cx.cls_of[r[0]], cx.creator_of[r[0]])[1]
        for h, v in lab.items():
            if h in cen:
                res.setdefault((r[1], h), {}).setdefault(tags_by_rec[r], []).append(v - cen[h])
    for g in GROUPS:
        rs = [icc(v) for (a, h), v in res.items() if cx.L.group_of(h) == g]
        rs = [x for x in rs if x is not None]
        rho = sum(rs) / len(rs) if rs else None
        out[g] = {"heads": len(rs), "icc_mean": rho, "captures_for_10pct": captures_needed(rho),
                  "expected_rms_ratio_at_3": math.sqrt(expected_ratio(rho, 3)) if rho is not None else None}
    return out


def fold_wise(cx, recs, tags_by_rec):
    """The like-for-like row with the reader: the stored fold Cen (answers/cen.json) and a family centre that leaves
    out what the reader's fold models leave out (fold k and every record sharing an identity with a fold-k unit);
    the reader's clean-kind and rc-xl@-3 answers, both halves averaged. Per record {row: {group: (D_g, cen_d)}}."""
    L = cx.L
    ents = {e["unit"]: e for e in cx.st["entries"]}
    ans = {row: json.loads(L.answers_path(row).read_text())["answers"] for row in ("cen", "clean-kind", "rc-xl@-3")}
    read_units = cx.R.read_units(cx.st)
    parts = {(ru["unit"], ru["amp"]): ru for ru in read_units if ru["set"] in ("cap1", "n12")}
    if set(parts) != set(recs):
        raise SystemExit("the ladder's capture parts are not the 133 records")

    def stored(row, r):
        ru = parts[r]
        return ans[row][ru["set"]][f"{r[0]}|{r[1]}"]

    fold_cen = {}
    for ru in read_units:
        key = (ru["fold"], ru["amp"], ru["prt"]["cls"])
        s = ans["cen"][ru["set"]][f"{ru['unit']}|{ru['amp']}"][cx.P.ANY_HALF]["settings"]
        if key in fold_cen and fold_cen[key] != s:
            raise SystemExit(f"the stored fold Cen differs within {key}")
        fold_cen[key] = s
    out = {}
    for r in recs:
        if tags_by_rec[r] == NONE:
            continue
        k = ents[r[0]]["fold"]
        ban = set().union(*[e["ids"] for e in cx.st["entries"] if e["fold"] == k])
        mem = [q for q in recs if q[1] == r[1] and tags_by_rec[q] == tags_by_rec[r] and ents[q[0]]["fold"] != k
               and not (ents[q[0]]["ids"] & ban)]
        if not mem:
            continue
        lab = cx.encoded(*r)[1]

        def cen_of(cls, a=r[1], k=k):
            key = (k, a, cls)
            if key not in fold_cen:
                raise SystemExit(f"no stored fold Cen for {key}")
            return L.knob_values(fold_cen[key], a)

        cen = cen_of(cx.cls_of[r[0]])
        fam = fam_centre(cen, offsets_for(cx, r, mem, cen_of))
        rows = {"fam-fold": record_d(lab, cen, fam, L.group_of)}
        for row in ("clean-kind", "rc-xl@-3"):
            st_ = stored(row, r)
            per_h = [record_d(lab, cen, L.knob_values(st_[h]["settings"], r[1]), L.group_of) for h in ("A", "B")]
            rows[row] = {g: ((per_h[0][g][0] + per_h[1][g][0]) / 2, per_h[0][g][1])
                         for g in per_h[0] if g in per_h[1]}
        out[r] = rows
    return out


def cmd_read(_args):
    """The read (zero renders, CPU): the main row, the shuffle, the beside rows and GF_TABLE's cell -> report.json."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    table_guard()
    P.require(PHASE)
    path = family_dir() / "report.json"
    if path.exists():
        raise SystemExit(f"{path} exists; never overwritten")
    t0 = time.time()
    st = R.state()
    recs, units = capture_records(st)
    tags = load_tags()
    if set(tags) != {f"{u}|{a}" for u, a in recs}:
        raise SystemExit("tags.json's records are not C3r's trusted capture records")
    tags_by_rec = {r: tags[f"{r[0]}|{r[1]}"]["family"] for r in recs}
    pack_of = {r: tags[f"{r[0]}|{r[1]}"]["pack"] for r in recs}
    cx = Ctx(st)
    stored_cen_check(cx)
    cr = cx.creator_of

    per, left_out = read_family(cx, recs, tags_by_rec)
    main = summary(per, cx, tags_by_rec)
    stop_rows = {g: wider(main["T_creator"][g], main["T_family"][g]) for g in GROUPS}
    real_t = {g: main["T_creator"][g]["mean"] for g in DECIDING}

    usable = sorted(per)
    pack_tags = {}
    for r in recs:
        pack_tags[pack_of[r]] = tags_by_rec[r]
    shuffled = []
    for j in range(SHUFFLES):
        sh = shuffle_tags(pack_tags, j)
        tb = {r: sh[pack_of[r]] for r in recs}
        sp, _ = read_family(cx, recs, tb, only=set(usable))
        tr = t_rows(sp, lambda r: cr[r[0]])
        shuffled.append({g: tr[g]["mean"] for g in DECIDING})
        if j % 250 == 0:
            print(f"shuffle {j}/{SHUFFLES} ({time.time() - t0:.0f} s)", flush=True)
    p, stat, norm = joint_p(real_t, shuffled)
    nearer, ruled, p_small = readings(main["T_creator"], stop_rows, main["cen_distance"], p)
    code, nxt = gf_cell(nearer, ruled, p_small)

    beside = {}
    beside["plain mean (w = 1)"] = summary(read_family(cx, recs, tags_by_rec, w_fn=lambda n: 1.0)[0], cx, tags_by_rec)
    beside["same class only"] = summary(read_family(cx, recs, tags_by_rec, same_class=True)[0], cx, tags_by_rec)
    no_odd = {r: (NONE if pack_of[r].startswith(ODD_PACK) else f) for r, f in tags_by_rec.items()}
    beside["without the prototype pack"] = summary(read_family(cx, recs, no_odd)[0], cx, no_odd)
    lofo = {}
    for fam in FAMILIES:
        sub = {r: d for r, d in per.items() if tags_by_rec[r] != fam}
        lofo[fam] = {g: t_rows(sub, lambda r: cr[r[0]])[g] for g in DECIDING}
    beside["leave one family out (T_creator without each family's records)"] = {
        "by_family": lofo,
        "range": {g: [min(v[g]["mean"] for v in lofo.values() if v[g]["mean"] is not None),
                      max(v[g]["mean"] for v in lofo.values() if v[g]["mean"] is not None)] for g in DECIDING}}
    fw = fold_wise(cx, recs, tags_by_rec)
    fw_rows = {}
    for row in ("fam-fold", "clean-kind", "rc-xl@-3"):
        fw_rows[row] = t_rows({r: v[row] for r, v in fw.items()}, lambda r: cr[r[0]])
    for row in ("clean-kind", "rc-xl@-3"):
        paired = {}
        for r, v in fw.items():
            paired[r] = {g: (v["fam-fold"][g][0] - v[row][g][0], 0.0) for g in v["fam-fold"] if g in v[row]}
        fw_rows[f"fam-fold less {row} (paired)"] = t_rows(paired, lambda r: cr[r[0]])
    beside["fold-wise, like for like with the reader"] = {"records": len(fw), "rows": fw_rows}
    beside["switches and mics"] = switch_mic_shares(cx, recs, tags_by_rec, usable)
    beside["variance share and captures needed"] = variance_share(cx, recs, tags_by_rec)

    out = {"plan": PLAN, "ledger": f"pipeline-fix {PHASE}", "c3r_sha256": st["sha256"], "tags_sha256": TAGS_SHA256,
           "main": main, "stop_intervals (wider of creator and family)": stop_rows,
           "left_out": {"records": len(left_out), "no family": sum(tags_by_rec[r] == NONE for r in left_out),
                        "n = 0": sum(tags_by_rec[r] != NONE for r in left_out)},
           "shuffle": {"shuffles": SHUFFLES, "seed": SHUFFLE_SEED, "p": p, "real_statistic": stat,
                       "norm (mean, sd)": norm, "real_T": real_t},
           "readings": {"nearer": nearer, "ruled_out": ruled, "p_small": p_small},
           "outcome": {"code": code, "next": nxt}, "beside": beside,
           "seconds": round(time.time() - t0, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(path, out)
    print(f"FAMILY CHECK: {code} (nearer {nearer}, ruled out {ruled}, p {p}) -> {path}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.gear_family")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tags").set_defaults(fn=cmd_tags)
    sub.add_parser("read").set_defaults(fn=cmd_read)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
