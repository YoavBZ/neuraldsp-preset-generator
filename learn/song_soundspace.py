"""Arm B in sound space: the arms, training and evaluation (`docs/song-to-settings-soundspace-plan.md`).

Run order (MPS: one job at a time; renders: at most 3 processes machine-wide):

    $TORCH_PY        -m learn.song_soundspace mem-dry-run --fold 0              # B0's peak RSS (CPU, no training)
    .venv/bin/python -m learn.song_soundspace mem-check                         # may renders run beside training?
    $TORCH_PY        -m learn.song_soundspace train --arm B1 --fold f           # MPS (fold 0 alone first)
    $TORCH_PY        -m learn.song_soundspace train --arm B2 --fold f           # MPS, after song_relabel sets/features
    $TORCH_PY        -m learn.song_soundspace train --arm B1r --fold f --optional-approved   # B1′ (its own yes)
    $TORCH_PY        -m learn.song_soundspace propose-targets --arm B1|B2|B1r|B2a           # E1 (CPU, 2 threads)
    .venv/bin/python -m learn.song_soundspace score-targets --arm ARM --shard i/3           # E1 renders
    .venv/bin/python -m learn.song_soundspace report-1                                      # provisional choice
    # the songs (the user's yes): E2, E3, C-fine
    $TORCH_PY        -m learn.song_soundspace bridge --user-approved                        # E2, zero renders
    $TORCH_PY        -m learn.song_soundspace songs-top --user-approved
    .venv/bin/python -m learn.song_soundspace score-songs --what top --user-approved --shard i/3
    .venv/bin/python -m learn.song_soundspace report-2 --user-approved                      # the choice
    $TORCH_PY        -m learn.song_soundspace songs-more --user-approved [--b0-best8-approved]
    .venv/bin/python -m learn.song_soundspace score-songs --what more|cfine|b0best8 --user-approved --shard i/3
    .venv/bin/python -m learn.song_soundspace report-2 --user-approved
    # C-start: offered only if report-2 chose B1 or B2, and run on its own yes
    .venv/bin/python -m learn.song_soundspace c-start --c-start-approved --shard i/3
    .venv/bin/python -m learn.song_soundspace report-3

The pure functions (the head, the losses, the weights, the refusal rule, the readings, the
gates) take plain data and are unit-tested; the CLI steps are the only code that reads the
Mac's files, trains or renders.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import statistics
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import knob_ceiling as K  # noqa: E402
from learn import song_bank as B  # noqa: E402
from learn import song_diag as D  # noqa: E402
from learn import song_relabel as RL  # noqa: E402
from learn.song_readout import EPS, bw_stats, finite  # noqa: E402

OUT = RL.OUT
MODELS = OUT / "models"
B0_MODELS = B.OUT.parent / "models"
SS_OUT = B.OUT.parent
LEVERS = SS_OUT / "levers"
DIAG = RL.DIAG

ARM_SPEC = {"B1": {"seed": 20261018, "new": False, "sets": False, "optional": False},
            "B1r": {"seed": 20261031, "new": False, "sets": False, "optional": True},
            "B2": {"seed": 20261018, "new": True, "sets": True, "optional": False},
            "B2a": {"seed": 20261018, "new": True, "sets": False, "optional": True}}
COST_ORDER = ("S", "constant", "B0", "B1", "B2")
SEED_E1, SEED_E3 = 20261029, 20261030
SEED_C_START = 20261013
K_E1, K_E3 = 4, 8
N_CFINE = 8
BOX = 0.02
LIMIT_TOL = 1e-6
MU_LO, MU_HI = -1.0, 2.0
M_MAX = 9                                 # the label + up to 8 probes (S is the scale, not a member)
STEP3_DROPS = (("telefunken-Gym_Hours-GTR_1", "pr12", "A"), ("telefunken-Sculptor's_Request-GTR_1", "pr12", "B"))
N_STEP3 = 142
CAPS = {"e1": 4350, "e1_b2a": 1450, "e3": 1750, "cfine": 450, "b0best8": 1150, "c_start": 7650}
SCORE_GROUP_CAP = {"top": "e3", "more": "e3", "cfine": "cfine", "b0best8": "b0best8"}
RAM_TOTAL, RAM_FREE_KEEP = 32e9, 6e9
THREADS = 2
VIEWS = ("1a", "1b")


# ============================================================================== gates

def require(flag, what):
    if not flag:
        raise SystemExit(f"{what} runs only on the user's own yes")


def c_start_allowed(choice, approved):
    """C-start is offered only if E3 chose B1 or B2, and runs only on its own yes."""
    if not choice or choice.get("chosen") not in ("B1", "B2"):
        raise SystemExit("C-start is offered only if E3 (report-2) chose B1 or B2")
    require(approved, "C-start")
    return choice["chosen"]


def arm_allowed(arm, optional_approved):
    if arm not in ARM_SPEC:
        raise SystemExit(f"unknown arm {arm}")
    if ARM_SPEC[arm]["optional"]:
        require(optional_approved, f"{arm} (optional)")


def check_cap(group, spent_n, planned):
    if spent_n + planned > CAPS[group]:
        raise SystemExit(f"{group}: {spent_n} spent + {planned} planned exceeds the hard cap {CAPS[group]}")


def spent(folder):
    return sum(json.loads(p.read_text()).get("renders", 0) for p in pathlib.Path(folder).rglob("*.json"))


# ============================================================================== memory

def peak_rss_bytes(ru_maxrss, system=None):
    """`resource.getrusage(...).ru_maxrss` in bytes: macOS reports bytes, Linux kilobytes."""
    import platform

    return int(ru_maxrss) if (system or platform.system()) == "Darwin" else int(ru_maxrss) * 1024


def current_peak_rss():
    import resource

    return peak_rss_bytes(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def beside_ok(peak_bytes, render_rss_bytes, n_render=3, total=RAM_TOTAL, keep=RAM_FREE_KEEP):
    """Render processes may run beside training only if the measured peak plus n render processes
    leaves the guard's 6 GB."""
    return peak_bytes + n_render * render_rss_bytes + keep <= total


def parse_ps_rss(text):
    """`ps -axo rss=,command=` -> [rss bytes] of render shard processes (`-m learn.` with `--shard`)."""
    out = []
    for line in text.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[0].isdigit() and "-m learn." in parts[1] and "--shard" in parts[1]:
            out.append(int(parts[0]) * 1024)
    return out


def b0_split(idx, fold, seed=None):
    """`song_model.train`'s split, verbatim (full data): rows (i, fold, band, amp, cls, label) of
    fold != f; validation = whole development bands in a seeded order until ≥ 10% of the rows.
    -> (train rows, val rows, val bands)."""
    from learn import song_model as M

    rng = random.Random((M.SEED if seed is None else seed) + fold)
    idx = [r for r in idx if r[1] != fold]
    dev_bands = sorted({r[2] for r in idx if not r[2].startswith("Guitar-TECHS")})
    rng.shuffle(dev_bands)
    val_bands = set()
    per_band = {b: sum(r[2] == b for r in idx) for b in dev_bands}
    for b in dev_bands:
        if sum(per_band[v] for v in val_bands) >= M.VAL_SHARE * len(idx):
            break
        val_bands.add(b)
    tr = [r for r in idx if r[2] not in val_bands]
    va = [r for r in idx if r[2] in val_bands]
    return tr, va, val_bands


def dry_run_b0(fold, idx, feat_path, out_path):
    """B0's fold arrays loaded exactly as `song_model.train` loads them (np.stack, no training);
    the peak RSS is written to `out_path`."""
    import numpy as np

    from learn import song_model as M

    t0 = time.time()
    tr, va, vb = b0_split(idx, fold)

    def load(rows):
        X, C, Y = [], [], []
        for i, f, band, amp, cls, label in rows:
            d = np.load(feat_path(i))
            for h in "AB":
                X.append(M.norm_feat(d[f"feat{h}"]))
                C.append(M.cond_vec(amp, cls, d[f"lufs{h}"]))
                Y.append(M.encode(label))
        return np.stack(X), np.stack(C), [np.stack(z) for z in zip(*Y)]

    Xt, _, _ = load(tr)
    Xv, _, _ = load(va)
    rep = {"fold": fold, "train_rows": len(tr), "val_rows": len(va), "val_bands": sorted(vb),
           "train_bytes": int(Xt.nbytes), "val_bytes": int(Xv.nbytes), "peak_rss_bytes": current_peak_rss(),
           "seconds": time.time() - t0}
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    K._atomic(pathlib.Path(out_path), rep)
    return rep


# ============================================================================== the model

