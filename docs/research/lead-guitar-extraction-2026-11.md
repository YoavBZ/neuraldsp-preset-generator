# Separate in stereo first, then pick the lead

*Research, 2026-11-14, for the ML session; not a declared plan. Web and repo reading only: nothing was downloaded, installed or run. Tags: **[M]** measured or published; **[C]** community result (model card, forum, service page); **[R]** measured or stated in this repo; **[I]** inferred; **[none]** no evidence found. Builds on `single-guitar-separation-2026-10.md`, `guitar-separation-2026-10.md` and `effects-estimation.md`, and does not repeat them.*

**Answer.** No open model, prompted or not, has been shown to pull one electric guitar out of several [none]. Every one that reports music results selects by class [I from M]. So the lead has to come from a pipeline built on `gtr_mss`, and today's pipeline runs in the wrong order. It masks the whole song to its centre, then separates a mono signal (`centre_mix`, `--version stem_C`) [R]. That mask cuts two equal, overlapping hard-panned rhythm takes by only about 7.4 dB, which fits the user's "Still many leaks though" [I]. It also removes about 80% of the lead's own stereo reverb and delay power [I]. The cheapest decisive test needs no download: run `gtr_mss` on the true stereo song, gate its stereo stem by time-averaged coherence, and compare with today's route [I]. Next come two open lead/rhythm checkpoints (337.1 MB and 109.8 MB) with no licence, no data statement and no metric [M]. They most likely run after `gtr_mss`. SAM-Audio and the other query models rank low. A lead-vs-rest model can be trained on the Mac, but slowly (about 3.5 h per fold per 1,000 steps, estimated) and with a real risk of level collapse [I, R]. A small refinement net on frozen `gtr_mss` is the cheaper way to train [I].

## 1. Separators split all guitars; two untested files claim lead/rhythm

| Model | Guitar SDR, MVSEP | Size | Licence |
|---|---|---|---|
| BS-RoFormer SW | 9.01 [M] | 699.4 MB fp32, 349.5 MB MLX [M] | Unknown [M] |
| X-LANCE `gtr_mss` (current, on the Mac) | 8.60 [M] | 204 MB [R] | MIT card, derived from SW; accepted [R] |
| Mega-53 guitar head (`learn/separate.py`) | 8.25 [M] | 1.37 GB full [R] | MIT repo, weights unstated [M] |
| listra92 Mel-Band RoFormer "Lead-Rhythm Guitar" | None [none] | 337.1 MB [M] | None stated [M] |
| Dry Paint Dealer HTDemucs `lead_rhythm_guitar` | None [none] | 109.8 MB [M] | None stated [M] |

MVSEP's guitar leaderboard is the only public guitar benchmark: 30 one-minute tracks, acoustic and electric pooled ([leaderboard](https://mvsep.com/quality_checker/leaderboard/guitar/?sort=guitar)) [M]. SW leads `gtr_mss` by 0.42 dB [I from M]. On the repo's multi-guitar parts, network swaps gained only +0.3 to +0.4 dB [R]. So a better all-guitar separator will not fix the leaks [I]. No leaderboard scores electric, lead or rhythm guitar alone [M].

