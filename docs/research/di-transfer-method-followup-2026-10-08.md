# DI-transfer methods: follow-up after timing verification

2026-10-08. Source review and hypotheses only; no new experiment, data access,
model selection or training authorization. The timing result is independently
verified; score-coordinate sensitivity is independently reviewed and declared,
awaiting committed execution.
Current execution state remains in the roadmap/monitor.

## Relevant published choices

EG-VAE separates played content from tone, reconstructs dry audio by masking the
tone path, and adds variational tone sampling plus gain/EQ/distortion augmentation
in a second stage. Its audio objective uses multi-scale mel, adversarial and
feature-matching losses. Training includes Cory Wong X and EGDB-PG processing;
Morgan presets are an unseen-plugin evaluation. Thus its reported unseen-tone
results concern generated plugin audio, not demonstrated transfer to arbitrary
microphone recordings or songs. This supports investigating processing diversity
and disentanglement, without claiming those choices solve our native-data gap.
[EG-VAE, §§III-E–IV-A](https://arxiv.org/html/2608.05513).

Okita and Katayose combine dry-signal prediction with reconstruction-based search.
Their evaluation favors dividing prediction and search rather than relying only
on direct prediction; the test inputs are effect-chain-processed guitar excerpts.
That supports our broad recovery-plus-search structure, but does not establish
Morgan preset accuracy on real songs or justify expanding search after our failed
reserved confirmation.
[Audio Effect Estimation with DNN-Based Prediction and Search Algorithm](https://arxiv.org/html/2604.22276).

## Bounded questions worth reviewing next

These are our hypotheses, not findings of either paper:

1. **Timing relevance:** the independently verified constructed-pair timing
   errors should be related to recovery and selection error before treating a
   sample-level timing failure as an ML bottleneck. A few samples might matter
   differently to waveform and spectral objectives. Do not relax the stopped
   study's tolerance or use its panel to choose a new one.
2. **Processing sensitivity:** a frozen-model control with exactly known input
   transformations could distinguish sensitivity to delay, nonlinear processing
   and frequency-dependent phase. Use declared transformations, known targets and
   simple competitors before considering augmentation training. This would remain
   a synthetic development test, not a substitute for native transfer validation.
3. **Native evidence:** any later native-transfer test needs a separately reviewed
   way to establish usable pairing on different development material. Reusing the
   failed panel with adjusted rules would not supply independent evidence.

A larger VAE, more Morgan-only training, or new pretrained weights is not selected
by this source review. Open-source restrictions remain; no unreleased or unlicensed
checkpoint is used. Any proposed run still needs its own declared procedure,
cheap controls and fresh independent review before computation.

## Additional code-based hypothesis

The frozen [network](../../learn/direc.py) has five encoder layers with stride four
and corresponding transposed-convolution decoding. Its preprocessing also keeps
the fixed 52-sample render latency. This motivates a possible **input-coordinate
control**: a known shift applied before inference may behave differently from
the same shift applied to an already saved prediction. Strided layers do not by
themselves establish exact sample-shift equivalence. No actual shift response has
been measured here. The current scoring-coordinate study cannot answer this
question, and this source observation does not select a new run or justify
altering the latency, training recipe or stopped native-pairing rules.
