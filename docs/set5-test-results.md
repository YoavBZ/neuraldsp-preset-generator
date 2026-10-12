# Held-out test on set 5: the corrected DI network — results

Run 2026-10-12 under the [plan](set5-test-plan.md) and its amendments, on set 5's first
declared use. The ledger entry and network hashes were committed before any render. An
adversarial audit re-derived every number (`tmp/set5-audit.md`, local).

## In short

- **Gate 1 helps:** on fresh bands, the corrected network (C′, the mean of three seeds) picks
  presets closer than the old network C.
  - The band mean is −0.124 (90% −0.244 to −0.003), with 5 of 5 bands better.
  - The upper bound clears 0 by only 0.003.
  - Part-weighted it is −0.059.
- **It is a crunch effect, and fragile:**
  - crunch −0.147, clean −0.024;
  - two small crunch bands carry it, and dropping either one leaves it inconclusive.
- **C′ replaces C as the research network,** as declared. Seed 0 is frozen at its pinned hash;
  it also passes alone.
- **The product question (report-only here) is not answered.** On crunch, C′'s pick only
  matches `generate`'s starting preset (−0.023). C was worse than it (+0.124), and the oracle
  is at −0.129.

## Numbers (band-weighted first; part-weighted in brackets)

- **Gate 1, C′ against C:**
  - **All:** −0.124 (−0.059), 5 of 5 bands better, "helps".
  - **Clean (3 bands):** −0.024. **Crunch (4 bands):** −0.147.
- **Per band:**

  | band | parts | mean |
  |---|---|---|
  | Saturn Syndicate | 2 (one tone, double-tracked) | −0.263 |
  | The Ferryboat Men | 1 (re-hosted) | −0.258 |
  | BKS (with Fytakyte) | 10 | −0.049 |
  | Hazael | 4 | −0.047 |
  | Ronnie Jones | 8 | −0.001 |

- **Leaving one band out:**
  - without Saturn Syndicate: −0.089 (−0.224 to +0.047), inconclusive;
  - without The Ferryboat Men: −0.090, inconclusive;
  - publisher originals only: −0.085, inconclusive.
- **Each seed alone** (−0.126, −0.125, −0.120, each "helps"): these are correlated views of
  the same data against the same C (per-cell correlation 0.84–0.88), not replications.
- **Report only, against `generate`'s start, on crunch:** C′ −0.023, C +0.124, the oracle
  −0.129. Pooled: C′ −0.063.
- **Cells:** 75 in-scope part-amp cells from 5 bands, with BKS and Fytakyte merged. Ronnie
  Jones ElecGtr05 dropped out: the measure refused a whole half.

## What the audit found

- **Integrity:**
  - The ledger and hashes were committed at 13:06:47, and the first set-5 file appeared at
    13:08:30.
  - The hashes match across the ledger, the manifest and the files on disk.
  - The only change between the reviewed code and the run is one print label.
- **C's rebuilds are not broken.** Levels match, nothing clips, and their timing against the
  true DI matches C′'s.
  - On the parts that drive the gate, C's rebuilt DI is darker and further from the true DI.
    That fits the gradient bug.
  - On crunch tracks, C picks clean or ambient presets (Low-Watt Americana nine times, Dotted
    8th Dark Echoes seven times), ranked 21st–41st by the measure. C′ picks mid-gain presets.
  - **So the gain is C′ avoiding C's bad crunch picks,** not finding better presets.
- **Not one unlucky C:** the three C′ seeds agree with each other on 74–80% of picks, but with
  C on only 46–48%.

## What this establishes, and what it doesn't

**It establishes:** on fresh bands, from amp tracks, by the flat judge, the corrected network
picks better than the old one, mainly by not misjudging crunch.

**It doesn't establish:**
- anything about songs (the input was isolated amp tracks);
- the training recipe in general (there is only one C);
- a firm effect size (the result rests on 3 parts and 2 tones);
- any benefit on clean;
- product value;
- anything heard.

**Next:**
- no further set-5 analyses;
- the frozen C′ seeds go into the declared combined set-5 + MedleyDB test from separated
  stems, with power computed first.

Set 5 suggests that beating the crunch starting preset there is unlikely unless the chooser
closes part of the gap to the oracle.
