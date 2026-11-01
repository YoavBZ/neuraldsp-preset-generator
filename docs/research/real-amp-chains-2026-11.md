# Only captures reach 100 real amp chains

*Research, 2026-11-01, for the ML session; not a declared plan. Public pages only: nothing was downloaded, no account was made and no terms were accepted.*

No open dataset holds 100 real amp chains with a matched DI. Purpose-built DI-plus-real-amp datasets add up to about **12 physical amps**, and only **3 have a mic on the amp** (Guitar-TECHS, already in the project). Band multitracks with mic'd amps are nearly all in use or held out. The only open source with **thousands of distinct real chains** is Neural Amp Modeler (NAM) captures on TONE3000. A capture models one amp at one fixed setting; it is not a recording. But an `amp-cab` pack captures a real amp, cab and mic together, and running the project's own DIs through it gives exactly matched pairs. Each pack's licence fits, but TONE3000's terms forbid bulk download, so the clean route is to ask TONE3000 for research access, which is the user's call. GOAT, already requested, pairs real DIs with about 7,000 captures, but its cab and mic come from Neural DSP IRs. Its "8.5 TB" is a download counter, not its size. For every capture route the main catch is input level, not unknown knobs.

## Recorded datasets stop at about a dozen amps

| Source | Real chains | Amp track | Licence | Size | Catch |
|---|---|---|---|---|---|
| Guitar-TECHS ([site](https://guitar-techs.github.io/), [Zenodo](https://zenodo.org/records/14963133)) | **3** | Small combos, mic'd | CC BY 4.0 | 4.1 GB | Already held; exercises; hum |
| Schmitz & Embrechts ([Zenodo](https://zenodo.org/records/5211257)) | 5 amps × 10 gain steps | Load box, no cab or mic | CC BY 4.0 | 3.0 GB | Short DI |
| Marshall JVM410H ([Zenodo](https://zenodo.org/records/7970723)) | 1 | Preamp or speaker out | CC BY 4.0 | 4.4 GB | No cab or mic |
| ToneTwist AFx ([GitHub](https://github.com/mcomunita/tonetwist-afx-dataset)) | 8, of which 2 not above (HT1, Blues Jr) | Not stated | MIT on GitHub vs CC BY-NC on [Zenodo](https://zenodo.org/records/10796829) | about 50 MB each | Conflict, though both allow non-commercial use: user checks |
| Amp-Space ([HF](https://huggingface.co/datasets/narad/rockingface)) | 2 released; the [paper](https://dafx2020.mdw.ac.at/proceedings/papers/DAFx20in21_paper_47.pdf) describes 15 tube amps | Load box | None stated; gated | not stated | Paper and release disagree: user checks |
| EGDB family ([paper](https://arxiv.org/pdf/2202.09907), [Zenodo](https://zenodo.org/records/19789500)) | **0** | Guitar Rig 5, BiasFX2, Neural DSP | none / CC BY 4.0 | 135.4 GB | Plugins; EGDB already held |
| [EGFxSet](https://zenodo.org/records/7044411), IDMT ([effects](https://zenodo.org/record/7544032), [guitar](https://zenodo.org/record/7544110)), [GuitarSet](https://zenodo.org/records/1422265) | **0** | Pedals, plugins, none, acoustic | CC BY / BY-NC-ND | 1.3–8.2 GB where stated | No amp chain |

Neural DSP's robot-swept Matchless DC-30 set is unreleased ([arXiv](https://arxiv.org/html/2403.08559)). Band multitracks hold roughly **60–100 real amp chains** across 65–75 bands, an estimate, since no session names its amp. Cambridge's readme allows "educational purposes only" ([archive](https://mtkdata.cambridgemusictechnology.co.uk/MTK005/DunningKruger_EnDance_Full.zip)). Almost all are training, test or held-out bands here, and Telefunken sessions share house mics. The Cambridge metal sessions came in on 2026-10-26, and six of their DIs sit at near-zero lag to the amp track, which suggests re-amps or plugin prints ([DI source inventory](di-source-inventory-2026-10.md)).

## TONE3000 has thousands of mic'd rigs and a no-bulk rule

| Question | Answer |
|---|---|
| How many? | **10,197 packs** in the [sitemap](https://www.tone3000.com/sitemap.xml) and "100K models" by July 2025 ([changelog](https://www.tone3000.com/changelog)). Real-amp packs are likely in the low thousands (estimate from pack names). Total size is not published. |
| Licence? | **Per pack**, the creator's choice: T3K, CC variants or CC0 ([API](https://www.tone3000.com/api)). T3K lets users "use the data file in software and publish the resulting outputs" but not redistribute it ([example](https://www.tone3000.com/tones/laney-irt-studio-39500)). |
| Mic and cab? | Amp Head is "Amplifier only"; Amp + Cab is "Mic'd combo amp or amp head with cabinet" ([guide](https://www.tone3000.com/guides/capture-your-gear-with-nam-sweep-method)). |
| IRs paired? | Not with amp-head packs; IRs are a separate format ([API](https://www.tone3000.com/api)). |
| Bulk access? | **Forbidden** by the site [Terms](https://www.tone3000.com/terms) ("a substantial portion of available tones for any purpose") and the [API Terms](https://www.tone3000.com/api/terms) ("Do not bulk download, scrape, mirror, or cache"). |
| Capture audio shared? | **Never**: TONE3000's licence from creators is "limited to internal purposes" ([Terms](https://www.tone3000.com/terms)). |

**Only `amp-cab` packs are real mic'd chains.** An amp-head capture plus a cab IR the project picks is not one. Captures are close copies: after the A2 retrain the library's median error-to-signal ratio is 0.0033 ([A2 guide](https://www.tone3000.com/guides/nam-a2-the-complete-guide)). Unknown knob settings do not matter, because labels come from the search. Input level does. A `.nam` file can store its expected input level ([NAM docs](https://neural-amp-modeler.readthedocs.io/en/latest/model-file.html)), but neither sampled pack had calibration ([1](https://www.tone3000.com/tones/laney-irt-studio-39500), [2](https://www.tone3000.com/tones/bad-cat-jet-black-106905)). Smaller catches: "Convert" models are rebuilt from older models ([A2 guide](https://www.tone3000.com/guides/nam-a2-the-complete-guide)), some old uploads capture software ([example](https://tone3000.com/tones/mesa-mark-ii-c-from-proteus-software-2173)), and paid tones are "coming soon" ([policy](https://www.tone3000.com/guides/tone-sharing-guidelines)).

The plan's line "Bulk-download NAM captures | TONE3000's terms forbid it" still holds. Suggested wording: **"Bulk, scripted or scraped download or caching of TONE3000 captures | Forbidden by TONE3000's site Terms and API Terms (2026-07-07). Each pack's licence (usually T3K) allows using it and publishing renders, so the only routes are access TONE3000 grants on request, or hand downloads within limits the user has checked."** The user decides between emailing support@tone3000.com for research access (cleanest), picking 100–300 packs by hand (the Terms never define "normal human browsing patterns"), or fetching favourites through the free API (possibly the forbidden "cache"). All three need an account.

Other capture libraries are smaller or blocked. GuitarML has 59 amp captures, mostly with no cab, and an unclear licence ([library](https://guitarml.com/tonelibrary/tonelib-pro.html)). IK's ToneNET offers 60,000+ captures through the free TONEX 2 CS plug-in ([SonicState](https://sonicstate.com/news/2026/10/23/ik-multimedia-releases-tonex-free-unlimited/)), but in a closed format, under terms that could not be fully read ([terms](https://www.ikmultimedia.com/legal/terms_and_conditions_template_txc_us.php)); the notes disagree on whether all are free ([IK](https://www.ikmultimedia.com/products/tonex2/)). GitHub re-hosts carry licences picked by the re-hoster ([example](https://github.com/troutstar/NAM_models)). Kemper and Quad Cortex need the hardware ([Kemper](https://www.kemper-amps.com/rig-manager)).

## GOAT pairs real DIs with captures and plugin cabs

GOAT renders **5.9 h of DI covers through about 7,000 NAM profiles from over 1,000 amps** ([paper](https://arxiv.org/html/2509.22655v1)). It is CC BY-NC 4.0, restricted and research only ([Zenodo](https://zenodo.org/records/15690894)), and the user requested access on 2026-10-23. With about 170 items and 29.5 h of amp audio, about five renders each, several hundred distinct captures likely appear (estimate). For T3K profiles, "publish the resulting outputs" supports sharing those renders.

The notes call its cabs "Neural DSP IRs" or "Nolly IRs". The paper settles it: "IRs were used from the NeuralDSP Archetype Nolly plugin". **The cab and mic come from a plugin, not a real mic**, and not one of the project's targets ([README](../../README.md)). The notes disagree on the render design: one random profile per item (paper) or 5 amps × 5 cabs per item ([poster](https://ismir2025program.ismir.net/poster_245.html), per earlier notes); 29.5 h fits five renders per item. The pages read do not say how the profiles were collected, how hot the DI was driven, or whether `amp-cab` profiles also got a cab IR. If they did, those renders have two cabs.

The size was checked on 2026-11-01. Zenodo lists 8.5 TB as "Total data volume" in its statistics, next to 732 downloads. So it is the **sum of all downloads** (about 11.6 GB each), not the archive. The real size is unknown; the earlier 15–25 GB guess is unverified. The project had about 17 GB above its 31 GB floor on 2026-10-30. The file list is hidden, so whether a part can be fetched shows only once access is granted.

## Free IRs and shootouts add cabs, not chains

Free IR libraries cover about 10–20 real cabs. God's Cab has one Mesa 4x12 ([Rekkerd](https://rekkerd.org/signals-audio-releases-gods-cab-1-3-free-ir-library)), Redwirez has one Marshall 1960A with 17 mics ([Rekkerd](https://rekkerd.org/?p=25023)), and Origin has 6 cabs ([SOS](https://www.soundonsound.com/news/origin-effects-launch-free-ir-cab-library)). Celestion's licence bans derivative works ([quote](https://forum.kemper-amps.com/forum/thread/42300-poll-ethics-of-profiling-using-impulse-responses/?pageNo=4)) and Kalthallen's could not be read ([page](https://shop.kalthallen.de/?page_id=423)), so the user checks both. An IR joined to an amp the project picks is not a real mic'd chain. Forum shootouts re-amp one DI through 3–12 amps ([Rig-Talk](https://www.rig-talk.com/forum/threads/high-gain-amp-shootout.178021)), but they are lossy, unlicensed and rarely include the DI: spot checks only.

## Two routes reach 100 chains

| Rank | Route | Real mic'd? | 100+? | Licence | Within terms | Effort | Decides |
|---|---|---|---|---|---|---|---|
| 1 | TONE3000 `amp-cab` packs via a research request | **Yes** (captures) | Yes | Fits | If TONE3000 agrees | Medium: filter, render own DIs | User, TONE3000 |
| 2 | GOAT renders | No: plugin cabs | Likely | Fits | Yes, requested | Low once granted | GOAT's owners (access), user |

## Conclusion

Real recordings at this scale do not exist publicly, so the choice is how much realism to give up. `amp-cab` captures keep the real amp, cab and mic but fix one setting and hide the input level; GOAT also swaps in a plugin's cab. The cheap check is whether a centre learned from capture renders improves the leave-one-out score on the 14 BKS recordings. If too few packs are calibrated, sweep the input level and let the search pick the best one; those sweeps are variants, not new chains.
