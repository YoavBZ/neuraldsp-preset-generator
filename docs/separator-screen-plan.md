# Separator screen: plan (DI-recovery experiment 1)

Declared 2026-10-15, before any compute. **Review:** reviewed 2026-10-15
(`tmp/separator-screen-plan-review.md`, local): approved with changes, all folded in. It is
experiment 1 of the DI-recovery report
([`research/di-recovery-2026-10.md`](research/di-recovery-2026-10.md), "The cheapest quick test,
made decisive by two margins"). Development data only: set 3's 5 clean and crunch check parts. No
held-out data is read (not Guitar-TECHS P3, not sets 5 or 6). No training.

## Why

Two errors stand between a song and the knob search: separation, then the DI rebuild. Arm A's
known-target control showed the rebuild alone already breaks the search on clean renders
([song-settings-plan.md](song-settings-plan.md), "Recorded outcome (2026-10-15)"). The ladder
then placed C′'s error in fine structure and transients, under about 10 ms, not in tilt or slow
dynamics ([rank-margin-ladder-results.md](rank-margin-ladder-results.md)). Nothing yet says how
much separation adds. The merged separation report keeps htdemucs_6s
([`research/guitar-separation-2026-10.md`](research/guitar-separation-2026-10.md)): Mega-53 gained
only +0.5 to +0.6 dB paired SNR on 61 parts and loses the top octave
([separator-upgrade-results.md](separator-upgrade-results.md)).

This plan answers two questions:
1. **Does separation alone flip the ranking?** With the true DI, does the search objective still
   rank the target T above the start S when the recording is a stem?
2. **Does any licence-clean challenger flip fewer cells than htdemucs_6s?**

**What the result is.** The rank margin is a weak screen: it agreed with search success on 14 of
18 searches, and within the C′ run on 5 of 9 (Spearman 0.00) (ladder, step A). Every count here
inherits that agreement rate. So this screen's result is **descriptive evidence about
separation, not a gate.** A row that "advances" only earns the merged report's full switching
test; nothing here switches the separator or passes or stops a rebuild.

## Rows

| Row | What | Eligible |
|---|---|---|
| `htdemucs` | htdemucs_6s with `learn/separate.py`'s settings (shifts 0, overlap 0.25, split, 30-s context), CPU, 4 torch threads | the control |
| `mega53` | Mega-53's `electric-guitar` head (below) | yes |
| `blend` | the fixed crossover blend (below) | yes |
| `clean` | no separation: the clean fake recording itself | reference only |

**htdemucs.** `learn.separate.GuitarSeparator` with `DEVICE=cpu`. Its constructor sets 2
threads, so the screen calls `torch.set_num_threads(4)` after construction, as the stored set-3
stems were made (`learn/set3/stems/_work/separate_demucs.py`, 4 threads, CPU).

**Mega-53.** `~/ndsp-presets/tools/msst/` (provenance.json): ZFTurbo/Music-Source-Separation-
Training v1.0.21 (commit ea7eb9c), `mvsep_mega_model_bs_roformer_53_stems_v1.ckpt` (sha256
c62820…3ff3519f) and its yaml (sha256 7e198062…dfc51103). Approved by the user on 2026-10-15
(MIT repo, no separate weights licence). The wrapper checks both hashes before loading, and that
the repo checkout is at ea7eb9c.
- **Input, as the 2026-10-08 test:** the mono 48-kHz context duplicated to two channels, 48 →
  44.1 kHz (`scipy.signal.resample_poly` 147/160), `utils.model_utils.demix` with the yaml's
  inference settings (20-s chunks, `num_overlap` 2, batch 1, no normalisation), the
  `electric-guitar` stem, channel mean, back to 48 kHz (160/147), padded or cut to the context.
- **CPU only:** `device='cpu'`, `PYTORCH_ENABLE_MPS_FALLBACK=0`, 4 threads. MPS is busy with arm B.
- **Pruned to one head:** only the `electric-guitar` mask estimator is kept. Before any screen
  stem, on one context (colour-me-red, real): the pruned stem must equal the full 53-stem
  model's (max |difference| 0.0). If not, every Mega-53 stem uses the full model (about 191 s
  per context instead of about 102 s). This is the only internal check of the wrapper:
  `learn/sep2` was deleted, so nothing can be reproduced against 2026-10-08. As a sanity check,
  each real part's Mega-53 SNR against its amp track is reported beside the 2026-10-08 set-3
  median (1.48 dB).