def build_model2():
    """B0's network with the censored head: each continuous mean is −1 + 3·sigmoid(z), a soft bound
    on (−1, 2). The parameters are B0's, so the state dicts have the same keys."""
    import types

    import torch

    from learn import song_model as M

    net = M.build_model()

    def forward(self, x, cond):
        h = self.body(x)
        h = torch.cat([h.mean(-1), h.std(-1)], dim=1).flatten(1)
        h = self.trunk(torch.cat([h, cond], dim=1))
        n = len(M.CONT)
        mu = MU_LO + (MU_HI - MU_LO) * torch.sigmoid(self.mu(h))
        return (torch.log_softmax(self.pi(h), -1), mu.view(-1, M.K_MIX, n),
                self.ls(h).view(-1, M.K_MIX, n).clamp(-6, 1), self.sw(h), [c(h) for c in self.cat])

    net.forward = types.MethodType(forward, net)
    return net


def load_net2(arm, fold):
    import torch

    net = build_model2()
    net.load_state_dict(torch.load(MODELS / arm / f"fold{fold}" / "model.pt", map_location="cpu"))
    return net.eval()


def censored_lp(u, mu, ls, tol=LIMIT_TOL):
    """Log-likelihood of a label u under N(mu, e^ls) censored to [0, 1]: within tol of 0 the mass
    below 0, within tol of 1 the mass above 1, else the density."""
    import torch

    sigma = ls.exp()
    z = (u - mu) / sigma
    dens = -0.5 * z ** 2 - ls - 0.5 * math.log(2 * math.pi)
    lo = torch.special.log_ndtr((0.0 - mu) / sigma)
    hi = torch.special.log_ndtr((mu - 1.0) / sigma)
    return torch.where(u <= tol, lo, torch.where(u >= 1.0 - tol, hi, dens))


def member_terms(out, bt, lp_fn=None):
    """Per example and member: (L, joint, n_active). L is B0's loss structure with the weights inside
    each group (continuous: per example, normalised by its weight sum; switches and mics: normalised
    over the batch, from the label member), so Σ_e L[e, 0] is B0's loss when every weight is 1. joint
    is the weighted joint log-likelihood; n_active the member's number of active (unmasked) terms:
    continuous settings, switches and mics. `bt`: c, sc, s, ss (B, M, ·) floats; k (B, M, n_cat)
    long; km (B, M, n_cat)."""
    import torch
    import torch.nn.functional as F

    lp_fn = lp_fn or censored_lp
    logpi, mu, ls, swl, catl = out
    c, sc, s, ss, k, km = (bt[n] for n in ("c", "sc", "s", "ss", "k", "km"))
    Bn, M = c.shape[0], c.shape[1]
    lp = lp_fn(c[:, :, None, :], mu[:, None], ls[:, None])                 # B, M, K, n
    wl = (lp * sc[:, :, None, :]).sum(-1)
    cont_ll = torch.logsumexp(logpi[:, None, :] + wl, -1)                   # B, M
    cont_norm = sc.sum(-1).clamp(min=1)
    bce = F.binary_cross_entropy_with_logits(swl[:, None, :].expand_as(s), s, reduction="none")
    sw_w = (bce * ss).sum(-1)
    ce = torch.stack([F.cross_entropy(catl[j][:, None, :].expand(-1, M, -1).reshape(Bn * M, -1),
                                      k[:, :, j].reshape(-1), reduction="none").view(Bn, M)
                      for j in range(len(catl))], -1) if catl else torch.zeros(Bn, M, 0)
    mic_w = ce * km
    d_sw = ss[:, 0, :].sum().clamp(min=1)
    d_mic = km[:, 0, :].sum(0).clamp(min=1)
    L = -cont_ll / cont_norm / Bn + sw_w / d_sw + (mic_w / d_mic).sum(-1)
    joint = cont_ll - sw_w - mic_w.sum(-1)
    n_active = ((sc > 0).sum(-1) + (ss > 0).sum(-1) + (km > 0).sum(-1)).clamp(min=1).to(joint.dtype)
    return L, joint, n_active


def responsibilities(logw, joint, n_active):
    """Amendment 1: γ_m ∝ w̃_m · exp(joint_m / D_m), D_m the member's number of active terms (the
    log-likelihood tempered per dimension), detached. Padding members (log w̃ = −inf) get 0."""
    import torch

    return torch.softmax(logw + (joint / n_active).detach(), dim=1)


def loss_soundspace(out, bt, lp_fn=None):
    """The arms' loss. Responsibilities γ_m ∝ w̃_m · exp(joint_m / D_m), detached (amendment 1: the
    log-likelihood tempered per active term); L_e = Σ_m γ_m L_e,m (the responsibility-weighted NLL);
    total Σ_e ω_e L_e / mean(ω). With one member and ω = 1 it is B0's loss (B1's when the weights
    are s_j)."""
    L, joint, n_active = member_terms(out, bt, lp_fn)
    gamma = responsibilities(bt["logw"], joint, n_active)
    Le = (gamma * L).sum(1)
    om = bt["omega"]
    return (om * Le).sum() / om.mean()


def gaussian_lp(u, mu, ls):
    """B0's density (no censoring), for the equality test and B0 itself."""
    return -0.5 * ((u - mu) / ls.exp()) ** 2 - ls - 0.5 * math.log(2 * math.pi)


# ============================================================================== training data

def record_weights(rows):
    """ω per row: K_S-centred rows (`ks`) carry half of the training loss: ω = n_other / n_ks."""
    n_ks = sum(r["ks"] for r in rows)
    n_other = len(rows) - n_ks
    w = n_other / n_ks if n_ks else 1.0
    return [w if r["ks"] else 1.0 for r in rows]


def is_ks_centred(e):
    return e.get("mode") == "jitter" and e.get("centre") not in (None, "S")


def split_rows(rows, fold, val_bands):
    """Model f's rows: fold != f only; validation = B0's validation bands for fold f."""
    rows = [r for r in rows if r["fold"] != fold]
    tr = [r for r in rows if r["band"] not in val_bands]
    va = [r for r in rows if r["band"] in val_bands]
    assert not any(r["fold"] == fold for r in tr + va)
    return tr, va


def encode_member(amp, label, table):
    """(c, sc, s, ss, k, km) for one member: song_model's encoding with s_j and the right-cab mask."""
    import numpy as np

    from learn import song_model as M

    c, cm, s, sm, k, km = M.encode(label)
    cw, sw, mic = RL.label_weights(amp, label, table)
    return (c, np.asarray(cw, np.float32) * cm, s, np.asarray(sw, np.float32) * sm, k,
            np.asarray(mic, np.float32) * km)


def unit_weights_member(label):
    """B0's masks as weights (every s_j = 1, nothing gated), for the equality test."""
    from learn import song_model as M

    c, cm, s, sm, k, km = M.encode(label)
    return c, cm, s, sm, k, km


def members_for(row, half, sets):
    """[(label, log w̃)] for a row's half: its set if relabelled (and not a point half), else the label."""
    st = sets.get(row["i"])
    if st is None or st[half]["point"]:
        return [(row["label"], 0.0)]
    return [(m["label"], m["logw"]) for m in st[half]["members"]]


def member_arrays(rows, sets, table, m_max=M_MAX):
    """Member arrays for every (row, half) in order A then B per row."""
    import numpy as np

    from learn import song_model as M

    n = 2 * len(rows)
    nc, ns, nk = len(M.CONT), len(M.SW), len(M.CAT)
    arr = {"c": np.zeros((n, m_max, nc), np.float32), "sc": np.zeros((n, m_max, nc), np.float32),
           "s": np.zeros((n, m_max, ns), np.float32), "ss": np.zeros((n, m_max, ns), np.float32),
           "k": np.zeros((n, m_max, nk), np.int64), "km": np.zeros((n, m_max, nk), np.float32),
           "logw": np.full((n, m_max), -np.inf, np.float32)}
    j = 0
    for r in rows:
        for h in "AB":
            mem = members_for(r, h, sets)
            assert len(mem) <= m_max, (r["i"], len(mem))
            for m, (lab, lw) in enumerate(mem):
                for name, v in zip(("c", "sc", "s", "ss", "k", "km"), encode_member(r["amp"], lab, table)):
                    arr[name][j, m] = v
                arr["logw"][j, m] = lw
            j += 1
    return arr


def load_features(rows, feat_path):
    """Features into preallocated float32 arrays (no np.stack copy): X (2N, 2, MELS, T), C (2N, 7)."""
    import numpy as np

    from learn import song_model as M

    first = np.load(feat_path(rows[0]))["featA"]
    X = np.empty((2 * len(rows), *first.shape), np.float32)
    C = np.empty((2 * len(rows), len(M.AMPS) + len(M.CLASSES) + 2), np.float32)
    j = 0
    for r in rows:
        d = np.load(feat_path(r))
        for h in "AB":
            X[j] = M.norm_feat(d[f"feat{h}"])
            C[j] = M.cond_vec(r["amp"], r["cls"], d[f"lufs{h}"])
            j += 1
    return X, C


