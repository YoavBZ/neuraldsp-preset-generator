# Mega-53 as default, the stereo check and mix vs raw track: plan

Declared 2026-10-19, before any measurement. Development only, zero renders (stage F's 21 parts,
13 bands; ledger entry `stereo-and-mix-check`). Descriptive: effect sizes with 90% band-bootstrap
intervals, no pass or fail. Code: `learn/stereo_mix_check.py`.

## Why

The user's listening of the separation samples (`~/ndsp-presets/listening/separation-samples-1/`)
heard Mega-53 as much better than htdemucs overall and on four of the parts, with leaked other
guitars in both separations on Signs ElecGtr3 and get-out-of-bed elecgtr2, and a distortion in
magilla's raw amp track that neither separation, nor the mix, lets them hear.

## Task 1: Mega-53 as the ML default (code; no reruns)

`learn/separate.py` gets `DEFAULT_SEPARATOR = "mega53"` and `guitar_separator(name)`. Arm A
(`learn/arm_a_mega53.py`: `separate`/`rebuild` without `--sep`) and the
direct model (`learn/direct_existing.py`: `--sep`, default Mega-53; the stored htdemucs run stays
in place and `--sep htdemucs` reproduces it, others write to `sep-<name>/`) use it. The finished
known-answer pilot B1 is pinned to htdemucs, its declared separator. The product (`scripts/`,
`skills/`) is only read: it runs no separator (below). Caveat: D_existing was trained on htdemucs
stems, so a Mega-53 run of it feeds a stem unlike its training (not a reading on the separator);
`render` refuses predictions made with another separator.

## What the data allows (inventory, already run, zero cost)

- Stage F's stored 30-s contexts and both stems are **mono**, so no stored L/R exists.
- Every context is a **unity sum of raw tracks** (`learn/separate.context`), and **none of the 21
  sessions ships a mix, master or bounce** (every folder holds the tracks and a Readme only).
- The 21 target amp tracks are **mono**, so a native-channel stereo sum puts the target dead
  centre: L = R for the target, mid = the current mono, side holds no target. Only the stereo
  tracks (overheads, rooms, keys; on get-out-of-bed three other electric guitars, on Today's The Day
  one) differ between L and R.

## Task 2: the stereo check

Two stereo versions of each part's 30-s context, both built from the session tracks exactly as
`separate.context` builds the mono one, but keeping channels:

- **As recorded (R):** stereo tracks native, mono tracks centred at gain 1 per side. Check: its
  (L+R)/2 equals the stored mono context within 1e-6.
- **Panned (P), a model of a typical mix:** the target at pan −0.6 (left), the session's other
  guitar tracks (name contains "gtr" or "guitar", mono) alternately at +0.6 and −0.6 in file order
  starting opposite the target, everything else as in R. Pan law gL = √2·cos θ, gR = √2·sin θ,
  θ = (p+1)·π/4 (centre = 1 per side). One declared scenario; not a measured property of songs.

Separators: Mega-53 (msst-venv, 4 threads, `MsstSeparator`'s model and resampling, stereo input
in, stereo stem out) and htdemucs (`GuitarSeparator`'s settings, stereo in and out), CPU, nice 19.
The stored paths are mono-only (they duplicate the input and average the output), so a small
stereo wrapper (`StereoSep`) calls the same model; check: a dual-mono input through it, averaged,
reproduces the stored stem within 1e-4. R mostly tests how the model reacts to the stereo tracks
(the target is centred, so the oracle is mid and side holds only leakage). The panning rule's
tracks are listed per part in `contexts/log.json` before separating (multi-mic tracks of one
guitar can land on opposite sides; a known simplification).
Runs per part: R stereo, P stereo, P mono (R mono is the stored stem; recomputed SNR must match
the stored log within 0.01 dB). About 21 × 3 × 90 s ≈ 1.6 CPU hours for Mega-53, a few minutes
for htdemucs.

Channel modes, on the 10-s crop of the stem (gain-fitted SNR against `reference.wav`,
`local_objective_1c.snr_db`): **mono** (separate the mono fold, current), **left**, **right**,
**mid** (L+R)/2, **side** (L−R)/2 of the stereo stem; **pan-matched (ORACLE)**: the target's known channel gains
(1, 1 in R; the pan law's gains in P), stem gL·L + gR·R (the LS gain ⟨ref, mix_c⟩/⟨ref, ref⟩ is
logged only as a diagnostic, since correlated backing biases it);
**blind**: weights from the stereo stem's own channel RMS, rmsL·L + rmsR·R (what the product
could do). Each scenario's gains are against its own mono (P stereo against P mono).
Reported: per mode, the band-weighted mean SNR gain over mono with its 90% band
bootstrap (4,000 draws, seed 20261019), per part, the input mix's own SNR per mode, and flags on
Signs ElecGtr3 and get-out-of-bed elecgtr2 (the user's "other guitar leaked" parts). Separating
L and R as two dual-mono inputs is not run: the stereo models see both channels at once, which
is the cheaper and the product-like input.

## Task 3: mix vs raw track

The best estimate of "the guitar as it sounds in the mix" is the raw track through the session's
mix processing; there is none (no session has a mix bus or master), and our mix sums the raw
track at unity, so in our data the in-mix guitar **is** the raw track by construction (checked:
mix − backing equals reference within 1e-5 per part). This holds for our contexts only and says
nothing about mastered songs. What differs is what can be recovered from the mix.
Per part, against the raw track: the least-squares FIR (2,048 taps) of the mix onto the raw track
(the best linear recovery, an oracle; fitted on one half of the crop and applied to the other, both
ways), the Mega-53 stem and the htdemucs stem (stored mono).
Measures: long-term spectrum distance (LSD, dB RMS over 1/3-octave bands 80 Hz–12 kHz after one
broadband gain), crest (median over active 100-ms frames of peak/RMS, dB, difference) and
brightness (energy 3–10 kHz over 0.2–3 kHz, dB, difference; distortion fizz lives there, but so
does separator high-frequency loss, which it cannot tell apart). "How often": the share of
parts above 3 dB LSD and above 1 dB of crest or brightness loss, band-weighted means with
intervals; magilla reported on its own.

## Review and audit

One independent review of this plan before measuring (go with changes, all applied above: the
stereo wrapper and its check, each scenario against its own mono, the oracle from known gains,
the panned tracks listed, the FIR held out, brightness renamed, the D_existing caveat); one brief audit of the results that
recomputes the key numbers from the saved per-part table.
