"""T3's label space: every Morgan control (`docs/every-control-plan.md`, amendment 2; the T3 design in
`docs/trusted-data-t0-design.md`, "T3 (declared 2026-10-26)"). Pure parts only: the layout, the new controls' draw,
the encoding with the switched-off mask, the written answer, the network with its amp head and the masked loss.
The commands that use them are in `learn/trusted_data_t3.py`.

**The space:** the 115 Morgan controls of `every_control.table` (union over the three amps; never-set and
reparametrised controls out). Continuous ones on the unit interval over their declared range (`knob_ceiling.Dim`:
log for frequencies and times), switches as one probability each, the two mics as 10-way heads, the amp choice as a
3-way head that reads the audio only. Output gain is not a head: it is fitted to loudness per answer (confirmed by
the user 2026-10-26, amendment 2), and training renders hold it at the draw's base preset value (S's).
The spring is a derived switch (`springOn`, level above 0) plus its level, masked when off and written back as 0.

**Switched-off features** (the user's rule): the loss, E, the constant and the pull weigh a dimension only where it
sounds in the true label (`every_control.mask`, mono). A switch is scored whenever its own gate sounds; the amp
choice always. An answer writes a feature it switches off at its neutral values (`every_control.neutralise`).

**The new controls' draw** (seed 20261107 per example; T3 design, "How a new example is drawn"): part C's mode of the
example, part C's draw rule on the new controls around the mode's centre (factory: the same factory preset as the
core draw, un-dried; start: S; wide: uniform in unit space, each switch on with p 0.5):
- continuous: factory and start jitter the centre's unit value by part C's sigma (0.1), wide draws uniformly; the
  gate threshold's wide draw stops at the factory presets' 95th percentile (`gate_cap_u`);
- switches: factory and start keep the centre's value with part C's keep probability (0.7, else a fair coin), wide
  is a fair coin;
- the spring's derived switch: factory and start on when the centre's level is above 0 (the plan's own rule), wide a
  fair coin; its level then jittered (above 0) or uniform above 0;
- a draw with both cabs off is redrawn (the plugin needs one cab on);
- written as sync off (the delay's time in ms, the tremolo's rate in Hz) and every section on; a section the centre
  has off has its features switched off first (the same sound).
"""

from __future__ import annotations

import math
import random

import functools

from learn import every_control as EC
from learn import knob_ceiling as K
from learn import song_model as SM
from learn.knob_ceiling import Dim

PACK = "morgan"
AMPS = ("pr12", "sw50r", "ac20")                  # song_model.AMPS's order (the condition vector)
NEW_SEED = 20261107                              # the new controls' stream, per example
SIGMA = 0.1                                      # part C's jitter (pretrain_set.SIGMA)
KEEP_P = 0.7                                     # part C's switch keep probability (pretrain_set.KEEP_P)
GATE_CAP_PCT = 95                                # the wide gate threshold stops at the factory presets' 95th pct
SPRING_KEY = "springOn"
SPRING = {"pr12": ("pr12Amp", "pr12Reverb"), "sw50r": ("sw50rAmp", "sw50rReverb")}
SPRING_MIN = 1e-3                                # an "on" spring's least level (stored, so level 0 stays "off")
FREE = {("delay", "delaySync"): "0", ("tremolo", "tremoloSync"): "false"}   # sync off: syncMode 0 is Free
SECTIONS = ("ampParameters", "eqParameters", "pedalParameters", "cabParameters", "fxParameters")
SECTION_MEMBERS = {"eqParameters": tuple((f"{a}EQ", f"{a}EQActive") for a in AMPS),
                   "pedalParameters": (("compressor", "compressorActive"), ("drive1", "drive1Active"),
                                       ("drive2", "drive2Active")),
                   "fxParameters": (("reverb", "reverbActive"), ("delay", "delayActive"), ("tremolo", "tremoloActive"))}