def bank_rows():
    """The bank's rows (song_model.bank_index) with their band, class and K_S-centred flag."""
    from learn import song_model as M

    ex = {e["i"]: e for e in json.loads((B.OUT / "examples.json").read_text())}
    return [{"i": i, "fold": f, "band": band, "amp": amp, "cls": cls, "label": label, "src": "bank",
             "ks": is_ks_centred(ex[i])} for i, f, band, amp, cls, label in M.bank_index()]


def new_rows():
    """The record-like examples (all K_S-centred, or counted S fallbacks)."""
    ex = json.loads((RL.BANK2 / "examples.json").read_text())
    out = []
    for e in ex:
        r = RL.BANK2 / "renders" / f"{e['i']:05d}.json"
        f = RL.BANK2 / "features" / f"{e['i']:05d}.npz"
        assert r.exists() and f.exists(), f"record-like example {e['i']} lacks a render or features"
        out.append({"i": e["i"], "fold": e["fold"], "band": e["window"]["band"], "amp": e["amp"],
                    "cls": e["class"], "label": json.loads(r.read_text())["label"], "src": "new",
                    "ks": is_ks_centred(e)})
    return out


def feat_path(r):
    return (B.OUT if r["src"] == "bank" else RL.BANK2) / "features" / f"{r['i']:05d}.npz"


def load_sets():
    plan = json.loads(RL.PLAN.read_text())["examples"]
    out = {}
    for k in plan:
        p = RL.SETS / f"{int(k):05d}.json"
        assert p.exists(), f"set {k} missing: run song_relabel sets first"
        out[int(k)] = json.loads(p.read_text())
    return out


# ============================================================================== training

def train(arm, fold, device=None):
    import numpy as np
    import torch

    from learn import song_model as M

    spec = ARM_SPEC[arm]
    seed = spec["seed"] + fold
    torch.manual_seed(seed)
    torch.set_num_threads(THREADS)
    t0 = time.time()
    table = json.loads(RL.WEIGHTS.read_text())["weights"]
    rows = bank_rows() + (new_rows() if spec["new"] else [])
    sets = load_sets() if spec["sets"] else {}
    val_bands = set(json.loads((B0_MODELS / f"fold{fold}" / "log.json").read_text())["val_bands"])
    tr, va = split_rows(rows, fold, val_bands)
    om_tr = np.repeat(np.asarray(record_weights(tr), np.float32), 2)
    Xt, Ct = load_features(tr, feat_path)
    Xv, Cv = load_features(va, feat_path)
    Mt, Mv = member_arrays(tr, sets, table), member_arrays(va, sets, table)
    dev = device or torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    net = build_model2().to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=M.LR)
    out = MODELS / arm / f"fold{fold}"
    out.mkdir(parents=True, exist_ok=True)
    best, bad, log = math.inf, 0, []

    def batches(X, C, Mm, om, rng):
        order = rng.permutation(len(X)) if rng is not None else np.arange(len(X))
        for j in range(0, len(X), M.BATCH):
            b = order[j:j + M.BATCH]
            bt = {n: torch.tensor(v[b]) for n, v in Mm.items()}          # the loss runs on the CPU
            bt["omega"] = torch.tensor(om[b]) if om is not None else torch.ones(len(b))
            yield torch.tensor(X[b], device=dev), torch.tensor(C[b], device=dev), bt

    def cpu(o):
        logpi, mu, ls, swl, catl = o
        return logpi.cpu(), mu.cpu(), ls.cpu(), swl.cpu(), [c.cpu() for c in catl]

    for epoch in range(M.EPOCHS):
        net.train()
        tl = []
        for x, c, bt in batches(Xt, Ct, Mt, om_tr, np.random.default_rng([seed, epoch])):
            loss = loss_soundspace(cpu(net(x, c)), bt)
            opt.zero_grad()
            loss.backward()
            g = torch.nn.utils.clip_grad_norm_(net.parameters(), 1e9)
            if torch.isfinite(g):
                for p in net.parameters():
                    if p.grad is not None:
                        p.grad.mul_(min(1.0, 5.0 / (float(g) + 1e-9)))
                opt.step()
            tl.append(float(loss))
        net.eval()
        with torch.no_grad():                                           # validation: ω = 1
            vl = [float(loss_soundspace(cpu(net(x, c)), bt)) for x, c, bt in batches(Xv, Cv, Mv, None, None)]
        v = sum(vl) / max(1, len(vl))
        log.append({"epoch": epoch, "train": sum(tl) / max(1, len(tl)), "val": v})
        print(arm, fold, log[-1], flush=True)
        if v < best - 1e-4:
            best, bad = v, 0
            torch.save(net.state_dict(), out / "model.pt")
        else:
            bad += 1
            if bad >= M.PATIENCE:
                break
    K._atomic(out / "log.json", {"arm": arm, "fold": fold, "seed": seed, "log": log, "train_rows": len(tr),
                                 "val_rows": len(va), "val_bands": sorted(val_bands),
                                 "relabelled_rows": sum(r["i"] in sets for r in tr),
                                 "ks_weight": record_weights(tr)[[r["ks"] for r in tr].index(True)]
                                 if any(r["ks"] for r in tr) else None,
                                 "seconds": time.time() - t0, "peak_rss_bytes": current_peak_rss()})
    (out / "DONE").write_text("")


# ============================================================================== answers and scores

def heads(net, feat, lufs_v, amp, cls):
    """pi, mu, sigma, sw_p, mic_p for one half (B0 or a new arm's net)."""
    return D.net_heads(net, feat, lufs_v, amp, cls)


def top_answer2(h, amp, S):
    """The heaviest component's mean clipped to [0, 1]; switches at p > 0.5; mics' top choice."""
    import numpy as np

    top = int(np.asarray(h["pi"]).argmax())
    u = np.clip(np.asarray(h["mu"][top], np.float64), 0.0, 1.0)
    return D.settings_from(amp, S, u, np.asarray(h["sw_p"]) > 0.5, [int(np.argmax(p)) for p in h["mic_p"]])


def sample2(h, rng):
    """One sample of the censored model: a component by π, each continuous setting from its
    Gaussian clipped to [0, 1], switches by p, mics by softmax."""
    import numpy as np

    pi = np.asarray(h["pi"], np.float64)
    k = int(rng.choice(len(pi), p=pi / pi.sum()))
    cont = np.clip(rng.normal(np.asarray(h["mu"][k], np.float64), np.asarray(h["sigma"][k], np.float64)), 0.0, 1.0)
    sw = [bool(rng.random() < float(p)) for p in h["sw_p"]]
    mics = []
    for p in h["mic_p"]:
        p = np.asarray(p, np.float64)
        mics.append(int(rng.choice(len(p), p=p / p.sum())))
    return list(cont), sw, mics


def answer(arm, h, amp, S):
    return D.top_mean_settings(h, amp, S) if arm == "B0" else top_answer2(h, amp, S)


def draw(arm, h, amp, S, rng):
    return D.settings_from(amp, S, *(D.sample_units(h, rng) if arm == "B0" else sample2(h, rng)))


def _norm_cdf(x):
    from scipy.special import ndtr

    return ndtr(x)


def box_logprob(h, x, amp, kind, box=BOX, tol=LIMIT_TOL):
    """E2's score: log P of a ±box around each continuous value (censored: a box reaching a limit
    takes the censored mass beyond it; truncated (B0): the truncated normal's mass), mixed over
    components, plus the switch and mic log-probabilities."""
    import numpy as np
    from scipy.special import logsumexp

    from learn import song_model as M

    space = {d.name: d for d in K.space(amp, x)}
    ci = [j for j, n in enumerate(M.CONT) if n in space]
    u = np.array([space[M.CONT[j]].to_unit(x.get((space[M.CONT[j]].module, space[M.CONT[j]].key),
                                                  space[M.CONT[j]].lo)) for j in ci])
    mu = np.asarray(h["mu"], np.float64)[:, ci]
    sg = np.asarray(h["sigma"], np.float64)[:, ci]
    lo, hi = u - box, u + box
    if kind == "censored":
        a = np.where(lo <= tol, -np.inf, lo)
        b = np.where(hi >= 1 - tol, np.inf, hi)
        mass = _norm_cdf((b - mu) / sg) - _norm_cdf((a - mu) / sg)
    else:
        a, b = np.maximum(lo, 0.0), np.minimum(hi, 1.0)
        z = _norm_cdf((1 - mu) / sg) - _norm_cdf((0 - mu) / sg)
        mass = (_norm_cdf((b - mu) / sg) - _norm_cdf((a - mu) / sg)) / np.maximum(z, 1e-300)
    cont = logsumexp(np.log(np.asarray(h["pi"], np.float64)) + np.log(np.maximum(mass, 1e-300)).sum(1))
    return cont + _cat_logprob(h, x, amp)