The two lead/rhythm checkpoints are new since October. Both are mirrored at [noblebarkrr/mvsepless_resources](https://huggingface.co/noblebarkrr/mvsepless_resources) [M]. Their configs train on "Lead" and "Rhythm" only, with no "other" stem [M]. So they most likely expect a guitar-only input, after `gtr_mss` [I]. Who trained them, on what, and what "lead" means are unknown [none]. MVSep's lead/rhythm service is popular (15,559 uses a month) but publishes no SDR ([MVSep](https://mvsep.com/en/)) [M]. Role labels could split lead from rhythm by register and playing style, but not near-unison doubles [I].

## 2. Prompts pick the class, not the guitar

| Method | Cue | Guitar evidence | Size, licence | Mac |
|---|---|---|---|---|
| SAM-Audio small | Text; "+"/"−" spans | No SDR or guitar figure [none]; listener score on MUSDB stems 4.45 vs Demucs 4.26 [M] | 5.10 GB, gated; accepted 2026-10-20 [M, R] | Official code fails on macOS [C]; "guitar" gave near-silence at about 75× real time [C] |
| Banquet | Audio example | MoisesDB median SNR: clean electric 0.7, distorted 2.4 dB [M] | 0.55–0.77 GB, CC BY-NC-SA [M] | Untested [none] |
| AudioSep and kin | Text | No electric-guitar figure [none]; same listener score 2.0–2.6 [M] | AudioSep 3.62 GB, MIT [M] | Unstated [none] |
| Solo-region adaptation | The song's solo sections | Piano concertos: +1.7 dB average for piano, +4.4 dB at best [M] | None | Own training per song |

No text, audio, span or example prompt has been shown to pick one guitar among several [none]. Banquet's results match within 0.2 dB whether its query clip comes from the same song or another ([Banquet](https://arxiv.org/html/2406.18747v2)) [M]. SAM-Audio's benchmark dropped prompts that could match several look-alike instruments ([SAM-Audio](https://arxiv.org/html/2512.18099v1)) [M]. Its "+" and "−" spans are the only released span cue. A "−" span over rhythm-only bars could tell it which guitar to leave out [I], but that is untested [none]. The seconds must come from the user, since the project never estimates them [R]. SAM-Audio also rebuilds its output with a generative decoder, a risk for tone matching [I].

Test-time adaptation has one music result, and its test mixes were remixes of the same solo sections it trained on ([Özer & Müller 2022](https://archives.ismir.net/ismir2022/paper/000059.pdf)) [M]. The repo found usable solo regions on only 1 of 19 stage-F parts [R].

## 3. Real stereo helps, and the mask belongs after the separator

Today the separator never sees true stereo. Every version is a mono mix, the default `stem` ((L+R)/2) included, which the `gtr_mss` wrapper copies into two equal channels (`XLanceG`) [R]. R1 Amendment 4 (e5f769ed) added the versions to `product_path separate`. The latest main commit, 3fc430ea (2026-11-14), passes `--version` (`stem`, `stem_C`, `stem_L`, `stem_R`, `stem_S`) through `scripts/model_preset.py`, keeps `stem` as the default, and notes in `reference/model-path.md` that `stem_C` "is not yet checked by the score" [R].

Stereo input helps on panned parts. A Wave-U-Net gained 3.2 dB median SDR on accompaniment from stereo input, against 0.5 dB on vocals ([Stoller et al. 2018](https://ar5iv.labs.arxiv.org/html/1806.03185)) [M]. No such test exists for BS-RoFormer or for guitar [none]. Stereo alone does not choose a guitar: without a pan hint, a stereo network scored −2.3 and −3.2 dB SIR on two same-class guitars, and 4.8 and 4.5 dB with it ([SpaIn-Net](https://arxiv.org/pdf/2202.07523)) [M].

| Bin content | Today: psi^4·max(cos, 0) | Coherence gate (proposal) |
|---|---|---|
| Centred lead, alone | Passes [I] | Passes [I] |
| One guitar at pan 0.5 | −12 dB [I] | Cut by a balance window [I] |
| Two equal hard-panned takes, overlapping | Only −7.4 dB [I] | Coherence near 0.3, cut hard [I] |
| The lead's stereo reverb or delay | About 80% of power removed [I] | Also removed [I] |
| Centred keys or snare | Passes [I] | Passes [I] |

The leak has a plain cause. The repo's psi has no time averaging, so it measures only level balance, and two equal independent takes often look centred [I]. Avendano and Jot's ambience extractor averages the cross-spectra over time, with a forgetting factor of 0.90 ([US 7567845](https://patents.google.com/patent/US7567845B1/en)) [M]. Over about 10 frames, two independent takes then give a coherence near 0.3, and a centred source near 1 [I]. A gate on that coherence should reject doubles far better. It is untested on guitars [none], and near-unison takes may stay coherent at low frequencies [I].

Order matters as much as the mask. Masking a stereo guitar stem pits guitar against guitar, keeps the separator in its training domain, and leaves an unmasked stem for the effects route [I]. Mid/side cannot help: hard-panned doubles sit in the mid at full level [I]. gilliaan's learned centre/wide models score 16.45–18.93 dB centre SDR on MVSep's undescribed set ([MVSep](https://mvsep.com/algorithms/125)) [C]. Their "center" means vocals, bass, kick and snare, and they were never tested on guitar ([card](https://huggingface.co/gilliaan/CenterWide-Models)) [C]. No spatial method can split a centred lead from a centred keyboard [I from M].

## 4. A lead-vs-rest model is possible, slow, and prone to collapse

Two designs fit. The cheaper is a small refinement net on frozen `gtr_mss`. It reads the stereo stem, the mix and the repo's centre, coherence and level-difference maps, and outputs a lead mask [I]. It cannot forget the base model, but it cannot beat the stem either, which keeps about 75% of the guitar's wet energy [R]. The stronger is a partial fine-tune or LoRA of `gtr_mss` with two outputs, lead and rest, the lead head started from the stock guitar mask [I].

An untested recipe [I]: the target is a section's labelled lead, wet, at its in-mix gain. The rest always includes that session's rhythm guitars, plus guitars from other sessions in the fold, some rendered with the lead's own preset so timbre alone cannot solve it. Draw the lead from 6 dB below to 12 dB above the rhythms. Mix in true stereo, with lead-centred, same-side and hard-doubled cases; today's `self_built_mix` folds to mono [R].

About 70 sessions sits at the low end of community fine-tunes, which used 97 pairs to 750 songs ([MSST #1](https://github.com/ZFTurbo/Music-Source-Separation-Training/issues/1)) [C]. Their lead audio is uncounted; a guess is 2–7 hours [I]. Synthetic pre-training helps most when real data is scarce: on choral parts it lifted median SDR from 1.42 to 3.73 dB with 10% of a real set ([arXiv 2209.02871](https://arxiv.org/pdf/2209.02871)) [M].

| Option | Rate | Time per fold | Note |
|---|---|---|---|
| `gtr_mss` fine-tune, CPU | 43.3 s per step [R] | 12 h per 1,000 steps [I] | 18.9 GB peak [R] |
| Same, MPS, STFTs on the CPU | About 12.7 s per step [I] | About 3.5 h per 1,000 steps [I] | 21.3 GB at 6-s windows, over the 20 GB cap [R] |
| Refinement net | 850 separations an hour on MPS [R] | Bank of 2k–10k mixes: 2.4–11.8 h; training unmeasured [I] | — |

Two folds double every figure [I]. Level collapse is the main risk. D_F5ft's stems came out at −33 LUFS against stock's −15, about 12 dB low, and lost to stock on 9 of 11 real parts [R]. A published query separator collapses the same way without a level term ([arXiv 2501.16171](https://arxiv.org/html/2501.16171)) [M], and MSST's L1SNR-dB loss is built against it [M]. Unclear "lead" labels act as label noise, which cost 1.42 dB in SDX23, more than bleed's 0.83 ([SDX23](https://arxiv.org/html/2308.06979)) [M]. Split by band, and keep stage F, V-real and sets 4–6 out [R]. On MPS, `torch.stft` gradients are wrong above 65,536 samples, so spectral losses run on the CPU [R].

## 5. Ranked recommendation

Cheapest and most decisive first [I]. The repo's earlier bar for a new stem was about +2 dB project SNR over the current separator before a render test is worth running [R].

| Rank | Test | What it decides | Expected gain | Cost | User's yes? |
|---|---|---|---|---|---|
| 1 | **Stereo-first screen on stage F**, with declared pans (lead centred with hard doubles; ±0.6; same side). Arms: `gtr_mss` on true stereo plus a coherence gate on its stem; the same with today's psi^4 mask; today's `stem_C`; plain `stem` | Whether order and the gate fix the double-track leak, and whether stereo helps `gtr_mss` | Unknown on guitar [none]; up to 3.2 dB from stereo on panned accompaniment [M]; doubles now only 7.4 dB down [I] | No download or training; a few hundred 10-s separations, under 1 h at the repo's 850 an hour on MPS [I from R]; a wrapper change to keep both channels. A borrowed second take flatters the gate [I] | No |
| 2 | **Ear check** of the stereo-gated, `stem_C` and plain arms on the 7 R1 songs | Whether rank 1 holds on real doubles in commercial mixes | Unknown [none]; `stem_C` won 5 of 7 by ear [R] | Minutes of separation [I]; the user's listening | Listening only |
| 3 | **Lead/rhythm checkpoints** on the stereo `gtr_mss` stem: the 19 of 21 stage-F parts with another electric [R], then R1 | Whether any released weights carry role information | Unknown, no metric anywhere [none]; doubles likely stay [I] | 446.9 MB (337.1 + 109.8) [M]; about 1 h [I]; no licence, fine for development [R] | Yes |
| 4 | **Learned centre and keys**: gilliaan CenterWide BS-RoFormer v2, then `gtr_mss` on "center"; `bs_keys_xlancer` as a competing mask | Learned against DSP centre; how much leak is keys | Unknown on guitar [none]; keys model 7.78 dB on MVSEP piano [M] | 204 MB, CC BY-NC-SA 4.0 [C]; 204.4 MB, licence untraced [M]; 1–2 h [I] | Yes |
| 5 | **Refinement net** on frozen `gtr_mss`, stereo lead-vs-rest mixes from ~70 sessions, leads labelled by ear | Whether learned cues beat the gate | Unknown [none]; capped by the stem's 75% wet energy [R] | 2.4–11.8 h bank separation, short training [I]; the user's labels | Yes |
| 6 | **`gtr_mss` lead-vs-rest fine-tune** (partial or LoRA), 1,000-step pilot per fold, checked every 250 steps against silence and stock | Whether a role fine-tune beats rank 5 | Several dB of headroom [I]; choral analogue about 4–6 dB [I from M]; a two-guitar model's weaker guitar near 1.6 dB project SNR [R] | About 7 h for two folds, estimated [I]; over the 20 GB cap at 6-s windows [R] | Yes |
| 7 | **SAM-Audio small** on stage F: text, text + "+", text + "+" + "−" | Whether any prompt carries instance cues | Unknown [none]; near-silence for "guitar" on one Mac [C] | 5.10 GB [M]; a community fork or MLX port [C]; about 13 h per prompt arm [I from C] | Yes |

Not ranked: Banquet and the text models select by class only [M]; solo-region adaptation needs solo regions that stage F rarely has [R].

## Corrections and open decisions

- **The brief's order is reversed.** The repo masks the whole stereo song, then separates mono (`learn/product_path.py` `centre_mix`, lines 59–90; `docs/full-controls-plan.md`, Amendment 4) [R]. No version gives the separator true stereo [R].
- **Round-5 figure.** `docs/research/round-5-guitar-models.md` (line 53) lists "MVSep lead/rhythm guitar 9.0–9.2". MVSep publishes no lead/rhythm SDR [M]. The numbers match the all-guitar leaderboard's top (9.00–9.12) and look mis-attributed [I]. Its "the only lead/rhythm splitter" is out of date too: two open checkpoints exist [M].
- **ML plan §5** still reads "Separators: adapt, don't build" [R]. Ranks 5–6 may need a dated amendment: the ML session's and the user's call.
- **Licences.** MoisesDB and MedleyDB are CC BY-NC-SA, so weights trained on them would be share-alike; MedleyDB is held-out set 6 anyway [M, R]. The plugin EULA on renders as training data is unchecked [none].
- **Effects route.** Both centre masks strip most of the lead's stereo tail [I]. The effects read should keep an unmasked stereo stem whichever stem the amp read uses: an open choice for the ML session.

## Links

- Notes (2026-11-14): four researcher notes files (guitar separators, query-based extraction, stereo and spatial, training a lead separator), kept locally and not committed; the figures above carry their sources.
- Repo (read 2026-11-14, main at 3fc430ea): [learn/product_path.py](../../learn/product_path.py), [learn/direct_stems.py](../../learn/direct_stems.py), [reference/model-path.md](../../reference/model-path.md), [docs/full-controls-plan.md](../../docs/full-controls-plan.md), [docs/trusted-data-t0-design.md](../../docs/trusted-data-t0-design.md), [docs/research/round-5-guitar-models.md](./round-5-guitar-models.md), [docs/research/ml-plan-2026-10.md](./ml-plan-2026-10.md), [docs/research/single-guitar-separation-2026-10.md](./single-guitar-separation-2026-10.md), [docs/research/effects-estimation.md](./effects-estimation.md).
- Checkpoints (sizes read 2026-11-14): [lead/rhythm and keys mirror](https://huggingface.co/noblebarkrr/mvsepless_resources) (337.1, 109.8, 204.4 MB); [xlance-msr](https://github.com/ModistAndrew/xlance-msr); [SW](https://huggingface.co/FractalSurfer/BS-RoFormer-SW-6stem) (699.4 MB); [gilliaan CenterWide](https://huggingface.co/gilliaan/CenterWide-Models) (204–870 MB); [SAM-Audio small](https://huggingface.co/facebook/sam-audio-small) (5.10 GB); [Banquet weights](https://zenodo.org/api/records/13694558) (0.55–0.77 GB each).
- Benchmarks and services: [MVSEP guitar leaderboard](https://mvsep.com/quality_checker/leaderboard/guitar/?sort=guitar); [MVSep lead/rhythm news](https://mvsep.com/news/67?lang=en); [MVSep phantom centre](https://mvsep.com/algorithms/125).
- Papers and reports: [Banquet](https://arxiv.org/html/2406.18747v2); [SAM-Audio](https://arxiv.org/html/2512.18099v1); [SAM-Audio on a Mac](https://gotofritz.net/blog/2026-01-01-can-sam-audio-be-used-to-replace-demucs/); [Özer & Müller 2022](https://archives.ismir.net/ismir2022/paper/000059.pdf); [Wave-U-Net](https://ar5iv.labs.arxiv.org/html/1806.03185); [SpaIn-Net](https://arxiv.org/pdf/2202.07523); [Avendano 2003](https://www.ee.columbia.edu/~dpwe/papers/Aven03-unmix.pdf); [Avendano–Jot patent](https://patents.google.com/patent/US7567845B1/en); [SDX23](https://arxiv.org/html/2308.06979); [choral pre-training](https://arxiv.org/pdf/2209.02871); [level collapse](https://arxiv.org/html/2501.16171); [L1SNR-dB](https://raw.githubusercontent.com/crlandsc/torch-l1-snr/main/README.md); [MSST community fine-tunes](https://github.com/ZFTurbo/Music-Source-Separation-Training/issues/1).