OUTPUT = ("parameters", "outputGain")
OUTPUT_RANGE = (-24.0, 24.0)                     # the manifest's
AMP = ("", "selectedAmp")
CABS = (("cabParameters", "leftCabActive"), ("cabParameters", "rightCabActive"))
GATE_THR = ("parameters", "gateThreshold")
# The answer families of the T3 readout ("the answer minus the answer with one family at S")
FAMILIES = {"EQ": ("amp_eq",), "pedals": ("pedals",), "time effects and spring": ("time_effects", "spring"),
            "gate and doubler": ("gate_doubler",), "cab rest": ("cab_rest",)}
OUTPUT_FIT_STATUS = "confirmed by the user 2026-10-26 (amendment 2)"


# --- the layout ------------------------------------------------------------------------------------------------

def spring_dim(amp):
    m, _ = SPRING[amp]
    return Dim(m, SPRING_KEY, "switch", values=("false", "true"))


def _known_dims():
    """{path: Dim} from the stages that declared each range (today's space, knob ceiling's EQ, knob ceiling 2's
    pedals, effects and spring, stage 1's groups and the screen)."""
    from learn import knob_ceiling2 as K2

    out = {}
    for amp in AMPS:
        for d in K.space(amp) + K.eq_space(amp):
            out.setdefault((d.module, d.key), d)
    for d in K2.pedal_dims():
        out.setdefault((d.module, d.key), d)
    for _, (sw, _, dims) in K2.EFFECTS.items():
        out.setdefault(sw, Dim(*sw, "switch", values=("false", "true")))
        for d in dims:
            out.setdefault((d.module, d.key), d)
    for _, (_, dims) in K2.SPRING.items():
        for d in dims:
            out.setdefault((d.module, d.key), d)
    return out


def learned_controls():
    """The table's controls that take a head (the 115 less the amp choice and output gain), in table order."""
    return [c for c in EC.table(PACK) if c.source not in ("never", "reparam") and c.path not in (AMP, OUTPUT)]


def space_controls():
    """The full label space: every Morgan control but the never-set and reparametrised ones (115)."""
    return [c for c in EC.table(PACK) if c.source not in ("never", "reparam")]


@functools.lru_cache(maxsize=None)
def dims():
    """{path: Dim} of every learned control: the declared range where a stage declared one, else stage 1's
    (`every_control._dim`)."""
    known = _known_dims()
    return {c.path: known.get(c.path) or EC._dim(c.path) for c in learned_controls()}


def layout():
    """(continuous names, switch names, mic names) of the heads, in table order; the derived spring switches follow
    the switches."""
    D = dims()
    cont = [D[c.path].name for c in learned_controls() if D[c.path].kind in ("cont", "log")]
    sw = [D[c.path].name for c in learned_controls() if D[c.path].kind == "switch"] + [spring_dim(a).name for a in SPRING]
    cat = [D[c.path].name for c in learned_controls() if D[c.path].kind == "cat"]
    return cont, sw, cat


CONT, SW, CAT = layout()
MICS = list(K.MICS)
TODAY = frozenset(SM.CONT + SM.SW + SM.CAT)            # today's space (part C's labels): 25 names


@functools.lru_cache(maxsize=None)
def by_name():
    D = dims()
    out = {d.name: d for d in D.values()}
    out.update({spring_dim(a).name: spring_dim(a) for a in SPRING})
    return out


@functools.lru_cache(maxsize=None)
def new_paths():
    """The learned controls outside today's space (the new controls of the F5 twins), in table order."""
    D = dims()
    return tuple(c.path for c in learned_controls() if D[c.path].name not in TODAY)


def family_of(path):
    by = {c.path: c for c in EC.table(PACK)}
    return by[path].family