def _cat_logprob(h, x, amp):
    from learn import song_model as M

    space = {d.name: d for d in K.space(amp, x)}
    out = 0.0
    for j, n in enumerate(M.SW):
        if n in space:
            d = space[n]
            p = float(h["sw_p"][j])
            on = x.get((d.module, d.key)) == d.values[1]
            out += math.log(max(p if on else 1 - p, 1e-12))
    for j, n in enumerate(M.CAT):
        if n in space:
            d = space[n]
            v = x.get((d.module, d.key))
            if v in M.MICS:
                out += math.log(max(float(h["mic_p"][j][M.MICS.index(v)]), 1e-12))
    return out


def trunc_logdensity(h, x, amp):
    """The diagnostics' figure (B0): truncated-normal density, plus switches and mics."""
    import numpy as np
    from scipy.special import log_ndtr, logsumexp

    from learn import song_model as M

    space = {d.name: d for d in K.space(amp, x)}
    ci = [j for j, n in enumerate(M.CONT) if n in space]
    u = np.array([space[M.CONT[j]].to_unit(x.get((space[M.CONT[j]].module, space[M.CONT[j]].key),
                                                  space[M.CONT[j]].lo)) for j in ci])
    m = np.asarray(h["mu"], np.float64)[:, ci]
    s = np.asarray(h["sigma"], np.float64)[:, ci]
    z = (u - m) / s
    lpdf = -0.5 * z ** 2 - np.log(s) - 0.5 * math.log(2 * math.pi)
    lnorm = np.log(np.clip(np.exp(log_ndtr((1 - m) / s)) - np.exp(log_ndtr(-m / s)), 1e-300, None))
    return float(logsumexp(np.log(np.asarray(h["pi"], np.float64)) + (lpdf - lnorm).sum(1))) + _cat_logprob(h, x, amp)


# ============================================================================== the refusal rule

def as_S(d, d_S):
    """A refused (non-finite or non-positive) answer scores as S. -> (value, refused)."""
    return (d, False) if finite(d) and d > 0 else (d_S, True)


def best_of_refusal(search, held, S_search, S_held):
    """Best of K picked on the search half, each sample refused on a half scoring as S on that half.
    -> (held value of the pick, index, number of refused samples)."""
    sv = [as_S(v, S_search) for v in search]
    hv = [as_S(v, S_held) for v in held]
    j = min(range(len(sv)), key=lambda i: (sv[i][0], i))
    return hv[j][0], j, sum(a[1] or b[1] for a, b in zip(sv, hv))


def log_vs_S(u, name):
    """log(d_name / d_S) on the held half with the refusal rule (S itself: 0). -> (value, refused)."""
    if name == "S":
        return 0.0, False
    v, ref = as_S(u["d"].get(name), u["d"]["S"])
    return math.log(v / u["d"]["S"]), ref


# ============================================================================== readings

def bw(rows):
    """rows: (band, value) -> bw_stats with the leave-one-band-out range."""
    s = bw_stats(rows)
    lobo = s.get("leave_one_band_out") or []
    s["lobo_range"] = [min(lobo), max(lobo)] if lobo else None
    return s


def bw_parts(rows):
    """rows: (part, band, value). Units are averaged per part (or target) first, then band-weighted,
    with the part-weighted mean beside it."""
    by = {}
    for part, band, v in rows:
        by.setdefault((part, band), []).append(v)
    pm = [(b, statistics.fmean(v)) for (_, b), v in sorted(by.items())]
    out = bw(pm)
    out["part_weighted_mean"] = statistics.fmean(v for _, v in pm) if pm else None
    out["units"] = len(rows)
    return out


def part_of(u):
    return str(u.get("slug", u.get("target")))


def choose_rows(units, names, unit_id):
    """{candidate: {unit key: (part id, band, log vs S)}} with the refusal rule; refusals counted."""
    vals, refused = {}, {}
    for cand, name_of in names.items():
        vals[cand], refused[cand] = {}, 0
        for u in units:
            if name_of(u) != "S" and name_of(u) not in u["d"]:
                raise SystemExit(f"{cand}: {name_of(u)} not scored for unit {unit_id(u)}")
            v, ref = log_vs_S(u, name_of(u))
            refused[cand] += int(ref)
            vals[cand][unit_id(u)] = (str(u.get("slug", u.get("target"))), u["band"], v)
    return vals, refused


def decide(units, names, order, unit_id):
    """The choice among `order` (cost order) by `arm_a_levers.choose`: best band-weighted mean,
    ties (paired 90% interval contains 0) to the first in cost order."""
    from learn import arm_a_levers as AL

    vals, refused = choose_rows(units, {c: names[c] for c in order if c in names}, unit_id)
    ch = AL.choose(vals, [c for c in order if c in names])
    ch["refused"] = refused
    return ch


def e1_names(arms):
    """Each candidate's E1 view-1b top answer, per unit."""
    out = {"S": lambda u: "S", "constant": lambda u: "constant", "B0": lambda u: f"1b:{u['search']}:top"}
    for a in arms:
        out[a] = (lambda arm: lambda u: f"{arm}|1b:{u['search']}:top")(a)
    return out


def e1_unit_id(u):
    return (u["target"], u["search"])


def provisional_choice(units, arms):
    """Without the songs: the E1 view-1b top answer on BROAD targets decides; the K_S-prior half is
    reported beside it, and the result is 'undecided' if the halves name different winners."""
    names = e1_names(arms)
    broad = decide([u for u in units if u["type"] == "broad"], names, COST_ORDER, e1_unit_id)
    ksp = decide([u for u in units if u["type"] == "ks_prior"], names, COST_ORDER, e1_unit_id)
    same = broad["chosen"] == ksp["chosen"]
    return {"broad": broad, "ks_prior": ksp, "chosen": broad["chosen"] if same else "undecided",
            "provisional": True}


def select_units(units, dropped_targets, mode="report"):
    """E1's unit list. 'report': the diagnostics' report (repeat-dropped targets out, then
    non-informative units out: 228). 'audit': the audit's (any target with a non-informative unit
    out whole: 224)."""
    units = [u for u in units if str(u["target"]) not in set(map(str, dropped_targets))]
    if mode == "report":
        return [u for u in units if D.informative(u)]
    bad = {u["target"] for u in units if not D.informative(u)}
    return [u for u in units if u["target"] not in bad]


def units_hash(units):
    import hashlib

    return hashlib.sha256(json.dumps(sorted([int(u["target"]), u["search"]] for u in units)).encode()).hexdigest()[:16]


def paired(units, a, b):
    """log(d_a / d_b) on the held half, averaged per part then band-weighted; the refusal rule on
    both sides ('S' allowed). Units where either name was not scored are left out (counted)."""
    rows, missing = [], 0
    for u in units:
        na, nb = a(u), b(u)
        if any(n != "S" and n not in u["d"] for n in (na, nb)):
            missing += 1
            continue
        va, _ = log_vs_S(u, na)
        vb, _ = log_vs_S(u, nb)
        rows.append((part_of(u), u["band"], va - vb))
    out = bw_parts(rows)
    out["missing"] = missing
    return out


def best_k_held(u, names):
    """Held value of a best of K (search-picked) with the refusal rule. -> (value, refused count)."""
    v, _, nref = best_of_refusal([u["s"].get(n) for n in names], [u["d"].get(n) for n in names],
                                 u["s"]["S"], u["d"]["S"])
    return v, nref


