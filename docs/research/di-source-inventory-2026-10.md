# Clean guitar DIs to widen the direct model's training set: an inventory

*Research report, 2026-10-22. Zero compute: no audio or archive was downloaded, nothing was
rendered or separated. Local facts come from the stored inventory, manifest and pool files; outside
facts from dataset pages, papers, the Telefunken "Live From The Lab" (LFTL) pages, the Hugging Face
re-host's file listing and archived Cambridge-MT pages. Research, not a declared plan.*

Tags: **[V]** verified at the source in this session; **[P]** this repo's committed docs or stored
files (`~/ndsp-presets/learn/clean-di/`, `~/ndsp-presets/learn/pretrain-set/pool.json`);
**[U]** a search snippet, an estimate or an inference.

## Bottom line

- **Nothing on disk can add a new band to the direct model's training set without spending a test
  or a held-out set.** Every local DI is in one of four places:
  - in the pool;
  - locked as a test: stage F's 12 bands, V_dev's 5 and part B's 3;
  - held out: sets 1–6;
  - screened or set aside: Guitar-TECHS for hum, "Sascha" because its band is held out, "Crucial
    Taunt" because its DI comes after the amp, Timo And The Timezone as a B2 candidate, and
    EGFxSet and ToneTwist, which are notes or capture inputs.
- **The pool is short of exactly what the tests ask for.** Of the 277 training sections [P]:
  - 135 come from high-gain DIs or a melodic death metal session;
  - 96 of the 97 clean-class sections are one band, Eggy;
  - 1 is crunch-class.
  - Part C's learning curve flattened, and drawing the same number of renders from half the
    sections was worse (one seed) ([pretrain-set results](../pretrain-set-results.md)). So new
    clean and crunch bands are the lever.
- **The best outside source is Telefunken LFTL sessions this project never downloaded:**
  - **2 whose mic charts list a direct box on the electric guitar:** Jen Hartswick & Nick
    Cassarino (4 songs) and Uglybraine (1 song), 1.9 GB [V].
  - **2 whose charts list an "Acoustic Guitar" direct box:** Melt (1 linked song) and Braiden
    Sunshine (4 songs), 7.7 GB [V]. In the project's own Catbite and Wild & Co sessions, that
    "Acoustic Guitar" box is the electric guitar's same-take DI [P]. So these probably hold one
    too [U].
  - **5 more** list no direct box at all, so a DI there is unlikely (23.6 GB) [U].
  - They are new bands with live backings and same-take amp microphones. Their styles look clean
    to crunch, but that is not yet checked [U].
  - So they could also be **fresh DI+amp test bands**. The October multitrack search
    ([report](fresh-di-amp-multitracks-2026-10.md)) found no fresh pair at all.
- **Ranked additions:**
  1. the first four Telefunken sessions (two of them probable);
  2. the Cambridge DI-only sessions Strobe "Maya" and MekaPhil ×4 (parked as part B2 candidates);
  3. EGDB's DI folder (1 player);
  4. GOAT (5.9 h, needs an access request);
  5. a zero-download swap: once fresh test bands exist, stage F's bands could train. That adds 284
     already-screened sections in 10 bands, 123 of them clean-class.

## Where the training set stands

The direct model trains on part C's sections from bands that are not stage F, V_dev, known-answer
or reserve bands: **277 sections in 9 bands** ([plan](../direct-model-stems-plan.md)) [P].

