# Estimating every control from the song: research plan, round 2

*Produced on 2026-10-03 by a research workflow, building on round 1 (`docs/research/round-1-song-only-matching.md`). The question: can every control of a Morgan or Tone King preset — amp or channel, mics, pedals and effects, every knob — be estimated from the song alone, deterministically and fast?*

*Structure:*
- *four parallel tracks:*
  - *which controls are recoverable;*
  - *features per control family;*
  - *one model for every control;*
  - *a hybrid of proposal and checking renders;*
- *one adversarial critic per track, who opened every cited source and checked feasibility and the measured failures;*
- *a synthesis.*

*Nothing here has been run yet. Each approach carries the experiment and gate that would decide it.*

> **Status, 2026-10-05.** Not run, apart from the silent-render guard. Round 3 ([round-3-supervised-preset-model.md](round-3-supervised-preset-model.md)) and the parked [supervised-model-plan.md](../supervised-model-plan.md) took its question further.

## 1. Executive summary

Every control can get a value from the song alone, but not every control can be measured from it. For some controls the honest answer is "set by a stated rule" or "the usual value in the factory presets", and the tool should say which.

**Likely measurable:**
- the overall tone curve: the graphic EQ, the amp's tone controls at low gain, and the cab and mic, measured together as one curve;
- delay time and feedback;
- tremolo rate and depth.

**Partly measurable:**
- a coarse drive class (clean, edge of breakup, crunch, high gain);
- amp choice and Tone King channel;
- drive pedal on/off;
- a broad mic family;
- reverb amount on isolated tracks.

**Not measurable:**
- how much of the distortion came from the guitarist's picking and pickups rather than the amp (only the sum shows);
- output level, pans, phase and stereo controls;
- the gate threshold;
- a compressor in a mastered song;
- the song's own reverb as opposed to the preset's;
- probably most voicing switches (bright, input mode, high-cut, attenuation steps), because other controls can imitate them.

**Round 1's three obstacles are different kinds of problem:**
- **Playing confound.** Partly a feature problem, worth attacking by measuring inside notes, in gaps and after stops.
- **Many settings, one sound.** A property of the plugin, not of the features. It is solved by estimating groups of equivalent settings rather than individual knobs.
- **Plugin renders against real recordings.** This gap can be detected but only partly closed.

**Most promising approach for the whole plugin.** A deterministic estimator rather than a trained network:
- simple estimators per control family (a closed-form solver for EQ and cab, signal-processing detectors for time effects, drive measured inside each note);
- a fixed-rule solver that turns their outputs into every knob;
- 5–40 checking renders through real guitar DI clips from a library, instead of 300 blind ones. A match would take about 1–2 minutes.

**Fallback.** One learned model over the whole preset, if the hand-made drive measurements fail. Its limit is how few distinct guitarists exist to train on, not the network.

**First step.** None of this should be built before a recoverability screen: about 3–4 days of code and about 7–8 hours of plugin time on an idle machine, measuring per control what the song can and cannot tell us.

**Tone King's flakiness is mostly ours to fix (section 7).**
- The late silences line up with macOS killing the iLok licence daemon, which our habit of starting a new plugin process per render wears out.
- The "5 dB noise" figure is taken in a near-empty 25 Hz band. In the audible range the plugin repeats very well.

## 2. Recoverability: what to expect per control family

The verdicts below are expectations, to be confirmed or overturned by the screen in section 4. Its steps are:
- **S0:** noise and render-history floor;
- **S1:** sensitivity of each control, with playing level treated as an unknown;
- **S2:** the linear chain (EQ, cab, mic);
- **S3:** "can another control imitate it" tests;
- **S4:** a probe given the true DI's loudness.

The writable controls are:
- **Morgan:** amp selector, about 88 continuous controls, 32 switches, and 7 other selectors (2 cab mic types, 2 room-mic slots, delay sync mode and 2 sync notes).
- **Tone King:** channel, 61 continuous controls, 21 switches, 12 selectors.

Expect roughly 10–15 independent quantities per amp or channel to be measurable. The rest of the roughly 90 controls end up as a rule or a prior.

### Likely recoverable

**Overall tone curve**
- Controls: graphic EQ bands, high- and low-pass filters, and the amp tone controls while their effect is still EQ-like (SW50R Treble/Bass, AC20 Cut, PR12 Treble/Bass at low gain; Tone King EQ).
- Why: the inversion already fits it. M7-2 found EQ bands 2–8 and the low-pass predictable (R² ≥ 0.70) even from one source signal.
- Limit: the guitar and pickups sit in the same curve. How the curve is split between tone knobs, EQ and mic is a rule, not a measurement.
- Measured by:
  - S1: each band's effect against the spread between players;
  - S2 and a zero-render check: how much 43 development DIs still differ from each other after the same EQ fit.