def e1_measures(units, arm):
    """E1's reported figures for one arm (B0 included as 'B0')."""
    pre = "" if arm == "B0" else f"{arm}|"
    top1b = lambda u: f"{pre}1b:{u['search']}:top"           # noqa: E731
    top1a = lambda u: f"{pre}1a:{u['search']}:top"           # noqa: E731
    S = lambda u: "S"                                         # noqa: E731
    out = {"top_vs_S_1b": paired(units, top1b, S), "top_vs_S_1a": paired(units, top1a, S),
           "top_vs_B0_1b": paired(units, top1b, lambda u: f"1b:{u['search']}:top")}
    for typ in ("broad", "ks_prior"):
        out[f"top_vs_S_1b_{typ}"] = paired([u for u in units if u["type"] == typ], top1b, S)
    b4, b0b4, gaps, nref = [], [], [], 0
    for u in units:
        v, n = best_k_held(u, [f"{pre}1b:{u['search']}:s{k}" for k in range(K_E1)])
        w, _ = best_k_held(u, [f"1b:{u['search']}:s{k}" for k in range(K_E1)])
        nref += n
        b4.append((part_of(u), u["band"], math.log(v / u["d"]["S"])))
        b0b4.append((part_of(u), u["band"], math.log(v / w)))
        tv, ref = as_S(u["d"].get(top1b(u)), u["d"]["S"])
        nref += int(ref)
        gaps.append((u["d"]["S"] - tv) / (u["d"]["S"] - u["d"]["target_repeat"]))
    out["best4_vs_S_1b"] = bw_parts(b4)
    out["best4_vs_B0best4_1b"] = bw_parts(b0b4)
    out["gap_closed_median_1b"] = statistics.median(gaps) if gaps else None
    out["share_closing_half_1b"] = sum(g >= 0.5 - EPS for g in gaps) / len(gaps) if gaps else None
    out["refused"] = nref
    return out


def answer_shape(rows):
    """rows: [(amp, answer settings, target settings)] -> the share of continuous answers within
    0.01 of a limit, answer spread over target spread (mean over settings), per-setting Spearman
    (input gain and the amp's tone knobs), and switch accuracy."""
    import numpy as np
    from scipy.stats import spearmanr

    lim, per, sw_hit, sw_n = [], {}, 0, 0
    for amp, x, t in rows:
        for d in K.space(amp, t):
            k = (d.module, d.key)
            if d.kind in ("cont", "log"):
                ua, ut = RL.unit_of(d, x), RL.unit_of(d, t)
                lim.append(ua <= 0.01 or ua >= 0.99)
                per.setdefault(d.name, []).append((ua, ut))
            elif d.kind == "switch":
                sw_n += 1
                sw_hit += int(x.get(k) == t.get(k))
    spread = [np.std([a for a, _ in v]) / np.std([b for _, b in v]) for v in per.values()
              if len(v) > 2 and np.std([b for _, b in v]) > 0]
    tone = {n for amp in K.AMPS for d in K.AMP_DIMS[amp] if d.kind == "cont" for n in [d.name]}
    rho = {}
    for n, v in per.items():
        if (n == "parameters/inputGain" or n in tone) and len(v) > 2:
            r = spearmanr([a for a, _ in v], [b for _, b in v]).correlation
            rho[n] = None if r is None or not math.isfinite(r) else float(r)
    return {"limit_share": sum(lim) / len(lim) if lim else None,
            "spread_ratio": statistics.fmean(spread) if spread else None,
            "spearman": rho, "switch_accuracy": sw_hit / sw_n if sw_n else None}


def path_spearman(scores, held):
    """Spearman of model score against held distance over a K_S path (finite, positive; ≥ 10)."""
    from scipy.stats import spearmanr

    ok = [i for i, (a, b) in enumerate(zip(scores, held)) if finite(a) and finite(b) and b > 0]
    if len(ok) < 10:
        return None
    r = spearmanr([scores[i] for i in ok], [held[i] for i in ok]).correlation
    return None if r is None or not math.isfinite(r) else float(r)


def path_picks(scores, held, search, start_held):
    """Held log ratio vs S of the highest-scoring setting among the first 8, first 16 and all, and of
    K_S's own pick at 8 (lowest search-half value among the first 8)."""
    out = {}
    for name, n in (("maxscore8", 8), ("maxscore16", 16), ("maxscore_all", len(scores))):
        ok = [i for i in range(min(n, len(scores))) if finite(scores[i]) and finite(held[i]) and held[i] > 0]
        if ok:
            j = max(ok, key=lambda i: (scores[i], -i))
            out[name] = math.log(held[j] / start_held)
    ok = [i for i in range(min(8, len(search))) if finite(search[i])]
    if ok:
        j = min(ok, key=lambda i: (search[i], i))
        if finite(held[j]) and held[j] > 0:
            out["ks8"] = math.log(held[j] / start_held)
    return out


def cfine_pick(evaluated, objective, score_fn, n=N_CFINE):
    """C-fine: of arm A's main-stage settings, the n with the lowest finite C′ objective; the model's
    score picks one. -> index into `evaluated`."""
    ok = sorted((i for i, v in enumerate(objective) if finite(v)), key=lambda i: (objective[i], i))[:n]
    if not ok:
        return None
    sc = {i: score_fn(evaluated[i]) for i in ok}
    return max(ok, key=lambda i: (sc[i], -i))


def main_stage_settings(dims, S, curve):
    """Arm A's stored main stage replayed with zero renders: (evaluated settings, objective values)."""
    from learn import arm_a_levers as AL

    rep = AL.Replay(curve)
    AL.main_stage(dims, S, rep)
    return rep.xs, curve[:len(rep.xs)]


def e3_cells():
    from learn import song_settings as SS

    out = [c for c in SS.cells() if (c[0], c[1], c[2]) not in STEP3_DROPS]
    assert len(out) == N_STEP3, len(out)
    return out


def e3_sample_rng(slug, amp, search):
    import numpy as np

    parts = sorted(s for s in K.parts() if s != "telefunken-Honey-GTR")
    return np.random.default_rng(np.random.SeedSequence([SEED_E3, parts.index(slug), K.AMPS.index(amp),
                                                         "AB".index(search)]))


def e1_sample_rng(target, view, search):
    import numpy as np

    return np.random.default_rng(np.random.SeedSequence([SEED_E1, int(target), VIEWS.index(view), "AB".index(search)]))


# ============================================================================== CLI: memory

def cmd_mem_dry_run(fold):
    from learn import song_model as M

    rep = dry_run_b0(fold, M.bank_index(), lambda i: B.OUT / "features" / f"{i:05d}.npz",
                     OUT / "memory" / f"B0-dry-fold{fold}.json")
    print(json.dumps(rep, indent=1))


def cmd_mem_check(render_rss_gb=None):
    rep = json.loads((OUT / "memory" / "B0-dry-fold0.json").read_text())
    if render_rss_gb is None:
        ps = subprocess.run(["ps", "-axo", "rss=,command="], capture_output=True, text=True).stdout
        rss = parse_ps_rss(ps)
        if not rss:
            raise SystemExit("no render shard running: pass --render-rss-gb (measured) explicitly")
        render = max(rss)
    else:
        render = render_rss_gb * 1e9
    ok = beside_ok(rep["peak_rss_bytes"], render)
    print(json.dumps({"peak_rss_gb": rep["peak_rss_bytes"] / 1e9, "render_rss_gb": render / 1e9, "beside_ok": ok}))
    if not ok:
        raise SystemExit(1)


# ============================================================================== CLI: E1

def _target_heads(net, dz, t):
    return {(v, h): heads(net, dz[f"{v}_feat{h}"], dz[f"{v}_lufs{h}"], t["amp"], t["class"]) for v in VIEWS
            for h in "AB"}


def e1_candidates(arm, hd, t, S):
    """{name: settings} for one target: per direction the 1a top, the 1b top and K_E1 1b samples."""
    out = {}
    for search, _ in D.DIRS:
        out[f"{arm}|1a:{search}:top"] = answer(arm, hd[("1a", search)], t["amp"], S)
        out[f"{arm}|1b:{search}:top"] = answer(arm, hd[("1b", search)], t["amp"], S)
        rng = e1_sample_rng(t["i"], "1b", search)
        for k in range(K_E1):
            out[f"{arm}|1b:{search}:s{k}"] = draw(arm, hd[("1b", search)], t["amp"], S, rng)
    return out


def cmd_propose_targets(arm, optional_approved):
    import numpy as np
    import torch

    arm_allowed(arm, optional_approved)
    torch.set_num_threads(THREADS)
    menu = D._menu()
    targets = json.loads((DIAG / "targets.json").read_text())
    nets = {f: load_net2(arm, f) for f in range(4)}
    out, planned = {}, 0
    for t in targets:
        _, S = D._S(menu, t["amp"], t["class"])
        dz = np.load(DIAG / "targets" / f"{t['i']:03d}-features.npz")
        c = e1_candidates(arm, _target_heads(nets[t["fold"]], dz, t), t, S)
        planned += len(D.render_plan(c)[0])
        out[str(t["i"])] = {n: D.sj(x) for n, x in c.items()}
    group = "e1_b2a" if arm == "B2a" else "e1"
    others = sum(spent(OUT / "e1" / "scores" / a) for a in (("B2a",) if arm == "B2a" else ("B1", "B2", "B1r"))
                 if a != arm)
    check_cap(group, others, planned)
    (OUT / "e1").mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "e1" / f"proposals-{arm}.json", {"planned_renders": planned, "targets": out})
    print(arm, "planned renders", planned)


