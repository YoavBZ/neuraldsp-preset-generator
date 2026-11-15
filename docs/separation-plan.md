# Separation plan: one guitar part from a real song

**Status:** declared 2026-11-14, on the user's "I allow working on the separator in any promising way, including
creating/retraining/using other tools and approaches … the final result is simply not good on real songs". Nothing has
run yet. Ledger `separation`.

## Why

The model now reads a separated guitar well on known-truth units (F80–F90). On real songs the input is the weak link.
X-LANCE `gtr_mss` returns every guitar plus bleed. The user's picker (R1 Amendment 4) found leaks in most songs,
even in the best version ("Still many leaks though"), and the centre mask helped on 5 of 7. The model can't be better
than what it hears.

## What earlier work found (October 2026, Mega-53 on stage F's 21 parts)

- **The other guitars are the limit, not the guitar class.** On parts with another electric guitar, the others sat
  about 5.5 dB above the target. A perfect "all electric guitars" separator would gain only +0.30 dB
  ([separation step 0](separation-step01-results.md)). So a better class separator alone won't fix real songs. The
  lever is telling the named guitar from the other guitars.
- **Stereo cues help a little, and only with the side known**
  ([stereo side screen](stereo-side-results.md)): keeping the target's channel gained +1.50 dB, and the MDX23C
  centre model +1.35 dB on a centred target against hard-panned rhythms. Every blind method lost, since the pan
  histogram found the louder other guitars. The level-difference mask gained +0.6 to +0.9 dB, and the coherence mask
  +0.35 dB.
- **What S1 adds:** those screens fed Mega-53 a mono or picked channel. S1 tests X-LANCE (the model path's
  separator) on real stereo, with the centre masks and on the target's own channel, on E1e's three strata. October's
  +1.5 dB was Mega-53 on mono or picked inputs, and not clear of +1 dB after Holm. That cap is for blind or centred
  cases, not for a known side (October's hard-pan ceiling was +6.88 dB). S2 and S3 still start only on the declared
  trigger.
- **S1 Amendment 1 (2026-11-14, before any S1 read):** option (g), the earlier screen's MDX23C phantom-centre model
  (hash-checked, CPU), then X-LANCE, beside the centre mask.

## The goal and the stop rule

One guitar part, the one the user names, as clean as an existing or a new tool can make it. Each step is decided by
the measuring stick (S0) on held-out mixes, then by the user's ear on R1's songs. A step that doesn't gain on S0 stops
there. The steps run in cost order, cheapest first.

## S0, the measuring stick (zero renders)

Real songs have no ground truth, so every option is first measured on known-truth stereo mixes.

- **The mixes:** E1e's items rebuilt in stereo by D_CC's recipe. The target is the item's guitar (its render, as
  drawn). The "others" track holds the session's other guitars, and the backing holds the rest. Bass, kick, snare and
  vocals are centred, and the other backing parts sit within ±0.5. The drawn ratio and mastering are kept. The
  target's placement takes one of three strata, about a third each, seeded (the review: a centred lead alone would
  favour the centre mask by construction, and the user's part isn't always the centred lead):
  - **centred lead:** the target within ±0.15, each other guitar at ±0.6 to ±1.0;
  - **off-centre target:** the target at ±0.4 to ±0.8, with another guitar opposite or centred;
  - **double-tracked target:** the target on both sides at ±0.6 to ±1.0 with a slight offset, and another guitar
    centred.
  - 200 items, stratified by band; the bands any later training uses are held out of S0's read.