| Group of the clean DI library | Bands | DIs | DI audio | Clean 10-s sections, non-overlapping | Role today |
|---|---|---|---|---|---|
| Direct model's 9 train bands | Ale Lak, Death Of A Romantic, Eggy, Hollow Ground, Rebuild The Evil, Renesans, Starnes And Shah, Storm Of Particles, The Long Wait | 36 | 121 min | 280 (277 in the pool) | training |
| V_dev bands | Adam Buckley, Cnoc An Tursa, Dark Ride, John Morgan Kimock, Swatkins | 24 | 102 min | 55 | validation; 4 are the sound gate's R_in |
| Stage F bands | Atlantis Bound, Bernard Purdie Tribute All-Stars, Diesel13, Dom McLennon, Doom Flamingo, Eat The Feeder, Magician's Nephew, Szymon Skiba, The Travelling Band, Turbosauro, Wall Of Death, Zeno | 77 | 267 min | 401 (294 outside the stage F parts' own DIs; 284 of those in part C's pool) | the fresh-song test (21 parts); part C trained on their other DIs |
| Known-answer bands | Chris Coltraine, Rebecca Haviland, The Apprehended | 12 | 52 min | 69 | part B's test |
| Timo And The Timezone | 1 band | 1 | 2.5 min | 2 | left out as a B2 candidate |
| Guitar-TECHS P1, P2 | 2 players, no band | 87 | 265 min | 1 | left out by source (hum) |

- **Gain class of the 277 sections** [P]:

  | Class | Sections |
  |---|---|
  | High-gain | 111 |
  | Clean | 97 (96 of them Eggy) |
  | Crunch | 1 |
  | Unclassed | 68, of which 24 are Storm Of Particles (melodic death metal) |

  Today's checks score clean and crunch parts only.
- **Clean minutes per DI minute:** Telefunken DIs give 0.39, Cambridge DIs 0.21 and Guitar-TECHS
  0.001 [P]. Hiss flags more of Cambridge's lost windows than hum (770 against 386). Telefunken's
  are about even (394 against 382), and Guitar-TECHS loses almost everything to hum [P].
- **Screened out, inside the train bands:**
  - Of 793 overlapping activity windows, 185 carry only a hiss flag and 91 only a hum flag [P].
  - In the library, Starnes And Shah (5 DIs) keeps 4 sections and The Long Wait 1; nearly all
    the rest are lost to hum. In the pool, Starnes And Shah has 1, because the hum audit dropped 3.
  - Starnes And Shah has clean and crunch DIs; The Long Wait is unclassed country rock. The two
    blind listening pages that could move these screens still wait for the user
    ([results](../clean-di-library-results.md)).

## The inventory

"Already used" names the step or set. "Conflicts" means it would collide with a test, a held-out
set or a declared reservation. Sizes are archive sizes.

### On disk

