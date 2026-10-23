# The song-to-preset routes on real mixes: plan

*Amended 2026-10-23 (the trusted-data plan, set by the ML session, the user may overrule):* it runs on V-real's parts
(stage F's parts that pass T0's checks and the ear), not on the data review's list. Its "9 bands (8 df)" power is now
at most 7 bands.

*Status, 2026-10-22 evening:* merged (#267). It runs after the data review and the cleaning, on
trusted parts only ("use only what we can trust, no dirty tracks", the user, 2026-10-22), which
replaces the no-high-bleed row below. **Amendment 1 (user, 2026-10-22): the direct model joins
regardless of step 3's gate** ("of course the direct model should join the test"). D_real runs
with step 4's models and readout, labelled like step 4 ("run under a user override of a GATE
STOP"). The conditions on `GATE OK` below are replaced by this.

Drafted 2026-10-22, zero compute. **Approved by the user on 2026-10-22.** It runs after the
every-control stages and the data-quality audit's first findings (the user suspects the datasets need
cleaning; any cleaning that touches these parts is applied first). Development data only. The ML plan's rules apply (section 5; the user's rules of
2026-10-16): effect sizes with 90% band-clustered intervals, no pass/fail bars, renders declared.
This is ROADMAP step 0, Next item 4.

- **Code (after approval and a code review, before any compute):** `learn/real_mix_test.py`,
  tests `tests/test_real_mix_test.py`.
- **Ledger:** `real-mix-test` in [`dev-test-ledger.json`](dev-test-ledger.json).
- **Data:** `~/ndsp-presets/learn/real-mix-test/`.

## Why

Stage F's "full mixes" are unity sums of the raw tracks
([stereo and mix check](stereo-and-mix-check-results.md)). The [released mixes](mix-previews-results.md)
of 10 of those songs, plus the Signs remix, are the same takes. On them, Mega-53's stem loses
0.62 dB SNR against the raw track (17 parts). Half of that is per-track lag. The rest is mostly EQ:
a filter fitted against the raw track recovers it on average. What this costs the routes
themselves is not measured. This plan runs each route on each part's real mix and on its unity sum
(same takes), so every part gives a paired reading.

## What is tested

- **Inputs:** the stored real-mix 10-s crops and Mega-53 stems in
  `~/ndsp-presets/learn/mix-previews/sep/mega53/`, aligned by `alignment.json`. Their hashes are
  recorded before first use. The stems were made exactly like stage F's M stems: same checkpoint,
  pruned head, CPU at 4 threads, the same 30-s window and crop.
