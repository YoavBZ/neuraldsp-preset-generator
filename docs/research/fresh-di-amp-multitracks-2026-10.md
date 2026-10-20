# Public multitracks cannot triple the fresh test

*Research report, 2026-10-17, for the ML session's request for fresh DI+amp development material. Research, not a declared plan.*

No public source checked here can give the ML session 3–5× its current fresh-song test. That would mean about 63–105 usable parts, against today's **21 parts in 12 bands** (repo `docs/arm-a-mega53-plan.md`, amendment 1). Among the sources that could be checked, the number of never-used, non-metal, clean-to-crunch electric-guitar parts with a same-take DI and amp track is **zero**. The two Cambridge-MT sessions a first pass listed as "genuinely unused" turn out to be used already. The project downloaded **The Long Wait "Drag"** in set 3 and kept no part from it. It downloaded **Peter White "Crazy Girl"** in set 5, and all 5 of its DIs failed the same-take test (repo `docs/validation-set3.md`, `docs/validation-set5.md`). The Cambridge-MT library is the only large real-song source, and the project has already mined almost all of its non-metal DI+amp sessions. The academic datasets either re-index those same Cambridge sessions (Gururani & Lerch: 92 pairs, **0 fresh**), are already in use (MedleyDB is set 6), or are software renders with no band mix. The biggest pool left is the project's own held-out sets 4–6: **39 parts in 11 bands**, which the ML plan reserves for its final step-7 test. Spending them here would cost that test. Real growth needs one of four things: a direct scan of the Cambridge sessions this container could not reach, a paid look at Weathervane's *Shaking Through* archive, a wider scope, or new recordings.

## The project has already used Cambridge-MT's non-metal pairs