def cmd_score_targets(arm, shard, optional_approved):
    from learn import knob_ceiling2 as K2

    arm_allowed(arm, optional_approved)
    D.check_shards(shard[1])
    guard = D.MemoryGuard()
    menu = D._menu()
    targets = {str(t["i"]): t for t in json.loads((DIAG / "targets.json").read_text())}
    ppath = OUT / "e1" / f"proposals-{arm}.json"
    props, phash = json.loads(ppath.read_text())["targets"], D.file_hash(ppath)
    d = OUT / "e1" / "scores" / arm
    d.mkdir(parents=True, exist_ok=True)
    group = "e1_b2a" if arm == "B2a" else "e1"
    pool = (("B2a",) if arm == "B2a" else ("B1", "B2", "B1r"))
    rr = K.Renderer()
    try:
        for key in sorted(props, key=int)[shard[0]::shard[1]]:
            f = d / f"{int(key):03d}.json"
            if f.exists():
                continue
            if not K2.disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            t = targets[key]
            c = {n: D.st(x) for n, x in props[key].items()}
            first, of = D.render_plan(c)
            check_cap(group, sum(spent(OUT / "e1" / "scores" / a) for a in pool), len(first))
            meta = json.loads((DIAG / "targets" / f"{int(key):03d}.json").read_text())
            sel, _ = D._S(menu, t["amp"], t["class"])
            di = D.measured_di(t["window"])
            ref = D.load_flac(DIAG / "targets" / f"{int(key):03d}-24.flac", meta["peak24"])
            dist = {}
            for k, n in first.items():
                dist[k] = D.judge_trimmed(ref, rr.render(di, sel, c[n]), di)
                guard.tick()
            K._atomic(f, {"proposals_hash": phash, "renders": len(first), "d": {n: dist[of[n]] for n in c}})
            print(arm, key, len(first), flush=True)
    finally:
        rr.close()


def e1_load_units(mode="report"):
    """The diagnostics' units (its stored scores and candidates), with every new arm's scores."""
    targets = json.loads((DIAG / "targets.json").read_text())
    cj = json.loads((DIAG / "candidates.json").read_text())
    scores = {str(int(p.stem)): json.loads(p.read_text()) for p in sorted((DIAG / "scores").glob("*.json"))}
    flat = json.loads((DIAG / "flat.json").read_text())
    rep = json.loads((DIAG / "report.json").read_text())
    for arm in ARM_SPEC:
        ppath = OUT / "e1" / f"proposals-{arm}.json"
        if not ppath.exists():
            continue
        phash = D.file_hash(ppath)
        props = json.loads(ppath.read_text())["targets"]
        for p in sorted((OUT / "e1" / "scores" / arm).glob("*.json")):
            s = json.loads(p.read_text())
            assert s["proposals_hash"] == phash, f"{p} scored from another proposals file"
            key = str(int(p.stem))
            scores[key]["d"].update(s["d"])
            cj["targets"][key].update(props[key])
    units = D.build_units(targets, cj["targets"], scores, flat)
    units = select_units(units, rep["setup"]["targets_dropped_repeat"], mode)
    if mode == "report":
        assert len(units) == sum(rep["readings"]["informative"].values()), "E1's unit list differs from the report"
    return units, targets, cj["targets"]


def cmd_report_1():
    units, targets, cands = e1_load_units("report")
    audit_units, _, _ = e1_load_units("audit")
    arms = [a for a in ("B1", "B2", "B1r", "B2a") if all(f"{a}|1b:A:top" in u["d"] for u in units)]
    menu = D._menu()
    tby = {str(t["i"]): t for t in targets}
    rep = {"units": len(units), "units_hash": units_hash(units), "audit_units": len(audit_units),
           "audit_units_hash": units_hash(audit_units), "arms": arms,
           "measures": {a: e1_measures(units, a) for a in ["B0", *arms]},
           "measures_audit_list": {a: e1_measures(audit_units, a)["top_vs_S_1b"] for a in ["B0", *arms]},
           "provisional_choice": provisional_choice(units, [a for a in arms if a in COST_ORDER])}
    shape = {}
    for a in ["B0", *arms]:
        rows = []
        for key, t in tby.items():
            _, S = D._S(menu, t["amp"], t["class"])
            pre = "" if a == "B0" else f"{a}|"
            for search in "AB":
                n = f"{pre}1b:{search}:top"
                if n in cands[key]:
                    rows.append((t["amp"], D.st(cands[key][n]), D.st(t["settings"])))
        shape[a] = answer_shape(rows)
    rep["answer_shape"] = shape
    if "B1" in arms and "B1r" in arms:
        rep["seed_yardstick_B1r_minus_B1"] = paired(units, lambda u: f"B1r|1b:{u['search']}:top",
                                                    lambda u: f"B1|1b:{u['search']}:top")
    K._atomic(OUT / "e1" / "report-1.json", rep)
    print(json.dumps({"units": rep["units"], "provisional": rep["provisional_choice"]["chosen"],
                      **{a: rep["measures"][a]["top_vs_S_1b"]["band_weighted_mean"] for a in ["B0", *arms]}}, indent=1))


# ============================================================================== CLI: E2

def _nets_for(arm):
    from learn import song_model as M

    return {f: (M.load_net(f) if arm == "B0" else load_net2(arm, f)) for f in range(4)}


def cmd_bridge(approved):
    require(approved, "E2 (the songs)")
    import numpy as np
    import torch

    from learn import arm_a_levers as AL

    torch.set_num_threads(THREADS)
    menu = D._menu()
    ps, fo = K.parts(), B.folds()
    preds = json.loads((SS_OUT / "armB" / "predictions.json").read_text())["cells"]
    arms = ["B0"] + [a for a in ("B1", "B2") if (MODELS / a / "fold0" / "DONE").exists()]
    nets = {a: _nets_for(a) for a in arms}
    ev = SS_OUT / "eval-features"
    rows = {a: {"rho": [], "rho_shuf": [], "diff": [], "picks": {}} for a in arms}
    # path statistics are per direction; bw() treats each direction's band as its row
    rows["B0_truncated_density"] = {"rho": [], "rho_shuf": [], "diff": []}
    for slug, amp, search, held in e3_cells():
        kc = json.loads((K.OUT / "cells" / slug / amp / "result.json").read_text())
        run = kc["runs"][search]
        if "K_S" not in run:
            continue
        part = ps[slug]
        cls = part["gain_class"]
        _, S = D._S(menu, amp, cls)
        traj, _ = AL.replay_ks(amp, S, run["K_S"]["evals"], search)
        xs = [x for x, _ in traj]
        hv = [d[held] for _, d in traj]
        sv = [d[search] for _, d in traj]
        dz = np.load(ev / f"{slug}.npz")
        dzo = np.load(ev / f"{preds[f'{slug}|{amp}|{search}']['shuffled0']['source']}.npz")
        fold, band = fo[part["band"]], part["band"]
        for a in arms:
            h = heads(nets[a][fold], dz[f"feat{search}"], dz[f"lufs{search}"], amp, cls)
            ho = heads(nets[a][fold], dzo[f"feat{search}"], dzo[f"lufs{search}"], amp, cls)
            kind = "truncated" if a == "B0" else "censored"
            sc = [box_logprob(h, x, amp, kind) for x in xs]
            so = [box_logprob(ho, x, amp, kind) for x in xs]
            r, ro = path_spearman(sc, hv), path_spearman(so, hv)
            if r is not None:
                rows[a]["rho"].append((band, r))
            if ro is not None:
                rows[a]["rho_shuf"].append((band, ro))
            if r is not None and ro is not None:
                rows[a]["diff"].append((band, r - ro))
            for k, v in path_picks(sc, hv, sv, run["K_S"]["start_held"]).items():
                rows[a]["picks"].setdefault(k, []).append((band, v))
            if a == "B0":
                td = [trunc_logdensity(h, x, amp) for x in xs]
                tdo = [trunc_logdensity(ho, x, amp) for x in xs]
                r, ro = path_spearman(td, hv), path_spearman(tdo, hv)
                if r is not None:
                    rows["B0_truncated_density"]["rho"].append((band, r))
                if ro is not None:
                    rows["B0_truncated_density"]["rho_shuf"].append((band, ro))
                if r is not None and ro is not None:
                    rows["B0_truncated_density"]["diff"].append((band, r - ro))
    rep = {a: {k: (bw(v) if isinstance(v, list) else {p: bw(w) for p, w in v.items()}) for k, v in r.items()}
           for a, r in rows.items()}
    (OUT / "e2").mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "e2" / "report.json", {"renders": 0, "report": rep})
    print(json.dumps({a: rep[a]["rho"]["band_weighted_mean"] for a in rep}, indent=1))