**Delay** (Morgan delay; Tone King delay)
- Controls: on/off, time (or sync note via the song's tempo), feedback and mix. Cuts only partly.
- Why: repeats show in the gaps, and the maps from measurement to setting are closed-form (`match/invert.py` has Morgan's; Tone King's still needs mapping).
- Limits: riffs that repeat at the tempo, and parts with no gaps.
- Measured by: injecting the plugin's delay into real amp tracks (Phase 2, F1).

**Tremolo** (Morgan rack tremolo; Tone King amp tremolo)
- Controls: rate and depth, measured inside sustained notes.
- Limit: a tremolo synced to the strumming cannot be told from the playing, so the detector abstains there.
- Measured by: F1.

### Partly recoverable

**Drive, as one "effective drive" number**
- Controls: Morgan input gain, amp Volume (and AC20 Power), drive pedal gain; Tone King channel volume, attenuation, overdrive pedals.
- What survives: a coarse class probably. The split between guitar output and amp gain does not.
- Evidence:
  - PR12's 5% distortion point moves from about 66% to about 28% of the knob when the input is tripled (`packs/morgan/tone.md`).
  - Whole-excerpt features pick the right one of 7 drive steps 22–27% of the time across performances (chance 14.3%). The single-note harmonic row is at chance (14.9% SW50R, 13.5% Tone King; `docs/data/matching/harmonic-study-*.json`).
- Measured by:
  - S1: whether Volume and input gain move in step with playing level (correlation of 0.9 or more means only the joint number is recoverable);
  - S4;
  - the Phase 2 drive screen (F2).

**Amp choice and Tone King channel**
- Why only partly: the differences are real but subtle. Herbst found five real valve amps differed little in roughness, flux or tonalness.
- Measured by: S3, in the song-like arm where target and candidates go through different DIs.

**Drive pedal on/off and pedal tone**
- What survives: on/off may, because a pedal's mid boost before the clipping is not the same as more amp volume. Pedal Level does not, because loudness normalisation removes it.
- Measured by: S3.

**Cab mic type, and Tone King's speaker (E33/H30)**
- Expected: at best a 2–3-way family (dynamic, condenser, ribbon).
- Position and distance probably fold into the EQ: Morgan's full position range is a gentle tilt (about +1.4 dB in the low mids, −1.1 dB at 6.3 kHz, per the manifest).
- Measured by: S2, where mic type survives only if its residual after EQ exceeds the DI-to-DI residual.

**Reverb**
- Controls: Morgan rack reverb, Tone King reverb, and the amp springs (PR12 Reverb/Dwell, SW50R Reverb, Tone King ampReverb).
- Expected: amount on isolated tracks, perhaps spring against rack, and little inside a mix.
- Why: the earlier reverb estimate called reverb on/off at chance on played material (4 against 5 of 12). A song's own reverb is indistinguishable from the preset's, so let the preset carry the ambience the listener hears.
- Measured by: F1 for the rack and Tone King reverbs, and a separate spring test.

**Chorus (Tone King)**
- Expected: low to medium, and subtle in mono stems.
- Measured by: F1.

### Not recoverable: set by rule or prior, and labelled

**Voicing switches**
- Controls: SW50R Bright, Treble Boost and Input mode; AC20 Bright and Bass/Treble; Tone King high-cut (HFC), rhythmAttBypass and the attenuation steps; compressor speed and release.
- Expected to be imitated by EQ and gain. S3 confirms or overturns this switch by switch.

**Compressor in a mastered song**
- Bus compression and the limiter dominate. Listeners are insensitive even to heavy compression (Hjortkjær & Walther-Hansen).
- On an isolated stem it may be detectable.

**Gate threshold**
- It depends on the user's own guitar noise, so set it by rule.
- Stop the no-DI search moving it: section 7 explains why.

**Mix and production controls**
- Output level, pans, phase, stereo width, ping-pong, doubler spread and transpose are mastering or mix decisions.
- Level comes from today's trim; the rest stay at the template.

**Morgan room mic type**
- It has no control in the plugin's UI (a reserved slot, per the manifest), so leave it at the template.
- Custom IR slots are excluded.

**Wah (Tone King)**
- It is on in only 6 of 130 factory presets.
- A parked wah would show as a resonance in the tone curve; auto-wah cannot be measured. The prior is off.

## 3. Ranked approaches

They are ranked by expected payoff for the effort, given the evidence. Approaches 1–5 together are the deterministic estimator; 6 is the fallback.

### 1. Time-effect estimators from the song, with no renders

**What it is.** Upgrade the numpy detectors in `analysis/features.py`:
- **Delay:** from the repeats heard in gaps. Time; feedback from the ratio of successive repeats; mix from the first repeat against the direct sound; high cut from the repeats' tilt. Sync note from the song's tempo.
- **Tremolo:** amplitude wobble inside sustained notes after removing each note's natural decay, plus a phase-continuity test. A free-running tremolo keeps its phase across notes; playing restarts at every pick.
- **Chorus:** periodic pitch wobble of strong partials.
- **Reverb:** from the fastest free decays after notes stop (an order statistic, Ratnam et al.), replacing the median of note decays, which measured sustain. Spring against rack from the spring's chirpy echoes.

Each detector abstains when the playing leaves no room, and the template value stands. Tone King's delay and reverb need their maps measured: about 100 renders.

**Controls covered:**
- Morgan: tremolo, delay and rack reverb (on/off, rate, depth, sync, time, feedback, mix, cuts, decay, pre-delay); doubler on/off.
- Tone King: amp tremolo, chorus, delay, reverb.

**Benefit and confidence.**
- Medium for delay and tremolo on isolated tracks, lower on stems. Reverb and chorus probably stay at the template for songs.
- These are switches today's search cannot change, so wins are visible, but their share of a rock tone is modest.
- Side benefit: once time effects are set without renders, the amp and cab can be scored with the rack reverb and tremolo off, in a reused plugin process. A reused instance with the rack reverb on does not repeat itself (0.27–0.57 apart after other settings; fresh processes are bit-identical). So this removes most fresh-process renders, and with them most of the licence-daemon churn in section 7.

**Cost.**
- About 2–3 days of code.
- About 1 hour of renders for the test (partly fresh processes).
- Under 2 s per match, no renders, no new dependencies.

**Key references:**
- Jürgens, Hinrichs, Ostermann, DAFx 2020: tremolo rate and depth from the envelope spectrum (errors 0.06/0.08); low rates confused with string decay; delay wet level the weakest (0.16). https://www.dafx.de/paper-archive/2020/proceedings/papers/DAFx2020_paper_2.pdf
- Hinrichs et al. 2022: time-effect parameters around 0.05 error in simulated band mixes; errors 2–3× higher as the backing gets louder. https://www.tnt.uni-hannover.de/papers/data/1571/EURASIP_2022.pdf
- Guo & McFee, DAFx 2023: modulation, delay and reverb classes carried over to an unseen dataset; drive classes did not. https://dafx.de/paper-archive/2023/DAFx23_paper_30.pdf
- Ratnam et al. 2003: blind decay estimation, biased upward when notes fade gradually rather than stop, so use muted stops and gaps. https://www.ee.columbia.edu/~dpwe/papers/Ratnam03-reverb.pdf

### 2. Closed-form solver for the linear chain: EQ, cab, mic, speaker, level

**What it is.**
- With the amp section switched off, measure once per plugin version the response of every internal mic: Morgan's 10, and Tone King's 16 (8 mics × E33/H30 speakers). Use a few positions and distances, and check linearity at two levels.
- For every pair of mic setups, fit the graphic EQ to their difference (`invert.fit_graphic_eq` with the measured basis).
- If the EQ absorbs the difference, mic choice becomes a rule (template or factory pair) and the EQ carries the tone.
- If not, at match time pick the mic family by the residual left after the EQ fit, and confirm with one render. Two-mic blends are computed from the measured responses.

**Controls covered:**
- Morgan: cab on/off, mic type, position, distance, mic level, phase, room level, EQ bands, high- and low-pass filters, output.
- Tone King: cab 1/2 mic IR (mic and speaker), position, distance, level, phase, room IR level, EQ.

**Benefit and confidence.**
- High that the measurement is clean. Low that mic type can be told from a song, because players' guitars differ in spectrum by several dB.
- Most likely result: mic folds into the EQ and is set by rule. That still gives about 20 cab controls a stated, deterministic value. A 2–3-way family is possible.

**Cost.**
- 1.5–2 days of code.
- About 300 Morgan and 480 Tone King renders (minutes).
- Milliseconds plus one render per match.

**Key references:**
- Fractal Audio, Axe-Fx III Tone Match manual: the commercial "match a recording" feature fits only a linear response, from isolated recordings, with amp and drive set by hand. https://www.fractalaudio.com/downloads/manuals/axe-fx-3/Axe-Fx-III-Tone-Match-Manual.pdf
- Peladeau & Peeters 2023: judge estimates by their sound, not their parameter accuracy. https://arxiv.org/abs/2310.11781
- Hayes, Saitis, Fazekas 2025: with many-to-one settings, treat equivalent solutions as alternatives rather than averaging them. https://arxiv.org/abs/2506.07199

### 3. Drive and dynamics measured inside each note

**What it is.** Replace whole-excerpt statistics with relations measured inside each note's decay, where the note is its own reference:
- **Brightness against level.** How brightness (a pitch-free high-band ratio) changes as the note gets quieter. A saturating amp holds brightness, then drops through a knee.
- **Decay curvature.** A compressor flattens the start of the decay.
- **Off-harmonic energy on chords.** Intermodulation from distortion.
- **Attack shape.**
- **Hiss in rests relative to the notes.** It rises with preamp gain.

One song plays the same preset at many intensities, so these slopes trace the amp's transfer curve, partly independent of how hard the guitarist played. They would be calibrated per amp with played-DI renders into an "effective drive" class at a typical DI level (the −22.9 LUFS development median). The amp or channel would be picked by whose curve fits.

**Controls covered:**
- effective drive (input gain, amp Volume/Power, pedal on/off and gain; Tone King channel volume, attenuation, overdrive pedals);
- compressor on/off where audible;
- amp and channel, together with approach 4.

**Benefit and confidence.**
- The most valuable family, since drive is the most audible difference, and the least certain: about a 1-in-4 chance of clearing its gate at real playing levels.
- The committed harmonic row was already a within-note measurement and was at chance. What is new is tracking brightness against level, which is untested anywhere at unknown input level.

**Cost.**
- 2–3 days of code, extending `scripts/study_harmonic.py`.
- About 15–20 minutes of renders.
- Calibration tables only after the gate passes: minutes on reused Morgan, about 40 minutes for AC20 in fresh processes, Tone King reused.
- 1–2 s per match.

**Key references:**
- Jürgens et al. 2020: distortion gain to 0.05 error from feature slopes over one decaying note. It was peak-normalised at a fixed input level, so it does not test our confound. URL above.
- Guo & McFee 2023: drive classes collapsed on a dataset with a different loudness distribution, which is the playing-level confound. URL above.
- Comunità, Stowell, Reiss 2021: gain estimates biased toward training values; a pedal's Level not estimable after normalisation. https://arxiv.org/html/2012.03216v1
- Herbst 2017: the distortion setting strongly changes chord roughness, flux and tonalness; five amps differed little. https://eprints.hud.ac.uk/id/eprint/33379/1/Herbst%20Influence%20of%20distortion%20on%20guitar%20chord%20structures.pdf

### 4. Choosing the topology with few renders: factory-preset retrieval and imitation tests

**What it is.**
- Render the 108 Morgan and 130 Tone King factory presets once each (gate and time effects off) through a fixed bank of library DI clips, and store their fingerprints.
- At match time, rank them against the song after removing what EQ and level can fix. This is done analytically from the stored spectra, with no renders.
- Invert the top few, then decide among the 2–4 surviving discrete choices (amp or channel, pedal on/off) by the median distance through 3–4 library DIs, not one.
- The generate skill's text research about the song's real rig, and approach 3's drive class, act as priors.

**Controls covered:** amp or channel, voicing switches, pedal and compressor on/off, and the mic pair (factory pairs), always as a coherent whole topology.

**Benefit and confidence.**
- Low to medium. It is capped by how much a better topology can ever gain, which has never been measured, and choices made across performances have been weak (22–27% right picks across performances, level left out).
- Most likely value: speed, and a shortlist with genuinely different voices.

**Cost.**
- About 1.5 days of code.
- Library: about 1 minute on reused Morgan plus a few minutes of AC20 fresh.
- The headroom test is about 1 hour.
- At match time, zero renders to rank and 10–20 to check.

**Key references:**
- Raue et al. 2009: testing whether a fitted quantity can be imitated by re-fitting the others detects both structural and data-limited non-identifiability. https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:19505944%20AND%20SRC:MED&resultType=core&format=json
- Wieland et al. 2021: the Fisher-information shortcut "has severe shortcomings" for practical identifiability; use the profile likelihood. https://arxiv.org/abs/2102.05100
- Yu et al. 2025: a preset-derived prior cut parameter error by up to 33%, without a significant listening difference, so use the prior for tie-breaking only. https://arxiv.org/html/2505.11315v1

### 5. The assembly: estimate groups, solve every knob by rule, check with a few renders

**What it is.** Approaches 1–4 output about 10–15 quantities per amp or channel:
- the combined tone curve;
- mic family, or "undetermined";
- effective drive and voicing;
- tremolo, delay, reverb and chorus;
- level.

A deterministic solver maps these quantities to every knob through measured tables: `eq_basis.json`, drive curves re-measured with played DIs, the reverb decay map, and the mic basis.

Fixed rules settle the splits:
- drive from the amp's volume before a pedal on non-master-volume amps;
- tone knobs at the template, with the remainder on the graphic EQ;
- mic at the template unless approach 2 is decisive;
- factory defaults for everything else.

Checking:
- 2–6 candidates are rendered through 3–4 library DIs.
- The answer falls back to neutral settings plus inversion unless one candidate wins on most clips.

Every written control carries a label: estimated, estimated as part of a group, detected, set by rule, or prior.

**Controls covered:** all.

**Benefit and confidence.**
- This is what gives "every control", honestly and fast: 5–40 renders, about 1–2 minutes, against about 325 renders and 8 minutes today.
- Its quality equals what 1–4 deliver. Nothing yet shows that a few checking renders through a library DI match the 300-render search. The design is sound; the outcome is unknown.

**Cost.**
- 4–5 days after 1–4 pass.
- Tests take about 4–5 hours of renders.
- No new dependencies.

**Key references:**
- Gutenkunst et al. 2007: in many-parameter models, fits pin down predictions while leaving individual parameters loose; "focus on predictions rather than parameters". https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.0030189
- Makinen et al. 2026, The Degeneracy Distillery: finds parameter combinations that have independent effects, from the Fisher information, and needed up to 10× fewer simulations. https://arxiv.org/abs/2606.23838
- Salimi et al. 2026: scoring only the shared, meaningful parameters agreed with blind listening on the top-ranked loss in 5 of 7 scenarios. https://arxiv.org/abs/2608.27698

### 6. One learned model for the whole preset (fallback)

**What it is.**
- A CNN on the guitar stem, with one output per control: a choice over members for each selector and switch, and a 32-bin choice per live knob on the plugin's own grid.
- Training is masked by `match/space.py`'s gates, so an amp's knobs train only when that amp is selected.
- Trained on plugin renders of many DIs at random levels and pickup EQs, mixed into other bands' backings and partly put through Demucs.
- If several equally good answers turn out to be the limit, upgrade to a mixed discrete/continuous posterior (sbi's MNPE).
- Its top candidates feed approach 5's check.
- It must beat a no-training baseline: nearest neighbour over played-guitar renders through many DIs.

**Controls covered:** all, as probabilities.

**Benefit and confidence: low.** Data limits it, not the architecture:
- Training DIs would come mostly from the 13 local set-2 development bands (7 Cambridge, 6 Telefunken), used leave-band-out, which round 1's E9 avoided by training on CC BY DIs only. Guitar-TECHS P1/P2 must be downloaded, and IDMT is non-commercial and no-derivatives.
- So it may learn the players rather than the tone.
- M7-2 showed per-knob losses can improve parameter error while the sound gets worse.
- Weights trained on non-commercial DIs and backings stay on your Mac.

**Cost.**
- Pilot: about 2 days of code and 10–12k renders.
- Most of those renders need fresh processes if drawn from the factory presets: 93 of 108 have the rack reverb or tremolo on or are AC20 (91 have the reverb switch on, 88 of them with the effects section on), so they take about 4–6 hours, or time effects are handled by approach 1 and left off in training renders. MPS training time is unmeasured; benchmark it for 10 minutes first.
- Production at 150–300k renders per pack would kill the licence daemon repeatedly (section 7) unless time effects are handled by approach 1 and renders stay in reused processes.
- Torch in an optional extra.

**Key references:**
- Hayes et al. 2025: a flow model beat regression in-domain (spectral distance 6.13 against 14.73, 2M renders, 165 parameters). https://arxiv.org/abs/2506.07199
- Synth-JEPA: out of domain, regression was worst (28.06), flow matching 16.67, embedding search 10.25. https://arxiv.org/html/2609.31024
- Boelts et al. 2026, mixed neural posterior estimation: posterior split into a discrete part and a continuous part conditioned on it; in sbi; no support for posteriors whose dimension varies. Tested at most at 2 discrete by 4 continuous parameters, so ours would be 1–2 orders of magnitude larger. https://arxiv.org/html/2605.13551
- Hinrichs et al. 2022: a network trained on clean guitar fell below 40% accuracy when just a kick drum was mixed in, so mix augmentation is mandatory. URL above.

## 4. Experiment-first plan

**Ground rules (round 1's, plus four new ones).**

From round 1:
- Set-2 development parts only.
- Score through each part's own DI against the amp track, with `unpaired-v3` and level left out.
- Compare only within one run, and count wins by part and by band.
- Commit the band-stratified 20-part draw before the first run.

New:
1. **Decide process policy from S0, not by habit.** Reuse a process where its gap to fresh is at most 0.15× the distance between settings.
2. **Watch the licence daemon on every run.** Log its PID and port count, run the watchdog, and limit fresh processes to one per candidate (section 7).
3. **Render the in-run neutral fresh, or after a fixed predecessor.** SW50R's committed neutral repeats spread a median of 0.14 (up to 0.60) after other parts' searches, against 0.002–0.004 on the first two parts. This also affects round 1's E2 counts.
4. **Tone King's process policy comes from S0 like every other section** (rule 1); until then run it as today, and restart when the daemon restarts.

### Phase 0: fixes and zero-render checks

About 2 days of code, plus passive logging during existing overnight runs.

**R0, renderer hardening (section 7):**
- a watchdog on the daemon's PID, plus a canary render every 200 renders;
- a count of non-finite samples in the server's reply, plus a finiteness check in Python;
- discard warm-up renders on Tone King instance start;
- report band noise over 63 Hz–16 kHz;
- test, by rescoring stored no-DI answers with the gate reset, whether to keep the gate out of no-DI searches.

Changing `match/renderer_au.py`, `au_render_server.swift` or `au_probe.swift` changes the renderer hash (`_renderer_build`), and `invert.py` refuses a calibration from another build, so the calibrations must be re-measured (Tone King EQ basis about 77 s, drive curve about 330 s, plus Morgan's). The watchdog, canary and warm-up discard all live in `renderer_au.py`.

Gate, passive: in the next overnight runs, every Tone King silent or failed render follows a daemon restart. If one does not, the S0 host test below becomes urgent.

**Z1.** The 43 development DIs' long-term spectra are fitted to each other with the graphic EQ, in numpy. The residual is the yardstick for S2's mic gate.

**Z2. Does the song reveal how hard the guitarist played?**
- Regress each development part's DI loudness and tilt from its amp-track features, leaving each band out in turn.
- If R² ≥ 0.5 for loudness, effective drive can be referred back to an absolute input.
- Otherwise presets assume a median-level guitar.

**Z3.** Screen the 43 development amp tracks for printed delay, reverb or tremolo: existing detectors plus a 5-minute listen. This keeps F1's "off" class clean.

**Z4.** Round 1's Phase 0 harness changes, shared:
- `--signal file/dir`;
- `--no-search`;
- `--reference-source`.

Also commit the 20-part draw.

### Phase 1: the recoverability screen

About 3–4 days of code and about 7–8 hours of plugin time (the itemised steps below add to 6.7–7.7 h) in batches of 2 hours or less, on an idle machine.

`scripts/study_recoverability.py` is numpy and scipy, reusing `match/space.py` and `match/renderer_au.py`. Renders go through 8 set-2 development DIs from 8 bands at their own recorded levels (−32 to −10 LUFS), never noise.

**S0, floors (about 1 hour).**
- Repeat floor and render-history floor per section: reused, fresh, and after a fixed "flush" predecessor.
- Tone King warm-up curve: 3 fresh instances × 12 renders.
- On a scratch-built server, a 2×2 of the offline-render flag and main-run-loop pumping, plus realtime pacing.
- Decides: process policy per section. Adopt the flag or pacing only if fresh repeats become byte-exact or at least 10 dB closer.

**S1, sensitivity (SW50R pilot, about 20 minutes).**
- A radial one-control-at-a-time design (Campolongo et al.) with 16 base points, topology fixed, time effects off.
- Gates:
  - the control ranking from the two halves of the base points agrees (Spearman ≥ 0.8);
  - Volume's effect against the spread between players agrees with the harmonic study's ratio within ×2;
  - dropping one DI keeps the ranking (Spearman ≥ 0.7), otherwise add DIs;
  - report how strongly Volume and input gain track DI level after level and tilt are marginalised out. A correlation of 0.9 or more means only the joint drive number can be recovered.
- If the gates pass: SW50R in full plus Tone King rhythm, about 2–3 hours. PR12, AC20 and Tone King lead come later, about 3–4 hours, only for families Phase 2 keeps.

**S2, linear chain (about 15 minutes).**
- As in approach 2.
- Gates:
  - linear within 0.1 dB over 63 Hz–12.5 kHz;
  - at least 3 mic clusters more than 1 dB apart after the EQ fit;
  - the mic-to-mic residual exceeds Z1's DI-to-DI residual.
- Fail: mic is set by rule, and the family is closed.

**S3, imitation tests (40 minutes for amp choice; about 1 hour per pack for pedals and Tone King selectors).**
- Setup: 3 amps × 6 base sounds matched by distortion × 4 DIs.
- Each target is inverted onto every amp two ways:
  - through a different DI: the song case;
  - through its own DI: the upper bound.
- The refit budget (up to 20 renders) is reported as a factor.
- Pass: the true amp ranks first in the song-case arm on at least two-thirds of cases (chance one-third), by more than the S0 floor. Then build approach 4's checking step.
- Near chance: the amp comes from text research and the prior.

**S4, probe given the true DI's loudness (about 25 minutes of renders).**
- Setup: 600 settings × 12 DIs from 12 bands; ridge and nearest-neighbour models, leaving each band out.
- Compare song-side features alone against the same features plus the true DI's loudness, tilt and onset strength.
- **Large gap:** the obstacle is playing level, and Z2 decides what can be done.
- **Both low:** the features are the limit. Only then fund a learned encoder, with at least 30 training performances.

**Output.** `docs/recoverability-<path>.json` and a section in `docs/tone-matching-plan.md`. For each control, a verdict (estimate, estimate as part of a group, detect, rule, prior) and its estimator.

Phase 2 builds only the families the screen marks as estimable or detectable.

### Phase 2: family estimators, each with its own gate

About 1.5 weeks. Runs can share nights.

**F1, time effects (approach 1).**
- Setup: inject factory-drawn settings into the Z3-clean development amp tracks, with the amp and cab sections off.
- Rungs:
  - the amp track;
  - the amp track plus backing;
  - Demucs on a 120-clip subset.
- Spring reverb is tested separately through 8 DIs.
- Machine time: about 1 hour, plus 30 minutes of Demucs.
- Pass on the amp-track rung:
  - per effect, specificity ≥ 0.95 and sensitivity ≥ 0.80;
  - delay time within 5% (or the right note division) on ≥ 80%;
  - tremolo rate within 0.3 Hz on ≥ 80%;
  - reverb decay Spearman ≥ 0.6, per decay bin up to 4 s.
- Stem rung: specificity ≥ 0.95 and sensitivity ≥ 0.6. Otherwise the template stands for songs.

**F2, drive (approach 3).**
- Setup:
  - a 5-step Volume ladder plus a pedal ladder;
  - Tone King attenuation at 3 positions;
  - at −18 LUFS and at each DI's own level;
  - each row's same-passage ceiling;
  - round 1's E6 regret metric, sharing E6's renders.
- Machine time: about 20 minutes.
- Pass: a new row reaches ≥ 37% recovery (timbre's 26.5% plus 10 points) and ≥ 0.6× its own ceiling at real playing levels, on both SW50R and Tone King rhythm, with regret ≤ 0.75× `unpaired-v3`'s.
- Fail: close the hand-made drive features. Drive stays at the text-research value, and Phase 4 becomes the only route.

**F3, topology (approach 4), as arms of round 1's E5.**
- Factory-only library, 20 parts.
- Arms:
  - neutral plus inversion;
  - retrieval top-1;
  - the render-free re-rank;
  - a split-half oracle;
  - E2's search.
- Machine time: about 1 hour.
- Stop: the oracle is not ≥ 15% closer than neutral plus inversion on ≥ 15 of 20.
- Pass, all three:
  - retrieval beats neutral plus inversion on ≥ 15 of 20;
  - it recovers ≥ 50% of the oracle's median gain;
  - its median is no more than 5% worse than the search's.

**F4, linear solver (only if S2 passed).**
- First through each part's own DI, then through the library probe. About 30 minutes.
- Pass: ≥ 15 of 20 closer, with a median ≥ 5% closer. The library-probe leg must keep ≥ 50% of that gain.

**How this connects to round 1.**
- **E1/E2 (library-DI probe)** run first or alongside Phase 1. The screen uses the same clip banks, and approach 5's checking renders only make sense if E2 shows a library DI beats neutral (≥ 15 of 20). If E2 fails, Phase 3 is not built (as it says), and the families that passed ship only as estimators of their own controls.
- **E4 (mix rungs)** gives every family its in-mix column. Run F1's stem rung, and F2/F3 on stems, only after E4 shows the stem keeps ≥ 50% of the gain.
- **E5** hosts F3, **E6** shares renders with F2, and **E7** (DI recovery) is unchanged.
- **B0** (Tone King without a DI returns neutral settings) is still your call (round 1, §5). If adopted, it stands until Phase 3 beats neutral on Tone King.

### Phase 3: assemble the deterministic estimator

About 1 week. Built only if E2 passes and at least two of F1–F3 pass.

**A1, does the parameterisation lose anything? (about 2–3 hours; no estimation).**
- Setup: 30 SW50R and 30 PR12 targets from perturbed factory presets. Their quantities are read from the known settings, solved back to knobs by the rules, and rendered through the same DI.
- Compare against:
  - neutral plus inversion;
  - a 300-render same-DI search on 10 targets per amp.
- Pass: the solved preset beats neutral plus inversion on ≥ 80%, with a median within 1.2× of the search's.
- Fail: the failing targets share a missing quantity; add it.

**A2, the song-side test (about 2 hours).**
- 20 parts, three arms:
  - (a) inversion plus a 300-render search through the library probe, which is round 1's bar;
  - (b) the deterministic estimator with at most 40 renders;
  - (c) neutral plus inversion.
- Pass: (b) is no worse than (a) on ≥ 12 of 20 and beats (c) on ≥ 14 of 20.
- Then repeat on E4's stem rung, confirm on all 43 parts, and run Tone King in warmed, reused instances.

### Phase 4: learned model

Only if F2 fails, S4 shows a learnable gap, and E6 shows `unpaired-v3`'s regret well above the same-DI floor. About 2–3 weeks.

**Pilot as in approach 6, against the nearest-neighbour baseline.**
- Simulation pass: the CNN's regret is ≤ 0.6× neutral's, and it beats the baseline on ≥ 60% of targets.
- Real pass: on amp tracks it is closer than neutral on ≥ 15 of 20, and no worse than E1's inversion arm.
- It abstains on ≤ 30%.
- Stop if it does not beat the baseline.

### Listening test

Declare it in a committed file before running, following the `docs/heldout-listening-sw50r*.md` procedure, after A2 and the 43-part confirmation pass.

- **Parts:** held-out set-2 parts, on passages where the guitar is exposed.
- **Arms:**
  - the deterministic estimator;
  - round 1's library-DI search, or today's noise search if that is not built;
  - neutral settings.
- **Reference:** from the song once the Demucs extra exists; from the amp track before that, stated as such.
- **Pass:** the estimator is preferred on at least two-thirds of the parts the listener can tell apart, and is clearly worse than neutral on no more than one.

### Timeline

- Phase 0: about 2 days.
- Phase 1: about 1 week.
- Phase 2: about 1.5 weeks.
- Phase 3: about 1 week.

That is roughly a month to a working estimator, and any gate can stop it earlier. Plugin time is about 7–8 hours in Phase 1, 3–4 in Phase 2 and 4–5 in Phase 3, all in batches on an idle machine.

## 5. What not to do

- **Build before the screen.** No model, 2,400-entry preset library or calibration tables before the screen and the factory-only headroom test.
- **Score by raw knob error.** In M4, parameter error rose from 0.247 to 0.266 while the sound got about 4× closer. M7-2 showed the reverse.
- **Treat Fisher information as the verdict on what is identifiable.** Confirm "equivalent" and "not recoverable" with imitation renders.
- **Estimate controls that are not identifiable.** Output level, pans, phase, stereo, ping-pong, doubler spread, transpose and gate threshold are set by rule. Never write Morgan's room mic type. Never estimate a compressor from a mastered song.
- **Let one library DI judge a discrete choice.** Use the median over 3–4.
- **Start a fresh plugin process per render by default.** Each costs the licence daemon about 10 ports. Keep fresh processes for AC20 and for the few checks with the rack reverb or tremolo on. Never modify the system daemon itself.
- **Replicate every Tone King render** because of the "5 dB" figure.
- **Run topology racing or mixed categorical search over the whole space as the pipeline.** It costs 150–300 renders with no speed gain, and §12p showed that splitting the budget made targets worse. No exhaustive mic × topology grids either.
- **Build a token decoder with render-reward training, or a neural proxy, now.** Pretrained encoders stay as comparison rows in round 1's E6.
- **Run per-control listening threshold tests.** Calibrate per family later, only if a verdict depends on it.
- **Use noise or synthetic-guitar probes anywhere the amp distorts.**
- **Ship weights trained on non-commercial DIs or backings.** Never let held-out parts or set-1 P3 into any library or training set.
- **Use an abstain rule based on repeat noise.** It becomes meaningless once renders are deterministic; use agreement across clips instead.

## 6. Decisions needed from you

1. **Labelled answers.** Every control gets a value, but some will be shown as "set by rule" or "typical factory value" rather than measured. I recommend showing these labels in the shortlist. Needed before Phase 3.
2. **Optional: your pickup output, once.** A one-time preference (low, medium or high output pickups), with no recording. Without it, presets assume a median-level guitar, and the input gain may be off for you: on PR12, tripling the input moves the distortion point from 66% to 28% of the knob. Ask it only if Z2 and F2 show the input level matters and cannot be read from the song; needed before Phase 3.
3. **B0, from round 1:** whether Tone King without a DI returns neutral settings. Still open.
4. **Round 1's open decisions still apply.** Guitar-TECHS P1/P2 as the shipped clip source (needed before shipping, not for the screen, which uses local DIs), and Demucs or torch extras later. Nothing new here.

## 7. Tone King flakiness: is it something we do?

Mostly yes. The plugin's audio repeats well; the failures come from how we run it, and each has a cheap fix. I confirmed these points from the system log, the committed runs and the code; nothing was rendered.

**1. The late silences follow the iLok licence daemon being killed.**
- macOS killed PACE's licence daemon for "allocating too many mach ports" twice:
  - 07:10 on 2 Oct (the kill line has since rotated out of the system log; the daemon restarted at 07:10:06 under a new PID and lasted 17.1 h);
  - 00:15:44 tonight, at 267,659 ports.
- Tone King set-2 run 1 started at about 04:48 and went silent 2.2–2.45 h in. The kill came 2.37 h in.
- Tonight, a running Tone King search's last six renders came back silent about five minutes after the 00:15 kill. That comes from the review's check of its trial log; I did not re-check it.
- The daemon gains about 10 ports for every plugin host process started. In a 4-minute sample tonight it rose by 2,133 while 212 new host processes appeared.
- The leak is PACE's, but our process churn wears the daemon out within hours: a new process per render for AC20, tremolo and fresh-policy benchmarks, with several workers and jobs at once. The daemon started at boot (31 Aug) lasted until 2 Oct; its replacement lasted 17 h.
- Nothing in `match/renderer_au.py` notices that the daemon restarted.
- The current daemon (started 00:15:45) held 22,723 ports at 00:48 and 86,451 at 07:21; the count went flat once the fresh-process load ended at about 06:13, with no further kill.

**2. The "~5 dB band noise" is our own statistic.**
- It is the largest difference over five repeats in the 25 Hz band: 3.38 dB on rhythm, 4.39 dB on lead, in a band with almost no energy.
- From 63 Hz up, repeats differ by at most 0.0034 dB (`packs/toneking/eq_basis.json`), better than Morgan's reused instance.
- The manifest's 5.23 and 6.73 dB figures feed the user-facing caveat and the search's fallback noise floor.
- Also, `band_shape` in `analysis/compare.py` weights the 25–40 Hz and 16–20 kHz bands fully, while `match/invert.py` down-weights them to 0.15. This is small (about 0.02 on a total) and not the cause of the outliers.

**3. We don't discard warm-up renders.**
- In all four committed set-2 Tone King runs, the first three parts (the first on each worker) have neutral repeat spreads of median 0.028 (max 0.35).
- The other 34 parts have median 0.004 (max 0.038).

**4. Two of our templates add their own noise.**
- Through the noise probe, repeats spread:
  - neutral template: median 0.013;
  - Default (delay and reverb on): 0.056, mostly in the ambience score;
  - Reset All Settings (gate at −80 dB): 0.35, mostly in dynamics.
- The no-DI search pushed the gate above −60 dB on 7 of 43 answers from the neutral start, 11 from Reset All Settings and 1 from Default, where it cuts into the note decays. These counts and the template spreads come from the 2026-10-02 starting-point runs, written up separately.

**5. Our silence check cannot see NaN.**
- The server computes its peak with Swift's `max`, which skips NaN, so an all-NaN render reports a peak of 0.
- The Python check lets NaN audio through as not silent.
- There is no evidence the plugin outputs NaN. This is hardening.

**6. Untested: the host's offline flag and run loop.**
- The render server never sets the Audio Unit's offline-render flag, which Apple's header recommends for hosts without realtime deadlines, and never runs the main run loop.
- JUCE-based hosts, pedalboard included, do not set that flag on hosted Audio Units either. So this is a possible cause of the tiny fresh-process differences (−31.3 and −39.5 dB in the repo's measurements), not a known one.
- S0 tests it in about 40 minutes on an idle machine.

**Fixes (Phase 0, R0):**
- restart rendering when the daemon's PID changes, plus a canary render;
- far fewer process spawns;
- discard warm-up renders;
- measure the noise floor over 63 Hz–16 kHz;
- the gate test above;
- check for non-finite samples.