- **The scores, per option:**
  - the target's SI-SDR on half A;
  - the other guitars' leak (the stem's energy correlated with the others track, against the target's);
  - the model's read: the cosine of the adopted model's floored body features (the amp pick's own measure) between
    the stem and the clean target, both at the product's input level.
  - beside, the effects row (since better stems also serve R3): the stem's cepstral delay hit and T0's delay vote;
  - all are reported per stratum and by band, with a band bootstrap, against today's input (X-LANCE on the mono mix);
  - each item's effective target-to-backing ratio is recorded, and the strata are read beside it, since a double
    stands about 1.5–2.5 dB hotter by construction;
  - a post-hoc check (`s0-check`): the built backing, folded as if centred, against the recipe's own backing.
  - The win rule is coded into the read, per stratum: SI-SDR gain lo90 > 0, and the model's read hi90 ≥ 0. s0-feats
    runs after every stem exists. The read prints n(cosine) beside n, and it refuses a win where the model's read is
    incomplete.

## S1, existing tools (zero training)

- **(a)** X-LANCE fed the true stereo channels, the mean of its two outputs. Until now it got the mono mix twice.
- **(b)** The picker's centre mask, then X-LANCE.
- **(c)** Mega-53's electric-guitar stem. This is a deviation, declared after the code review: the pipeline's Mega-53 is pruned to that one head in its 'fast' setting, so its guitar head isn't run.
- **(d)** An agreement ensemble: per STFT bin, the smaller of X-LANCE's and Mega-53's magnitudes, with X-LANCE's
  phase.
- **(e)** X-LANCE run again on its own stem.
- **(f)** (b) with the mask's exponent at 2 and at 8, beside 4.
- **(g)** (Amendment 1) The MDX23C phantom-centre model, then X-LANCE. The October screen found it "either helps a
  lot or hurts" (+5 to +6 dB on one song, −2.8 on another), so it goes to the picker as a choice, not the default.
- **(h)** (Amendment 1, the review) X-LANCE on the target's own channel, exactly the picker's stem_L or stem_R. The
  side comes from the drawn pan: the louder copy for a double. It's an oracle standing in for the user's pick, and
  it's read on the off-centre and double strata, where the centre options remove the target by construction.
- **(i)** X-LANCE on the side signal (L−R)/2, the picker's stem_S.
- **The rule:** an option wins if its SI-SDR gain over today's is above 0 on the band bootstrap and it loses nothing
  on the model's read, meaning the paired cosine interval isn't wholly below 0. It's read per stratum: an option
  that wins only on the centred lead goes on the picker as a choice, not as the default. The best one or two go on
  the user's picker for R1's songs.
- **The trigger for S2 and S3:** the best gains under 1 dB, or the user's ear still finds the best S1 option leaky
  on R1's songs. Each of S2 and S3 carries its own stop rule when declared: a held-out S0 gain and a budget of
  nights.

## S1 Amendment 2: the researcher's tests (2026-11-14, before any S1 read; ledger `phase_s1_a2`)

The cloud researcher's survey ([lead-guitar-extraction-2026-11.md](research/lead-guitar-extraction-2026-11.md))
found no open model shown to pick one electric guitar out of several. It also found two gaps in S0, and ranked the
cheapest decisive tests. The user approved three downloads ("You can download anything you need that looks
promising"). Each is hash-checked against `tools/sep-models/manifest.json` and loaded with `weights_only=True`, after
a yaml check that admits only MSST's `!!python/tuple`. Code is in `learn/sep_s1b.py`.

- **Corrections to this plan:**
  - October's screens fed Mega-53 true stereo (63 stereo separations), not a mono or picked channel. The stereo check
    found a stereo stem's mid within −0.06 to +0.24 dB of mono, a modest prior for (a).
  - S0 puts every other guitar at one drawn pan, not one pan each. Its double is a coherent delayed copy, not an
    independent take, so it flatters any coherence gate. S0's double stratum is read with that caveat.
- **The new options:**
  - **(j)** X-LANCE on the true stereo pair with both output channels kept (`xlst2`); (a) averaged them. From it, two
    masks applied after separating, on the stem's own channels: psi^4 · max(cos, 0) (`xlst_psi`), and a
    time-smoothed coherence × level-similarity mask, Avendano–Jot with forgetting 0.90 per frame (`xlst_coh`).
  - **(k)** gilliaan's CenterWide BS-RoFormer v2 'center' output, then X-LANCE (`cw`). CC BY-NC-SA 4.0, development
    only.
  - **(l)** X-LANCE's keys model (`key_mss.pth`, MIT) as a competing mask on today's stem: G·|G|/(|G|+|K|)
    (`keymask`).
  - **(m)** The two open lead/rhythm checkpoints on the `xlst2` stem: listra92's Mel-Band RoFormer (its Lead output,
    and the stem less it: `lr_mbr_lead` and `lr_mbr_rest`), and Dry Paint Dealer's HTDemucs (`lr_htd_lead`,
    `lr_htd_rhythm`). Neither publishes a licence or a metric. Both outputs are read, since S0's target isn't always
    a "lead".