- **Memory:** the checkpoint is 1.37 GB (about 340M fp32 parameters), and the identity check
  loads all 53 heads. Mega-53 runs alone (no htdemucs, rebuild or render at the same time). Peak
  RSS is logged, and the run stops if swap grows. Arm B shares the CPU and unified memory (about
  10.4 GB RSS); only arm B's MPS is untouched.
- **The venv:** `~/ndsp-presets/tools/msst-venv`, torch 2.14 on CPU (as demucs-venv), plus what
  `models.bs_roformer` and `utils.model_utils` import: einops==0.8.1 (the repo's pin),
  rotary_embedding_torch==0.3.5, beartype==0.14.1, ml_collections, omegaconf==2.2.3, librosa
  (the mel-band variants in `models/bs_roformer/__init__.py`), loralib, tqdm, packaging,
  soundfile, scipy, pyyaml. From PyPI only, no git URLs. `pip freeze` goes into `run.json`.
  demucs-venv isn't touched. The packages are part of running Mega-53, so they fall under the
  user's approval of 2026-10-15.

**The blend,** built at 48 kHz from the two **float32** 30-s stem arrays (not from FLAC), before
the crop is cut:
- `sos = scipy.signal.butter(4, 6000, "low", fs=48000, output="sos")`;
- `LP(x) = scipy.signal.sosfiltfilt(sos, x)` (zero-phase; effective order 8, −6.02 dB at 6 kHz);
- **blend = LP(mega53) + (htdemucs − LP(htdemucs)).**

The two branches are exactly complementary (they sum to the identity for any x), so identical
stems give back the stem. No gain matching between the stems; their level difference in 4–8 kHz
is recorded. **Relative lag:** the GCC lag between the two 30-s stems themselves
(`rank_margin.gcc_lag`) must be 0 samples. Otherwise the blend for that context is stopped and
reported (a few samples' offset would comb the crossover band).

**Research-only anchors: none.** None is on disk: a search of `~/ndsp-presets` and `~/.cache`
for weights found only Mega-53, htdemucs_6s (HF cache), DAC and PANNs. BS-RoFormer SW, X-LANCE,
MDX23C De-Reverb and FoxJoy are not there, and `learn/sep2` with its venv was deleted on
2026-10-13. Nothing else is downloaded for this plan.

## Cells

The 5 set-3 check parts (`learn/cprime_folds.py` `check`'s selection, asserted) × PR12 and SW50R
= **10 cells**. Each slug is also asserted to be in `knob_ceiling.parts()` with the class below
(`START` is keyed on it).

| Part | Band | Class | Fold (C′) | Other guitars to own |
|---|---|---|---|---|
| `cambridge-colour-me-red-elecgtr01` | Diesel13 | crunch | 1 | −2.95 dB |
| `cambridge-femme-elecgtr3` | Wall Of Death | crunch | 0 | −1.58 dB |
| `cambridge-get-out-of-bed-elecgtr1` | Magician's Nephew | crunch | 1 | +2.94 dB |
| `cambridge-just-don-t-talk-elecgtr3` | Timo And The Timezone | clean | 3 | +4.28 dB |
| `cambridge-magilla-elecgtr1dt` | Turbosauro | clean | 2 | −1.47 dB |

- **Folds:** `docs/song-settings-folds.json` assigns the fold (and so the re-EQ). **The leak
  assertion** comes from what each C′ actually trained on: the bands in the three caches'
  `meta.json` (`cache`, `cache-sw50r`, `cache-ac20`) outside that fold under `train.k3_folds()`,
  plus Guitar-TECHS P1. The part's band must not be among them.
- **All 5 are multi-guitar** (set 3's `multi_guitar_mix` flag). There is no single-guitar part,
  so the single/multi split can't be made. Instead, parts are split by `other_guitars_to_own_db`:
  **loud** (get-out-of-bed, just-don't-talk; above 0 dB) against **quiet** (the other 3; −1.5 to
  −3 dB). A descriptive single-guitar variant follows below.
- **S:** `knob_ceiling.START[class][amp]`.
- **T:** the control's target, built exactly as `song_settings.control_render` does:
  `K.perturbed(dims, S, {**K.PERTURB[amp], **K.PERTURB_ALL})` (amp volume, treble, bass or mid,
  input gain, left cab position), plus the mic change (`CONTROL_MIC`, +4 mod 10). That is six
  changes. The DI-recovery report's "five moved knobs" is the deviation, kept so the result stays
  comparable with the control and the ladder.

## The "recording" per cell

1. **The 30-s window** is the stored context's (`learn/set3/stems/_work/contexts.json`: 30 s, crop
   at 10.0 s in all 5).
2. **The backing context:** the instrumental context rebuilt from the session tracks as
   `_work/build_contexts.py` did, minus the part's `own_amp_tracks`.
   - Line-up checks: the rebuilt instrumental context equals the stored
     `contexts/<slug>/mix_instrumental.wav` (max |difference| < 1e-6); the backing's crop slice
     equals the crop's `backing_instrumental.wav` (`backing.wav` for magilla, which has no vocals),
     within 1e-6.
3. **The raw DI over the window:** the session's DI track (`record.json` `pairing.di`). Its crop
   slice must equal the crop's `di.wav` within 1e-6. It is scaled by the gain that `to_lufs` gives
   the crop's `di.wav` (−22.9 LUFS), so the crop is driven exactly as the control drove it.
4. **The render:** `knob_ceiling.Renderer` (`isolate=True`), one warm-up of S on the 30-s DI, then
   T. Mean over channels. The 0.25-s fade-in sits 9.75 s before the crop.
5. **The level:** one gain on the whole render, so its crop's integrated loudness (pyloudnorm, as
   `direc_check.to_lufs`) equals the part's `reference.wav`, the amp track at its mix level.
6. **The mix:** backing + scaled render, at the render's own timing (no shift for the amp track's
   re-amp lag; the stem then lines up with the fake, so every judge lag below is 0).
7. **Separated** by `htdemucs` and `mega53`; `blend` from the two. The crop's 10 s is cut out
   (480,000 frames).

**The clean fake** (`clean`) is the crop of the scaled render. **Lag check:** every stem's GCC lag
against the clean fake must be within ±3 samples, or that row stops for that cell and is
reported.

**The single-guitar variant (descriptive, zero renders).** The same fake mixed into the backing
minus `contexts.json`'s `other_guitar_tracks_in_mix` too: 10 more mixes, separated by `htdemucs`
and `mega53`, with `blend` from the two. Scored on m_sep only (its renders are shared). It tests
the 2026-10-08 finding directly: other guitars, not the network, are the bottleneck.

## The two margins

As the ladder defines them ([rank-margin-ladder-plan.md](rank-margin-ladder-plan.md), "The rank
margin"): m_w = log d_w(S) − log d_w(T), with `rank_margin.distance` (judge flat, bands
"recording", `render_latency` 52, the activity fallback) and `rank_margin.margin`. m > 0 means T
ranks above S.

- **m_sep (row r):** the reference is r's stem crop. S and T are rendered through the **measure
  DI** (`knob_ceiling.measure_di`, the 10-s crop). Mask: the measure DI. Lag 0. The renders are
  shared by all rows, so this isolates the separator.
- **m_both (row r):** the reference is r's stem crop. S and T are rendered through **C′'s rebuild
  of that stem**: the part's fold C′ (`song_settings.cprime`, DONE marker required), on the CPU,
  re-equalised by (fold 2's average − fold f's), then −22.9 LUFS, as `control_rebuild`. Mask: the
  rebuild (realistic, as a gate would use it). Lag 0. The rebuild's GCC lag against the raw DI
  must be within ±3 samples, or that row stops for that cell and is reported.
- **For `clean`:** m_sep is the ceiling (the true DI on the clean fake). Its m_both is the
  control's condition (C′ on a clean render), so m_both(htdemucs) against m_both(clean) shows what
  separation adds through C′.
- **Windows:** primary m_full (1.0–10 s). m_A (1.0–5.5 s) and m_B (5.5–10 s) are fragility
  readings. Each margin is also read with the other mask (fragility, zero renders).
- **Informative cells:** d_S − d_T ≥ 0.1 on the full window, through the measure DI, against the
  clean fake (amendment 2's floor). This means m_sep(clean) > 0, the ladder's base set. Only
  these are counted below; the rest are reported.
- **A refusal** (no distance after the fallback) leaves m undefined. It counts as "not > 0" and is
  listed.
- **Δm_sep** (row − `htdemucs`) per cell is reported beside every count, so near-misses show.

## Also reported (descriptive)

- **1–3 kHz coherence** (`residual_eval._coherence`, `nperseg` 4096), C′ rebuild against the
  part's raw DI:
  - **on the real song (the screen's coherence):** step 1's check-2 measure, with the part's fold
    C′. Each row separates the part's real 30-s instrumental context: `htdemucs` is re-run on the
    5 contexts (the stored set-3 stems are 10-s crops, with no 30-s stem to blend). Every new
    crop must match the stored `_work` stem within 1e-5 (max |difference|), or the run stops.
    `mega53` is new (5 contexts); `blend` is built from the two. Lag hint: `judge_lag` + 52, as
    check 2. Mean over the 5 parts, and per part: the 0.02 margin can be used up by
    just-don't-talk alone (0.24–0.29 across networks). Also given: the rebuild of the real amp
    track (`reference.wav`), as the no-separation anchor;
  - **on the 10 fake cells:** each row's stem rebuild, lag hint 0; and the `clean` rebuild. C′
    trained on Morgan renders, so this is optimistic.
- **The stem against the clean fake,** over the 10-s crop, per row and cell:
  - **crest error:** `rank_margin.crest_db`(stem) − crest_db(fake), in dB;
  - **envelope-variation error:** the standard deviation of the 10-ms log-RMS envelope (frames
    within 40 dB of the fake's loudest), stem minus fake, in dB. Negative means flattened;
  - **attack-slope error:** onsets are the fake's spectral-flux peaks (half-wave-rectified log
    magnitude, STFT 1024, hop 256; peaks above median + 3 × MAD, at least 50 ms apart). Per onset,
    the slope is the rise of the 1-ms RMS envelope from 5 ms before the onset to its peak within
    30 ms, as a fraction of that peak, over the rise time (level-free: a quieter noise floor in a
    stem can't steepen it, as a dB rise would). The error is the median over onsets of
    log2(slope_stem / slope_fake). Negative means blunted. Reimplemented here: Ding's MSS-eval
    licence is unchecked;
  - SI-SDR against the fake, and band errors at 63 Hz, 8 kHz and 12.7 kHz (the edge losses the
    blend targets).
- Every figure is split loud / quiet (see Cells), and per part.
- **A repeat check, zero renders:** on the 4 cells shared with the control (colour-me-red and
  just-don't-talk), the judge distance between this fake's crop and the stored
  `<cell>-fake.npy`. They differ only by the 30-s render's earlier amp state.

## Declared decisions

**The screen, per eligible row (`mega53`, `blend`).** A row advances to the merged report's
full switching test ([guitar-separation-2026-10.md](research/guitar-separation-2026-10.md), "A
two-hour re-test") only if all three hold:
1. m_sep > 0 on **more** informative cells than `htdemucs`;
2. **no flip:** no informative cell where `htdemucs` has m_sep > 0 and the row has m_sep ≤ 0;
3. its mean real-song coherence ≥ `htdemucs`'s − **0.02**.

- **Coherence alone never advances a row.** m_both doesn't gate. It is reported beside each
  verdict, with a note if an advancing row has m_both > 0 on fewer cells than `htdemucs`.
- **Ceiling:** if `htdemucs` has m_sep > 0 on every informative cell, no row can advance. That is
  the "separation isn't what breaks it" reading, not a failure of the rows.
- **Two eligible rows, no multiplicity correction:** it is a screen, and the switching test
  decides.

**The separation-vs-rebuild reading, on `htdemucs`** (n = informative cells):
- **Separation isn't what breaks the objective:** m_sep ≤ 0 on at most 1 cell. The separator
  question waits behind the rebuild.
- **Separation is a co-equal problem:** m_sep ≤ 0 on at least one-third of n (rounded up). The
  merged report's re-test is promoted, and any corrected rebuild must also be checked on these
  stem cells.
- **Partial:** in between. For n = 4–6 the two readings cover every case, so "partial" exists
  only for n ≥ 7. Reported per part, loud against quiet.
- **Undecided** (the reading and the screen) if n < 4. Undecided is not failed.

**Precedence: none.** The screen and the reading are reported independently. A row that
advances only earns the full switching test; the reading stands on its own. Both can hold at
once (for example, `htdemucs` inverts 1 cell and a row fixes it).

**Failure branches.**
- A line-up check failure stops that part (both amps).
- A stem's lag check against the fake, or a rebuild's against the raw DI, failing stops that row
  for that cell. If `htdemucs` fails on any informative cell, the screen and the reading are both
  undecided.
- If `mega53` stops for a cell, `blend` stops for it too. A non-zero relative lag stops `blend`.
- A failed repeat render (below) stops the run.

**Fragility:** a verdict is reported as fragile if it changes under m_A or m_B, under the other
mask, or when any one part is left out. With one part per band here, leaving out a part is
leaving out a band. On the remaining n′ cells: the absolute "≤ 1" stays; one-third becomes
ceil(n′/3); n′ < 4 is undecided; screen rules 1–2 are re-counted on n′; the coherence mean is
taken over the 4 remaining parts. The declared reading still stands.

**Power, stated plainly.** 10 cells from 5 parts, 5 bands and 5 DIs; PR12 and SW50R share a
performance. One cell is the whole difference between "more" and "not more".

**A dated deviation (2026-10-15)** from the ML plan's statistics rule ("band-weighted results
with intervals"): no band-clustered interval is given. With 5 bands none is meaningful, and the
DI-recovery report asks for a screen.

**Repeat development use.** All 5 parts were used before:
- the separator-upgrade test (2026-10-08; all 33 set-3 development parts);
- step 3's parts (knob ceiling, knob ceiling 2, label table, song-settings arm A);
- step 1's check 2 (cprime-folds), on exactly these 5;
- colour-me-red and just-don't-talk are 2 of the 6 control parts, read again by the rank-margin
  ladder; get-out-of-bed is the ladder's bleed source.

Declared as a repeat use. Nothing here is a preset choice or a held-out claim.

## Budget

| Part | Renders |
|---|---|
| Fakes: warm-up S + T on the 30-s DI, × 10 cells | 20 |
| Per cell: one warm-up, then S and T through 5 DIs (measure, C′ of `clean`, `htdemucs`, `mega53`, `blend`) | 110 |
| Per cell: S through the measure DI again | 10 |
| **Total** | **≈ 140 (hard stop at 170)** |

**The repeat render:** the second S's d (full window, measure-DI mask, lag 0, against the clean
fake) must be within |log ratio| ≤ 0.005 of the first's.

**The running total:** about 139k of 200k after the rank-margin ladder; this adds ≈ 0.14k.

**CPU, with the renderer idle** (separation runs only when no Morgan render process is running;
it never uses MPS):
- Mega-53, run alone: 25 contexts (10 fakes, 10 single-guitar, 5 real) at about 102 s wall each,
  plus the full-model identity check (about 191 s): about 45 min;
- htdemucs_6s: 25 contexts at about 15 s each: about 6 min;
- C′ rebuilds: 40 fake-cell and 20 real-song rebuilds of 10 s: minutes;
- renders: minutes.

**Disk:** 72 GB free at review. The msst-venv (about 1–2 GB) and small outputs; free space must
stay ≥ 31 GB.

## Stated limits

- **A weak screen.** The margin's sign agrees with search success on 14 of 18 searches (5 of 9
  within C′). The result is descriptive evidence about separation.
- **5 parts can't give band intervals.** It can forward a row to the switching test, never switch
  the separator.
- **No single-guitar part.** All 5 are multi-guitar, where the 2026-10-08 test found Mega-53's
  gain smallest (+0.3 to +0.4 dB). The single-guitar variant is synthetic (other guitars
  removed), and descriptive.
- **The fake is a clean render** of a known preset, mixed into a real backing at the amp track's
  level. Real amp tracks add mic, room and player dynamics, which no row sees.
- **The contexts are instrumental** (vocals removed by the session), which is optimistic for the
  product's full mixes.
- **The 5-part coherence mean is dominated by just-don't-talk** (about 0.29 against 0.04–0.16).
- **C′ is the only rebuild,** and its error is fine structure (the ladder). m_both says how this
  rebuild reads each stem, not how a corrected one would.
- **T is the control's target, six settings changed,** not a natural preset. The mic change
  widens d_S − d_T, so inversions are a little harder to reach.
- **The Mega-53 wrapper can't be checked against 2026-10-08,** only against the full model.

## Ledger entry (entered before any result)

```json
{
  "test_id": "separator-screen",
  "plan": "docs/separator-screen-plan.md",
  "entered": "2026-10-15, before any compute",
  "repeat_use": "repeat development use of set 3's 5 clean and crunch check parts (before: separator-upgrade 2026-10-08, step 3's parts, cprime-folds check 2, and for colour-me-red and just-don't-talk the song-settings control and the rank-margin ladder; get-out-of-bed was the ladder's bleed source)",
  "parts": [
    "cambridge-colour-me-red-elecgtr01",
    "cambridge-femme-elecgtr3",
    "cambridge-get-out-of-bed-elecgtr1",
    "cambridge-just-don-t-talk-elecgtr3",
    "cambridge-magilla-elecgtr1dt"
  ],
  "bands": "Diesel13, Magician's Nephew, Timo And The Timezone, Turbosauro, Wall Of Death (set 3, all multi-guitar)",
  "weights": "Mega-53 v1 (ZFTurbo/Music-Source-Separation-Training v1.0.21, commit ea7eb9c, ckpt sha256 c62820893bbf86d4e734f966bd142d9157cfc8bb8e79e9d8f9ea553f3ff3519f), user-approved 2026-10-15",
  "gate": "Descriptive screen, not a gate (the margin agrees with search success on 14 of 18 only). Cells: 5 parts x PR12, SW50R; informative = d_S - d_T >= 0.1 (full window, measure DI, clean fake). Primary m_full. A row (mega53, blend) earns the merged report's full switching test only if m_sep > 0 on more informative cells than htdemucs_6s, AND no informative cell flips from m_sep > 0 (htdemucs_6s) to m_sep <= 0, AND its mean real-song 1-3 kHz coherence (check-2 measure, the part's fold C') >= htdemucs_6s's - 0.02. Coherence alone never advances a row; m_both is reported, not gating. Reading on htdemucs_6s, independent of the screen: m_sep <= 0 on <= 1 informative cell -> separation isn't what breaks the objective; on >= ceil(n/3) -> co-equal problem, re-test promoted; else partial. n < 4 informative, or an htdemucs_6s lag-check failure on an informative cell -> undecided. Fragility (m_A, m_B, other mask, leave-one-part-out with n' rescaling) reported beside each verdict.",
  "outcome": null
}
```

## Code to be written

**`learn/separator_screen.py`:**
- `PARTS` (asserted equal to `cprime_folds.check`'s 5, and in `knob_ceiling.parts()` with the
  declared class), `cells()`, `fold(slug)`, `trained_bands(fold)` and the leak assertion;
- `window(slug)`, `backing_context(slug, solo=False)`, `raw_di(slug)`: the 30-s pieces with the
  line-up checks;
- `fake_gain(render_crop, reference)`, `mix(backing, fake)`;
- `MsstSeparator` (msst-venv): hash and commit checks against provenance.json, yaml load, head
  pruning, `demix` on the CPU with 4 threads, the 44.1-kHz round trip, `info()` with `pip freeze`
  and peak RSS;
- `htdemucs()`: `learn.separate.GuitarSeparator` with `DEVICE=cpu`, then 4 threads;
- `blend(mega, hd)` and `blend_lag(mega, hd)`, exactly as declared;
- `stem_metrics(stem, fake)`: crest, envelope-variation and attack-slope errors, SI-SDR, edge
  bands;
- `rebuild(slug, x)` (torch venv): the fold's C′, re-EQ, LUFS, lag check;
- `screen(...)`, `reading(...)` and `fragility(...)`: the declared rules;
- steps (`python -m learn.separator_screen <step>`): `contexts`, `fakes` (renders), `separate
  --row htdemucs|mega53` (each in its own venv; refuses if a render process is running),
  `identity` (the pruned-against-full check), `blend`, `rebuild`, `render` (a counter that stops
  at 170), `report`;
- outputs under `~/ndsp-presets/learn/separator-screen/`: 10-s crops and 30-s stems as float32
  `.npy`, a manifest with sha256s, per-cell distances as JSON. Nothing large in git.

**`tests/test_separator_screen.py`:**
- the blend returns its input when both stems are equal (≤ 1e-9); its two branches sum to the
  identity, are −6.02 dB each at 6 kHz, and have GCC lag 0; a shifted stem is caught by the
  relative-lag check;
- head pruning matches the full model on a tiny random-weight BS-RoFormer (seconds, CPU); skipped
  if the MSST imports aren't available in `.venv`;
- the hash check refuses a changed file;
- the 147/160 round trip keeps the length;
- the fake gain lands the crop at the reference's loudness within 0.05 LU;
- the metrics: zero for identical signals; envelope variation negative after compression; attack
  slope negative after the ladder's 10-ms envelope smear;
- `screen` on fixtures: advance; blocked by one flip; blocked by coherence; the ceiling case;
  coherence alone never advances; n < 4 undecided; an `htdemucs` lag failure undecided;
- `reading` at its thresholds (≤ 1, one-third rounded up, partial only for n ≥ 7);
- leave-one-part-out rescaling;
- the leak assertion refuses a band that trained the network;
- the render counter stops at its cap.

## Order

1. This plan, the review (done), the ledger entry, then commit. No number before that.
2. The code and tests; the tests pass. The msst-venv; the head-pruning identity check.
3. **Message the product session** (ML plan section 5): the renderer and the CPU are shared,
   and say when the renders and separation will run.
4. Build the 10 backing contexts (and the 10 single-guitar ones) and the 30-s DIs; the line-up
   checks.
5. Render the 10 fakes (renderer, `isolate=True`, `setopt no_bg_nice`).
6. With the renderer idle: separate (`htdemucs` on the 25 contexts with the repeat check against
   the stored stems, then `mega53` alone), the blends, the lag checks.
7. Rebuild (torch venv, CPU), and the coherence figures.
8. Render S and T through the 5 DIs per cell, with the repeat render.
9. The screen, the reading, fragility, per part, then an independent audit,
   `docs/separator-screen-results.md`, the ledger outcome, and the roadmap.

## Implementation notes (2026-10-15, before any compute)

- **Attack slope:** defined on the linear 1-ms envelope as a fraction of the peak, not as a dB
  rise. On a test signal, a dB rise grew after smearing, because the smear lowered the noise
  floor before each onset.
- **30-s stems** are kept as float32 `.npy` (not FLAC), so the blend is built from full-precision
  arrays.
- **m_sep's "other mask"** is the reference itself (the judge's activity fallback mask), since m_sep's
  own mask is already the measure DI.
- **The tiny-model pruning test** is skipped where the MSST imports are missing (the main `.venv`
  and demucs-venv). It runs in the msst-venv, before the identity check.
- **The DI gain** is `di_gain`, the gain `direc_check.to_lufs` applies to the crop's `di.wav`
  (tested equal).

## Environment notes (2026-10-15, before any compute)

- **beartype:** the repo's pin, 0.14.1, fails on Python 3.14, so msst-venv uses 0.23.1.
- **lzma:** this pyenv Python has no `_lzma`, and librosa's `pooch` imports `lzma` on import.
  `separator_screen` installs an inert `lzma` stand-in, which nothing here uses to decompress.
- **The pruning test** (a tiny BS-RoFormer, pruned against the full model) passes in
  msst-venv.
