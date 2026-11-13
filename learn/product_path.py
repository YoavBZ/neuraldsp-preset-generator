"""The model path for a real song: one copy for the generate skill's model flag and for the real-song test
(`docs/full-controls-plan.md`, "The model path"). Four stages, each writing into one folder for the next, because the
separator, the model and the renderer live in different environments:

    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.product_path separate SONG --out DIR [--start S]
    $TORCH_PY -m learn.product_path answers DIR --cls clean|crunch
    .venv/bin/python -m learn.product_path render DIR                    # 12 renders (3 amps x 2 stock DIs, primed)
    $TORCH_PY -m learn.product_path pick DIR                             # the amp and the output gain -> DIR/preset.json
    .venv/bin/python -m learn.product_path delay DIR [--mix M --feedback F --source S]   # optional: -> DIR/delay.json

What each stage reproduces, and where it was validated:
- **separate:** the song's 10-s window, separated by X-LANCE `gtr_mss` (the model's real-song input: V-real read 3, F41;
  N5b). With no start given, the window where the stem sits loudest against the mix (exposure matters: F87, F88).
- **answers:** the adopted model (`adopted-model.json`: R-all's all-labels pair, both seeds, held as C3-cabS) on each
  amp, from the window's half A at V-real read 3's level (the mix brought to -12.25 LUFS, the stem by the same gain).
- **render:** each amp's answer through the class's two stock DIs (A1's), fresh and primed, trimmed (F80, F81).
- **pick:** the amp whose renders sit closest to the stem in the model's floored body features, by cosine averaged over
  the DIs (F80 to F83); then the output gain that plays it at S's loudness on those renders, clamped, on the plugin's
  0.1 dB grid (F84).
- **delay (optional):** D1's candidate delay reader (F88, F89): the stem's own delay features against E1e's clean targets
  of the picked amp (15 neighbours); on when 70% of them have a delay; the time from the stem's cepstral peak when its
  halves agree within 10%, else the neighbours' median. Mix and feedback come from the song research when the skill
  passes them, else a declared conservative default (0.30, 0.30); the source is recorded.
The other effects stay the generate skill's (song research). The pure parts are unit-tested; the stages are smoke-tested.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import time

WINDOW_S = 10.0                       # the model's section (`pretrain_set.SEC_S`)
HOP_S = 5.0                           # the window search's step
MIX_LEVEL = -12.25                    # V-real read 3's mix level (`pipeline_fix.DFIX_VREAL_LEVEL`)
HALF = "A"                            # the half the answer and the pick read (both halves validated; one fixed)
FLOOR_U8 = 44                         # A1's -90 dB floor on every embedded input
EMBED_AMP = "sw50r"                   # A1's conditioning for every embedding
AMPS = ("pr12", "sw50r", "ac20")


# --- the pure parts -----------------------------------------------------------------------------------------------------

def exposure_window(levels):
    """levels: [(start_s, stem LUFS, mix LUFS)] -> the start whose stem sits loudest against its mix (ties: earliest)."""
    best = max(levels, key=lambda r: (r[1] - r[2], -r[0]))
    return best[0]


def cosine_distance(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return 1.0 - sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 1.0


def pick_amp(stem_feat, render_feats):
    """render_feats: {amp: [features per stock DI]} -> (the amp with the least mean cosine distance, {amp: distance})."""
    dist = {a: sum(cosine_distance(stem_feat, r) for r in rs) / len(rs) for a, rs in render_feats.items()}
    return min(sorted(dist), key=lambda a: dist[a]), dist


# --- the stages ---------------------------------------------------------------------------------------------------------

def _save(p, obj):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=str))


def cmd_separate(args):
    """The song's window and its X-LANCE stem -> DIR/window.npz, DIR/window.json."""
    import numpy as np
    import soundfile as sf

    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import trusted_data as T

    out = pathlib.Path(args.out)
    sep = DS.stem_separator(T.SEP, args.device)
    n = int(WINDOW_S * PS.SR)
    if args.start is not None:
        starts = [float(args.start)]
    else:
        dur = sf.info(args.song).duration
        starts = [s * HOP_S for s in range(int(max(0.0, dur - WINDOW_S) // HOP_S) + 1)]
    levels, keep = [], {}
    for s in starts:
        mix = np.asarray(PS.load_mono(args.song, PS.SR, s, WINDOW_S), np.float64)
        mix = np.pad(mix, (0, max(0, n - len(mix))))[:n]
        stem = np.asarray(sep(mix), np.float64)
        levels.append((s, float(SA.lufs(stem)), float(SA.lufs(mix))))
        keep[s] = (mix, stem)
    start = exposure_window(levels)
    mix, stem = keep[start]
    np.savez(out / "window.npz", mix=mix.astype(np.float32), stem=stem.astype(np.float32))
    _save(out / "window.json", {"song": str(args.song), "start_s": start, "chosen_by": "given" if args.start is not None
                                 else "exposure", "levels": levels, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"SEPARATE: window at {start:.1f} s ({len(levels)} tried)")


def _adopted():
    from learn import full_controls_c3 as C3
    from learn import pipeline_fix as P

    a = json.loads((P.out_dir() / "adopted-model.json").read_text())
    loaded = [P.load_run(a["model"]["base"], sd, "best") for sd in P.SEEDS]
    if [r["model_sha256"]["best"] for _, r in loaded] != [a["model"]["sha256"][str(sd)]["best"] for sd in P.SEEDS]:
        raise SystemExit("the adopted model's runs differ from adopted-model.json")
    if not str(a.get("answer_hold", "")).startswith("C3-cabS"):
        raise SystemExit("adopted-model.json names another hold than C3-cabS, the one C4 and C3r read")
    hold = C3.hold_for("C3-cabS")
    return [n_.eval() for n_, _ in loaded], hold, P.model_input_lufs(loaded[0][1])


def _feats(nets, x):
    import numpy as np
    import torch

    with torch.no_grad():
        X = torch.tensor(np.asarray([x], np.float32))
        hs = [torch.cat([(h := net.body(X)).mean(-1), h.std(-1)], dim=1).flatten(1)[0].numpy() for net in nets]
    return np.mean(hs, 0).tolist()


def cmd_answers(args):
    """The adopted model's answer on each amp, and the stem's floored features -> DIR/answers.json."""
    import numpy as np

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    d = pathlib.Path(args.dir)
    w = np.load(d / "window.npz")
    mix, stem = np.asarray(w["mix"], np.float64), np.asarray(w["stem"], np.float64)
    nets, hold, model_lufs = _adopted()
    g = DE.inference_gain_db(mix, MIX_LEVEL)
    s8, _, ls, _ = DS.step4_half(stem, mix, HALF, g)
    ms = P.A_menu_S()
    ans = {}
    for a in AMPS:
        sel, S = ms[a][args.cls]
        x, c = P.vreal_model_input(s8, ls, HALF, a, args.cls)
        r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
        st = F.answer_settings(a, S, r["a2"], r["sw_p"], r["mics"])
        st = P.hold_outside_space(st, S, a) if hold is None else P.hold_outside_space(st, S, a, hold)
        ans[a] = {"select": sel, "settings": LO.sdict(st), "amp_p": r.get("amp_p")}
    f = _feats(nets, DS.model_input(np.maximum(s8, FLOOR_U8), np.maximum(s8, FLOOR_U8), ls, ls, HALF, EMBED_AMP,
                                    args.cls, "Dstem")[0])
    _save(d / "answers.json", {"cls": args.cls, "gain_db": g, "model_lufs": model_lufs, "answers": ans, "stem_feat": f,
                               "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"ANSWERS: {len(ans)} amps, gain {g:+.2f} dB")


def cmd_render(args):
    """Each amp's answer through the class's two stock DIs (fresh, primed, trimmed): its LUFS and its model-input mel on
    the half at the model's input gain -> DIR/renders.npz, DIR/renders.json."""
    import numpy as np

    from learn import amp_di_compare as A1
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import song_bank as B

    d = pathlib.Path(args.dir)
    ans = json.loads((d / "answers.json").read_text())
    stock = json.loads((A1.a1_dir() / "plan.json").read_text())["stock"][ans["cls"]]
    dis = [B.measure(PS.section_audio(s["di_path"], s["start_s"])).astype(np.float32) for s in stock]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    mels, rec = {}, {"stock": [s["di"] for s in stock], "lufs": {}}
    for a in AMPS:
        x = ans["answers"][a]
        st = LO.tdict(x["settings"])
        for j, di in enumerate(dis):
            y = np.asarray(AM.fresh_render(CB.new_renderer, di, x["select"], st, st), np.float64)[trim[0]:trim[1]]
            rec["lufs"].setdefault(a, []).append(float(SA.lufs(y)))
            g = DE.inference_gain_db(y, ans["model_lufs"])
            m8, _, lu, _ = DS.step4_half(y, y, HALF, g)
            mels[f"{a}_{j}"], mels[f"{a}_{j}_lufs"] = m8, np.array([lu], np.float32)
    np.savez(d / "renders.npz", **mels)
    _save(d / "renders.json", rec)
    print(f"RENDER: {2 * len(AMPS) * len(dis)} renders")


def cmd_pick(args):
    """The amp by the floored features' cosine, then the matched output gain -> DIR/preset.json."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import loudness_step as L
    from learn import pipeline_fix as P

    d = pathlib.Path(args.dir)
    ans = json.loads((d / "answers.json").read_text())
    rec = json.loads((d / "renders.json").read_text())
    z = np.load(d / "renders.npz")
    nets, _, _ = _adopted()
    cls = ans["cls"]
    feats = {a: [_feats(nets, DS.model_input(np.maximum(z[f"{a}_{j}"], FLOOR_U8), np.maximum(z[f"{a}_{j}"], FLOOR_U8),
                                             float(z[f"{a}_{j}_lufs"][0]), float(z[f"{a}_{j}_lufs"][0]), HALF, EMBED_AMP,
                                             cls, "Dstem")[0]) for j in range(len(rec["stock"]))] for a in AMPS}
    amp, dist = pick_amp(ans["stem_feat"], feats)
    tab = json.loads((P.out_dir() / "ls" / "s-table.json").read_text())["table"]
    x = ans["answers"][amp]
    g0 = float(x["settings"][L.OUTPUT])
    gain, want, short = L.matched_gain(g0, tab[amp][cls], rec["lufs"][amp])
    _save(d / "preset.json", {"amp": amp, "select": x["select"], "settings": L.with_output(x["settings"], gain),
                              "distances": dist, "output_gain": {"from": g0, "to": gain, "wanted": want, "shortfall": short},
                              "cls": cls, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"PICK: {amp} (distances {json.dumps({k: round(v, 4) for k, v in dist.items()})}); output {g0:+.1f} -> {gain:+.1f} dB")


DELAY_VOTE = 0.70                     # D1's rule on all seven bands' leave-band-out votes, at most 10% false-on (F89)
DELAY_MIX, DELAY_FEEDBACK = 0.30, 0.30  # a declared conservative default when the song research gives none (the
#                                        review: the wide draws are uniform per knob, not a musical prior); the user's
#                                        taste to confirm
DELAY_GATE = 0.10                     # the halves' peaks agree within 10%


def delay_rule(vote, halves_ms, whole_ms, knn_ms, threshold=DELAY_VOTE, gate=DELAY_GATE):
    """D1's rule (F89): on if the neighbours' on-share clears the threshold; its time the stem's cepstral peak when the
    halves agree within the gate, else the neighbours' median. -> (on, time ms or None, which time)."""
    if vote < threshold:
        return False, None, None
    a, b = halves_ms
    if abs(a / b - 1) <= gate:
        return True, whole_ms, "the stem's cepstral peak (halves agree)"
    return True, knn_ms, "the neighbours' median"


def cmd_delay(args):
    """The optional delay reader (D1, F88-F89; a candidate, rare and not yet precise): the stem's T0 delay features
    matched to E1e's clean targets of the picked amp (15 neighbours), D1's rule for on/off and time; mix and feedback
    from the song research when given (--mix, --feedback, --source), else a declared conservative default ->
    DIR/delay.json."""
    import numpy as np

    from learn import fx_reader as FX
    from learn import fx_t0 as T0

    d = pathlib.Path(args.dir)
    w = np.load(d / "window.npz")
    stem = np.asarray(w["stem"], np.float64)
    amp = json.loads((d / "preset.json").read_text())["amp"]
    z = np.load(T0.out_dir() / "features.npz")
    its, _ = T0.items()
    if [it["i"] for it in its] != list(z["i"]):
        raise SystemExit("T0's items differ from its features")
    L = [T0.labels(it["settings"]) for it in its]
    Y = {c: np.array([l_[c] for l_ in L]) for c in L[0]}
    amps = np.array([it["amp"] for it in its])
    j = [T0.FEATURES.index(f) for f in T0.OWN["delay"]]
    lib = np.where(amps == amp)[0]
    q = np.asarray(T0.features(stem), np.float64)[j][None]
    nb = lib[T0.neighbours(z["target"][lib][:, j], q)[0]]
    vote = float(np.mean(Y["don"][nb]))
    t = Y["dtime"][nb]
    t = t[np.isfinite(t)]
    knn_ms = float(2 ** np.median(t)) if len(t) else float(2 ** np.nanmedian(Y["dtime"]))
    half = len(stem) // 2
    halves = (FX.cep_pick(FX.cepstrum(stem[:half]))[0], FX.cep_pick(FX.cepstrum(stem[half:]))[0])
    whole = FX.cep_pick(FX.cepstrum(stem))[0]
    on, ms, which = delay_rule(vote, halves, whole, knn_ms)
    if (args.mix is None) != (args.feedback is None):
        raise SystemExit("delay: pass --mix and --feedback together (the song research's pair), or neither for the default")
    given = args.mix is not None
    mix, fb = (args.mix, args.feedback) if given else (DELAY_MIX, DELAY_FEEDBACK)
    src = args.source if given else "the declared default (no song research given)"
    rec = {"on": on, "vote": vote, "threshold": DELAY_VOTE, "time_ms": ms, "time_from": which,
           "mix": mix, "feedback": fb, "mix_feedback_from": src,
           "halves_ms": list(halves), "whole_ms": whole, "neighbours_ms": knn_ms, "amp": amp,
           "settings": ({"delay/delayActive": "true", "delay/delaySync": "0", "delay/delayTime": f"{ms:.1f}",
                         "delay/delayMix": f"{mix:.3f}", "delay/delayFeedback": f"{fb:.3f}"} if on else {}),
           "note": ("a candidate reader (F89), on synthetic songs: it catches about a quarter of audible delays; about 6 in 10 "
                    "of the delays it switches on are real when half the songs have one, about 3 in 10 at a quarter; "
                    "it reads on/off and time only: mix and feedback come from the song research or a declared default"),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(d / "delay.json", rec)
    print(f"DELAY: {'on' if on else 'off'} (vote {vote:.2f}){f', {ms:.0f} ms from {which}' if on else ''}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("separate")
    s.add_argument("song")
    s.add_argument("--out", required=True)
    s.add_argument("--start", type=float, default=None)
    s.add_argument("--device", default="mps")
    s.set_defaults(fn=cmd_separate)
    a = sub.add_parser("answers")
    a.add_argument("dir")
    a.add_argument("--cls", choices=("clean", "crunch"), required=True)
    a.set_defaults(fn=cmd_answers)
    r = sub.add_parser("render")
    r.add_argument("dir")
    r.set_defaults(fn=cmd_render)
    p = sub.add_parser("pick")
    p.add_argument("dir")
    p.set_defaults(fn=cmd_pick)
    dl = sub.add_parser("delay")
    dl.add_argument("dir")
    dl.add_argument("--mix", type=float, help="the delay mix from the song research (0-1), with --feedback")
    dl.add_argument("--feedback", type=float, help="the delay feedback from the song research (0-1), with --mix")
    dl.add_argument("--source", default="the song research", help="where --mix and --feedback came from")
    dl.set_defaults(fn=cmd_delay)
    args = ap.parse_args(argv)
    os.makedirs(getattr(args, "out", None) or args.dir, exist_ok=True)
    args.fn(args)


if __name__ == "__main__":
    main()