- **The split set** (S0's realism gap): 60 of S0's items, rebuilt with the target centred (±0.15) and its own other
  guitars hard to one side (±0.8 to ±1.0). An independent take, another item's other guitars from the same band and
  another section, goes hard to the other side. The backing is the item's built rest, centred, so its stereo image is
  lost. S1's mono, stereo, centre4, mdxc and side options are rerun on it beside the new ones.
- **After its review:**
  - **The split set:** no double is a source (its stored target is a coherent pair). Both takes must be within 20 dB
    of the target, so neither side is empty. The references are stored as they sit in the split's mid (each source
    times its fold), and the leak is fitted on the target, the own take and the partner's take. The mix is
    LUFS-matched to its source.
    - A different section's guitars aren't a second take of the same part. That's fair for the centre and coherence
      masks, and easier than real life for the content-based options (X-LANCE, CenterWide, the keys mask, the
      lead/rhythm models).
    - `side` on the split set is a control: the target is centred there.
  - **More options:** `xlst_coh4`, the smoothed similarity to the 4th power, so it can be read against `xlst_psi`
    at a matched exponent (`xlst_coh` is psi¹). `xlst_mdxc`, the MDX23C centre model on the `xlst2` stem: October's
    actual setup, separate then centre. October's +1.35 dB is a prior for that, not for (g).
  - **The lead/rhythm outputs:** read as separate options. The per-item better of each pair is shown beside, as the
    ceiling of picking by ear (an oracle), never under the rule.
  - **Many options:** S1 now has about 20 options across 4 cells, so a few chance wins are expected and the best
    mean is biased up. So wins are candidates for the ear, ranked by the SI-SDR gain's lo90.
  - **The trigger's scope** (the review): the S2/S3 trigger is the best lo90 among candidates (options that win
    under the rule, the model's read included). It's read over S1's read and s1b's main and split reads together
    (`s1b-trigger`), and it fires with no candidate or with the best under 1 dB. An option with a high lo90 that
    fails the model's read doesn't count.
  - **The effects row** (cepstral delay hit, T0's vote) is read for every new option. An unmasked stereo stem
    (`xlst2`) is kept for the effects read, whichever stem wins.
  - **Safety:** every config's SHA-256 is checked too. XLanceKeys asserts torch ≥ 2.6 (`weights_only` by default).
    The lead/rhythm checkpoints come from a third-party mirror, so the risk is a different model than named, not
    code.
- **The read:** S1's rule, per stratum and on the split set, against mono, with the same completeness guard.
- **Cost:** zero renders, about 2.6 GB of stems, and roughly 1.5 h of MPS after S1's queue.

## S2 and S3, declared later on S1's evidence and the cloud researcher's survey

- **S2, targeted extraction:** pull the named part only, for example query-by-example from a stretch where it plays
  clearly, test-time adaptation of X-LANCE on the song itself, or an open prompt-based model. Any download goes to
  the user first, with its size.
- **S3, our own lead-versus-rest separator:** fine-tune X-LANCE (or train a RoFormer) on thousands of stereo mixes
  built as in S0 from our multitracks, with the other guitars as the leak to remove. MPS over nights, no rented
  machines. The bands S0 reads stay out of training.

## S1 Amendment 3 and S3: steer, then separate (declared 2026-11-14; ledger `phase_s1_a3`, `phase_s3`)

**Why now.** S1's first round (read and audited) showed what works is where the guitar sits. The MDX23C centre model
gains +7.0 dB on a centred target but removes an off-centre one (−17.3 dB). The guitar's own channel gains +7.2 dB
off-centre. The user said "Go for all. Plan carefully, review independently, work step by step, document and audit",
to the proposal: read the second round, put the best on the picker, and train our own separator tonight. So S3
starts on that go, ahead of the trigger. The trigger is still computed and reported.

**How it differs from what failed.** Every tool so far was trained to pull out "the guitar", meaning every guitar
together. October showed the other guitars are what limits separation (a perfect all-guitar separator gains only
+0.30 dB). Both steps here use the one cue that separates a guitar from another guitar in S1: where it sits.

**Steering.** For a constant-power pan p, the angle is θ = (p + 1)·π/4 (so L = cos θ, R = sin θ). Given a hint p_h,
rotate the pair [L, R] by φ = π/4 − θ_h. A source at the hint lands in the centre (L′ = R′). A source on the other
side turns anti-phase, which a centre extractor removes. The rotation is orthonormal, so it's undone exactly by −φ.
A centre hint is no rotation at all.

**The hint** is coarse, as the picker gives it: centre (|p| < 0.25) is 0, left is −0.7, right is +0.7. A double's
hint is its louder copy's side, the `side` option's rule. In S0 the hint comes from the drawn pan, an oracle standing
in for the user's pick: the same information `side` already uses. ±0.7 is fixed here, before any steering read: it
lies between S0's off-centre (±0.4 to ±0.8) and double (±0.6 to ±1.0) ranges and is near a typical hard pan. The
exact drawn pan as the hint is read beside, as a ceiling, never under the rule.

### S1 Amendment 3: steering with the existing tools (zero training)

- **`steer_mdxc`:** steer by the hint, run the MDX23C centre model, average its two outputs, then X-LANCE. It's (g)
  with steering. On a centred hint it's (g) exactly, which is a check.
- **`steer_mid`:** steer by the hint, X-LANCE on the steered pair (both outputs), then the stem's mid. The target is
  whole in the mid, and anti-phase sources cancel.
- **`steer_mdxc_exact`:** `steer_mdxc` with the exact pan, the ceiling.
- **Where:** all of S0's 200 items and the split set's 60, by S1's rule against mono, per stratum. Beside: the best
  existing option per stratum on the same items, chosen on those same items (that favours the old options).
- **Cost:** zero renders. MDX23C and X-LANCE on the CPU, 4 threads, so the MPS stays free for S3.

### S3: our own steered separator (training on MPS, no rented machines)

- **What it learns:** the job `steer_mdxc` does, learned. Input: the mix steered by the hint (stereo, 44.1 kHz).
  Output: the target as it sits in the steered mix (stereo). The stem is rotated back and its channels averaged, as
  every S0 stem is. It starts from X-LANCE's `gtr_mss` (BS-RoFormer: 12 layers, dim 256, stereo, one stem;
  hash-checked), so it starts as today's separator and learns what to remove.
