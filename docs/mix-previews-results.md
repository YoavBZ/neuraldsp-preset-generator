# Released mixes against our unity sums: results (2026-10-19)

Descriptive, development only, zero renders. Code: `learn/mix_previews.py`. Data:
`~/ndsp-presets/references/mix-previews/` (the previews and `alignment.json`) and
`~/ndsp-presets/learn/mix-previews/` (`report.json`, per-block alignment, stems, logs).
Figures are band-weighted means with 90% band-bootstrap intervals (4,000 draws, seed 20261019).
There are no pass/fail bars.

## Why

The [stereo and mix check](stereo-and-mix-check-results.md) found no session that ships its
released mix. Our "mixes" are unity sums of the raw tracks, so the guitar in them is the raw amp
track. Cambridge MT sells the released mixes as "Full Preview" MP3s (mastered) and some as
unmastered WAVs. The user downloaded 10 previews, Sound On Sound's Mix Rescue remix of Signs
(`1003_Remix.mp3`), and 5 unmastered WAVs (Signs' is the same remix, unmastered). This asks two
questions. Are these the same performances as our multitracks? And how much harder do real
mixing and mastering make separation than our unity sums do?

## Alignment

**Method.** The session is the unity mono sum of the records' `included_mix_tracks`. The preview
is folded to mono and resampled from 44.1 to 48 kHz with `analysis.io`. A whole-file GCC-PHAT
gives the global offsets. Each 4-s block (2-s hop) is then located by its own envelope search
and by the top three global offsets, and refined to the sample. A block matches when at least 3
blocks agree on its offset within 2 ms. The main offset's blocks form the span, with a fitted
linear drift. Every crop also gets its own 10-s GCC-PHAT check: it counts as covered when the
crop's peak lies within 2 ms of the main offset and stands at least 8 SD above its spread. That
crop-level lag is the offset used for separation.

**Every file matches the session at one main offset: the same take and arrangement.** Signs is
"partial" under the block rule (see below). The main whole-file peak stands 100–5,000 SD high;
the next is at most 61 SD.

| song | file | offset (s) | main-offset blocks (of judged) | same take |
|---|---|---|---|---|
| Get Out Of Bed | preview / unmastered | 3.00 / 3.02 | 81/84, 82/84 | yes / yes |
| Today's The Day | preview | 4.10 | 107/117 | yes |
| Magilla | preview | 2.24 (drift −5.2 ppm) | 128/128 | yes |
| It Was My Fault For Waiting | preview | 16.35 | 109/118 | yes |
| Colour Me Red | preview | −0.002 | 95/98 | yes |
| Let's Dance | preview | 10.44 | 63/67 | yes |
| Passing Ships | preview / unmastered | 2.15 / −0.05 | 86/125, 93/127 | yes / yes |
| Quicksand | preview / unmastered | 27.72 / 3.79 | 58/65, 63/69 | yes / yes |
| Wickerman | preview | 3.79 | 93/93 | yes |
| Femme | preview / unmastered | −0.013 / 0 | 107/112, 112/112 | yes / yes |
| Signs (Mix Rescue remix) | remix / unmastered | 3.43 / 3.43 | 55/113, 56/113 | partial / partial |

- **No edits were detected at 4-s block resolution.** The only other offsets that several blocks
  agree on are copy-pasted repeats in the session: Passing Ships at about ±1.07 s (and, in the
  preview only, +3 s), Signs at 20.4 s and 69.4 s,
  and 3 blocks in Today's The Day. Their median waveform r is below the main offset's (0.03 against
  0.10 on Passing Ships, 0.02–0.04 against 0.05 on Signs), so they are ambiguity, not edits. On
  Signs 27–35% of the blocks fall there, so the rule says "partial". That is partly a polarity
  artefact: 14 of its 31 other-offset blocks are anti-correlated at the main offset (r < −0.05),
  against 1 of the 55 main blocks, and the signed-r rule rejects them. Signs' spans have maximum
  residuals of 18 and 24 samples. Signs' stage F crop (ElecGtr3) and ElecGtr2 still check out at
  the main offset; ElecGtr6 only in the unmastered file (see Coverage). A cluster about 20 ms from
  the main offset in the Passing Ships preview and the Signs unmastered file sits on the ±960-sample
  refine edge, so it is an edge artefact.
- **The previews are full songs, apart from trims.** Quicksand's preview starts 27.7 s into the
  session; its matched blocks end at 126 s of its 133 s, though the file runs to the session's end
  (its unmastered WAV is the full song). It Was My Fault and Let's Dance start 16 s and 10 s in,
  and It Was My Fault ends about 12 s before the session does. Today's The Day's preview covers
  only session 4.1–241 s of 277 s (hence the 79% context below).
- **The waveform correlation is low even when aligned.** The median Pearson r of matched 4-s
  blocks against the unity sum is 0.05–0.42, against near 0 for unmatched blocks (−0.00 to 0.07; Let's Dance 0.16, from only
  4 blocks). The real
  mixes differ a lot in balance, effects and processing from a flat sum of every track.
- **Sample-rate handling:** every file is 44.1 kHz stereo (the WAVs too). Resampled to 48 kHz, the
  drift is under 1 ppm except Magilla (−5.2 ppm, fitted; residual ≤ 1 sample at the crop).

**Coverage.** All 17 stage F parts in these songs (9 bands) are covered, in every file that has
them. Of the label table's other 13 crops in these songs, 11 are covered in every file. It Was My
Fault ElecGtr1 (12.5–22.5 s) is 62% inside, because the preview starts at 16.4 s. Signs ElecGtr6
is covered in the unmastered remix (25 SD) but not in the mastered one, where its check lands on
a loop 3 s away (46 SD); why the two files differ there is unexplained. Three stage F 30-s contexts run past a preview's edge and are zero-padded there;
the 10-s crops themselves are always inside: Today's The Day 07 (79% of the context inside), It
Was My Fault 3 (77%), wickerman 1 (97%).

## Raw track, unity stem and real-mix stem

For each covered stage F crop: (a) is the raw amp track (`reference.wav`), (b) is the stored
Mega-53 stem of our unity context, and (c) is Mega-53 (the same pruned head, CPU, mono) on the
aligned preview's 30-s context, cut to the crop. SNR is gain-fitted against (a). LSD is the RMS
difference of the 1/3-octave long-term spectra after one gain (`stereo_mix_check`). There are 17
mastered parts in 9 bands; for Signs the mastered file is the Mix Rescue remix. 23 Mega-53 runs, about 81 s each.

| measure (mastered, 17 parts) | (b) unity stem | (c) real-mix stem | c − b |
|---|---|---|---|
| SNR vs raw track, dB | 0.87 [0.60, 1.17] | 0.24 [0.11, 0.39] | **−0.62 [−0.95, −0.31]** (15/17 lower) |
| SNR with the stem's own best lag (±100 ms) | 0.87 [0.60, 1.17] | 0.56 [0.36, 0.77] | −0.31 [−0.55, −0.03] |
| SNR after a held-out 2,048-tap LS FIR | 0.92 [0.62, 1.23] | 0.92 [0.55, 1.30] | −0.00 [−0.25, +0.29] |
| LSD vs raw track, dB | 8.13 [6.53, 9.65] | 8.34 [6.71, 9.99] | +0.21 [−1.21, +2.13] |
| LSD (b) vs (c), dB | | 6.38 [4.84, 8.07] | |
| real mix vs unity mix on the crop: r, LSD | | 0.22 [0.16, 0.28], 3.40 dB [2.97, 3.84] | |

- **Real mixes cost SNR, and part of the cost is timing.** At the crop's aligned offset (the
  song's offset, refined per crop by at most 5 samples), the real-mix stem keeps a band mean of 0.24 dB against the raw track, close to none. In the real mix,
  single guitar tracks are moved, and some flipped, against the rest of the mix, which sets the
  global offset: wickerman 1–3 by −398 samples (8 ms), Today's The Day 07 by −491, Let's Dance by
  −89 and −90. The same shifts appear between the raw track and the real mix itself, so they belong
  to the mix, not the separator. Nine of 17 correlate negatively at their best lag. Eight look
  polarity-flipped: magilla (r = −0.49), get-out-of-bed (−0.21), Let's Dance 3 and 4 (−0.45,
  −0.44), Quicksand 2 (−0.55), and, only weakly, wickerman 1–3 (−0.10 to −0.15). The ninth,
  Passing Ships ElecGtr4 (−0.03), is at noise level.
  With the stem's own lag the loss halves, to −0.31 dB. A 2,048-tap filter from the stem onto the
  raw track, fitted on the other half of the crop (it also absorbs lag and sign), leaves no gap on
  average (0.92 both; c − b −0.00 [−0.25, +0.29]). It lifts the unity stem too, and it needs the
  raw track. So, on average, most of the gap is timing and EQ, linearly recoverable with lag and
  filter fitted against the raw track, rather than missing content. Polarity costs nothing here:
  the gain-fitted SNR already allows a negative gain. It matters only for sign-sensitive scores.
  But it varies a lot per part. magilla falls from 1.92 to 1.21 dB even lag-matched;
  get-out-of-bed from 1.10 to 0.20. Passing Ships 2 and Quicksand 2 rise (0.24 → 1.63, 0.42 →
  1.56). Their real mixes expose these guitars more than a flat sum does: the raw track explains
  more of the real mix than of the unity mix (FIR SNR 0.16 against 0.02, and 0.45 against 0.06).
