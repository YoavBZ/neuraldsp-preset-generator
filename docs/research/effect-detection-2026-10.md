# The mix hides the effects, not the labels

*Research report, 2026-10-27, for the ML session's request on effect detection, audibility-aware labels, input features, separation and amp knobs. Research, not a declared plan: any run needs its own plan, review and ledger entry.*

The project's [tone probe](../tone-info-probe.md) has answered most of this request. A linear probe reads 86 of 116 heads from the clean render, 30 from the mix and 20 from the X-LANCE stem; a finer STFT reads 87, and the DI adds nothing. Faint "on" labels are common but rarely near zero (4–10% below 0.05), and they explain only part of the delay. So the hypothesis is mostly wrong: masking by the backing is the big loss, the separator a smaller one. This report adds evidence that `gtr_mss` probably learned dry guitar and how to fine-tune it to keep tails, an audibility measure taken in the mix for the roadmap's step (c), and the amp-knob literature.

## Features and mix plus stem are settled; stereo is blocked

The probe's summaries already include the descriptors this research would propose, such as envelope autocorrelation to 1.8 s, and the target reads 13 of 19 time-effect heads with them: no new features. Caveat: the linear probe is a lower bound, and D_F5's CNN read 1 time-effect head to the probe's 3 on the same stem, so its time pooling may cost something. Mix plus stem read 24 against the mix's 30: drop "mix − stem" as an input. Stereo is untestable: every stored render is mono.

| Effect | Best published result | Probe AUC: target / mix / stem |
|---|---|---|
| Delay | time error 0.06, level 0.16, isolated notes ([Jürgens 2020](https://www.dafx.de/paper-archive/2020/proceedings/papers/DAFx2020_paper_2.pdf)) | 0.81 / 0.66 / 0.62 |
| Reverb | music T60 error 126–152% ([Callens 2020](https://arxiv.org/abs/2010.11167)); no wet/dry estimator | 0.75 / 0.60 / 0.58 |
| Tremolo | rate 0.06, depth 0.08 ([Jürgens 2020](https://www.dafx.de/paper-archive/2020/proceedings/papers/DAFx2020_paper_2.pdf)) | 0.72 / 0.55 / 0.52 |
| Springs | chirped echo train ([Parker 2011](https://acris.aalto.fi/ws/portalfiles/portal/13004391/art_10.1155_2011_646134.pdf)); no detector | 0.72–0.73 / 0.59–0.61 / 0.56–0.57 |

## A dry-trained separator will not hand tails back

A stem keeps reverb only if its training targets did. MoisesDB stems get no effects at mixing ([MoisesDB](https://arxiv.org/pdf/2307.15913)), and the MSR task scores the unprocessed stem ([MSR](https://arxiv.org/pdf/2505.21827)). `gtr_mss`'s released guitar configs train on raw MoisesDB and RawStems with augmentation off ([config](https://huggingface.co/spaces/chenxie95/xlance-msr/raw/main/configs/bsmoise/gtr.yaml)); uncertain, because the paper says guitar came from the frozen base model ([X-LANCE](https://arxiv.org/pdf/2602.09042)). Live-music separators scored best on the reverb condition they were trained on, by about 0.9 dB either way ([CrowdioSet](https://arxiv.org/pdf/2607.27828)). Test-time augmentation adds ≤ 0.06 dB SDR, and its channel swap does nothing on mono ([MSST 2026](https://arxiv.org/pdf/2607.23395)).

For the roadmap's fine-tune (b): use the stored wet target renders as targets, reversing `gtr_mss`'s dry habit; keep its mono-duplicated input; train on clips at least as long as the 4.5-s halves (configs use 3 s; uncertain gain); and score new stems with the tone probe, not SDR alone. Check gradients first: a RoFormer's MPS gradient here had cosine 0.001 with the CPU's, and a 3-s CPU step took 11 s ([fine-tune plan](../separation-finetune-plan.md)). The [roadmap](../ROADMAP.md)'s "up to about 11 h of MPS" assumes MPS works.

## Measure audibility in the mix, not by the knob

The probe's audibility proxy is the knob value. Reverb, tremolo and the springs stayed weak from the stem even at their loudest third (0.52–0.63, against 0.77–0.87 on the target): a loud knob is not enough in the mix. For step (c), let A_e be the judge distance between a render and the same render with effect e off, with the backing as the judge's masking floor. Inaudible even solo: count as off, knobs masked (extends your switched-off rule; your call). Audible solo but masked in the mix: weight 0. Also mask idle knobs: delay time at low mix, tremolo rate at low depth. Published precedents: restricted draws ([Okita 2026](https://arxiv.org/html/2604.22276)), "subjective equivalence" ([Hinrichs 2022](https://www.tnt.uni-hannover.de/papers/data/1571/EURASIP_2022.pdf)), and pruning processors whose removal barely changes the loss, 69% of them ([Lee 2024](https://arxiv.org/abs/2406.01049v2)). Set τ by blind ear test, since repeat renders agree to 3e-6 ([every-control plan](../every-control-plan.md)). Skip ViSQOL and PEAQ, calibrated on codecs ([ViSQOL v3](https://arxiv.org/pdf/2004.09584)).

## Amp knobs read from the render, but modestly

The target reads 55 of 85 knobs, but with a median gain of 3.1 points of range against the constant's error of about 17. No paper reads amp knobs from a song. Published tone-stack recovery needs DI plus output, and works only up to equivalence (learned parts at 0.62–1.31× nominal) ([Esqueda 2021](https://dafx2020.mdw.ac.at/proceedings/papers/DAFx20in21_paper_39.pdf)). That fits modest gains: gain can move between serial stages unseen ([Vanbeylen 2008](https://skoge.folk.ntnu.no/prost/proceedings/ifac2008/data/papers/1005.pdf)), so input gain, pedal level and amp gain set one drive, and tone stack, EQ, cab and mic multiply into one curve. The DI's null result may not hold on songs: training DIs are EQ'd to an average guitar.

## Ranked changes

| # | Change | Cheapest decisive experiment | Mac cost | Licence |
|---|---|---|---|---|
| 1 | Bound the fine-tune | Oracle mask from stored target and mix mels (needs the guitar's mix gain: unchecked), then the tone probe. Near 86 → room; near 30 → little | 0 renders, minutes, CPU | project code |
| 2 | Fine-tune `gtr_mss` on wet targets | Roadmap (b) with the recipe above, read by the tone probe | gradient check, else CPU, hours to days; your approval | X-LANCE MIT; base unlicensed, in use |
| 3 | Audibility labels in the mix (step c) | Re-render up to 200 "on" FS5 examples per effect with it off; re-read the probe by A_e thirds beside knob thirds | ~1,000 renders, about an hour | project code |
| 4 | Check the CNN's pooling | D_F5mix's time-effect row, when run, against the probe's mix row (5 of 19); if short, feed the summaries to the heads | none extra | — |
| 5 | Effective-drive and response-curve heads | Probe the target for these against single knobs | 0 renders, minutes | scikit-learn BSD-3 |
| 6 | Stereo | Make the renderer keep stereo; ~100 renders, coherence against mono | minutes after the change | as now |

## Conclusion

The mix, not the labels, is the main loss; row 1 says in minutes whether the fine-tune can pay.