def cell_masks(amp):
    """(continuous, switch, mic) masks of the dims that can sound on `amp` (a cell's labelled space)."""
    import numpy as np

    by = {c.path: c for c in EC.table(PACK)}
    D = dims()
    name_amp = {D[p].name: by[p].amp for p in D}
    name_amp.update({spring_dim(a).name: a for a in SPRING})
    ok = lambda n: name_amp[n] in (None, amp)          # noqa: E731
    return (np.array([ok(n) for n in CONT]), np.array([ok(n) for n in SW]), np.array([ok(n) for n in CAT]))


# --- the encoding (masked by what sounds) -----------------------------------------------------------------------

def _truthy(v):
    return str(v).strip().lower() in ("true", "1")


def spring_on(x, amp):
    if amp not in SPRING:
        return False
    try:
        return float(x.get(SPRING[amp], "0")) > 0
    except (TypeError, ValueError):
        return False


def sounding(x, amp):
    """{path: sounds?} of every learned control in setting x on amp (mono, as the judge and the inputs); the
    springs' derived switches by their level's gate, their levels only when on."""
    m = EC.mask(x, PACK, amp=amp, mono=True)
    out = {p: m[p] for p in dims()}
    for a, p in SPRING.items():
        out[(p[0], SPRING_KEY)] = m[p]
        out[p] = m[p] and spring_on(x, a)
    return out


def encode(x, amp):
    """A full setting {(module, key): stored} on amp -> (cont, cont_mask, sw, sw_mask, mic, mic_mask, amp index), the
    masks 1 only where the dimension sounds (and the setting stores it)."""
    import numpy as np

    D = by_name()
    snd = sounding(x, amp)
    c = np.zeros(len(CONT), np.float32)
    cm = np.zeros(len(CONT), np.float32)
    s = np.zeros(len(SW), np.float32)
    sm = np.zeros(len(SW), np.float32)
    k = np.zeros(len(CAT), np.int64)
    km = np.zeros(len(CAT), np.float32)
    for j, n in enumerate(CONT):
        d = D[n]
        p = (d.module, d.key)
        if p in x:
            c[j] = d.to_unit(x[p])
            cm[j] = float(snd[p])
    for j, n in enumerate(SW):
        d = D[n]
        p = (d.module, d.key)
        if d.key == SPRING_KEY:
            a = next(a for a, q in SPRING.items() if q[0] == d.module)
            s[j], sm[j] = float(spring_on(x, a)), float(snd[p])
        elif p in x:
            s[j], sm[j] = float(_truthy(x[p])), float(snd[p])
    for j, n in enumerate(CAT):
        d = D[n]
        p = (d.module, d.key)
        if p in x and str(x[p]) in MICS:
            k[j], km[j] = MICS.index(str(x[p])), float(snd[p])
    return c, cm, s, sm, k, km, np.int64(AMPS.index(amp))


def label_of(x, amp):
    """A full label (JSON): the amp and the setting ({"module/key": stored})."""
    return {"amp": amp, "settings": {f"{a}/{b}": v for (a, b), v in sorted(x.items())}}


def encode_label(label):
    """`encode` from a stored full label; the six arrays `song_model.encode` gives (the amp apart)."""
    x = {tuple(k.rsplit("/", 1)): v for k, v in label["settings"].items()}
    return encode(x, label["amp"])[:6]


# --- the new controls' draw ------------------------------------------------------------------------------------

def gate_cap_u(thresholds, pct=GATE_CAP_PCT):
    """The wide gate threshold's upper end in unit space: the factory presets' `pct` percentile (nearest rank)."""
    v = sorted(float(t) for t in thresholds)
    if not v:
        raise ValueError("no factory gate thresholds")
    k = max(0, min(len(v) - 1, int(math.ceil(pct / 100 * len(v))) - 1))
    return dims()[GATE_THR].to_unit(v[k]), v[k]


def sections_on(centre):
    """The centre with every section on; a section it has off has its features switched off first."""
    y = dict(centre)
    for sec in SECTIONS:
        if not _truthy(y.get((sec, "sectionActive"), "true")):
            for p in SECTION_MEMBERS.get(sec, ()):
                y[p] = "false"
        y[(sec, "sectionActive")] = "true"
    return y


