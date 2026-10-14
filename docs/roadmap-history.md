# Roadmap history: product steps

Moved from [ROADMAP.md](ROADMAP.md) on 2026-10-14, unchanged, so the roadmap stays one
short living plan. The ML session keeps its own history for step 0.

1. **Listening check of the page: run, inconclusive**
   ([plan](listening-check-plan.md), [results](listening-check-results.md)). Sitting 1
   was void: both its controls were answered "?", and the "?" answers cluster there,
   so a playback problem in that sitting is not ruled out. The page stays an option in
   `generate`. The listener reported that for some songs the target guitar could not
   be found, or tone could not be compared across different notes. The picks leaned
   closer than chance under one band set only, and not beyond a song-blind taste.
   The declared rerun was set aside with the listener (reasons in the results); the
   own-DI version waits for the derived-DI route.
   - **Learned while setting it up:** a riff must match the song guitar's style. The
     listener found single-note parts can't be judged against strummed chords (drive
     sounds different on several notes at once), so the check now plays each part
     through the riff in its own style, measured from its clean recording. The page
     should do the same from the song alone (classifying a separated guitar stem as
     chords or single notes), and may need more styles (arpeggios, power chords).
2. **A distance without a DI: hand-made features fail**
   ([plan](di-free-distance-plan.md), [results](di-free-distance-results.md)). None of
   the eight DI-free distances tested beside the v3 baseline (v3c, log-mel and MFCC
   statistics, the lean fingerprint, masked spectra, an LDA) picks presets clearly
   better than a song-blind constant: regret 0.30 to 0.48 against 0.36 to 0.42,
   agreement with the judge at most 0.38. With the part's own notes, the masked spectra
   pick within the judge's near-tie range (0.04); through another player's notes they
   fall to the constant (0.36): the performance moves them more than the preset.
   *2026-10-07, from step 0: log-mel statistics and PANNs CNN14, used as rerankers over
   renders through other players' DIs, also failed ([rerank-plan.md](rerank-plan.md)).
   Our own contrastive guitar encoder passed identification on renders but failed on
   real recordings (step 0).* Remaining candidate, deferred while the development
   chooser diagnostic runs:
   - **Pretrained effect encoders** (AFx-Rep, about 1.2 GB; verify open licence before use),
     with CLAP as the floor. General audio models (CLAP, MERT, wav2vec2) are floors
     only: once the notes differ they score near chance, and they discard the input
     level that carries the drive.
   - **Own contrastive encoder: already tested, failed on real recordings** (step 0).
     Another run needs a declared intervention addressing transfer from renders to
     recordings and a cheap positive control; do not repeat the original training.
3. **The derived-DI route** (experiment 5). *Done, 2026-10-06*
   ([results](di-robustness-results.md)). It did not pass as declared. Under the
   average-guitar measure, a realistic rebuilt DI loses little, so DI recovery was
   built (step 0).
4. **The judge's coverage.**
   - High-gain calibration needs high-gain references with a DI (a download).
   - The listening checks the judge's review asked for: whether hiss matters, and
     whether drive with a matched spectrum is heard as the judge weights it.
   - Any search scored by the judge needs a positive control first.
5. **Defects in the DI path** ([ground-truth audit](ground-truth-audit-2026-10-03.md)).
   In the product, only `match_preset.py`'s search reaches these (with `--probe-di`,
   `--search-without-di` or `--reference-mode probe`); song-only `generate` never
   does. Research benchmarks reach them too.

   Fixed: D-H1 (#107), D-M6 (#119), D-M9 (#114), D-M15 (#113), and on 2026-10-12
   D-M1 (#170), D-M7 (#168) and D-M8's calculated start (#169). Moot: D-M2 (the
   level trim now runs only for a paired reamp) and D-M14 (research E1). About how
   results were reported: D-H2, D-M5. Parked:
   - **Tone King re-scoring (rest of D-M1):** the research benchmark's Tone King
     scoring renders still have no pre-roll; that is the ML session's.
   - **Morgan's reused-instance history (D-M13):** addressed in the product match path
     for the carry-over of the previous render: Morgan renders now isolate each state
     write, which removed it on one PR12 part (knob-ceiling plan, amendment 3). AC20,
     the tremolo and the rack reverb still need `--process-policy fresh`; the 0.25 s
     fade-in isolation adds is unmeasured on the match loss. The shared renderer's
     default is unchanged; the ML session audits its own pipelines.
   - **Search controls:** `--enumerate` (D-M17) and the screen's false premise
     (D-M18): their help and report texts are corrected by #171. Parked: screening
     each enumerated variant's own active controls, and a midpoint probe.
   - **Inversion:** a mix's or separated stem's bands below 250 Hz are left alone
     (D-M8, #169), but the search and its loss can still move them, parked with the
     search objective below. A false tremolo (D-M7) is no longer set from a
     recording (#168); parked: the finer `tremoloRate` step, and whether a reamp of
     the user's own DI (`paired_di`) also fires falsely (measure on the 43
     development DIs through a tremolo-off template before changing it), and
     offering `--enumerate` for the tremolo.
   - **The search objective,** which still steers the DI path though it no longer
     judges: spectral extremes (D-H3), level handling (D-M3, D-M4), ambience, decay
     and renormalising (D-M10–D-M12), and an untested stereo term (D-M16). These are
     loss questions (the ML session's); none has been shown by listening to change
     a preset.

6. **Product checks, alongside the ML work** (added 2026-10-12, from an independent
   review of the direction).
   - **Measure `generate`'s own risky steps:** *done 2026-10-12
     ([results](generate-routing-results.md), independently re-derived).* Routing
     costs: from the song alone it sent 9 of 22 clean parts to crunch, mostly by genre
     or song-level write-ups (+0.114 against knowing the class); `generate` now
     installs the neighbouring starting point too, and routes by the part's own
     documented sound. Research edits: undecided (+0.014, −0.008 to +0.036), no change.
     As first planned, from the song and a time alone, on development parts: how often research
     puts a part in the right class (a wrong class loses: on set 4's heavier parts the
     crunch presets lost 11 of 12 to the driven ones), and whether the research edits
     on top of the dry starting preset help or hurt (one case, Cut It Out, was mixed:
     the darkened preset lost through the rebuilt DI but won through a real DI riff;
     see [reading a reference](../reference/reading-a-reference.md)).
     *Re-checked 2026-10-12 ([results](generate-routing-recheck-results.md)): the new
     routing rule helps* (−0.081 against the old skill rerun, 90% −0.134 to −0.033;
     regret 0.059 against 0.140), and every new run wrote a second start.
   - **A short listening check of the starting presets** against what they replaced,
     through the part's own notes ([plan](starting-preset-listening-plan.md)): *done
     2026-10-13 ([results](starting-preset-listening-results.md)): heard.* The listener
     chose the preferred option on 17 of 21 trials (p 0.004); every block leaned that
     way; hidden references and repeats passed; one reversed-taste trial cannot rule out
     a preference for lighter gain. In-sample, one listener.
   - **Another end-to-end run** of `generate` on a clean or Tone King song (Cut It Out
     is the one case recorded so far).