| Source | What it holds | EG DI: hours; songs / players / bands | Genre fit | Licence | Local path | Already used? | Conflicts | Size | Quality notes |
|---|---|---|---|---|---|---|---|---|---|
| Clean DI library, 9 train bands | DI + amp/mic + full multitrack (session backing) | 2.0 h; 13 songs / 9 bands [P]; players not counted | poor: 49% high-gain or metal, clean = Eggy [P] | Cambridge "educational purposes only"; Telefunken home-studio and educational use [P] | `references/datasets{,-set3}/` | part C; direct model (277 sections) | none | in place | hum and hiss screened; bleed mostly "partial" [P] |
| Library, stage F bands | same | 4.5 h; 20 songs / 12 bands [P] | good: 123 clean-class + 7 crunch of the 284 sections [P] | same | same | part C trained on 243 of the 284; stage F test | **stage F is the fresh-song test of record** | in place | as above |
| Library, V_dev and known-answer bands | same | 1.7 h, 5 bands; 0.9 h, 3 bands [P] | mixed (Cnoc An Tursa and Dark Ride are metal) | same | same | V_dev, R_in; part B1 | **validation and known-answer tests** | in place | Rebecca Haviland almost all hum (1 clean section) [P] |
| Train-band DIs lost to screens | DI | 3 DIs lose every window to the screens, and 1 has no activity window; 276 windows flagged for hum or hiss only [P] | Starnes And Shah is clean and crunch | same | same | no | none | 0 | the listening pages may return some (e.g. Prodigal ElecGtr1: 18 sections before amendment 3, 1 after) |
| Guitar-TECHS P1, P2 | DI + amp mic, no band | 4.4 h; exercises (chords, scales, techniques) / 2 players [P] | no music | CC BY 4.0 [V] | `references/datasets/guitar-techs/` | the older DI pool (`learn/di_pool.py`) | none (P3, another player, is held out) | 6.1 GB | 60-Hz hum 40 dB over its neighbours; 1 clean section in 2,327 [P] |
| Guitar-TECHS P3 | DI + amp mic | 8 min; 12 solos / 1 player [V] | clean (Orange CR-12) | CC BY 4.0 | same | held-out tests | **4 excerpts held out; P3 never used** [P] | 240 MB | — |
| Dunning Kruger "Sascha" | full multitrack, DI-only part | 4.0 min; 1 DI (Gtr8DI) [P] | likely clean indie [P] | Cambridge | `references/datasets-set3/cambridge/` | set 3 catalogue | **band is set-3 held-out, spent** | 1.0 GB | no amp track [P] |
| Umphrey's McGee "Crucial Taunt" | multitrack | its "DI" is a Palmer PDI-09 after the amp [P] | — | Telefunken | same | no | — | 1.2 GB | not a raw DI |
| "Keys GTR" DIs (Hikikomori, New One, Procession) | multitrack | 5 files [P] | unknown | Telefunken | `references/datasets/telefunken/` | no | John Morgan Kimock is a V_dev band | in place | instrument unverified |
| ToneTwist DRY | DI-like capture inputs | about 11–15 min unique locally; about 27 min guitar overall, mostly IDMT and NAM inputs [P, V] | exercises | CC BY-NC 4.0 | `references/datasets-set3/tonetwist/` | gain calibration | set 3 declares it calibration only | 627 MB | not musical, no backing |
| EGFxSet Clean | DI single notes | 57 min; 1 Strat [V] | notes only | CC BY 4.0 | `references/datasets/egfxset/` | shipped riffs | none | 477 MB | too short for 10-s sections |
| Held-out sets 4–6 (set 6 is MedleyDB); sets 1–3's held-out sessions sit beside the library | multitracks | — | — | — | `references/datasets-set4`, `-set5`, `-medleydb` | held out for step 7 | **never for training** | 32 GB (sets 4–6) | — |

### Not on disk