def _centre_value(centre, S, p, by):
    if p in centre:
        return centre[p]
    if p in S:
        return S[p]
    return by[p].neutral


def draw_once(rng, mode, centre, S, gate_u):
    """One draw of the new controls (part C's rule, the T3 design's modes). -> {(module, key): stored}."""
    by = {c.path: c for c in EC.table(PACK)}
    D = dims()
    springs = {p for p in SPRING.values()}
    out = {}
    for p in new_paths():
        d = D[p]
        if p in springs:
            if mode == "wide":
                on = rng.random() < 0.5
                u = 1.0 - rng.random() if on else 0.0
            else:
                lv = d.to_unit(_centre_value(centre, S, p, by))
                on = lv > 0
                u = min(1.0, max(d.to_unit(SPRING_MIN), lv + rng.gauss(0, SIGMA))) if on else 0.0
            out[p] = K.fmt(max(SPRING_MIN, d.from_unit(u))) if on else "0"
            continue
        if d.kind in ("cont", "log"):
            if mode == "wide":
                u = rng.random() * (gate_u if p == GATE_THR else 1.0)
            else:
                u = min(1.0, max(0.0, d.to_unit(_centre_value(centre, S, p, by)) + rng.gauss(0, SIGMA)))
            out[p] = K.fmt(d.from_unit(u))
        elif d.kind == "switch":
            v = str(_centre_value(centre, S, p, by)).lower()
            if mode == "wide" or rng.random() > KEEP_P or v not in d.values:
                v = rng.choice(d.values)
            out[p] = v
        else:                                                     # no new categorical control (the mics are today's)
            raise ValueError(f"{p}: a new categorical control")
    return out


def full_settings(core, new):
    """The full twin's setting: the core draw (today's space and S's values elsewhere, output gain S's), the new
    controls, sync off and every section on."""
    x = dict(core)
    x.update(new)
    x.update(FREE)
    for sec in SECTIONS:
        x[(sec, "sectionActive")] = "true"
    return x


def cabs_ok(x):
    return any(_truthy(x.get(p, "true")) for p in CABS)


def draw_new(i, mode, core, centre, S, gate_u, max_tries=1000):
    """The new controls of example i (seed NEW_SEED, i) around `centre` (factory: the un-dried factory preset; start:
    S; wide: unused), redrawn while the full setting has both cabs off. -> (full setting, tries)."""
    from learn import pretrain_set as PS

    rng = random.Random(PS.seed_int(NEW_SEED, int(i)))
    c = sections_on(centre if mode == "factory" else S)
    for t in range(1, max_tries + 1):
        x = full_settings(core, draw_once(rng, mode, c, S, gate_u))
        if cabs_ok(x):
            return x, t
    raise SystemExit(f"{i}: no draw with a cab on in {max_tries} tries")


def positive_settings(core, S):
    """The positive control's setting: the full pipeline's setting with every new control at S's value."""
    return full_settings(core, {p: S[p] for p in new_paths() if p in S})


# --- the written answer ----------------------------------------------------------------------------------------