The Cambridge-MT "Mixing Secrets" library is still the only real-song source with many same-take DI+amp pairs. A track-name scan covered its **404 rock, indie and pop sessions** and **307 other-genre sessions**. Track lists came from ZIP central directories, the MS500 per-track annotation and the RawStems re-host; no audio was downloaded ([MS500 CSV](https://github.com/felixCheungcheung/mixing_secrets_v2/blob/main/mixing_secret_dataset_annotation_with_comment.csv); [RawStems](https://huggingface.co/datasets/yongyizang/RawStems)). Of the in-scope rock, indie and pop sessions, **86** have any file named as an electric-guitar DI. Every non-metal session that has a name pair is in one of four groups:

- on the exclusion list;
- in the project's validation sets;
- a false pair, such as Tall Heights, whose `Paul-DI` + `Paul Amp` is a cello;
- in the sibling genres, where the pair sessions are again already used.

The naming is consistent enough to trust the scan (`ElecGtr<k>` or `ElecGtr<k>Mic<n>` next to `ElecGtr<k>DI`). But a name pair is not proof of one take. In set 5, the project's waveform test rejected **28 of 59** declared DIs, including all 8 Jeff Hirata "Sunshine" DIs and all 5 Peter White DIs (repo `docs/validation-set5.md`).

Checks against the repo:

- **Already used:** Chris Coltraine is set 1 ("Heather Jane" is development; "That's How I Got To Memphis" is held out and used in four declared tests, per `held_out_uses` in `docs/validation-datasets.json`). Hazael's two songs are set 5.
- **Not fresh after all:** the two remaining "unused" finds are also in the repo, with zero usable parts between them (see above).
- **Never used, but excluded twice over:** Umphrey's McGee "Crucial Taunt". It is a Telefunken session, and its "DI" is a Palmer PDI-09 speaker-sim line-out placed after the amp, not a clean DI ([MS500 CSV](https://github.com/felixCheungcheung/mixing_secrets_v2/blob/main/mixing_secret_dataset_annotation_with_comment.csv)).

The academic "Mixing Secrets" dataset tells the same story. Gururani & Lerch's YAMLs keep the original Cambridge filenames. They yield about **92 DI+amp parts in 25 songs** (about 19 labelled clean) ([paper](https://musicinformatics.gatech.edu/wp-content_nondefault/uploads/2017/10/Gururani_Lerch_2017_Mixing-Secrets.pdf); [metadata](https://github.com/SiddGururani/mixing_secrets/tree/master/metadata)). Checked against the repo, **every one of the 25 songs** is already used or excluded:

- **In the label table or development ledger:** Atlantis Bound, Diesel13, Zeno, both Travelling Band songs, Timo, Wall Of Death, Death Of A Romantic and Hollow Ground.
- **In sets 1–2:** Boogiesnakes, Forkupines "Semantics", North To Alaska and Tim Taler.
- **In set 3:** both Dunning Kruger songs, Scott Elliott, Cnoc An Tursa and The Long Wait.
- **In set 4:** Decypher, Last Legacy, Lead Inc and The Black Crown.
- **In set 5:** Ronnie Jones, BKS and Chris Durban.

Several of these are also MUSDB18 songs. **Fresh pairs from that table: 0.**

Metal is the one large never-used pool. About **9 sessions with about 70 pairs** (Peppermark ×2, Serapis ×2, V.M.GY "Equilibrium"/"Purgatory" (new songs, but V.M.GY is already a set-3 held-out band), Daimon B, Inhumanity Vortex, Arcadian Alone) are available only if heavy styles come into scope.

## Earlier validation sets hold 73 named pairs, mostly locked as held-out

The rock/pop scan treated sessions in sets 3–5 as used. Those **16 sessions (about 73 named pairs; 15 sessions and about 71 pairs without the Telefunken-sourced "57 Chevy")** form a separate tier: they appear in earlier validation sets but not in the label table. A grep of `docs/label-table-parts.json` and `docs/dev-test-ledger.json` finds **none of them in either file**. So none has been a development test. Their status comes from the held-out rules instead, and whether any counts as "fresh" is **the ML session's call** under the ML plan. That plan says "the held-out sets stay untouched until step 7", and step 7 spends set 4's unused parts, set 5 and set 6 (repo `docs/research/ml-plan-2026-10.md`).

| Session (repo set) | Named pairs | Kept in-scope parts (project's same-take + crop rules) | Status in repo | Size / route |
|---|---|---|---|---|
| Ronnie Jones – Why Don't You Stay (5) | 10 | 9 (8 clean, 1 crunch) | held out, unused; step-7 reserve | 770 MB [direct](https://mtkdata.cambridgemusictechnology.co.uk/MTK012/RonnieJones_WhyDontYouStay_Full.zip) |
| Hazael – A Mi Lado / Resistencia (5) | 3 + 2 | 2 + 2 clean | held out, unused; step-7 reserve | ≈286 / ≈373 MB, challenged host |
| Saturn Syndicate – Never Leave The Night Alone (5) | 6 | 2 crunch (+1 high-gain) | held out, unused; step-7 reserve | ≈508 MB via Wayback |
| The Ferryboat Men – Winds Of Gypsy Moor (5) | 3 | 1 crunch | held out; re-host tracks don't share a timeline | RawStems re-host |
| Fytakyte – Too Much (5) | 2 | 1 crunch | held out; re-host | RawStems re-host |
| Jeff Hirata – Sunshine (5) | 8 | **0, all 8 failed the same-take test** | held out | RawStems re-host |
| Nova-One Studio – Four Graham (5) | 5 | 0 in scope (4 high-gain) | held out | ≈303 MB |
| Sonnet & Alcohol – Back To The Nineties (4) | 2 | 2 clean | held out, unused; heavy bleed ("Only DI.wav are clean") | 460 MB via Wayback |
| Lead Inc – The Inner Circle (4) | 3 | 2 crunch (+1 high-gain) | **spent** by the set-4 confirmation test (one of set 4's first five sessions) | ≈1,377 MB |
| The Laminar Flow – Headspace (4) | 11 | 1 crunch (+2 high-gain; 7 cut by the window rule, 1 failed the waveform test) | held out, unused | 1,278 MB via Wayback |
| The Bright Star Alliance – Error 404 (4) | 7 | 1 crunch (+6 high-gain) | held out, unused | ≈663 MB via Wayback |
| Silona – Learning How To Fly (3) | 6 | 3 clean | **spent**: "excluded from further tuning, training, or confirmation" | 1,407 MB [direct](https://mtkdata.cambridgemusictechnology.co.uk/MTK021/Silona_LearningHowToFly_Full.zip) |
| Dunning Kruger – EnDance / Japan Song (3) | 2 + 1 | 1 + 0 clean | **spent** (same ledger) | 381 / 447 MB [direct](https://mtkdata.cambridgemusictechnology.co.uk/MTK005/DunningKruger_EnDance_Full.zip) |
| Rebecca Haviland – 57 Chevy (1, Telefunken route) | 2 | 2 | **excluded** (Telefunken source); held out, used in four declared tests | Telefunken S3 |

Sources: kept counts are from repo `docs/validation-set3.md` (Silona, Dunning Kruger), `docs/validation-set4.md` and `docs/validation-set5.md`; the spent status is from `docs/set3-heldout-use-ledger.json`, and Lead Inc's from `held_out_uses` in `docs/validation-set4.json`; pair names are from the [archive central directories](https://mtkdata.cambridgemusictechnology.co.uk/MTK012/RonnieJones_WhyDontYouStay_Full.zip). Two more sets are not in the table. Set 5 also holds **BKS "Too Much" and "Bulldozer"** (9 in-scope parts), but both are MUSDB18 songs. Chris Coltraine "Heather Jane" (set 1 development) has **5 named pairs, of which 2 pass the same-take test** (ElecGtr1 and its double, one tone). It is in neither the label table nor the ledger, but it was already used in the recordings benchmark (repo `docs/tone-matching-plan.md`), so it would be a repeat use, and its band's other song is held out.

The arithmetic is plain. The ML plan's step-7 pool is **39 parts in 11 bands** (set 4 unused 10, set 5 26, set 6 3). Adding all of it to today's 21 parts gives about **60 parts, under 3×**, and leaves no final held-out test. The set-5 figure of 26 includes BKS's MUSDB18 songs. Without them, set 5 gives **17 parts in 5 bands**. Set 4's 10 unused parts are Umbriferous's 6 crunch parts (a metal-genre session, so it is left out of the table above), Sonnet & Alcohol's 2, and one each from The Laminar Flow and The Bright Star Alliance. Lead Inc and Last Legacy were spent by the set-4 confirmation test. (The ML plan counts the pool as 11 bands; `docs/validation-set5.md` gives set 5 six bands, which would make 12.)

## Other public sources add little, and none is a real song test

Outside Cambridge-MT, this search found no free source with documented same-take DI+amp guitar pairs across many bands:

- **Weathervane *Shaking Through*** is the only plausible candidate. It has 50+ professionally engineered indie/rock episodes, with "multi-track raw audio and stems" for members ([Weathervane (snippet)](https://weathervanemusic.org/shakingthrough/remix)). But DI presence per episode is **unverified**, back-catalogue access costs **$8/month or $80/year** ([membership (snippet)](https://weathervanemusic.org/membership)), and the terms conflict. They reportedly apply "Creative Commons Attribution-NonCommercial 4.0" to personal-use downloads, yet also say "You may not reproduce any of it without getting our written permission!" ([Terms (snippet)](https://weathervanemusic.org/termsofuse)).
- **The Stairway Project** gives one DI folder plus printed amp tracks, but it is a Led Zeppelin cover with no licence ([site](https://thestairwayproject.com/?p=528)).
- **LEWITT challenges** do not document DI tracks ([myLEWITT](https://my.lewitt-audio.com/downloads)).
- **Metal-only:** the Ultimate Metal DI list and URM/Nail The Mix.
- **No DI+amp pairs:** the NIN remix stems, Converse Rubber Tracks and NAM/TONE3000.

Among the general research multitracks, **MedleyDB** (CC BY-NC-SA 4.0, gated on Zenodo) never marks a DI ([description](https://medleydb.weebly.com/description.html); [Zenodo](https://zenodo.org/records/1649325)). The project has already used it as set 6, where the user's ear-labelling gives just 3 in-scope crunch parts in 2 bands (repo `docs/validation-set6.md`). **MoisesDB** (240 songs, CC BY-NC-SA 4.0) keeps individual tracks per stem, but nothing documents a DI, so pairs would have to be found by inspecting the audio ([paper](https://arxiv.org/html/2307.15913); [repo](https://github.com/moises-ai/moises-db)). The Open Multitrack Testbed was down (HTTP 503) and mostly indexes the same Cambridge archives.

The purpose-built datasets are renders or single notes, so they can serve as **known-target tests, not fresh-song tests**:

| Dataset | What it is | Licence / size | Possible use here |
|---|---|---|---|
| EGDB-NDSP | EGDB DI performances rendered through Neural DSP presets in 3 gain groups (e.g. Asato Vintage Clean, Tone King; Plini Crunch, Henson Pink) | CC BY 4.0; open on [Zenodo 19789500](https://zenodo.org/records/19789500), one 135.4 GB FLAC archive shared with EGDB-PG | Known-preset recovery on real played DI, no mix ([project page](https://ss12f32v.github.io/Guitar-Transcription-with-Amplifier/)) |
| EGDB-PG | Same DI through BiasFX2, 256 presets: 96 low-gain, 64 crunch, 96 high-gain; 514 h | CC BY 4.0, same archive ([arXiv](https://arxiv.org/html/2504.07406v1)) | Gain-class labels for clean/crunch training |
| GOAT | 5.9 h DI covers rendered through ~7,000 NAM profiles + Nolly IRs | Research use, by request ([arXiv](https://arxiv.org/html/2509.22655v1)); the ML plan records it as CC BY-NC and says "not now" | Training bank, no real amp |
| ToneTwist AFx | Dry/wet through real analog amps (Blues Jr, Engl Retro Tube 50, Mesa) | MIT on [GitHub](https://github.com/mcomunita/tonetwist-afx-dataset); the repo records the Zenodo data as CC BY-NC 4.0 and has used it for gain calibration | Real-amp capture checks, test material only |
| EGFxSet | Strat single notes through 12 hardware pedals | CC BY 4.0, 5.8 GB ([Zenodo](https://zenodo.org/records/7044411)) | Pedal checks only |

**Licence summary.** The Cambridge readme grants use "for educational purposes only, and the material contained in it should not be used for any commercial purpose without the express permission of the copyright holders" ([EnDance archive](https://mtkdata.cambridgemusictechnology.co.uk/MTK005/DunningKruger_EnDance_Full.zip)). The Telefunken readme adds "home studio use and for educational purposes only… Any commercial use or reuse is strictly forbidden", with a required attribution line ([Crucial Taunt archive](https://mtkdata.cambridgemusictechnology.co.uk/Telefunken/UmphreysMcGee_CrucialTaunt_Full.zip)). The FAQ is known only from a search snippet: it calls research use within "the general spirit of educational use" but "not specifically agreed with contributors" ([FAQ](https://cambridge-mt.com/ms3/mtk-faq/)). **No CC licence and no explicit research or ML permission was found on any Cambridge session.** MedleyDB and MoisesDB are CC BY-NC-SA. Non-commercial data was allowed then "only with the user's yes"; since 2026-10-20 the ML plan allows it, and the user said yes to training on Cambridge-MT audio.

## Realistic routes, ranked by usable pairs per effort

Every route is small. The list runs from cheapest per usable part to most expensive:

| # | Route | Likely usable in-scope parts | Effort | Catch |
|---|---|---|---|---|
| 1 | Decide whether sets 4–6 (and Heather Jane) count as fresh | up to 39 (17 from set 5 without BKS) + Heather Jane 2 (one tone) | none: crops already on disk | Uses up the step-7 held-out; Heather Jane is a repeat use |
| 2 | Local session lists the Cambridge sessions this container could not reach | unknown; likely a few | about 1–2 h in a real browser | Cambridge readme terms; same-take test will reject some |
| 3 | DI-only fresh Cambridge sessions re-amped through the project's own plugins | Strobe "Maya" 4, The Apprehended 3, MekaPhil (4 songs), The Timezone "GOTGF" 4 | low | Known-target test, not a real amp; none is in the repo, but "The Timezone" may be the label table's Timo And The Timezone (unchecked) |
| 4 | EGDB-NDSP as a known-preset test | many clean/crunch renders | 135 GB download | No song or mix context |
| 5 | Weathervane *Shaking Through*: one paid month to read track sheets, plus an email to confirm the licence (user: no, 2026-10-20) | 0 to a few dozen, unverified | $8 + a day of checking | Conflicting licence; DI presence unknown |
| 6 | Widen scope: metal sessions, or each mic or `DT` double as its own unit | about 70 metal pairs in ~9 sessions | medium | Out of the current style scope; doubles are not independent bands |
| 7 | Record new DI+amp material | as many as recorded (for example 10 players × 5 parts) | high | The only route that reliably reaches 3–5× |

For route 2, the ML session runs on the user's own machine, which can open cambridge-mt.com directly (a 2026 downloader confirms the site needs a real browser to pass Cloudflare, [giacecco](https://github.com/giacecco/cambridge-mt-downloader)). It should list the tracks of these sessions itself:

- **Sessions with no indexed track list,** none of them found in the repo: Redwood "Smoker And The Stoner", Paul Smith & 8 Days A Week Studio "The Weight", Escarràs "No Limits", Xarxa "Cors Desbocats", Mady & Seus Namorados "Pirarucumbia", Hazael "Amor Que Lucha" and "Esto Se Llama Vivir", Mikaela Davis & Southern Star "Cinderella" and "Home In The Country", Mipso "Wallpaper Baby", Erocy "Phantom", FriendZWorldMusic "Triba/Bao Kuku", Masé Jara "Petit Abisme" and Eddie Garrido "A Cry For Normalcy". Swatkins is already in the label table, and Big Head Todd is a Telefunken session, so both are left out.
- **Rock sessions the scan missed:** Perpetual Escape "Into My Dreams" (about 3.2 GB), and Daimon B "Collide" and "Crying Rivers" (metal).
- **Every session added since about mid-2025,** which no snapshot covers ([scraper CSV](https://github.com/sai-soum/cambridge-mt_scrapper/blob/HEAD/data/multitrack_website/metadata_with_fine_genre.csv)).

Two warnings apply to any pairs that turn up. First, run the project's waveform same-take test on every pair. Second, prefer the publisher archives over RawStems, because the set-5 re-host tracks did not share a timeline.

**Recommended acquisition order:**

1. Ask the ML session and the user to rule on sets 4–6 and Heather Jane.
2. Run the local Cambridge listing.
3. Pull any fresh pairs it finds.
4. ~~Buy one Weathervane month~~ (declined by the user, 2026-10-20).
5. Only then decide between widening the scope and recording new material.

## Conclusion

The bottleneck is no longer finding sources. The public supply of real, same-take, non-metal guitar DI+amp parts has been nearly used up by this project's own sets 1–6. After honest exclusions, about **0 parts** are confirmed fresh. A local scan of the unchecked Cambridge sessions might add a handful, and Weathervane is a gamble of unknown size. The true trade-off is internal: the only quick way to grow the test is to spend the 39-part held-out reserve, which still gives only about 60 parts (under 3×) and loses the final test.

If 3–5× really matters, the dependable path is to record it. New DI+amp takes from many players, on clean, edge-of-breakup and crunch amps, mixed into simple backing tracks, would give fresh bands under a clean licence. Purpose-built renders such as EGDB-NDSP can support that work as known-target checks, but they cannot stand in for real songs.
