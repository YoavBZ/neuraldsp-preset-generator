# The mix hides the effects, not the labels

*Research, 2026-10-27, for the ML session; not a declared plan.*

The [tone probe](../tone-info-probe.md) answers most of the request: a linear probe reads 86 of 116 heads from the wet target render, 30 from the mix and 20 from the X-LANCE stem; a finer STFT reads 87, and the DI adds nothing. So the user's hypothesis, as the ML session relayed it, explains only part of the delay: "on" labels are often faint (4–10% below 0.05), but masking by the backing is the main loss.

## Features and inputs are settled; stereo is blocked

The probe's summaries already include envelope autocorrelation to 1.8 s, and with them the target reads 13 of 19 time-effect heads: no new features. D_F5's CNN read 1 time-effect head to the probe's 3, within chance. Mix and stem together read 24 against the mix's 30, and the [roadmap](../ROADMAP.md) already feeds step (a) the mix alone. Stereo is untestable: stored renders are mono.

| Effect | Isolated notes ([Jürgens 2020](https://www.dafx.de/paper-archive/2020/proceedings/papers/DAFx2020_paper_2.pdf)) | Synthetic mixes ([Hinrichs 2022](https://www.tnt.uni-hannover.de/papers/data/1571/EURASIP_2022.pdf)) | Probe AUC: target / mix / stem |
|---|---|---|---|
| Delay | time 0.06, level 0.16 | slapback time and mix < 0.038 | 0.81 / 0.66 / 0.62 |
| Reverb | — | room size 0.041, mix 0.034 | 0.75 / 0.60 / 0.58 |
| Tremolo | rate 0.06, depth 0.08 | rate and depth < 0.052 | 0.72 / 0.55 / 0.52 |

Mean absolute errors, 0–1 scale. Hinrichs: single notes under bass, keys and drums (−36 to +3 dB), one plugin per effect.

## Whether the separator drops tails is untested

`gtr_mss` is in effect BS-Rofo-SW's frozen guitar output: the [X-LANCE paper](https://arxiv.org/pdf/2602.09042) trained new separation models only for synths, drums, percussion and orchestra, and the space's [config](https://huggingface.co/spaces/chenxie95/xlance-msr/raw/main/configs/gtr_mss.yaml) is "roformer_gtr_frozenall". SW's training data are undisclosed; the local `.pth` holds its config ([xlance_screen.py](../../learn/xlance_screen.py)). MedleyDB's stems carry their effects ([MedleyDB](https://medleydb.weebly.com/description.html)), MoisesDB's only recorded ones ([MoisesDB](https://arxiv.org/pdf/2307.15913)). No study measures tail retention; live-music separators scored about 0.9 dB better on their training reverb condition ([CrowdioSet](https://arxiv.org/pdf/2607.27828)). The probe loses no head to the separator alone.

For step (b): train on the stored wet target renders, as planned; keep the mono-duplicated input; score stems with the tone probe, not SDR alone. Run the [fine-tune plan](../separation-finetune-plan.md)'s MPS gate first (MPS gradients had cosine 0.001 with the CPU's); its fallbacks move the iSTFT, then the loss, to the CPU.

## Measure audibility in the mix, not by the knob

Even at their loudest knob third, reverb, tremolo and the springs read weakly from the stem (0.52–0.63; target 0.77–0.87). For step (c): A_e = |log(J(r_off, m) / J(r_on, m))|, where the judge J scores the target render r_on, and r_off (effect e off), against the stored mix m; nothing is re-mixed (untested against a mix). Start τ at the [every-control plan](../every-control-plan.md)'s 0.005 log bar, checked by ear. Solo audibility needs J(r_off, r_on), a plain distance whose threshold is open. Three uses need the user's ruling. Counting an effect inaudible solo as off extends the switched-off rule and touches amendment 1 ("No fixed rule stands in for a control the judge can't hear"). Weight 0 for one audible solo but under τ in the mix breaks "the switch itself is always scored" (an amendment). Masking idle knobs (delay time at low mix) must be measured per knob: Tone King's tremolo speed was audible at depth 0. Published work only restricts draws ([Okita 2026](https://arxiv.org/html/2604.22276)), accepts "subjective equivalence" ([Hinrichs 2022](https://www.tnt.uni-hannover.de/papers/data/1571/EURASIP_2022.pdf)) or prunes processors that barely change the loss ([Lee 2024](https://arxiv.org/abs/2406.01049v2)).

## Amp knobs read from the render, but modestly

The target reads 55 of 85 knobs, gaining a median 3.1 points of range on the constant's error of about 17. No paper reads amp knobs from a song; Hinrichs reads distortion and overdrive gain and tone from synthetic mixes at 0.014–0.029. Tone-stack recovery needs DI plus output, and works only up to equivalence ([Esqueda 2021](https://www.dafx.de/paper-archive/2021/proceedings/papers/DAFx20in21_paper_39.pdf)). Gain moves between serial stages unseen ([Vanbeylen 2008](https://skoge.folk.ntnu.no/prost/proceedings/ifac2008/data/papers/1005.pdf)), so input gain, pedal level and amp gain set one drive, and tone stack, EQ, cab and mic form one curve. Training DIs are EQ'd to an average guitar, so EQ-type knobs will likely read worse on songs.

## Ranked changes

Ranked by how directly each attacks the mix's loss, then by cost.

| # | Change | Cheapest decisive experiment | Mac cost | Licence |
|---|---|---|---|---|
| 1 | Wet-target fine-tune (roadmap b) | MPS gate, then train; tone probe on FS5 | up to ~11 h on MPS (about 3.4× slower on the CPU fallback), 4–6 h re-separation, ~40-min retrain; the user's approval | X-LANCE MIT; SW base unlicensed, in use |
| 2 | Audibility labels in the mix (step c) | Render up to 200 "on" FS5 examples per effect with it off; re-read the probe by A_e thirds. All of F5 needs thousands of renders, not (c)'s zero | ~1,000 renders, about an hour | project code |
| 3 | Ideal-ratio-mask indicator, not a bound | STFT mask on unmastered FS5 examples, rebuilt at zero renders ([`self_built_mix`](../../learn/trusted_data.py), stored [gains](../../learn/trusted_data_t3.py)); undo the stored gain, then the target-trained probe (a) | 0 renders, CPU | project code |
| 4 | Pooling check | Free: D_F5mix's time-effect row against the probe's mix row (5 of 19); the 1-vs-3 gap was within chance | none extra | — |
| 5 | Effective drive (a measured distortion amount; only input gain has a dB scale), response curve (target-to-DI long-term spectrum) | Probe the target for these against single knobs | 0 renders, minutes | project code |
| 6 | Stereo | Stereo renders (a renderer change); ~100, coherence against mono | minutes | as now |

## Conclusion

The mix, not the labels, is the main loss; the wet-target fine-tune is the supported lever, though tail loss in `gtr_mss` is untested.