- **M_real:** arm A exactly as on stage F (C′'s rebuild, 52 renders, shrink 0.5, same seed). Only the
  stem changes.
  - Before any real-mix rebuild, the C′ networks are hash-checked against stage F's
    `rebuild-log.json`, and one stored unity M rebuild must be reproduced within 1e-6.
  - A silent output or a non-finite objective falls back to S, as on stage F (likely on Passing
    Ships ElecGtr4). Fallbacks are counted.
- **D_real:** the direct model exactly as in step 4: amendment 5's readout, the search half only,
  step 4's separator and model hashes (checked against its `predictions.json`). It is fed a
  crop-only stem of the real-mix crop. The mix gets one gain to the training median and the stem
  the same gain. D_real runs (amendment 1; it first read "only on `GATE OK`"). D0 is not run.
- **The unity side is stored:** stage F's S and M, and step 4's D, on the same directions.
- **S needs nothing new.** It reads no input, and the truth does not change, so its score is the
  same on both sides. Each route's **real-mix penalty** is therefore X_real − X_unity, direction by
  direction, for X = M or D.
- **Not run:** H (no htdemucs real-mix stems; Mega-53 is the ML default), and arm A on the
  unmastered files (about 2,000 renders for 6 parts; a separate yes).

## Scoring

- **The judge is stage F's, unchanged.** `knob_ceiling.judge` scores the render through the part's
  measure DI against `reference.wav` on the held half, at the stored `judge_lag`, with its own level
  match. The judge never sees the mix, so the mix's lag, sign and gain cannot touch the score.
- **Contrasts:** per direction log(d_real / d_unity), with X_real − S beside it. Per part, the mean
  over amps and halves, then band-weighted with a 90% band-clustered t interval
  (`arm_a_levers.effects`, as every stage F arm).
- **Lag-invariant by construction.** No score compares a real-mix stem with the amp track at a
  fixed lag.
  - Arm A's search compares renders of C′'s rebuild with the stem it was rebuilt from, so the mix's
    lag moves both together. Polarity reaches C′ and the amps' clipping; that is a real input effect
    and part of the penalty.
  - **Check:** per part, GCC(real rebuild, real stem) must equal the stored GCC(unity rebuild, unity
    stem) within ±3 samples (the unity values are 0 or −53 to −69), or the run stops. Passing Ships
    ElecGtr4, whose stem has no coherent guitar, is logged instead.
  - Stage F's ±3-sample check against the htdemucs crop cannot hold on a real mix. It is replaced
    by a logged lag, searched over ±100 ms and gain-fitted (sign free), as in the mix-previews report.
  - Arm A's "first evaluation is S" check has no stored value on real stems. The repeat check
    replaces it: S re-rendered on 6 groups (`random.Random(20261092)`), within 1e-3 of the stored
    judge, or stop.
- **Why it stays honest when a mix differs.** The truth is the raw amp track, never the mix. The
  mix's EQ, compression, reverb, mastering and MP3 codec reach only the inputs, which is the effect
  measured. The score asks: does the route still recover the rig from a released song? The
  product's notional target is the guitar as heard, so a route that copies the mix's EQ counts as
  wrong here. One descriptive row looks at that.
- **"As mixed" (descriptive, zero renders).** The target is `reference.wav` carried into the real
  mix: one lag and a 1/3-octave EQ per part, fitted from the cross-spectrum of `reference.wav`
  against the real-mix crop on the search half. (Sign and gain do nothing under a level-matched
  magnitude judge.)
  - Every arm on both sides, S included, is re-judged on the held half against that target at one
    lag per part (judge_lag plus the fitted mix lag). All arms are judged from the kept FLACs,
    re-padded alike.
  - A part is left out when its fit's mean coherence over 0.2–5 kHz is below 0.1 (declared now).
  - **Control:** the same fit on the unity mix should come out flat at lag 0.
  - The EQ'd target changes the judge's bands, so this row's values are not comparable with the
    primary's. It cannot capture compression or reverb tails.
- **Beside the primary, never promoted:**
  - **per part:** against the stem SNR change (mix-previews' c − b) and D's input level shift (stem
    LUFS after the gain, real against unity);
  - **subsets:** the 6 lagged parts (Today's The Day 07, wickerman 1–3, Let's Dance 3 and 4), the 8
    flipped ones, and Colour Me Red ×2 (the X-LANCE failures);
  - **damping:** D's answer movement in knob space with its pull weight, since amendment 5's pull
    and arm A's shrink both damp how far an input change can move a route;
  - **a zero-render control:** D fed the unity stem shifted by each part's lag, and sign-flipped;
  - **the usual rows:** D's unmastered row, per class and amp, leave one band out, and
    part-weighted.

## Which parts, and the power

17 parts in 9 bands have a mastered real mix (the Signs remix for Zeno). They are exactly stage F's
"Cambridge only" row. Stage F's 4 Telefunken parts have no released mix; they include all 3
high-bleed parts (She's Gone among them), so every part here is in the no-high-bleed row.

| Band | Parts (`cambridge-` dropped) |
|---|---|
| Atlantis Bound | It_Was_My_Fault_For_Waiting-ElecGtr3 |
| Diesel13 | colour-me-red-elecgtr02, colour-me-red-elecgtr03 |
| Eat The Feeder | Today's_The_Day-ElecGtr07, wickerman-elecgtr1, -elecgtr2, -elecgtr3, -elecgtr7 |
| Magician's Nephew | get-out-of-bed-elecgtr2 |
| Szymon Skiba | let-s-dance-elecgtr3, let-s-dance-elecgtr4 |
| The Travelling Band | Passing_Ships-ElecGtr2, Passing_Ships-ElecGtr4, Quicksand-ElecGtr2 |
| Turbosauro | magilla-elecgtr1 |
| Wall Of Death | femme-elecgtr5 |
| Zeno | Signs-ElecGtr3 (Mix Rescue remix) |

The unmastered files cover 6 of these parts in 4 bands (get-out-of-bed 2, Passing Ships 2 and 4,
Quicksand 2, femme 5, Signs 3): a descriptive row for D only. Three 30-s contexts are zero-padded
where a preview ends (Today's The Day 07, It Was My Fault 3, wickerman 1); only separation sees it.

**Power: mostly descriptive.** With 9 bands (8 df), the 90% half-width is about 0.62 × the band SD,
and the effect found with 80% power about 0.92 × the band SD.

| Route | Band SD assumed | 90% half-width | Effect found with 80% power |
|---|---|---|---|
| Arm A | 0.04–0.07 (M − H, Cambridge only: about 0.05) | 0.025–0.043 | 0.04–0.06 |
| D | 0.07–0.17 (D_existing − S: 0.166) | 0.04–0.11 | 0.06–0.16 |

On these parts arm A read M − S −0.053 [−0.115, +0.008]. So only a penalty that wipes out most of a
route's gain would show. A smaller one reads as a tie: undecided, not absent. Eat The Feeder holds
5 of the 17 parts but weighs 1/9.

## Cost

| Item | Amount | Machine, time |
|---|---|---|
| Crop-only stems of the real-mix crops (D only) | 23 (17 mastered + 6 unmastered) | CPU about 5 min (27 CPU-s a clip at 2 threads), or MPS about 2 min when free |
| Mega-53 real-mix stems (arm A) | 0: stored | none |
| C′ rebuilds of the real-mix stems | 17 | CPU, minutes |
| Arm A renders | 51 priming + 102 directions × 55 = **5,661** | |
| D renders | 102 + 36 unmastered = **138** (+51 priming if run apart from arm A) | |
| Repeat check | 6 | |
| **Renders in all** | **about 5.8k (cap 6,300)** | about 1 h on 3 processes (stage F: 1.7–1.9 a second) |
| Disk | stems, rebuilds, kept FLACs: about 0.2 GB | 117 GB free on 2026-10-22 |
| Training, GPU, downloads | none | |

The usual rules hold: at most 3 render processes machine-wide, `isolate`, grouped by amp, one
discarded priming render per process start or amp change, the 31 GB disk guard, `setopt no_bg_nice`.

## What each outcome means

- **Penalty interval above 0:** real mixes measurably hurt the route, and stage F's unity figures
  overstate it on real songs. Before shipping, the inputs need work: separation on mixed input, D's
  input level, or lag and sign, as the per-part rows point. The fresh-song decision test (Next
  item 5) must then use real mixes.
- **Interval contains 0:** no penalty shown at this power. Stage F's figures stay the best estimate
  for real songs, stated with this interval. Item 5 should still prefer real mixes where they exist.
- **Interval below 0:** real mixes help. Some expose the guitar more than a flat sum (Passing Ships
  2 and Quicksand 2 gain SNR), so unity sums are conservative there.
- **X_real − S:** the first reading of a route against S on released songs. Not a ship decision:
  the parts are reused, and item 5 decides.
- **"As mixed" moves unlike the primary:** the routes follow the mix's EQ. Whether the preset should
  match the rig or the guitar as heard is a product question for the user, not a fix.

## Order

1. **Now:** the user reads this plan. No compute, no code.
2. **After step 4's report** (arm A and D, amendment 1): code, tests
   and an independent code review; the 23 separations when the renderer is idle; the renders; the
   report and an independent audit; then ROADMAP and docs/README.md. Arm A does not need D. It waits
   only so the gate and step 4 keep the render slots.

**Repeat use.** This is stage F's ninth set of arms (step 4 is the eighth; the ledger's 7th/8th
reservation for separation-finetune is noted in this entry). Nothing is chosen on these parts: the
recipes, the readout and the judge are fixed before any real-mix render.

## Approvals needed

- **The user's yes on this plan:** about 5.8k renders (cap 6,300), 23 separations, about 0.2 GB.
- **No training of any kind,** no new separator, no rented machine and no download. The previews
  are already local. Moises is not used.
- **Optional, a separate yes:** arm A on the 6 unmastered parts, about 2,000 more renders.

## Implementation notes (code, 2026-10-22; PR #277)

Recorded with the code after its review, before any real-mix render. They change no estimate,
recipe or judge.

- **Trusted parts:** every command takes `--parts-list FILE`, the trusted parts from the data
  review, and refuses to run without it. The file is JSON `{"parts": [...]}`, a bare JSON list, or
  text with one entry per line. An entry can also trust one held half (`slug:A`). The inputs record
  and the report store the list under `kept_parts`.
- **The repeat check uses 12 renders, not 6:** each of its 6 S renders gets a discarded priming
  render (the priming rule). The total is 5,811 renders on all 17 parts, under the 6,300 cap.
- **"As mixed" lag:** one lag per direction, fitted on its search half from the plain
  cross-correlation (sign free).
  - The method was chosen on lag agreement with the real-mix stems' logged lags (14 of 17 parts),
    not on any score.
  - GCC-PHAT locked onto the amp track's bleed at lag 0 (wickerman 1–3 read 0 instead of 398).
- **The coherence floor stays at the declared 0.1, so "as mixed" is a thin row.** Measured on all 17
  parts (zero renders), only 5 pass: Quicksand 2, femme 5, get-out-of-bed 2, Let's Dance 3 and 4 (4
  bands). The unity mixes mostly read below 0.1 too.
  - A part trusted on one held half only is also left out of this row, since its fit would read the
    untrusted half.
- **Plumbing checks added as stops:**
  - the real-mix crops re-derived from the previews (1e-6);
  - the stored S renders re-judged against today's `reference.wav` (0.005);
  - the X-LANCE separator reproducing step 4's stored stem (40 dB);
  - step 4's unity D answers reproduced (A1+A2 within 1e-5, and every pulled setting equal);
  - a rerun of `inputs` refusing changed input hashes.