# ============================================================================== CLI: E3 and E4

def _key(slug, amp, search):
    return f"{slug}|{amp}|{search}"


def cmd_songs_top(approved):
    require(approved, "E3 (the songs)")
    import numpy as np
    import torch

    torch.set_num_threads(THREADS)
    menu = D._menu()
    ps, fo = K.parts(), B.folds()
    nets = {a: _nets_for(a) for a in ("B1", "B2")}
    ev = SS_OUT / "eval-features"
    out = {}
    for slug, amp, search, held in e3_cells():
        part = ps[slug]
        _, S = D._S(menu, amp, part["gain_class"])
        dz = np.load(ev / f"{slug}.npz")
        c = {}
        for a in ("B1", "B2"):
            h = heads(nets[a][fo[part["band"]]], dz[f"feat{search}"], dz[f"lufs{search}"], amp, part["gain_class"])
            c[f"{a}:top"] = D.sj(top_answer2(h, amp, S))
        out[_key(slug, amp, search)] = c
    check_cap("e3", spent(OUT / "e3" / "scores"), len(out) * 2 + 72)
    (OUT / "e3").mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "e3" / "proposals-top.json", out)


def cmd_songs_more(approved, b0_best8):
    """Best of 8 and the shuffled input for the chosen arm (B2 if E3 chose S, constant or B0), the
    C-fine picks, and B0's best of 8 only with `b0_best8` (the user's own yes)."""
    require(approved, "E3/E4 (the songs)")
    import numpy as np
    import torch

    from learn import arm_a_levers as AL

    torch.set_num_threads(THREADS)
    choice = json.loads((OUT / "e3" / "choice.json").read_text())
    arm = choice["chosen"] if choice["chosen"] in ("B1", "B2") else "B2"
    menu = D._menu()
    ps, fo = K.parts(), B.folds()
    preds = json.loads((SS_OUT / "armB" / "predictions.json").read_text())["cells"]
    nets = {a: _nets_for(a) for a in {arm, "B0"}}
    ev = SS_OUT / "eval-features"
    more, cfine, b0b8 = {}, {}, {}
    for slug, amp, search, held in e3_cells():
        part = ps[slug]
        cls, fold = part["gain_class"], fo[part["band"]]
        _, S = D._S(menu, amp, cls)
        key = _key(slug, amp, search)
        dz = np.load(ev / f"{slug}.npz")
        dzo = np.load(ev / f"{preds[key]['shuffled0']['source']}.npz")
        h = heads(nets[arm][fold], dz[f"feat{search}"], dz[f"lufs{search}"], amp, cls)
        ho = heads(nets[arm][fold], dzo[f"feat{search}"], dzo[f"lufs{search}"], amp, cls)
        h0 = heads(nets["B0"][fold], dz[f"feat{search}"], dz[f"lufs{search}"], amp, cls)
        rng = e3_sample_rng(slug, amp, search)
        c = {f"{arm}:s{k}": D.sj(draw(arm, h, amp, S, rng)) for k in range(K_E3)}
        c[f"{arm}:shuffled"] = D.sj(top_answer2(ho, amp, S))
        more[key] = c
        stored, _ = AL.stored_a(slug, amp, search)
        dims = K.space(amp, S)
        xs, obj = main_stage_settings(dims, S, stored["objective_curve"])
        cf = {}
        for name, hh, kind in ((arm, h, "censored"), ("B0", h0, "truncated"), (f"{arm}-shuffled", ho, "censored")):
            j = cfine_pick(xs, obj, lambda x, hh=hh, kind=kind: box_logprob(hh, x, amp, kind))
            if j is not None:
                cf[f"cfine:{name}"] = D.sj(xs[j])
        cfine[key] = cf
        if b0_best8:
            rng0 = e3_sample_rng(slug, amp, search)
            b0b8[key] = {f"B0:s{k}": D.sj(draw("B0", h0, amp, S, rng0)) for k in range(K_E3)}
    check_cap("e3", spent(OUT / "e3" / "scores"), sum(len(D.render_plan({n: D.st(x) for n, x in v.items()})[0])
                                                      for v in more.values()) + 72)
    check_cap("cfine", spent(OUT / "e3" / "scores-cfine"), sum(len(v) for v in cfine.values()) + 72)
    K._atomic(OUT / "e3" / "proposals-more.json", {"arm": arm, "cells": more})
    K._atomic(OUT / "e3" / "proposals-cfine.json", {"arm": arm, "cells": cfine})
    if b0_best8:
        check_cap("b0best8", spent(OUT / "e3" / "scores-b0best8"), K_E3 * len(b0b8) + 72)
        K._atomic(OUT / "e3" / "proposals-b0best8.json", {"arm": "B0", "cells": b0b8})


SCORE_FILES = {"top": ("proposals-top.json", "scores"), "more": ("proposals-more.json", "scores"),
               "cfine": ("proposals-cfine.json", "scores-cfine"),
               "b0best8": ("proposals-b0best8.json", "scores-b0best8")}


def cmd_score_songs(what, approved, shard):
    require(approved, "E3/E4 (the songs)")
    import numpy as np

    from learn import confirm_run as CR
    from learn import knob_ceiling2 as K2

    D.check_shards(shard[1])
    guard = D.MemoryGuard()
    pname, sdir = SCORE_FILES[what]
    ppath = OUT / "e3" / pname
    raw = json.loads(ppath.read_text())
    props = raw.get("cells", raw)
    phash = D.file_hash(ppath)
    d = OUT / "e3" / sdir / what
    d.mkdir(parents=True, exist_ok=True)
    ps = K.parts()
    group = SCORE_GROUP_CAP[what]
    capdir = OUT / "e3" / sdir
    rr = K.Renderer()
    try:
        menu = rr.menu()
        warm = set()
        for key in sorted(props)[shard[0]::shard[1]]:
            f = d / f"{key.replace('|', '_')}.json"
            if f.exists():
                continue
            if not K2.disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            slug, amp, search = key.split("|")
            part = ps[slug]
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            c = {n: D.st(x) for n, x in props[key].items()}
            first, of = D.render_plan(c)
            check_cap(group, spent(capdir), len(first) + int((slug, amp) not in warm))
            di = K.measure_di(part)
            di32, ref = di.astype(np.float32), CR.mono(part["crop"] / "reference.wav")
            n0 = rr.count
            if (slug, amp) not in warm:
                rr.render(di32, sel, S)
                warm.add((slug, amp))
            dist = {}
            for k, n in first.items():
                dist[k] = K.judge(ref, rr.render(di32, sel, c[n]), di, part["judge_lag"])
                guard.tick()
            K._atomic(f, {"proposals_hash": phash, "renders": rr.count - n0, "d": {n: dist[of[n]] for n in c}})
            print(what, key, rr.count - n0, flush=True)
    finally:
        rr.close()


def _e3_scores(what):
    pname, sdir = SCORE_FILES[what]
    ppath = OUT / "e3" / pname
    if not ppath.exists():
        return {}
    phash = D.file_hash(ppath)
    out = {}
    for p in sorted((OUT / "e3" / sdir / what).glob("*.json")):
        s = json.loads(p.read_text())
        assert s["proposals_hash"] == phash, f"{p} scored from another proposals file"
        out[p.stem] = s["d"]
    return out


def e3_units():
    """Step 3's units (`arm_a_levers.gathered_units`), its pre-existing drops (asserted to be the
    two in the ledger), and the new scores on the held half (d) and the search half (s)."""
    from learn import arm_a_levers as AL
    from learn import song_readout as R

    units, dropped = R.drop_refused(AL.gathered_units())
    assert sorted((s, a, h) for s, a, h, _ in dropped) == sorted(STEP3_DROPS), dropped
    assert len(units) == N_STEP3
    extra = {w: _e3_scores(w) for w in SCORE_FILES}
    for u in units:
        k = f"{u['slug']}_{u['amp']}_{u['search']}"
        u["target"] = u["slug"]
        u["s"] = {"S": u["S_search"]}
        for w, sc in extra.items():
            for n, v in sc.get(k, {}).items():
                u["d"][n] = v[u["held"]]
                u["s"][n] = v[u["search"]]
        kc = json.loads((K.OUT / "cells" / u["slug"] / u["amp"] / "result.json").read_text())
        curve = kc["runs"][u["search"]]["K_S"]["curve"]
        u["d"]["K_S@8"] = curve[min(8, len(curve)) - 1][2]
        e = LEVERS / "early"
        for name, sub in (("3-C'", "C'"), ("3-C'-shrink-0.5", "lever-shrink-0.5")):
            p = e / sub / u["slug"] / u["amp"] / f"{u['search']}.json"
            if p.exists():
                u["d"][name] = json.loads(p.read_text())["judge"][u["held"]]
    return units