| Source | What it holds | EG DI: hours; songs / players / bands | Genre fit | Licence | Already used? | Conflicts | Download | Quality notes |
|---|---|---|---|---|---|---|---|---|
| **Telefunken LFTL, chart lists an electric-guitar DI box:** Jen Hartswick & Nick Cassarino (S4, 4 songs), Uglybraine "Sometimes" (S3) | DI + amp mic + full live multitrack (session backing) | about 5 DIs [U]; 5 songs / 2 bands [V] | jazz/soul, funk/jazz-rock: clean to crunch [U] | home-studio and educational use only, attribution line [V] | no (not in any set, ledger or `learn/` code) | none | 0.94 + 0.92 GB on Telefunken's Amazon S3 buckets [V] | TDA-1 box [V]; live room, so check bleed; 12 of the 28 local Telefunken DIs are hum-flagged, 6 in every window, and 27 of 28 read 60-Hz mains [P] |
| **Telefunken LFTL, chart lists an "Acoustic Guitar" DI box:** Melt (S9, 1 of 3 songs linked), Braiden Sunshine (S8, 4 songs) | full live multitrack; probably an electric DI | about 5 DIs if so [U]; 5 songs / 2 bands [V] | indie soul; rock/soul [U] | same | no | none | 1.84 + 5.86 GB [V] | In Catbite (2 songs) and Wild & Co "Past Dues", the chart's "Acoustic Guitar TDP-1" is the electric guitar's same-take DI (pairing with the amp 0.85–0.98) [P]. Mipso's is a real acoustic [P]. A file listing decides. |
| Telefunken LFTL, no DI box on the chart: Ryan Montbleau (S9, 3), Jeffery John Band (S8, 4), Jelly (S8, 1), Kat Wright (S4, 4), West End Blend (S4, 4) | full live multitrack; amp mics only | DI unlikely [U]; 16 songs / 5 bands [V] | singer-songwriter, blues rock, soul, funk [U] | same | no | none | 23.6 GB [V] | The one local session with such a chart, Mikaela Davis, has no DI [P]. West End Blend's S5 song lists a TDP-1 box, but its archive returns HTTP 403 [V]. |
| Telefunken LFTL, new songs of known bands: Bernard Purdie & Friends "It's Your Thing", John Morgan Kimock "Negative Space > Speed", Briana Maia "Over You", Wild & Co ×2 | full multitrack with DI | 5 songs [V] | clean/crunch | same | no | **stage F band, V_dev band, set-2 held-out band ×2** | 1–2 GB each | — |
| **Cambridge DI-only: Strobe "Maya", MekaPhil ×4** | full multitrack; DI-only guitar parts | 18 DI files, about 12 parts; 5 songs / 2 bands [V] | pop/electronica; anime alt rock (gain unknown) | Cambridge "educational purposes only" [V] | no | **part B2's proposed known-answer songs (parked)** | 0.40 + 1.99 GB [V] | MekaPhil's publisher host is behind Cloudflare; the Hugging Face re-host has it, but set 5 found re-host tracks trimmed to different lengths |
| Cambridge DI-only: The Timezone "GOTGF" | full multitrack, 4 DIs | 4 DIs; 1 song [V] | funk | same | no | **it is Timo And The Timezone** (same SoundCloud) [V], a B2-candidate band left out of part C | 616 MB | — |
| Cambridge DI-only: Perpetual Escape "Stop And Rise" | full multitrack, 11 DI parts in 19 files | 1 song / 1 band [V] | progressive heavy rock: likely out of scope [P] | same | no | B2 candidate | 657 MB | gain unknown until heard |
| Cambridge: Hollow Ground "Left Blind" | DI-only, 3 DIs + lead | 1 song [V] | heavy | same | no | MUSDB18 train; band already trains | — | adds no band |
| Cambridge, added since 2025: Blue Manic "Acomatay" (DI + amp), DGX "Rest In Hell" (4 DIs), Slimy Soul Suckers "Big Bang", Prusinski "80s Rocker", Hollowstate "Hurricane" | multitracks | DI confirmed only for the first two [V, partial re-host] | stoner rock; unknown; blues rock; MOR rock; hard rock | same | no | none known | about 1–1.3 GB each [U] | site behind Cloudflare; needs a human pass |
| Cambridge metal sessions with DIs (Arcadian Alone, Daimon B, Inhumanity Vortex, Peppermark ×2, Serapis ×2, SkalyVan ×3, Szymon Skiba "Trashy Thrash") | DI + amp or DI-only | about 80 DI files [V] | **metal: out of scope** | same | no | Szymon Skiba is a stage F band | — | — |
| **EGDB** | DI only (plus amp renders) | 1.97 h; 240 clips / 1 player / 1 Strat-type [V, U] | solo, arpeggio and comping, various genres [U] | none stated, "feel free to use" [V]; the Zenodo copy is CC BY 4.0 [V] | arm A literature only | none | about 0.6 GB DI folder [U]; 1.04 GB CC BY zip [V] | played to a click; hex pickup for labels; DI box vs hex sum unclear [U] |
| **GOAT** | DI only (plus NAM and Guitar Pro renders, tabs) | 5.9 h; 172 cover songs / authors + 2 creators, no performer IDs / 4 guitars (Strat 235 min) [V] | covers; some "rock/metal"; share unknown [V, U] | CC BY-NC 4.0, restricted: request on Zenodo, "research purposes only" [V] | no (ML plan: "not now") | none | 15–25 GB [U] | no backing [V] |
| GuitarJam (Hugging Face) | DI only | 2.5 h; 580 × 15-s monophonic improvisations / 1 Strat, players unstated [V] | single-note lines only | CC0 [V] | no | none | 796 MB [V] | no chords; no backing |
| IDMT-SMT-Guitar | DI, mostly notes and licks | about 15–20 min of short pieces (subsets 3–4) [U] / 7 guitars [V] | genre-tagged short pieces | CC BY-NC-ND 4.0 [V] | via ToneTwist | none | 1.33 GB [V] | ND: re-rendering makes derivatives, a question for the user |
| Five guitar | line out after the amp's preamp | 6 covers × 3 electrics / 1 player [V] | clean jazz amp | CC BY 4.0 [V] | no (ML plan: yes if a true DI) | none | 730 MB [V] | **not a true DI**: the DV Mark line out carries its EQ and reverb [V] |
| EG-IPT | DI + 5 mics, isolated notes | 4.7 h per signal / 1 player / 1 SG [V] | notes only | CC BY 4.0 [V] | no | none | 23.8 GB [V] | no phrases |
| GuitarSet | hex pickup + mic on an **acoustic** guitar | 3 h / 6 players [V] | out | CC BY 4.0 | no | none | 8.2 GB | not an electric DI |
| MedleyDB | raw multitracks, no DI flag | 196 songs; set 6 holds 73 [V, P] | — | CC BY-NC-SA, gated [V] | set 6 | **held out (set 6)** | — | DI role only by ear (crunch, high-gain) [P] |
| MoisesDB | stems; clean or distorted electric guitar labels | 240 songs / 47 artists [V] | — | CC BY-NC-SA 4.0 [V] | no | none | not stated | no DI label; guitars arrive as recorded through amps [U] |
| Slakh2100 | synthetic multitracks | 145 h synthetic [V] | synthetic guitar: out | CC BY 4.0 [V] | no | none | 104 GB FLAC [V] | a backing source only (drums, bass, keys) |
| SynthTab | plugin-rendered "clean DI" from tabs | 2,793 h electric clean [V] | synthetic | CC BY-NC 4.0 [V] | no | none | about 2 TB [V] | 82.9% of electric songs carry a render bug [V] |
| Free multitrack sites: Produce Like A Pro (email-gated), SOS Mix Rescue, myLEWITT, ccMixter, forum contests | multitracks | no guitar DI documented [V, U] | — | various, mostly practice-only | no | none | — | not worth a scan before the Telefunken listing |
| Weathervane *Shaking Through* | raw multitracks | unknown | indie | paid membership | — | **declined by the user (2026-10-20)** | — | — |