- **Data, trusted only:** D_CC's built examples, the reviewed set S0 is built from: the target render, the other
  guitars' render, the session's other guitar amp tracks (D_CC's `amp_tracks`), the backing stems, D_CC's gains.
  - **The bands, fixed before training:** the two bands with the most S0 items (Forkupines and BKS) plus the two
    S0 doesn't use (The Maybe Next Years, Adam Buckley) train: 2,218 examples with other guitars, 217 sections. The
    other five (Hazael, The Travelling Band, Ale Lak, Storm Of Particles, Dunning Kruger) are held out: 120 of S0's
    200 items and 38 of the split set's 60. That trades training volume for a five-band read.
  - **Validation, for the curve only:** 10% of the training bands' sections (seeded), their examples kept out of
    training. 200 fixed steered mixes from them, scored like S0. The held-out bands are never used for the curve.
- **The mixes, drawn on the fly:** each example's parts are cached once at 44.1 kHz. The guitars stay mono, and the
  non-guitar backing is pre-panned to stereo by S0's rule. Each draw takes:
  - a stratum: centred 30%, off-centre 30%, double 20%, split 20%. Split means the target centred with the other
    guitars hard to one side and a same-band partner's other guitars hard to the other. The pans are wider than
    S0's: a centred target within ±0.2, other guitars ±0.5 to ±1.0; off-centre ±0.35 to ±1.0, the others opposite
    or centred; a double ±0.5 to ±1.0 on each side, 8 to 30 ms apart, the second copy 0 to 4 dB down;
  - the render and the amp tracks at separate pans when both exist, so there are two guitar groups;
  - the target-to-rest ratio jittered ±3 dB around D_CC's, and S0's mastering draw at D_CC's rate;
  - a 1.4-s crop where the target plays (its level within 20 dB of the mix's);
  - steering by the coarse hint, plus a uniform ±0.1 jitter.
- **Training:**
  - The loss is X-LANCE's own: L1 plus a multi-resolution STFT term, on the steered stereo target.
  - The crop is 61,740 samples (1.4 s), so every STFT stays under the MPS gradient bug's 65,536 samples.
  - **Before the run, a gradient check:** one batch's gradients on MPS against the CPU's, per parameter tensor. It
    runs on MPS only if the median relative error is under 1e-3 and the largest under 1e-2. Otherwise it's
    reported, and the run waits.
  - AdamW at lr 3e-5 (X-LANCE trained at 2e-5) with 1,000 warm-up steps, fp32, the batch the speed check sets.
  - Gradients are clipped at norm 1.0 by hand, since `clip_grad_norm_` gives NaN on MPS. A non-finite step is
    skipped. After 25 in a row the last checkpoint is reloaded, and after 20 reloads the run aborts (direc's rule).
  - Never beside another MPS training.
- **The curve and the stop:** the validation score every 1,000 steps, keeping the best checkpoint. It stops at no new
  best in 5 evaluations, at the abort rule, or after 3 nights. The user can stop it.
- **The read, once, after the stop:**
  - **What runs:** the best checkpoint on the held-out 120 S0 items and 38 split items, with `steer_mdxc`'s hint. It
    gets S0's scoring: SI-SDR on half A, the leak, the model's read and the effects row.
  - **The rule:** S1's, against mono, and against the best existing option per stratum, `steer_mdxc` included, on
    the same items. That's a band bootstrap over the five held-out bands. With five bands the interval is wide, so
    an item bootstrap within bands is shown beside, never under the rule.
  - A win goes on the picker, and the user's ear on R1's songs decides.
- **What it can't say:**
  - The targets are amp-sim renders and the mixes are built by S0's recipe, which training shares. So the held-out
    gain is an upper bound for real songs.
  - The hint is an oracle from the drawn pan.
  - Two guitars at the same place, both centred say, can't be told apart by steering, only by tone. That case isn't
    tested: the split set puts them on opposite sides.
- **Cost:** zero renders. A cache of about 8 GB (61 GB free). MPS for up to 3 nights.

### After the plan's review (2026-11-14, before any run of A3 or S3; these replace the lines above where they differ)

- **The steering text, corrected.** A source on the far side turns anti-phase only for a hard hint. With the hint at
  +0.7, a source at −0.7 lands at −18° (L′ 0.95, R′ −0.31), and a centred source moves to −0.7. So the steered mid is
  a projection with gain cos(θ_s − θ_h). It keeps a source at −0.7 at −6.9 dB, against −12.4 dB in the target's own
  channel. `steer_mid` is therefore a control, not a candidate. The coarse hint leaves an off-centre target up to
  0.35 from the centre after steering, outside the ±0.15 where `mdxc` gained +7 dB. So every steered read is also
  reported by the target's steered pan |p′| (under 0.15, 0.15 to 0.3, 0.3 and over). A ±1.0 hint is declared now as
  a sensitivity check (`steer_mdxc_h1`, beside).
- **A3 reuses identical stems.** On a centre hint, no rotation happens, so `steer_mdxc` is `mdxc` and `steer_mid` is
  `stereo`, on S0's centred items and the whole split set. Those stems are copied, and 5 are recomputed as an
  identity check.
- **The doubles.** S0's double is a delayed copy of the same render. So a target "as it sits" rewards keeping
  far-side content that repeats the centre 8 to 30 ms later, a cue real doubles (independent takes) don't have. S3
  trains with only the hinted copy as its target. S0's double cell is out of S3's rule and is reported descriptively.
- **S3's rule, with the model's read co-primary.** In S1, `mdxc`'s +7.03 dB on centred items moved the read by only
  +0.006 [−0.026, +0.031]. So an SI-SDR gain alone needn't reach the preset. Per cell (the centred hint: S0's
  centred items and the split set; the side hint: S0's off-centre items):
  - **Against mono:** S3 must gain in SI-SDR (lo90 > 0) and in the read (cosine-distance drop, lo90 > 0).
  - **Against the routed comparator,** fixed now: what the hint routes to among the existing options. A centre hint
    routes to `mdxc`, a side hint to `side`.
  - **Default:** wins against mono, and against the comparator gains in SI-SDR (lo90 > 0) with a read not worse
    (hi90 ≥ 0). The centre hint's default needs both its cells.
  - **Picker choice:** wins against mono, with a read not worse than the comparator's, but the SI-SDR difference is
    undecided.
  - **Not used:** anything else.
- **The intervals.** The rule's interval is the band-clustered t interval over the five held-out bands (df 4, the
  repo's `clustered`), with per-band means and how many bands agree in sign. Hazael and The Travelling Band hold 65%
  of the items, and Dunning Kruger is one section. The percentile band bootstrap and the item bootstrap are shown
  beside. Beside too: the best existing option per stratum, chosen on the 80 training-band S0 items (Forkupines and
  BKS), then read on the held-out ones.
- **Validation: a whole band.** Adam Buckley (140 examples, 13 sections, not in S0) is the validation band. Training
  is on Forkupines, BKS and The Maybe Next Years: 2,078 examples.
  - **The mixes:** 200 validation mixes built by S0's strata recipe, the hinted copy as a double's target.
  - **Scored each evaluation:** the median SI-SDR of the rotated-back mono against the target's, plus the model's
    read (mean cosine distance, on the CPU).
  - **The curve:** step 0 (X-LANCE as it is) is the first best. A new best needs +0.1 dB on the median and a read no
    worse than step 0's. The run stops after 5 evaluations without a new best.
  - **The pilot:** those first evaluations are the pilot. A flat start stops the run within about 5,000 steps.
- **The gradient check.**
  - **Setup:** dropout off on both devices, since the config's 0.1 dropout draws different masks. Each tensor's
    error is ‖Δ‖ / max(‖g_cpu‖, a floor of 1e-3 × the median tensor norm).
  - **A positive control** at 98,304 samples, where the known bug should show. If it doesn't, that's reported.
  - **The crop:** 61,000 samples. The loss's 4,096 window pads it to 65,096, under 65,536.
- **The crops.** 12% of training draws drop the target, so the network learns to return silence where the hinted
  part rests.
- **The fine-tune:** all parameters train, with no weight decay, a batch of at least 4, and lr 1e-5 (lower, for four
  songs).
- **Freezing.** This configuration is committed before A3's read. Any later amendment is based on the
  training-band items only.
- **The MPS:** the other sessions are told it's in use before the run.

### Amendment 3b (2026-11-15, after s1b's main read, before any A3 or S3 read; ledger `phase_s1_a3b`)

- **Its basis, the training-band items** (the freeze rule): on Forkupines' and BKS's 32 centred items, separating in
  stereo first and then taking the centre (`xlst_mdxc`) gains +12.79 dB, against `mdxc`'s +8.89 (BKS +11.78 against
  +6.72, Forkupines +13.81 against +11.07). On all S0's centred items it's +10.85 dB [+8.71, +12.31], with a read gain
  of +0.067 [+0.048, +0.079], the largest on centred items; `mdxc`'s is +0.006.
- **`steer_xlmdxc`** (under S1's rule, beside `steer_mdxc`): steer by the coarse hint, X-LANCE on the steered pair
  (both outputs), MDX23C on that stereo stem, the mean, times cos φ. On a centre hint it's `xlst_mdxc`: copied, a few
  recomputed as the identity check (float64 on the CPU, where s1b's ran on MPS through float16). So its centred and
  split cells repeat an option already read; only its off-centre and double cells are new.
- **S3's routed comparator for the centre hint** becomes `xlst_mdxc` instead of `mdxc`. It's the stronger option on
  the training bands too, so the change makes S3's rule harder to meet in expectation (its interval against
  `xlst_mdxc` may still be tighter than against `mdxc`). The side hint stays `side`.
- **The training batch:**
  - **What happens:** a batch of 2 clips needs 15.8 GB of MPS memory and swaps, and 4 doesn't fit in 32 GB.
  - **The fix tried:** the model's gradient checkpointing fails, with a shape error in BS-RoFormer.
  - **So:** one clip per pass, four passes summed per update (accumulation), the same update as a batch of 4 since
    the model has no batch statistics. That's about 1.7 s per clip.
  - **The evaluations:** every 1,000 updates (4,000 clips), about 2 hours apart.
- **The gradient check, run:** at 61,000 samples the median relative error is 6.4e-5 (max 1.6e-3), a pass. At 98,304
  samples it's 0.88 (max 7.4), so the bug shows where expected.

## S1 results

Both rounds ran 2026-11-14 and 15 (zero renders), read by the rule above and audited by separate code (the same
means; the intervals within 0.3 dB). SI-SDR gain against mono, with the 90% band-bootstrap interval; the read is the
drop in the model's cosine distance (higher is better).

| Option | Centred | Off-centre | Double | Split set | Read (centred) |
|---|---|---|---|---|---|
| `xlst_mdxc` (X-LANCE stereo, then MDX23C) | **+10.85** [+8.71, +12.31] | −15.45 | −2.94 | **+5.33** [+3.92, +6.87] | **+0.067** |
| `cw` (CenterWide, then X-LANCE) | +6.37 | −1.42 | −2.65 | +5.06 | +0.037 |
| `mdxc` (MDX23C, then X-LANCE) | +7.03 | −17.32 | −2.78 | +4.71 | +0.006 |
| `side` (the target's own channel, an oracle) | +2.95 | **+7.16** [+6.05, +8.21] | −0.43 | −1.84 | +0.012 |
| `xlst_psi` (psi⁴ mask after separating) | +6.40 | −2.37 | −3.01 | +3.11 | +0.010 |
| `stereo` (X-LANCE on the true pair) | −0.70 | +1.05 | +0.12 | −0.29 | −0.002 |
| `centre4` (the picker's stem_C) | −1.77 [−5.82, +1.60] | −9.10 | −4.21 | −4.13 | −0.062 [−0.106, −0.024] |

- Mega-53's guitar head, the agreement ensemble, a second pass and the keys mask are level or slightly worse. The
  lead/rhythm models' lead outputs lose 1 to 14 dB; listra92's rest output gains +1.87 [+0.90, +2.62] off-centre,
  below the own channel's +7.16.
- Off-centre (+7.16 dB, read +0.044) the target's own channel works, but it needs the side, which the user's pick
  gives. A centred part is best served by `xlst_mdxc` on S0's centred items, by SI-SDR and by the read. With
  separate takes on both sides (the split set), `xlst_mdxc` (+5.33 dB, read +0.062) and `cw` (+5.06, read +0.073)
  are level: undecided between them.
- The trigger by the score doesn't fire (best lo90 +8.71, `xlst_mdxc` centred). S3 runs on the user's go (above).
- The product session added `--version xlst_mdxc` behind a flag (PR #492, merged). Its default stays until the
  user's ear decides.

## A3 results (steering with the existing tools)

Run 2026-11-15 (zero renders, CPU), read by S1's rule against mono and audited by separate code (the same means;
the intervals within 0.2 dB). SI-SDR gain against mono with the 90% band-bootstrap interval; the read as above (band
bootstrap). Beside the rule, against the target's own channel (`side`, the best existing option off-centre): the
band-clustered t interval over S0's 7 bands, whose centre is the mean of the band means.

| Option | Centred | Off-centre | Double | Split set | Read (off-centre) |
|---|---|---|---|---|---|
| `steer_xlmdxc` (steer, X-LANCE stereo, MDX23C) | +10.85 (= `xlst_mdxc`) | **+12.73** [+10.51, +14.51] | −16.11 | +5.33 (= `xlst_mdxc`) | **+0.073** [+0.040, +0.104] |
| `steer_mdxc` (steer, MDX23C, X-LANCE) | +7.03 (= `mdxc`) | +4.81 [+1.12, +7.46] | −26.69 | +4.71 (= `mdxc`) | −0.069 [−0.120, −0.030] |
| `steer_mid` (a control) | −0.70 | +5.16 | +0.21 | −0.29 | +0.037 |
| `steer_mdxc_exact` (the exact pan, a ceiling) | +7.21 | +5.42 | −27.63 | +4.32 | −0.041 |
| `steer_mdxc_h1` (hint ±1.0) | +7.03 | +2.18 | −22.01 | +4.71 | −0.100 |

- **A part on one side:** `steer_xlmdxc` wins against mono under the rule. Beside it, it gains +5.05 dB [+2.58,
  +7.52] over the own channel (band-clustered; 6 of 7 bands up; the paired item mean is +5.57), with a read not
  worse (+0.036 [−0.008, +0.081], undecided). It's the first option ahead of the own channel off-centre, by SI-SDR.
  The gain is about the same whether the coarse hint lands the part within 0.15 of the centre or 0.15 to 0.3 off
  it (+12.70 and +12.82, n 56 and 21; descriptive).
- **One route, given the side:** on a centred part `steer_xlmdxc` is `xlst_mdxc`, so one chain serves both. The side
  here is an oracle (the drawn pan, standing in for the user's pick). A wrong hint or a blind one is untested, and
  October's blind side methods lost; without a person the route needs a side detector.
- **The effects row** (descriptive, against mono, off-centre): the delay time is found on 7 more of the 42
  delay-ons (+0.17). T0's delay vote moves −0.030 on delay-ons (worse) and −0.027 on delay-offs (better).
- **`steer_mdxc` fails** off-centre: it gains in SI-SDR but hurts the read (−0.069), so it isn't used. Separating
  before the centre model matters, as in s1b: `steer_xlmdxc` over `steer_mdxc` off-centre is +8.76 dB [+5.55,
  +11.97] with the read +0.148, all 7 bands up (band-clustered; post hoc, not in the read files).
- **The doubles lose** (−16.11): steering keeps the hinted copy, and S0's double target is both copies, one
  delayed. That's why the cell is out of S3's rule; here it's descriptive. Whether one take of a real double reads
  its tone as well as both is untested.
- **The user's seven R1 songs:** steered left or right (±0.7), each song's span leaves 13 to 48 dB less than the
  mono stem, so no guitar sits near either side; steering doesn't change them. Their version page carries `stem`,
  `stem_C`, `xlst_mdxc` and `cw`.

### Amendment 3c (2026-11-15, after A3's read, before S3's read; ledger `phase_s1_a3c`)

- **S3's routed comparator for the side hint** becomes `steer_xlmdxc` instead of `side`. Otherwise S3 could become
  the side-part default while worse than `steer_xlmdxc`. Its basis is the training-band items (the freeze rule):
  against `side` off-centre, Forkupines +7.50 dB and BKS +2.62 (the read mixed: +0.074 and −0.025). That makes
  S3's side cell harder to meet. The centre hint's comparator stays `xlst_mdxc`, which `steer_xlmdxc` equals there.
  S3's read writes the `side` comparison beside (`vs_side`).

### Amendment 3d (2026-11-15, during S3's run, before any S3 read; ledger `phase_s3d`)

- **Why.** The run keeps `best.pt` by the median SI-SDR (+0.1 dB), with the read only as a floor (no worse than step
  0's), but the model's read is co-primary in S3's rule. At step 6,000 the validation read dropped from 0.1364 to
  0.1191, with the median level (+6.58 against step 5,000's +6.63, under the +0.1 dB bar). So `best.pt` stayed at step
  5,000, and the run would have overwritten step 6,000's weights at the next evaluation.
- **The checkpoint S3's read uses,** chosen after the stop. The eligible evaluations are those with a read no worse
  than step 0's. Among the eligible checkpoints whose weights are kept, those less than 0.1 dB under the highest
  eligible median qualify (`best.pt`'s step always does). The lowest read wins; on a tie, the earlier step.
  `best.pt` counts as its step. `s3-pick` runs after the run's own stop (patience, the abort or 72 h) or the
  user's stop (`--user-stop`), recorded in `pick.json`. The run's stop rule is unchanged (the run is going), so
  patience still counts on SI-SDR. No later amendment extends or stops the run by the read.
- **The weights kept:**
  - from step 6,000 on, `last.pt`'s after each evaluation (`s3-keep`, run every 10 minutes by a keeper loop that
    doesn't look at the read);
  - step 6,000's, copied from `last.pt` right after its evaluation (sha256 `614f4e3e…`); step 5,000's from
    `best.pt` (`6aa0168f…`);
  - steps 1,000, 3,000 and 4,000 are gone, and step 2,000's survives only as the scratch copy used for the table.
    Each is 0.48 dB or more under step 5,000's median, so none could qualify;
  - `pick.json` lists any evaluation from step 6,000 on whose weights weren't kept (`missing`).
- **Its basis is the validation band only** (Adam Buckley, a training band; the freeze rule). No held-out item has
  been read with S3. Descriptive and post hoc: S3 against `steer_xlmdxc` on the 136 centred and off-centre
  validation mixes. It's the comparator the rule routes to there. Item bootstrap, 90%:

  | Step | SI-SDR, centred | SI-SDR, off-centre | Read, centred | Read, off-centre |
  |---|---|---|---|---|
  | 2,000 | −0.56 [−1.95, +1.85] | +0.27 [−0.82, +1.43] | −0.055 [−0.067, −0.040] | −0.030 [−0.040, −0.020] |
  | 5,000 | −0.02 [−1.41, +2.32] | +1.43 [+0.48, +2.42] | −0.059 [−0.070, −0.045] | −0.031 [−0.042, −0.021] |
  | 6,000 | −0.03 [−1.40, +2.34] | +1.39 [+0.52, +2.42] | −0.041 [−0.052, −0.027] | −0.015 [−0.023, −0.006] |

  A read gain is a drop in the cosine distance. Step 6,000's read gain over step 5,000 is +0.016 to +0.018 in every
  stratum, doubles included. One band of 13 sections makes these item-bootstrap intervals optimistic. S3 followed
  by MDX23C's centre (in X-LANCE's place in `steer_xlmdxc`) is worse than S3 alone, at step 2,000: −0.61 dB and a
  read −0.016. These scripts stay outside the repo; the S3 write-up reports them.
- **What it changes.** Only which validation checkpoint the held-out read uses. The held-out rule, its comparators
  and its intervals are as declared. The choice is made among a few checkpoints on validation, never on the held-out
  bands.
- **Easier for S3 on the read.** The checkpoint is chosen for the read, at a cost of up to 0.1 dB of validation
  median SI-SDR. This was written after seeing evaluations 0 to 6,000. It picks 6,000 today and is prospective from
  7,000 on. The held-out read stays unbiased for the chosen checkpoint. The picked checkpoint's validation read is
  optimistic and isn't quoted as an estimate.
- **Code:** `s3-keep`, and `s3-pick` (after the stop; it writes `run/pick.json` with the file's sha256).
  - `s3-apply` needs that file and this key, and records the checkpoint in each set's `stems/s3/pick.json`.
  - It refuses stems from another checkpoint.
  - `s3-feats --options s3` and `s3-read --what s3` check that record.
  - `s3-apply`, `s3-feats` and `s3-read` run from main after this merges. The trainer's worktree holds the old
    `s3-apply`.

## S4: the centre model, fine-tuned (declared 2026-11-15, during S3's run, before any S3 or S4 held-out read; ledger `phase_s4`)

**Why now.** The user, at S3's step 10,000: "Quality and accuracy are the keys, and only measurements should lead
us. Continue training and measuring and select the best approach according to the results." S3 keeps running to its
own stop. S4 is the next candidate, measured the same way, on the MPS after S3 stops.

**The evidence, the validation band only** (Adam Buckley, descriptive, post hoc, item bootstrap; no held-out item
read). Against `steer_xlmdxc` on the 136 non-double validation mixes:

| Step | SI-SDR, centred | SI-SDR, off-centre | Read, centred | Read, off-centre |
|---|---|---|---|---|
| 5,000 | −0.02 | +1.43 [+0.48, +2.42] | −0.059 | −0.031 |
| 6,000 | −0.03 | +1.39 [+0.52, +2.42] | −0.041 | −0.015 |
| 7,000 | +0.19 | +1.48 [+0.55, +2.48] | −0.062 [−0.074, −0.048] | −0.032 [−0.042, −0.022] |
| 8,000 | +0.12 | +1.67 [+0.74, +2.68] | −0.050 [−0.061, −0.036] | −0.018 [−0.027, −0.009] |

S3 pulls out a cleaner waveform, but the model reads the part worse from it than from the chain at every step, and
the gap moves up and down rather than closing. The chain's MDX23C carries its read: X-LANCE alone is −4.5 dB (median)
under the chain, and S3 followed by MDX23C is worse than S3 alone (−0.61 dB, read −0.016).

**How it differs from what failed.** S3 retrained the chain's front (X-LANCE) on a waveform loss, and the model's
read didn't follow the SI-SDR. S4 keeps today's best chain whole and retrains only its tail, the MDX23C phantom-centre
model, on what it actually receives there: X-LANCE's output of a steered mix. Three things follow:
- it starts exactly at the comparator. Step 0 is `steer_xlmdxc` itself: checked on three validation mixes, the same
  SI-SDR to 0.01 dB and the same read to 0.001. So the curve measures the gain over the comparator directly;
- the curve and the best checkpoint are chosen by the model's read, with SI-SDR as a floor. That's S3's lesson: a
  best chosen by SI-SDR didn't move the read;
- the curve reads the rule's strata only, the 136 non-double mixes. The doubles are out of the rule, and S3's
  overall read moved most on them.

**The model and the data.**
- **The model:** wesleyr36's MDX23C phantom-centre model (TFC-TDF v3, 109.4 M parameters, hash-checked; MSST's
  config: n_fft 2,048, hop 512, chunk 130,560 samples). All parameters train.
- **The input:** X-LANCE `gtr_mss`, frozen (hash-checked), on S3's training draws (`sep_s3_train.build_draw`, the
  whole 10 s: the same strata, bands, jittered hint, 12% dropped targets and mastering). The target is S3's: the
  hinted copy as it sits in the steered mix.
- **The cache (`s4-cache`):** 2,000 fixed draws from S3's training bands (Forkupines, BKS, The Maybe Next Years),
  stored as X-LANCE's steered stereo output and the steered target (float16, about 7 GB). X-LANCE runs on the CPU
  beside S3 (two workers), so the cache matches the comparator's stems. It stops if the disk would fall under 20 GB.
- **Validation (`s4-val`):** X-LANCE's output on S3's 200 fixed validation mixes, on the CPU.

**Training (`s4-train`).**
- Crops of the model's own chunk (130,560 samples, 2.96 s), so training crops are its inference chunks. A crop is
  taken where the target plays (S3's rule, against the model's input), anywhere in a dropped-target draw.
- **The loss:** L1 between the model's output spectrogram and the target's, both by the model's own STFT. The
  checkpoint's name says it was trained on an L1 frequency loss. No inverse STFT is differentiated, so the MPS
  gradient bug (STFT backward over 65,536 samples) is out of the loss's path.
- **Before the run, the gradient check (`s4-check`):** one batch's gradients on MPS against the CPU's, per parameter
  tensor, at the training crop. It runs on MPS only if the median relative error is under 1e-3 and the largest
  under 1e-2, and the spectral forward, inverted, matches the model's own output (checked: max difference 0.0).
  Otherwise it's reported, and the run waits. The speed check sets the batch.
- AdamW at lr 1e-5 with 500 warm-up steps, fp32, a batch of at least 4 (micro-batches summed), no weight decay. A
  hand clip at norm 1.0, non-finite steps skipped, and S3's reload and abort rule. Never beside another MPS
  training.
- **The curve:** every 1,000 steps, on the 136 non-double validation mixes: the median SI-SDR (44.1 kHz) of the
  rotated-back mono estimate against the target's, and the model's read (mean cosine distance at 48 kHz, CPU), as
  S3's `evaluate`. Step 0 is the first best.
- **A new best** needs a read at least 0.002 lower than the best's, with the median SI-SDR no lower than step 0's.
  The run stops after 5 evaluations without one, at the abort rule, or after 48 hours. The user can stop it.

**The read, once, after the stop.**
- **What runs:** `s4-pick` names `best.pt` with its sha256. `s4-apply` runs on the held-out 120 S0 items and 38 split
  items: steer by the coarse hint, X-LANCE (CPU), the fine-tuned model, rotate back and average. The stems carry
  their checkpoint (`stems/s4/pick.json`). `s3-feats --options s4`, `s3-read --what s4` and `s3-decide --what s4`
  check it and score them.
- **The rule:** S3's, unchanged. Per cell, against mono and against the routed comparator (a centre hint to
  `xlst_mdxc`, a side hint to `steer_xlmdxc`), with the band-clustered t interval over the five held-out bands and the
  read co-primary. The doubles are descriptive.
- **Two trained candidates.** S3 and S4 are each judged by that rule on the same items. A cell either qualifies for
  goes on the picker. If both qualify for a cell, both go on it, with the held-out read difference beside, and the
  user's ear on R1's songs decides. This is fixed now, before either held-out read.

**What it can't say.** S3's caveats hold: built mixes, amp-sim targets, the oracle hint, two guitars at one place.
Plus: a fixed cache of 2,000 draws (about 5.6 hours of audio) is smaller than S3's on-the-fly stream, so
the model could fit the cache. The validation curve watches that, and the held-out read is its test.

**Cost.** Zero renders. The cache's X-LANCE about 4 CPU hours in two workers beside S3, which slows S3 by about 8%.
The MPS after S3's stop, up to 48 h. About 7 GB of disk, 44 GB free.

**Freezing.** This configuration is committed before any S4 run. S3's run, rule and pick are unchanged.

## What it can't say

S0's mixes are built, not mastered records. Their panning is drawn, not each song's own. E1e's targets are mono, so
stereo tails that a centre mask would strip (reverb, delay, chorus width) aren't in S0. The ear has to check those.
So S0 ranks the options, and the user's ear on real songs decides.