def answer_settings(amp, S, cont, sw_p, mics, at_S=()):
    """A full answer on top of S (amp's class start): every dim that can sound on amp from the heads (continuous on
    the unit interval, switch probabilities on above 0.5, mic indices), the spring's level 0 when its switch is off,
    sync off and every section on; the families in `at_S` back at S's values; both cabs off -> the likelier cab on;
    then a switched-off feature written at its neutral values. Output gain stays S's (fitted at render).
    -> {(module, key): stored}."""
    cm, swm, km = cell_masks(amp)
    D = by_name()
    x = sections_on(dict(S))
    for j, n in enumerate(CONT):
        if cm[j] and math.isfinite(float(cont[j])):
            d = D[n]
            x[(d.module, d.key)] = K.fmt(d.from_unit(float(cont[j])))
    pon = {}
    for j, n in enumerate(SW):
        if not swm[j] or sw_p[j] is None or not math.isfinite(float(sw_p[j])):
            continue
        d = D[n]
        if d.key == SPRING_KEY:
            a = next(a for a, q in SPRING.items() if q[0] == d.module)
            if float(sw_p[j]) <= 0.5:
                x[SPRING[a]] = "0"
            elif not spring_on(x, a):                         # on, but the level head reads 0: its least level
                x[SPRING[a]] = K.fmt(SPRING_MIN)
            continue
        pon[(d.module, d.key)] = float(sw_p[j])
        x[(d.module, d.key)] = d.values[int(float(sw_p[j]) > 0.5)]
    for j, n in enumerate(CAT):
        if km[j] and mics[j] is not None:
            d = D[n]
            x[(d.module, d.key)] = MICS[int(mics[j])]
    x.update(FREE)
    fams = {f for k in at_S for f in FAMILIES[k]}
    if fams:
        for c in EC.table(PACK):
            if c.family in fams and c.path in S:
                x[c.path] = S[c.path]
    if not cabs_ok(x):
        p = max(CABS, key=lambda q: (pon.get(q, 0.0), q == CABS[1]))
        x[p] = "true"
    return EC.neutralise(x, PACK, amp=amp, mono=False)


def output_gain_fit(gain_now, render_lufs, target_lufs, lo=OUTPUT_RANGE[0], hi=OUTPUT_RANGE[1]):
    """The output gain that brings a render (made at `gain_now` dB) to the target's loudness, within the manifest's
    range (output gain is a post gain: the level moves dB for dB). Confirmed by the user 2026-10-26
    (amendment 2). -> (gain, clamped?)."""
    g = gain_now + (target_lufs - render_lufs)
    c = min(hi, max(lo, g))
    return c, c != g


# --- the network: today's body and trunk, wider heads and the amp head ---------------------------------------------