## Which sources come with a backing

- **Session backing (realistic mixes):** every Telefunken and Cambridge session (the library, the
  new Telefunken sessions, Strobe, MekaPhil, The Timezone, Stop And Rise, the post-2025 Cambridge
  sessions). Part C's `backing_tracks` rule applies unchanged: the mix list, less the part's own
  tracks, every DI and the leaking tracks [P]. For the re-hosted MekaPhil, check first that the
  tracks share one timeline.
- **Synthetic or borrowed backing needed:** EGDB, GOAT, GuitarJam, IDMT, EG-IPT and Guitar-TECHS.
  Two options:
  - A borrowed backing from another session or MoisesDB's non-guitar stems. Its key and tempo won't
    match, and the separator may find that mix easier or harder than a real one [U].
  - Slakh's drums, bass and keys stems, which are synthetic.

  Either way these sources cannot be fair test bands for a mix model. GOAT ships Guitar Pro tabs;
  whether they carry the other instruments, which could be rendered as a time-aligned backing, is
  unverified [U].

## Ranked additions and their cost

**The cost model.** It holds today's density: 77 renders per section, the same in part C
(40,000 ÷ 520) and the direct build (21,311 ÷ 277) [P].

| Item | Per 100 new sections |
|---|---|
| Renders | 7,700 |
| Render time at 1.6 s each | 3.4 h of render time, about 1.1 h on 3 shards |
| X-LANCE separation at 4.3–5 s per clip on MPS | 9.2–10.7 h |
| Stored features (part C's mels plus the direct build's mix and stem mels) | about 1.4 GB |
| Screening | about 5 s of CPU per DI (the `clean_di` screen ran 231 DIs in 1,139 s) [P], held-out and MUSDB checks, the backing build (zero renders), a few minutes of listening for scope |