- **Mega-53 finds nothing of Passing Ships ElecGtr4 in either real mix** (its best lag is 1,302
  samples at r = −0.03, SNR 0.00 in both files), nor much in the unity sum (0.03 dB), so whether
  it is in the real mix is not settled.
- **The long-term spectrum moves, but not on average.** LSD to the raw track is about the same
  for both stems (8.1 and 8.3 dB): both sit about 8 dB LSD from the raw track either way. The two stems
  still differ from each other by 6.4 dB LSD. The per-part changes run both ways, from −5.3
  (Passing Ships 2) to +8.3 (Signs remix).
- **In SNR, mastering adds little beyond the mix.** On the 6 parts with both files (4 bands), the
  unmastered stem's SNR is equal or higher by 0.00–0.11 dB per part (for example Passing Ships 2:
  1.03 against 0.92; femme 5: 0.44 against 0.33). The spectra differ more (femme 5 b–c LSD 6.61 dB unmastered against
  2.40 mastered). The unmastered mixes sit about 10 dB below the unity sums (−10.4 [−12.4, −8.3])
  and the mastered ones near them (+0.65 dB band mean [−1.20, +2.71]; part median −1.4). Unmastered summary: c − b =
  −0.41 [−0.96, +0.09], lag-matched −0.18 [−0.73, +0.37], FIR +0.16 [−0.30, +0.62].

