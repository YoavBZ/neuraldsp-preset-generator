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
    mean is biased up. So wins are candidates for the ear, ranked by the SI-SDR gain's lo90. The S2/S3 trigger reads
    the best option's lo90, not its mean.
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

## What it can't say

S0's mixes are built, not mastered records. Their panning is drawn, not each song's own. E1e's targets are mono, so
stereo tails that a centre mask would strip (reverb, delay, chorus width) aren't in S0. The ear has to check those.
So S0 ranks the options, and the user's ear on real songs decides.