def build_net(width=None):
    """`pretrain_set.build_net` widened to the full space: the mixture, switch and mic heads over the full layout,
    and an amp head (3-way) on the audio features alone, before the amp and class condition joins the trunk.
    forward -> (logpi, mu, ls, switch logits, [mic logits], amp logits)."""
    import torch
    import torch.nn as nn

    from learn import pretrain_set as PS
    from learn import song_model as SM

    width = width or PS.WIDTHS

    class Block(nn.Module):
        def __init__(self, i, o):
            super().__init__()
            self.net = nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(),
                                     nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU())
            self.skip = nn.Conv2d(i, o, 1)
            self.pool = nn.AvgPool2d(2)

        def forward(self, x):
            return self.pool(self.net(x) + self.skip(x))

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            c = (2, *width)
            self.body = nn.Sequential(*[Block(c[j], c[j + 1]) for j in range(len(width))])
            feat = width[-1] * (96 // 2 ** len(width)) * 2
            d = feat + len(SM.AMPS) + len(SM.CLASSES) + 2
            self.amp = nn.Sequential(nn.Linear(feat, 256), nn.ReLU(), nn.Linear(256, len(AMPS)))
            self.trunk = nn.Sequential(nn.Linear(d, 256), nn.ReLU(), nn.Dropout(0.2), nn.Linear(256, 256), nn.ReLU())
            n = len(CONT)
            self.pi = nn.Linear(256, SM.K_MIX)
            self.mu = nn.Linear(256, SM.K_MIX * n)
            self.ls = nn.Linear(256, SM.K_MIX * n)
            self.sw = nn.Linear(256, len(SW))
            self.cat = nn.ModuleList([nn.Linear(256, len(MICS)) for _ in CAT])

        def forward(self, x, cond):
            h = self.body(x)
            h = torch.cat([h.mean(-1), h.std(-1)], dim=1).flatten(1)
            amp = self.amp(h)                                   # the audio only
            h = self.trunk(torch.cat([h, cond], dim=1))
            n = len(CONT)
            return (torch.log_softmax(self.pi(h), -1), torch.sigmoid(self.mu(h)).view(-1, SM.K_MIX, n),
                    self.ls(h).view(-1, SM.K_MIX, n).clamp(-6, 1), self.sw(h), [c(h) for c in self.cat], amp)

    return Net()


def loss_fn(out, c, cm, s, sm, k, km, a):
    """`song_model.loss_fn` on the full heads with the switched-off mask (the masks are the encoding's), plus the
    amp head's cross-entropy (always scored)."""
    import torch
    import torch.nn.functional as F

    logpi, mu, ls, swl, catl, ampl = out
    z = (c.unsqueeze(1) - mu) / ls.exp()
    lp = (-0.5 * z ** 2 - ls - 0.5 * math.log(2 * math.pi)) * cm.unsqueeze(1)
    nll = -torch.logsumexp(logpi + lp.sum(-1), dim=-1)
    nll = (nll / cm.sum(-1).clamp(min=1)).mean()
    bce = (F.binary_cross_entropy_with_logits(swl, s, reduction="none") * sm).sum() / sm.sum().clamp(min=1)
    ce = sum((F.cross_entropy(catl[j], k[:, j], reduction="none") * km[:, j]).sum() / km[:, j].sum().clamp(min=1)
             for j in range(len(catl)))
    return nll + bce + ce + F.cross_entropy(ampl, a)


# --- the readout (amendment 5's, extended) -------------------------------------------------------------------

def run_nets(nets, X, C, batch=128):
    """-> per seed, per row: (logpi, mu, ls, switch logits, [mic logits], amp logits or None) as numpy (a
    today's-space net has no amp head)."""
    import numpy as np
    import torch

    outs = [[] for _ in nets]
    with torch.no_grad():
        for j in range(0, len(X), batch):
            x = torch.tensor(np.asarray(X[j:j + batch], np.float32))
            c = torch.tensor(np.asarray(C[j:j + batch], np.float32))
            for k, net in enumerate(nets):
                o = net(x, c)
                amp = o[5] if len(o) > 5 else None
                for n in range(len(x)):
                    outs[k].append((o[0][n].numpy(), o[1][n].numpy(), o[2][n].numpy(), o[3][n].numpy(),
                                    [z[n].numpy() for z in o[4]], None if amp is None else amp[n].numpy()))
    return outs


def _softmax(z):
    import numpy as np

    z = np.asarray(z, np.float64)
    e = np.exp(z - z.max())
    return e / e.sum()


def readout(outs):
    """The T3 readout of one input. outs: per seed (logpi, mu, ls, switch logits, [mic logits], amp logits).
    -> {"a1": per seed medians, "a2": their mean, "sw_p": the mean switch probability, "mics": the argmax of the
    mean mic probabilities, "amp": the argmax of the mean amp probabilities (None without an amp head), and per seed
    "sw_p_seed", "mics_seed", "amp_p"}."""
    import numpy as np

    from learn import direct_stems as DS

    a1 = [DS.mixture_median(o[0], o[1], o[2]) for o in outs]
    swp = [1.0 / (1.0 + np.exp(-np.asarray(o[3], np.float64))) for o in outs]
    mp = [[_softmax(z) for z in o[4]] for o in outs]
    mean_mp = [np.mean([m[j] for m in mp], axis=0) for j in range(len(mp[0]))]
    amp_p = [None if o[5] is None else _softmax(o[5]) for o in outs]
    amp = None
    if all(p is not None for p in amp_p):
        amp = AMPS[int(np.argmax(np.mean(amp_p, axis=0)))]
    return {"a1": a1, "a2": np.mean(a1, axis=0), "sw_p": np.mean(swp, axis=0), "sw_p_seed": swp,
            "mics": [int(np.argmax(m)) for m in mean_mp], "mics_seed": [[int(np.argmax(z)) for z in m] for m in mp],
            "amp": amp, "amp_p": None if amp is None else [float(v) for v in np.mean(amp_p, axis=0)]}