**For the yardstick.** On real songs, the guitar to match is not the raw track. A stem from a
released mix is time-shifted, often polarity-flipped, and re-balanced and EQ'd against it. On these
17 parts that costs 0.6 dB of the 0.9 dB SNR that Mega-53 gets on unity sums, and half of it is
recovered by a per-stem lag (found against the raw track). Scores against the raw track that
ignore lag will understate real-mix matches; a gain-fitted SNR is already polarity-invariant, but
a positive-gain or correlation score is not. A lag-searched, gain-fitted SNR suits real songs best.
LSD is lag-invariant but moves by several dB per part with the real mix's EQ (a–c minus a–b from
−5.3 to +8.3). In SNR, mastering itself is a small part of the gap.

**Caveats.** There are 17 parts in 9 bands, and 6 parts in 4 bands for the unmastered files. The
previews are MP3s, so the codec moved the top band; LSD stops at 12 kHz. Signs' "real mix" is a
magazine remix, not the release. (c)'s context is zero-padded where a preview ends.

## Audit

Audited 2026-10-19 by an independent agent; changes: two independent audits (the original and a
re-run) both returned "confirmed with corrections". Every number reproduces: all 23 alignments, each
per-part row recomputed from the stems against `reference.wav` (SNR, lags, lag-matched and held-out
FIR SNR, LSDs) and the band means and 90% band-bootstrap intervals (re-run independently, 4,000
draws, seed 20261019). No code bug changes the numbers. Wording changes: the negative-correlation
count is nine of 17, not eight (Passing Ships ElecGtr4 at noise level); polarity is no longer
blamed for the SNR gap, since the gain-fitted SNR allows a negative gain; the yardstick now prefers
a lag-searched gain-fitted SNR and notes that LSD moves several dB per part; "same take" is per
file, with Signs' "partial" partly a polarity artefact of the block rule; "no edits found" became
"none detected at 4-s block resolution"; the FIR row shows its interval instead of "~0"; trims of
Today's The Day, It Was My Fault and Quicksand are stated; Signs ElecGtr6's file difference is
flagged as unexplained; Passing Ships ElecGtr4 is "not settled" rather than "absent"; the mastering
claim is limited to SNR; "the separator's own spectral error dominates" and "the drums set the
offset" were dropped as unsupported. Not verified: the MP3 codec's effect on the top band and the
12-kHz LSD cut-off.