Part C's curve suggests fewer draws per section over more sections. At 20 per section the render
and separation costs fall about 4×.

| Rank | Addition | Why | Download | New sections (estimate) | Renders; wall time on 3 shards | X-LANCE (MPS) | Screening | Also a test band? |
|---|---|---|---|---|---|---|---|---|
| 1 | **Telefunken, electric DI box on the chart:** Jen Hartswick & Nick Cassarino, Uglybraine | 2 new bands, likely clean to crunch, true DI box, real backing | 1.9 GB | about 50 (25–75), from about 5 DIs at the Telefunken yield of about 10 sections per DI | 3.9k; 0.6 h | 4.6–5.3 h | 5 DIs; listen to one clip per band | **yes: fresh DI + amp mic + backing**, the stage F format |
| 1b | **Telefunken, "Acoustic Guitar" DI box on the chart:** Melt, Braiden Sunshine | 2 more bands, if the box is the electric's (a ZIP file listing, tens of kB each, decides first) | 7.7 GB | 0–75, about 50 if so | up to 5.8k; 0.9 h | up to 6.9–8.0 h | as above | **yes**, if so |
| 2 | **Strobe "Maya" + MekaPhil ×4** | 2 new bands, real backing; DI-only | 2.4 GB | about 75 (40–110) at the Cambridge yield | 5.8k; 0.9 h | 6.9–8.0 h | 18 DI files; MekaPhil's gain by ear; re-host timeline check | as known-answer or V_dev-style bands (render truth), not real-amp; **taking them for training spends B2's pool** |
| 3 | **EGDB DI folder** | 1 new player and guitar, comping and arpeggios in many styles | 0.6 GB | cap about 100 (up to about 400 pass) | 7.7k; 1.1 h | 9.2–10.7 h | 240 clips; borrowed backing | no |
| 4 | **GOAT** | the most real musical DI (5.9 h), 4 guitars, several players | 15–25 GB [U], after an access request | cap about 100 per guitar, about 400 | 31k; 4.6 h | 37–43 h | 172 DIs; screen out metal by ear or tags; no player IDs, so cluster by guitar | no |
| 5 | **Stage F's 10 bands into training** (zero download) | 284 sections already screened and in part C's pool; 123 clean-class, 7 crunch; more than doubles the clean-class pool (97 to 220) and adds 10 bands | 0 | 284 (the 102 sections of stage F's own DIs stay out) | 21.9k; 3.2 h | 26–30 h | none new | **spends stage F**: only once rank 1 (or 2) gives replacement test bands |

- **Cheaper extras.**
  - GuitarJam: CC0, 2.5 h of single-note lines, 0.8 GB.
  - Blue Manic "Acomatay": a DI + amp pair, stoner rock, needs a scope check.
  - The two pending listening pages: they may return some hum- or hiss-flagged sections of the
    train bands, at no download.
- **Not recommended.** Five guitar (not a true DI), EG-IPT and EGFxSet (notes), GuitarSet
  (acoustic), Slakh and SynthTab (synthetic guitar), MoisesDB and MedleyDB (no DI; MedleyDB is held
  out), Guitar-TECHS (hum, exercises), and every metal session.

**Test bands.** Today the sound gate reads 4 bands, V_dev 5 and stage F 12. Only the Telefunken
sessions (and Blue Manic's one pair) give fresh real-amp DI + amp + backing parts, the format
stage F uses. Every band spent on
testing is lost to training, so the split is the user's call:
- (a) the Telefunken bands become new test bands, which lets stage F's bands train (rank 5);
- (b) the Telefunken bands train, and stage F stays the test.

## Questions for the user

1. **The Telefunken file listing.** Reading each ZIP's file names means fetching its last tens of
   kilobytes (a partial download). It confirms rank 1 and decides rank 1b and the five sessions
   with no DI box on the chart.
2. **Test or train** for the new Telefunken bands; and whether stage F may then train (rank 5).
3. **B2's songs.** Strobe and MekaPhil are B2's parked known-answer candidates. Training on them
   spends that pool.
4. **Licence wording to confirm:**
   - EGDB states no licence beyond "feel free to use";
   - IDMT-SMT-Guitar is NoDerivatives, and re-rendering makes derivatives;
   - GOAT needs a Zenodo request stating non-commercial research use.
5. **Disk.** About 119 GB is free now. Ranks 1–3 (with 1b) need about 13 GB of downloads plus
   about 4 GB of features. The five sessions with no DI box would add 23.6 GB.

## Sources

- **Telefunken LFTL:**
  - [session pages and mic charts](https://www.telefunken-elektroakustik.com/livefromthelab/),
    including the Jen Hartswick & Nick Cassarino and Uglybraine charts;
  - Telefunken's Amazon S3 buckets, e.g.
    [Uglybraine](https://season3multitracks.s3.us-east-2.amazonaws.com/UGLYBRAINE_Sometimes.zip)
    (HTTP HEAD only).
- **Cambridge-MT:**
  - [Hugging Face re-host listing](https://huggingface.co/datasets/kwatcharasupat/mixing-secrets-rawstems)
    (revision b482eb2e);
  - [archived library page](https://web.archive.org/web/20250717000000*/cambridge-mt.com/ms/mtk/)
    (2025-07-17);
  - direct host, e.g.
    [Strobe](https://mtkdata.cambridgemusictechnology.co.uk/MTK021/Strobe_Maya_Full.zip) and
    [The Timezone](https://mtkdata.cambridgemusictechnology.co.uk/MTK017/TheTimezone_GOTGF_Full.zip);
  - [partial 2026 re-host](https://huggingface.co/datasets/fattyyyyyyyyyy/free_multitrack_2026).
- **Datasets:**
  - GOAT: [Zenodo 15690894](https://zenodo.org/records/15690894),
    [paper](https://arxiv.org/html/2509.22655);
  - EGDB: [project page](https://ss12f32v.github.io/Guitar-Transcription/),
    [Zenodo 12674910](https://zenodo.org/records/12674910),
    [EGDB-PG Zenodo 19789500](https://zenodo.org/records/19789500);
  - [GuitarJam](https://huggingface.co/datasets/Julian-br/GuitarJam);
  - [IDMT-SMT-Guitar](https://zenodo.org/records/7544110);
  - [Guitar-TECHS](https://zenodo.org/records/14963133);
  - [Five guitar](https://zenodo.org/records/4988354);
  - [EG-IPT](https://zenodo.org/records/15205644);
  - [GuitarSet](https://zenodo.org/records/3371780);
  - [MoisesDB](https://github.com/moises-ai/moises-db);
  - [Slakh2100](https://zenodo.org/records/4599666);
  - [SynthTab](https://github.com/yongyizang/SynthTab);
  - [ToneTwist](https://github.com/mcomunita/tonetwist-afx-dataset).
- **This repo:**
  - [pretrain-set results](../pretrain-set-results.md);
  - [direct-model stems plan](../direct-model-stems-plan.md) and
    [results](../direct-model-stems-results.md);
  - [clean DI library results](../clean-di-library-results.md);
  - [fresh multitracks](fresh-di-amp-multitracks-2026-10.md);
  - [Cambridge local check](cambridge-local-check-2026-10.md);
  - [DI riffs](di-riffs-and-part-classifier-2026-10.md);
  - `validation-datasets.json` (the Catbite and Wild & Co pairs);
  - [known-answer B1 results](../known-answer-b1-results.md) (B2's candidates).