def e3_names():
    return {"S": lambda u: "S", "constant": lambda u: "constant", "B0": lambda u: "B",
            "B1": lambda u: "B1:top", "B2": lambda u: "B2:top"}


def e3_unit_id(u):
    return (u["slug"], u["amp"], u["search"])


def cmd_report_2(approved):
    require(approved, "E3 (the songs)")
    units = e3_units()
    have = [a for a in ("B1", "B2") if all(f"{a}:top" in u["d"] for u in units)]
    if len(have) < 2:
        raise SystemExit("E3's top answers are not all scored yet")
    names = e3_names()
    ch = decide(units, names, COST_ORDER, e3_unit_id)
    (OUT / "e3").mkdir(parents=True, exist_ok=True)
    if not (OUT / "e3" / "choice.json").exists():
        K._atomic(OUT / "e3" / "choice.json", {"chosen": ch["chosen"], "best": ch["best"],
                                               "tied_with_best": ch["tied_with_best"], "deciding": "E3 top vs S"})
    rep = {"choice": ch, "vs_S": {a: paired(units, names[a], names["S"]) for a in ("constant", "B0", "B1", "B2")},
           "vs_B0": {a: paired(units, names[a], names["B0"]) for a in ("B1", "B2")},
           "vs_constant": {a: paired(units, names[a], names["constant"]) for a in ("B0", "B1", "B2")},
           "per_class": {c: {a: paired([u for u in units if u["cls"] == c], names[a], names["S"])
                             for a in ("B0", "B1", "B2")} for c in ("clean", "crunch")},
           "per_amp": {amp: {a: paired([u for u in units if u["amp"] == amp], names[a], names["S"])
                             for a in ("B0", "B1", "B2")} for amp in K.AMPS}}
    mp = OUT / "e3" / "proposals-more.json"
    more = json.loads(mp.read_text()) if mp.exists() else None
    if more and all(f"{more['arm']}:s0" in u["d"] for u in units):
        arm = more["arm"]
        rep["best8"] = _best8(units, arm)
        rep["shuffled"] = paired(units, lambda u: f"{arm}:top", lambda u: f"{arm}:shuffled")
    if all("B0:s0" in u["d"] for u in units):
        rep["best8_B0"] = _best8(units, "B0")
    if more:
        arm = more["arm"]
        rep["cfine"] = {n: {ref: paired(units, lambda u, n=n: n, lambda u, ref=ref: ref)
                            for ref in ("S", "3-C'", "3-C'-shrink-0.5", f"{arm}:top")}
                        for n in (f"cfine:{arm}", "cfine:B0", f"cfine:{arm}-shuffled")
                        if any(n in u["d"] for u in units)}
    K._atomic(OUT / "e3" / "report-2.json", rep)
    print(json.dumps({"chosen": ch["chosen"], "best": ch["best"], "ties": ch["tied_with_best"],
                      **{a: rep["vs_S"][a]["band_weighted_mean"] for a in rep["vs_S"]}}, indent=1))
    if ch["chosen"] in ("B1", "B2"):
        print("C-start may be offered to the user (it needs its own yes)")


def _best8(units, arm):
    rows_S, rows_ks, nref = [], [], 0
    for u in units:
        v, n = best_k_held(u, [f"{arm}:s{k}" for k in range(K_E3)])
        nref += n
        rows_S.append((part_of(u), u["band"], math.log(v / u["d"]["S"])))
        if finite(u["d"].get("K_S@8")) and u["d"]["K_S@8"] > 0:
            rows_ks.append((part_of(u), u["band"], math.log(v / u["d"]["K_S@8"])))
    return {"vs_S": bw_parts(rows_S), "vs_KS8": bw_parts(rows_ks), "refused": nref}


def cmd_c_start(approved, shard):
    import numpy as np

    from learn import arm_a_levers as AL
    from learn import knob_ceiling2 as K2
    from learn import song_settings as SS

    arm = c_start_allowed(json.loads((OUT / "e3" / "choice.json").read_text()), approved)
    D.check_shards(shard[1])
    guard = D.MemoryGuard()
    tops = json.loads((OUT / "e3" / "proposals-top.json").read_text())
    ps = K.parts()
    d = OUT / "c-start"
    d.mkdir(parents=True, exist_ok=True)
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug, amp, search, held in e3_cells()[shard[0]::shard[1]]:
            f = d / slug / amp / f"{search}.json"
            if f.exists():
                continue
            if not K2.disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            check_cap("c_start", spent(d), 54)
            part = ps[slug]
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            x0 = D.st(tops[_key(slug, amp, search)][f"{arm}:top"])
            rebuilt = np.load(SS_OUT / "rebuilt" / f"{slug}.npy")
            stem_x = SS.stem(slug)
            r32 = rebuilt.astype(np.float32)
            counter = {"fallback": 0}
            n0 = rr.count
            rr.render(r32, sel, S)                                          # warm-up, as arm A

            def obj(x):
                guard.tick()
                return SS.rebuilt_objective(stem_x, rr.render(r32, sel, x), rebuilt, search, counter)

            x, best, n = AL.main_stage(K.space(amp, S), x0, obj, seed=SEED_C_START)
            di = K.measure_di(part)
            from learn import confirm_run as CR
            j = K.judge(CR.mono(part["crop"] / "reference.wav"), rr.render(di.astype(np.float32), sel, x), di,
                        part["judge_lag"])
            f.parent.mkdir(parents=True, exist_ok=True)
            K._atomic(f, {"judge": j, "held": held, "main_best": best, "main_renders": n,
                          "fallback": counter["fallback"], "renders": rr.count - n0, "settings": D.sj(x)})
            print(slug, amp, search, round(j[held], 4), flush=True)
    finally:
        rr.close()


def cmd_report_3():
    units = e3_units()
    for u in units:
        p = OUT / "c-start" / u["slug"] / u["amp"] / f"{u['search']}.json"
        if p.exists():
            u["d"]["c-start"] = json.loads(p.read_text())["judge"][u["held"]]
    arm = json.loads((OUT / "e3" / "choice.json").read_text())["chosen"]
    rep = {ref: paired([u for u in units if "c-start" in u["d"]], lambda u: "c-start", lambda u, r=ref: r)
           for ref in ("S", "3-C'", f"{arm}:top")}
    K._atomic(OUT / "c-start-report.json", rep)
    print(json.dumps({r: v["band_weighted_mean"] for r, v in rep.items()}, indent=1))


# ============================================================================== CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("mem-dry-run", "mem-check", "train", "propose-targets", "score-targets",
                                     "report-1", "bridge", "songs-top", "score-songs", "report-2", "songs-more",
                                     "c-start", "report-3"))
    ap.add_argument("--arm", choices=tuple(ARM_SPEC))
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--what", choices=tuple(SCORE_FILES))
    ap.add_argument("--render-rss-gb", type=float)
    ap.add_argument("--user-approved", action="store_true", help="the songs' yes (E2, E3, C-fine)")
    ap.add_argument("--optional-approved", action="store_true", help="B1′ or B2a: the user's own yes")
    ap.add_argument("--b0-best8-approved", action="store_true", help="B0's best of 8: the user's own yes")
    ap.add_argument("--c-start-approved", action="store_true", help="C-start: the user's own yes")
    a = ap.parse_args(argv)
    i, n = map(int, a.shard.split("/"))
    if a.step == "train":
        arm_allowed(a.arm, a.optional_approved)
    {"mem-dry-run": lambda: cmd_mem_dry_run(a.fold), "mem-check": lambda: cmd_mem_check(a.render_rss_gb),
     "train": lambda: train(a.arm, a.fold), "propose-targets": lambda: cmd_propose_targets(a.arm, a.optional_approved),
     "score-targets": lambda: cmd_score_targets(a.arm, (i, n), a.optional_approved), "report-1": cmd_report_1,
     "bridge": lambda: cmd_bridge(a.user_approved), "songs-top": lambda: cmd_songs_top(a.user_approved),
     "score-songs": lambda: cmd_score_songs(a.what, a.user_approved, (i, n)),
     "report-2": lambda: cmd_report_2(a.user_approved),
     "songs-more": lambda: cmd_songs_more(a.user_approved, a.b0_best8_approved),
     "c-start": lambda: cmd_c_start(a.c_start_approved, (i, n)), "report-3": cmd_report_3}[a.step]()


if __name__ == "__main__":
    main()
