# Clean guitar DIs to widen the direct model's training set: an inventory

*Research report, 2026-10-22; updated 2026-10-23 with the Telefunken file listings and the user's
decisions. The listings came from each ZIP's central directory, read with HTTP range requests
(about 1.7 MB over 27 archives, then 13.0 MB over the other 206 the site links; approved by the
user). The one confirmed band, Jen Hartswick & Nick Cassarino, was then downloaded (0.94 GB,
approved by the user) as a reserved test band. A scan of the Cambridge-MT library followed the
same day ([section](#cambridge-mt-library-scan-2026-10-23)). Later that day, at the user's
request, Blue Manic "Acomatay" (a second reserved test band) and EGDB's DI folder were downloaded
through the user's browser, and the user requested GOAT's access on Zenodo. Nothing was rendered,
separated or listened to. Local facts come from the stored inventory, manifest and pool files;
outside facts from dataset pages, papers, the Telefunken "Live From The Lab" (LFTL) pages, the
Hugging Face re-host's file listing and archived Cambridge-MT pages. Research, not a declared
plan.*

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

  Since 2026-10-23 three downloads sit beside them: two reserved test bands (Jen Hartswick & Nick
  Cassarino, Blue Manic) and EGDB's DI folder, which can train once its DIs pass the DI checks.
- **The pool is short of exactly what the tests ask for.** Of the 277 training sections [P]:
  - 135 come from high-gain DIs or a melodic death metal session;
  - 96 of the 97 clean-class sections are one band, Eggy;
  - 1 is crunch-class.
  - Part C's learning curve flattened, and drawing the same number of renders from half the
    sections was worse (one seed) ([pretrain-set results](../pretrain-set-results.md)). So new
    clean and crunch bands are the lever.
- **The Telefunken LFTL file listings (2026-10-23) found one new band with an electric-guitar DI
  and its amp track: Jen Hartswick & Nick Cassarino** [V]. The 2026-10-22 version of this report
  counted 2 sessions whose mic charts list an electric DI box and 2 probable ones; the archives
  settle them ([details](#telefunken-file-listings-2026-10-23)):
  - **Jen Hartswick & Nick Cassarino (S4, 4 songs, 0.94 GB):** every song has
    `Guitar-Passive DI.wav` and `Guitar-Amp-M81.wav`. It is a guitar-and-vocals duo. The backing
    is two vocal mics, plus a trumpet in one song; a stereo room pair also carries the guitar.
    **Downloaded 2026-10-23** to `~/ndsp-presets/references/datasets-telefunken-new/` (ZIPs kept,
    `manifest.json` with URLs, sha256s and WAV headers): 48 kHz, 24-bit, mono, 20.4 min of DI.
    Reserved as a new test band in `docs/dev-test-ledger.json`
    (`telefunken-new-test-band-jhnc`); not used until the user has listened to it.
  - **Uglybraine "Sometimes":** no DI, despite the chart's box. Its one guitar track is a stereo
    `GTR w-SYNTH.wav`, with no amp mic.
  - **Melt "Fake Romantic":** no guitar DI. It has two electric-guitar mics; its DIs are bass and
    keys.
  - **Braiden Sunshine (4 songs):** the chart's box is `Ac GTR_TDA-1.wav`, named as an acoustic
    beside separately named electric-amp mics. Catbite's and Wild & Co's electric DIs were named
    "Guitar …" in their files [P], so this is probably a real acoustic [U]. Only a pairing check on
    one song's audio (1.3 GB) decides.
  - **The 5 sessions with no DI box on the chart:** none has a guitar DI (16 archives). West End
    Blend's S5 song still returns HTTP 403.
  - **The rest of the catalogue** (206 more archives, 198 readable): no other new band has an
    electric DI with an amp track. The pairs found are new songs of Wild & Co, John Morgan Kimock
    and Rebecca Haviland, bands already held out, in V_dev or local.
  - The new band is a **fresh DI+amp test band** (the user's decision below). The October
    multitrack search ([report](fresh-di-amp-multitracks-2026-10.md)) found no fresh pair at all.
- **The Cambridge-MT scan (2026-10-23) found no new band with a confirmed DI + amp track** on any
  host it could read ([details](#cambridge-mt-library-scan-2026-10-23)). Every session found
  with an electric DI (75 in the re-host's lists, 11 of the 132 archives listed directly) is from
  a band the project already uses, holds out or parks, or is metal or not a raw DI. The site and its newer archive host sit behind a
  Cloudflare challenge, and the scan stopped there. The leads are on that host: Blue Manic
  "Acomatay" has a named DI + amp pair (`ElecGtr2DI` + `ElecGtr2`, stoner rock; downloaded later
  that day: 5 pairs, a reserved test band). Prusinski,
  Hollowstate, Ember Rev and DGX are possible at best; their DIs are unconfirmed or they have no
  amp track. (Superseded 2026-10-25: the newer-host listing confirms electric DIs in Ember Rev and
  DGX and finds 5 new in-scope DI bands; [details](#cambridge-mt-newer-host-listing-2026-10-25).)
- **Ranked additions:**
  1. Jen Hartswick & Nick Cassarino, as a test band first;
  2. the Cambridge DI-only sessions Strobe "Maya" and MekaPhil ×4: B2's parked songs, which the
     user allows for training (2026-10-23);
  3. EGDB's DI folder (1 player);
  4. GOAT (5.9 h, needs an access request);
  5. a zero-download swap: once fresh test bands exist, stage F's bands could train. That adds 284
     already-screened sections in 10 bands, 123 of them clean-class. Two new test bands are not
     enough to replace stage F's 12.
- **The user's decisions (2026-10-23):**
  - reading the Telefunken file lists: approved, and done;
  - B2's parked known-answer songs (Strobe "Maya", MekaPhil) may be used for training;
  - licences confirmed: EGDB, IDMT-SMT-Guitar and GOAT;
  - the new bands' use follows the ML session's recommendation: **new Telefunken bands with a
    confirmed DI and amp track become test bands first.** They are fresh, and trusted once the
    user has listened to them, which raises test power: the trusted test set is only 2 bands
    today. B2's songs go to training.

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

*Not on disk when this report was first written; the rows marked "downloaded" have since arrived.*

| Source | What it holds | EG DI: hours; songs / players / bands | Genre fit | Licence | Already used? | Conflicts | Download | Quality notes |
|---|---|---|---|---|---|---|---|---|
| **Telefunken LFTL: Jen Hartswick & Nick Cassarino** (S4, 4 songs) | guitar DI + amp mic in every song; 2 vocal mics, a trumpet in 1 song, a stereo room pair [V] | 4 DIs, 20.4 min at 48 kHz, 24-bit (headers read after the download) [V]; 4 songs / 1 band | jazz/soul duo: clean to crunch [U] | home-studio and educational use only, attribution line [V] | no (not in any set, ledger or `learn/` code) | none; **a reserved test band (2026-10-23)**, ledger `telefunken-new-test-band-jhnc` | 0.94 GB, **downloaded 2026-10-23** to `datasets-telefunken-new/` [V] | file named `Guitar-Passive DI`; live room, so check bleed; 12 of the 28 local Telefunken DIs are hum-flagged, 6 in every window, and 27 of 28 read 60-Hz mains [P]; the "Numb" archive's folder is named "Novacaine" [V] |
| Telefunken LFTL: Uglybraine "Sometimes" (S3), Melt "Fake Romantic" (S9) | full live multitrack, **no guitar DI** [V] | 0 | — | same | no | none | 0.92 + 1.84 GB [V] | Uglybraine: one stereo `GTR w-SYNTH` track, no amp mic, although the chart lists a DI box. Melt: two electric mics (`E GTR a_M80`, `E GTR b_TF11`); DIs only on bass and keys |
| Telefunken LFTL: Braiden Sunshine (S8, 4 songs) | full live multitrack; an `Ac GTR_TDA-1` DI and electric-amp mics (`Ele GTR 1` or `2`, M80 + TF11) [V] | electric DI unlikely [U]; 4 songs / 1 band | rock/soul [U] | same | no | none | 5.86 GB [V] | The chart's "Acoustic Guitar" box was the electric's DI in Catbite and Wild & Co, but there the file was named "Guitar …" [P]; here it is named "Ac GTR". Deciding needs one song's audio (1.3 GB) and a pairing check |
| Telefunken LFTL, no DI box on the chart: Ryan Montbleau (S9, 3), Jeffery John Band (S8, 4), Jelly (S8, 1), Kat Wright (S4, 4), West End Blend (S4, 4) | full live multitrack; amp mics only, **no guitar DI** in any archive [V] | 0 | singer-songwriter, blues rock, soul, funk [U] | same | no | none | 23.6 GB [V] | The DIs are bass, keys and a drum pad. West End Blend's S5 song lists a TDP-1 box, but its archive still returns HTTP 403 (2026-10-23) [V]. |
| Telefunken LFTL, new songs of known bands: Bernard Purdie & Friends "It's Your Thing", John Morgan Kimock "Negative Space > Speed", Briana Maia "Over You", Wild & Co ×2 | full multitrack with DI | 5 songs [V] | clean/crunch | same | no | **stage F band, V_dev band, set-2 held-out band ×2** | 1–2 GB each | listed 2026-10-23 [V]: DI + amp mics in both Wild & Co songs (one DI named `Guitar_Helix_DI`) and in JMK's (`Keys GTR`); Purdie's and Briana Maia's have a DI but no guitar amp track |
| **Cambridge DI-only: Strobe "Maya", MekaPhil ×4** | full multitrack; DI-only guitar parts | 18 DI files, about 12 parts; 5 songs / 2 bands [V] | pop/electronica; anime alt rock (gain unknown) | Cambridge "educational purposes only" [V] | no | part B2's parked known-answer songs; **the user allows them for training (2026-10-23)** | 0.40 + 1.99 GB [V] | MekaPhil's publisher host is behind Cloudflare; the Hugging Face re-host has it, but set 5 found re-host tracks trimmed to different lengths |
| Cambridge DI-only: The Timezone "GOTGF" | full multitrack, 4 DIs | 4 DIs; 1 song [V] | funk | same | no | **it is Timo And The Timezone** (same SoundCloud) [V], a B2-candidate band left out of part C | 616 MB | — |
| Cambridge DI-only: Perpetual Escape "Stop And Rise" | full multitrack, 11 DI parts in 19 files | 1 song / 1 band [V] | progressive heavy rock: likely out of scope [P] | same | no | B2 candidate | 657 MB | gain unknown until heard |
| Cambridge: Hollow Ground "Left Blind" | DI-only, 3 DIs + lead | 1 song [V] | heavy | same | no | MUSDB18 train; band already trains | — | adds no band |
| Cambridge, added since 2025: Blue Manic "Acomatay" | full multitrack | **5 DI + amp pairs** (ElecGtr1 with two amp mics, 2, 6, 7, 8), 20.2 min of DI, 44.1 kHz, 24-bit [V] | stoner rock: scope by ear | same | no | **a reserved test band (2026-10-23)**, ledger `cambridge-new-test-band-bluemanic` | 0.51 GB ZIP, **downloaded 2026-10-23** to `datasets-cambridge-new/` [V] | the site's mix (Full Preview MP3) not downloaded yet |
| Cambridge, added since 2025: DGX "Rest In Hell" (4 DIs), Slimy Soul Suckers "Big Bang", Prusinski "80s Rocker", Hollowstate "Hurricane" | multitracks | DI confirmed only for DGX [V, partial re-host] (superseded 2026-10-25: the newer-host listing confirms Ember Rev's DIs too) | unknown; blues rock; MOR rock; hard rock | same | no | none known | DGX not listed; 1.25, 0.42 and 0.52 GB for the last three [P] | site behind Cloudflare; a browser opened it (2026-10-23); ranked in the [scan](#cambridge-mt-library-scan-2026-10-23) |
| Cambridge metal sessions with DIs (Arcadian Alone, Daimon B, Inhumanity Vortex, Peppermark ×2, Serapis ×2, SkalyVan ×3, Szymon Skiba "Trashy Thrash") | DI + amp or DI-only | about 80 DI files [V] | **metal: out of scope** | same | no | Szymon Skiba is a stage F band | — | — |
| **EGDB** | DI only (plus amp renders) | 1.79 h (107.5 min, read after the download); 240 clips / 1 player / 1 Strat-type [V, U] | solo, arpeggio and comping, various genres [U] | none stated, "feel free to use" [V], which covers the downloaded Drive DIs; the Zenodo renders are CC BY 4.0 [V]; confirmed by the user (2026-10-23) | arm A literature only | none | **downloaded 2026-10-23**: the Drive `audio_DI` folder, 0.46 GB ZIP, 44.1 kHz, 16-bit, mono [V]; the 1.04 GB Zenodo zip holds the BIAS FX2 renders, not the dry DIs ([round 1's check](round-1-song-only-matching.md)) [P] | played to a click; hex pickup for labels; DI box vs hex sum unclear [U] |
| **GOAT** | DI only (plus NAM and Guitar Pro renders, tabs) | 5.9 h; 172 cover songs / authors + 2 creators, no performer IDs / 4 guitars (Strat 235 min) [V] | covers; some "rock/metal"; share unknown [V, U] | CC BY-NC 4.0, restricted: request on Zenodo, "research purposes only" [V]; confirmed by the user (2026-10-23); **access requested by the user (2026-10-23)** | no (ML plan: "not now") | none | 15–25 GB [U] | no backing [V] |
| GuitarJam (Hugging Face) | DI only | 2.5 h; 580 × 15-s monophonic improvisations / 1 Strat, players unstated [V] | single-note lines only | CC0 [V] | no | none | 796 MB [V] | no chords; no backing |
| IDMT-SMT-Guitar | DI, mostly notes and licks | about 15–20 min of short pieces (subsets 3–4) [U] / 7 guitars [V] | genre-tagged short pieces | CC BY-NC-ND 4.0 [V]; confirmed by the user (2026-10-23) | via ToneTwist | none | 1.33 GB [V] | ND: re-rendering makes derivatives; the user confirmed the licence |
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
  tracks share one timeline. Jen Hartswick & Nick Cassarino's backing is thin: two vocal mics
  (and a trumpet in one song), with the room pair dropped as leaking. Its mixes are guitar and
  vocals, with no drums, bass or keys [V].
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
| 1 | **Telefunken: Jen Hartswick & Nick Cassarino** (file listing confirmed, 2026-10-23) | 1 new band, likely clean to crunch, DI + amp mic in all 4 songs; the backing is vocals only (a trumpet in 1 song) | 0.94 GB | about 40 (20–60) if it trained, from 4 DIs at the Telefunken yield of about 10 sections per DI | 3.1k; 0.5 h if it trained | 3.7–4.3 h if it trained | 4 DIs; the user's listening makes it trusted | **yes, decided (2026-10-23): a test band first**, in the stage F format (DI + amp mic + backing) |
| 1b | **Telefunken: Braiden Sunshine** | 1 more band only if its `Ac GTR_TDA-1` DI turns out to be the electric's, which its name argues against | 1.3 GB for one song's check; 5.86 GB for all 4 | 0, or about 40 if so | — | — | a pairing check of the DI against the `Ele GTR` mics | a test band, if so |
| 2 | **Strobe "Maya" + MekaPhil ×4** | 2 new bands, real backing; DI-only | 2.4 GB | about 75 (40–110) at the Cambridge yield | 5.8k; 0.9 h | 6.9–8.0 h | 18 DI files; MekaPhil's gain by ear; re-host timeline check | no: **the user allows them for training (2026-10-23)**, which spends B2's pool |
| 3 | **EGDB DI folder** | 1 new player and guitar, comping and arpeggios in many styles | 0.46 GB, downloaded 2026-10-23 | cap about 100 (up to about 400 pass) | 7.7k; 1.1 h | 9.2–10.7 h | 240 clips; borrowed backing | no |
| 4 | **GOAT** | the most real musical DI (5.9 h), 4 guitars, several players | 15–25 GB [U], after an access request | cap about 100 per guitar, about 400 | 31k; 4.6 h | 37–43 h | 172 DIs; screen out metal by ear or tags; no player IDs, so cluster by guitar | no |
| 5 | **Stage F's 10 bands into training** (zero download) | 284 sections already screened and in part C's pool; 123 clean-class, 7 crunch; more than doubles the clean-class pool (97 to 220) and adds 10 bands | 0 | 284 (the 102 sections of stage F's own DIs stay out) | 21.9k; 3.2 h | 26–30 h | none new | **spends stage F**: only once rank 1 (or 2) gives replacement test bands |

- **Cheaper extras.**
  - GuitarJam: CC0, 2.5 h of single-note lines, 0.8 GB.
  - Blue Manic "Acomatay": downloaded 2026-10-23 as a reserved test band; 5 DI + amp pairs (20.2 min
    of DI), stoner rock, so scope by ear.
  - The two pending listening pages: they may return some hum- or hiss-flagged sections of the
    train bands, at no download.
- **Not recommended.** Five guitar (not a true DI), EG-IPT and EGFxSet (notes), GuitarSet
  (acoustic), Slakh and SynthTab (synthetic guitar), MoisesDB and MedleyDB (no DI; MedleyDB is held
  out), Guitar-TECHS (hum, exercises), and every metal session.

**Test bands.** Today the sound gate reads 4 bands, V_dev 5 and stage F 12, and the trusted test
set is 2 bands. Only the Telefunken sessions (and Blue Manic's five pairs) give fresh real-amp DI +
amp + backing parts, the format stage F uses. Every band spent on testing is lost to training.
**Decided (the user, 2026-10-23, on the ML session's recommendation):** new Telefunken bands with
a confirmed DI and amp track become test bands first, trusted once the user has listened, and B2's
songs go to training. The listings confirm one such band, Jen Hartswick & Nick Cassarino. Whether
stage F may then train (rank 5) stays open: two new bands do not replace 12.

## Telefunken file listings (2026-10-23)

Read from each ZIP's central directory with HTTP range requests: the last 64 kB of each archive,
1.7 MB over 27 archives [V]. Every archive answered with a byte range and none needed a second
read; no audio was fetched for the listing. macOS metadata entries (`__MACOSX`, `.DS_Store`) are
left out. Jen Hartswick & Nick Cassarino's WAV headers were read after its download; the local
Telefunken sessions are a mix of 48 and 96 kHz [P].

| Session (season) | Archives | Tracks per song | Electric-guitar DI | Amp or mic tracks for it | Backing (other instruments) |
|---|---|---|---|---|---|
| Jen Hartswick & Nick Cassarino (S4): "Drowning", "Numb" (folder "Novacaine"), "Silent Waves", "You Cant Take It Back" | 4; 0.16 + 0.24 + 0.23 + 0.31 = 0.94 GB | 6 (7 with the trumpet) | **`Guitar-Passive DI.wav` in all 4; high confidence** (the chart lists the box on the electric) | `Guitar-Amp-M81.wav` | thin: `Vocals-Jen-Ela M 251`, `Vocals-Nick-Ela M 251T`, `Trumpet-M81` in "You Cant Take It Back"; `Room-M60 L/R` carry the guitar too. Every track 48 kHz, 24-bit, mono; DI lengths 215.8, 327.6, 318.5 and 359.7 s (read after the download) |
| Uglybraine "Sometimes" (S3) | 1; 0.92 GB | 17 | **none**; the one guitar track is a stereo `GTR w-SYNTH.wav` | none separate | full band: drum mics and rooms, `BASS DI`, `KEYS`, `SYNTH`, `SAX`, `BONE`, `FLUTE` |
| Melt "Fake Romantic" (S9) | 1; 1.84 GB | 21 audio + a mic-preamp input list (PDF) | **none** | `E GTR a_M80.wav`, `E GTR b_TF11.wav` (no DI to pair) | full band: drums, `Bass DI_TDA-1`, `Bass Amp_M82`, `Nord_TDP-2`, 3 vocal mics, rooms |
| Braiden Sunshine (S8): "Beautiful Roads", "Live Again", "Sail Away", "Under Your Spell" | 4; 1.27 + 1.83 + 1.47 + 1.29 = 5.86 GB | 23–26 | **probably none** [U]: `Ac GTR_TDA-1.wav` is the chart's "Acoustic Guitar" box, named as an acoustic | `Ele GTR 2_M80` + `Ele GTR 2_TF11` (`Ele GTR 1_…` in "Live Again") | full band: drums, bass DI and amp, Nord and Roland keys, vocals; horns in 3 of the 4 songs |
| Ryan Montbleau (S9), 3 songs | 3; 5.87 GB | 25–26 | none | `E GTR_M80`, `E GTR_TF11`; `GTR_M80`, `GTR_TF11` (another guitar) | full band |
| Jeffery John Band (S8), 4 songs | 4; 7.83 GB | 26 | none | `GTR Amp M80`, `GTR Amp TF11` | full band |
| Jelly "XMAS jams" (S8) | 1; 1.82 GB | 17 | none | `GTR AMP TF47`, `GTR AMP M81` | full band |
| Kat Wright (S4), 4 songs | 4; 3.71 GB | 21–23 | none | `ELE Guitar-M80`, `ELE Guitar-Proto 647` | full band |
| West End Blend (S4), 4 songs | 4; 4.40 GB | 21–22 | none | `ELE Guitar1-Mike-Proto`, `ELE Guitar2-Jesse-Proto` | full band; the S5 song "Love Having You Around" returns HTTP 403 |

- **Braiden Sunshine's DI.** In Catbite and Wild & Co the chart's "Acoustic Guitar" box was the
  electric's DI, but their files were named `Guitar TDP-1`, `Guitar DI_18` and
  `Guitar DI_TDP-1` [P]. Here the file says `Ac GTR` and the electric has its own two mics, the
  same M80 + TF11 pair as Wild & Co's amp. Wild & Co's real acoustic was a separate mic track
  (`Ac Guitar_M260`) [P].
- **The rest of the Telefunken catalogue (pass of 2026-10-23).** The LFTL pages link 262 archives
  in seasons 2–7 [V]. 206 of them were neither local nor already listed above, and all 206 were
  tried with the same range reads (13.0 MB in all). The first run stopped at 115 on S3 refusals;
  under the coordinator's updated rule (a 403 on one archive is recorded and skipped, never
  retried) it was resumed and finished. **198 were read, 8 refused** (HTTP 403, `AccessDenied`
  XML from S3, per object, with other archives in the same buckets answering in between): Dopapod
  ×2, Holly Bowling ×4, Umphrey's McGee "Crucial Taunt" (its Cambridge copy is local) and Josh
  Quimby "Ten Year Town" [V].
  - **No new band has an electric-guitar DI with an amp or mic track** [V]. Jen Hartswick & Nick
    Cassarino stays the only one in the catalogue's readable archives.
  - **The electric DI + amp pairs found are all new songs of bands this project already uses**,
    so they belong to those bands' roles:

    | Song (season) | Archive | DI | Amp or mic tracks | Confidence | Backing | Band's role |
    |---|---|---|---|---|---|---|
    | Wild & Co "Run Crawl Walk" (S8) | 1.05 GB | `EGT2di.wav` | `EGT2m80.wav`, `EGT2tf11.wav` (plus `EGTlead`, `EGTleadHelix`) | high | full band | set-2 held out |
    | Wild & Co "Sorry Our Demons" (S8) | 2.09 GB | `Guitar_Helix_DI.wav` | `Guitar_Amp_M80.wav`, `Guitar_Amp_TF11.wav` | medium: may be a Helix output, not a raw DI ("Past Dues" has both a `Guitar DI_TDP-1` and a `Guitar Helix`) | full band | set-2 held out |
    | John Morgan Kimock "Negative Space > Speed" (S6) | 1.14 GB | `Keys GTR DI_TDP-1.wav` | `Keys GTR Amp_M80.wav`, `GTR KEYS AMP_TF51.wav` | instrument unverified, as for JMK's local "Keys GTR" DIs | full band | V_dev |
    | Rebecca Haviland ×3 (S6) | 0.69–0.86 GB | `GTR 1/2 DI_TDP-1` | `GTR 1/2 Amp M 80`, `GTR 1/2 Amp TF 11` | high | full band | already local: part B's known-answer band |

    Bernard Purdie "It's Your Thing" (`GuitarElectric(direct).wav`) and Briana Maia "Over You"
    (`GTR DI_TDP-1.wav`) have an electric DI but no guitar amp or mic track.
  - **Everything else is acoustic-guitar DIs or amp mics only.** The acoustic DIs include Toad The
    Wet Sprocket, Jesse Terry, Josh Quimby, People Like Us, the Oliver Myles Mashburn sessions,
    Hayley Reardon & Pau Figueres, The Great Enough, Plywood Cowboy and Megan Slankard; Megan
    Slankard and Cyro Baptista also put an acoustic through an amp. Penniless Wild, SixFoxWhiskey,
    Szlachetka, The Western Den, Mikaela Davis and all of seasons 2 and 3 have electric amp mics
    only. Seasons 5's jazz sessions (Kris Allen, Nicole Zuraitis, Thana Alexa) and Podunk
    Bluegrass have no electric guitar track.

## Cambridge-MT library scan (2026-10-23)

The user approved a scan of the Cambridge-MT ("Mixing Secrets") library for electric-guitar DIs
from new bands, with DI + amp/mic + full backing, as new test bands first. No audio and no full
archive was downloaded.

**What could be reached.**
- **The site is behind a Cloudflare challenge.** `cambridge-mt.com/ms3/mtk/`, `www.cambridge-mt.com`
  and `multitracks.cambridge-mt.com` answered HTTP 403 with `cf-mitigated: challenge`
  (2026-10-23, 07:29 UTC) [V]. `multitracks.cambridge-mt.com` also hosts the newer archives, and
  a HEAD on one of them (Hollowstate "Hurricane") got the same challenge [V]. The scan stopped at
  the challenge on those hosts and did not try to pass it.
- **The older archive host answers normally.** `mtkdata.cambridgemusictechnology.co.uk` served
  plain ZIP files with byte ranges; its folders give no directory listing (403, no challenge) [V].
- **Index and earlier listings, from local copies only.** Three listings saved by the 2026-10-17
  and 2026-10-22 passes; no request went to Hugging Face or the Wayback Machine this time:
  - the library index as archived on 2025-07-17 (625 rows, with archive links, sizes and genres)
    [P];
  - the RawStems re-host's file list (483 sessions, the library to about April 2025) [P];
  - the partial 2026 re-host's file list (24 sessions, revision `74d985e`, last changed
    2026-08-13) [P].

**Three passes.**
1. **The re-host's file names (483 sessions):** 75 sessions have a file named as an
   electric-guitar DI [P]. Every one belongs to a band this project already uses, holds out or
   parks, or is metal, or is not a raw DI:
   - train bands (Ale Lak, Death Of A Romantic, Rebuild The Evil, Starnes & Shah, Storm Of
     Particles, The Long Wait);
   - V_dev (Adam Buckley, Dark Ride, Swatkins);
   - stage F (Diesel13, Eat The Feeder ×2, Magician's Nephew, Szymon Skiba ×2, The Travelling
     Band ×2, Turbosauro);
   - known-answer or B2 (Chris Coltraine ×2, Rebecca Haviland, The Apprehended, MekaPhil ×4,
     Strobe, The Timezone and Timo, Perpetual Escape);
   - held-out sets 2–5 (Boogie Snakes, Forkupines, The Maybe Next Years; Dunning Kruger ×3,
     Scott Elliott, Silence Is Near, Silona, V.M.GY ×5; Decypher, Last Legacy, Lead Inc, Sonnet &
     Alcohol, The Black Crown, The Bright Star Alliance, The Laminar Flow, Tholas P., Umbriferous;
     Fytakyte, Hannes Keseberg, Hazael ×2, Jeff Hirata, MOPP, Nova-One Studio, Peter White, Ronnie
     Jones, Saturn Syndicate, The Ferryboat Men);
   - metal, never used (Arcadian Alone, Daimon B "Broken Again", Inhumanity Vortex, Peppermark ×2,
     Serapis ×2, SkalyVan ×3);
   - not a raw DI (Umphrey's McGee's Palmer PDI-09).
2. **Central-directory reads on the direct host (132 archives):** every session the July 2025
   index puts on `mtkdata` whose list the re-host lacks (112 archives, the MUSDB18 songs among
   them, which the re-host keeps apart), plus 20 whose re-host file count differs from the
   site's. The reads
   took 8.65 MB in all, the last 64 kB of each archive. All 132 answered with a byte range: no
   challenge, no refusal, no second read [V]. 11 archives have an electric DI, all from bands
   already in the project:
   - Atlantis Bound, Zeno and Wall Of Death (stage F);
   - Tim Taler, Forkupines "Semantics" and Lights Off Clarity's "All The Same"
     (`MR0912_NorthToAlaska`), all set-2 held out;
   - Chris Durban (set 5);
   - Cnoc An Tursa (V_dev);
   - Hollow Ground ×2 (train band);
   - Strobe (B2, now training).

   The other 121 have no electric DI. Rod Alexander's `02_DI.wav` sits in a two-track solo
   guitar instrumental (a main stereo pair + DI, no backing), probably acoustic [U]. The DIs in
   Al James and Signe Jakobsen are MIDI guitar tracks. The Telefunken sessions mirrored there
   (Big Head Todd, Kat Wright, Jackie Greene, Zane Carney, West End Blend and others) have amp
   mics, and acoustic DIs at most.
3. **The challenged host, where the new bands are:**
   - 31 sessions of the July 2025 index sit on `multitracks.cambridge-mt.com` with no track list
     in the re-host; 13 of them are in the partial 2026 re-host;
   - 11 more sessions appear only in that partial re-host, so they were added after July 2025;
   - anything added after 2026-08-13 is unknown.

   The partial re-host drops files all through each session (kick and snare, most of each
   session's tracks), so a missing number next to a guitar is weak evidence [P].

**Result: no new band with a confirmed electric DI + amp track and full backing on any readable
host.** The leads below are all on the challenged host; only the first is a named DI + amp pair.

| Rank | Band | Song | Genre | DI track | Amp/mic tracks | Backing | Archive size | Already local? | Held-out conflict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Blue Manic | "Acomatay" | stoner rock (earlier report): crunch or fuzz, needs a listen [U] | `17_ElecGtr2DI`; 13–15 and 22, 24, 26 are missing beside other electrics, so maybe more [U] | `16_ElecGtr2` | full band: drums, bass DI + amp, acoustic, 7 more electrics, synth, sax, vocals | not listed (challenged); about 1–1.3 GB [U] | no | none |
| 2 | Prusinski | "80s Rocker" | MOR rock (site): best gain fit | none seen; numbers 12, 16 and 19 are missing after `ElecGtr01`, `04` and `06` [U] | `ElecGtr01`–`ElecGtr10` | drums, bass DI, cowbell, vocals | 424 MB | no | none; but the band's 3 older sessions have amp tracks only [P] |
| 3 | Hollowstate | "Hurricane" | hard melodic rock (site) | none seen; 20 and 27 missing after `ElecGtr01` and `07` [U] | `ElecGtr01`–`ElecGtr13` | drums, bass DI, acoustic, vocals | 516 MB | no | none; the band's "Gravediggers" has no DI [P] |
| 4 | Ember Rev | "Divers & Lazarus" | art rock (site) | none seen; every other number is missing between `ElecGtr1` and `ElecGtr9` [U] | `ElecGtr1`–`ElecGtr9` | drums, percussion, bass DI, 4 acoustics, synths, accordions, vocals | 536 MB | no | none |
| 5 | DGX | "Rest In Hell" | unknown; the title suggests heavy [U] | `ElecGtr1DI`–`ElecGtr4DI` | none seen (17–19 missing) | drums, bass, vocals | not listed | no | none |
| 6 | Sunbreak | "Flawed" | post-hardcore (site): likely heavy | none seen; 14 and 16 missing [U] | `ElecGtr1`–`ElecGtr4` | drums, bass, synths, vocals | 454 MB | no | none |
| 7 | Escarràs | "No Limits" | ska fusion (site) | no list anywhere | — | 55 tracks | 644 MB | no | none |
| by ear | Empty Signifier | "Change" | "Various Styles" (site, read 2026-10-25); the band's "Wrong" is filed as punk metal: scope by ear | `ElecGtr1DI`, `ElecGtr2DI` | `ElecGtr1Mic1` | drums, bass amp, vocals | not listed | no | none |
| out | Daimon B ×4, Dark Illusion ×2, Peppermark "Lua Negra", Harvst | — | nu metal, metalcore, metal | some gaps beside guitars | — | — | — | no | none |
| — | Fytakyte "Dumber By The Minute", Saturn Syndicate "Dead Men's Ride" | — | melodic rock, retro pop | none seen | — | — | — | no | **set-5 held-out bands** |

The rest of the challenged-host list is unlikely to add a band:
- **electric guitars but no DI in the partial lists:** David Tyo, Fizzo Fizzzz & Triviul, Alas
  Vector, Moni Blue ×2, Fabian Navarro and Simplemachine. Slimy Soul Suckers "Big Bang" (blues
  rock, 1.25 GB) would fit by genre, but its 17 electrics are numbered without a gap
  (`19_ElecGtr01` to `35_ElecGtr17`), so a DI there is unlikely [U];
- **no list anywhere, and the band's other sessions have no electric DI:** Geometría Chicken ×2
  (funk rock; "Chasque" and "Das Funkeren" were read directly) and Perpetual Escape "Into My
  Dreams" (progressive heavy rock, 3.2 GB in 4 parts; the band's 4 listed sessions have DIs with
  no amp track or amps with no DI);
- **no list anywhere, other genres:** Masé Jara (Brazilian jazz, 10 tracks), FriendZWorldMusic
  (16 tracks), Gurnzy ×2 (drum & bass), Sören (disco pop), and the hip-hop, choral, classical
  and folk sessions.

**What it would take.** A real listing of ranks 1–7 needs the challenged host. Two routes, both
the user's call:
- the user opens each session page and downloads the archives by hand, as for MekaPhil
  (about 4 GB for ranks 1–7);
- the user passes the browser check once, and the archive lists are read in that session.

Blue Manic is the one with a named pair. Prusinski "80s Rocker" is the best genre fit, but the
band's three older sessions have no DI.

*Later: Blue Manic "Acomatay" was downloaded on 2026-10-23 through the user's browser at their
request and is reserved as a test band (ledger `cambridge-new-test-band-bluemanic`).*

## Cambridge-MT newer-host listing (2026-10-25)

With the user's approval, the library page was opened in their Chrome. Each of the 220 full-multitrack
archives on `multitracks.cambridge-mt.com` (the challenged host) was range-read for its ZIP central
directory only: file names, no audio. 218 were read; one request timed out and one ignored the
range. 48 sessions name an electric-guitar DI [V]:

- **Out of scope (metal):** 20 sessions from 14 bands. 7 of these bands are also set-4 held out:
  Decypher, Last Legacy, Sonnet & Alcohol, The Black Crown, The Bright Star Alliance, Tholas P.
  and Umbriferous.
- **Already held, held out or reserved:**
  - Saturn Syndicate, Hazael ×2, Fytakyte, MOPP, Nova-One, Jeff Hirata "Sunshine" and The
    Ferryboat Men "The Winds Of Gypsy Moor" (set 5);
  - Laminar Flow and Lead Inc (set 4);
  - known-answer/B2 (Chris Coltraine ×2) and stage F (Eat The Feeder ×2);
  - Swatkins and Rebecca Haviland (Telefunken bands with held-out songs);
  - Blue Manic (test band).
- **New and in scope: 5 bands** (genre from the site):

| Session | Genre | Electric DIs [V] | Amp tracks | ZIP |
|---|---|---|---|---|
| Ember Rev "Divers & Lazarus" | art rock | ElecGtr8DI, 9DI | ElecGtr1–9, some FX | 536 MB |
| Empty Signifier "Change" | "Various Styles": scope by ear | ElecGtr1DI, 2DI | three mics each | 193 MB |
| Goran Levi "Que Se Yo" | Afro-Cuban jazz | ElecGtrDI | ElecGtr | 457 MB |
| Mòpia "If You Then I" | jazz-metal big band: scope by ear | ElecGtr2DI, 3DI | ElecGtr1–4 | 717 MB |
| Sören "A Little Late" | disco-pop | ElecGtrDI, DTDI | none (DI only) | 613 MB |

DGX "Redemptive Pain" and "Rest In Hell" (827 and 686 MB) also name electric DIs; the site files
them as hard rock/metal, so their scope is by ear. They are not downloaded.

MekaPhil (four DI-only songs) is also listed; it was downloaded earlier by hand. The earlier
scan's other leads (Prusinski, Hollowstate, Sunbreak, Escarràs) show no electric DI, unless
one of them is among the 2 unread archives, whose names were not kept. Ember Rev's
DIs, unconfirmed on 2026-10-23, are now confirmed. The full list is in
`~/ndsp-presets/references/cambridge-scan-2026-10-25/scan.md`.

**Downloads (2026-10-25).** The user approved downloading the in-scope sessions through Chrome.
- Empty Signifier "Change" (197,314,032 bytes) was downloaded to
  `~/ndsp-presets/references/datasets-cambridge-new/_zips/`. Its audio is not opened until its
  ledger role is set.
- The other four (Ember Rev, Goran Levi, Mòpia, Sören) were blocked by Chrome's multiple-download
  prompt and are pending.
- Jeff Hirata and The Ferryboat Men are not downloaded (set-5 held out).
- *Later on 2026-10-25:* the other four were downloaded too (checksums in `_zips/sha256-2026-10-25.txt`).
  **The user decided all five are training bands, not test bands.** The role was recorded before
  any audio was opened: ledger `cambridge-new-training-bands-2026-10-25` and `TRAINING_DOWNLOADS` in
  `learn/clean_di.py` (read by the DI inventory and `assert_training_ok`). 9 electric DIs: Ember Rev 2,
  Empty Signifier 2, Goran Levi 1, Mòpia 2 (each with an amp or mic track) and Sören 2 (DI only).
  Mòpia and Empty Signifier are scope by ear. A DI trains only after T0's checks and the ear.
- *T0's checks (2026-10-25, zero renders; `verify_tracks`' functions unchanged, up to 5 windows per
  DI where it plays; outputs in `~/ndsp-presets/learn/trusted-data/intake-2026-10-25/`).* D3 passes
  all 9. **D2 passes 4 of 9:** Empty Signifier ElecGtr2DI, Goran Levi's DI and both Mòpia DIs. It
  fails, and so excludes whatever the ear says:
  - Ember Rev's two DIs: clipping in every window (and they play only from 3:15 on);
  - Empty Signifier ElecGtr1DI: hum, −40 to −50 dB against its playing level;
  - both Sören DIs: exact-zero gaps of 3–22 ms locked to the groove, about 200 per DI, so the DI
    was gated or edited (drop-outs in every window).

  The amp checks inform only. Empty Signifier's mics read as real amps: a cab is present and the
  mic leads the DI by 1.1 ms (A1 to the ear). They are not all bleed-free: A6 (bleed) fails in a
  window on ElecGtr1 Mic1 and Mic3, so bleed shows in 2 of 6 mics, and A5 (same take) fails in a
  window on ElecGtr2 Mic1. Goran Levi's "ElecGtr" is a processed copy of the DI, not a miked amp:
  zero lag, no cab, up to 0.98 correlation with the DI. Its DI fails D1, and D4 flags it. Mòpia's
  amp tracks have no coherent top end (A2 fails), and D4 flags both DIs, which suggests heavy drive
  and a scope worry. The user's ear page (`listening/trusted-data-ear/part6-new-bands/`) holds the
  4 D2-passing DIs, 2 windows each, with a tone-class card per window: 16 cards, pending.
- *The ear (2026-10-26; export `ear-exports/part6-new-bands-2026-10-26.json`, read by `verify_tracks lists`):*
  **1 new training DI from 5 bands.**
  - Empty Signifier 20_ElecGtr2DI: heard clean on both windows, and admitted (`verified.json`'s `intake_admitted`; the
    inventory lifts its `INTAKE_PENDING` note). Its amp track (Mic3) was heard high gain, so it adds a high-gain DI,
    not a clean or crunch one. The DI-and-amp pairing itself was never heard (part 6 had no pair card): hear it
    before anything uses that amp track.
  - Mòpia 19_ElecGtr2DI and 21_ElecGtr3DI: heard processed, excluded. Both amp tracks were heard high gain.
  - Goran Levi 12_ElecGtrDI: heard processed, excluded. Its amp track was heard clean, with drum and bass leaks, and is
    a processed copy anyway.
  - Under the user's scope refinement of 2026-10-26 ([ROADMAP](../ROADMAP.md#scope-user-decision-2026-10-10)), high gain
    no longer drops a training source. "Scope by ear" screens out only extreme cases.

## Decisions and open questions

**Decided by the user (2026-10-23):**
1. **The Telefunken file listing:** approved, and done (above). Then (relayed by the ML session):
   download Jen Hartswick & Nick Cassarino as a reserved test band, done; and list the rest of the
   catalogue, done (198 read, 8 refused; above).
2. **Test or train:** new Telefunken bands with a confirmed DI and amp track become test bands
   first (the ML session's recommendation).
3. **B2's songs:** Strobe "Maya" and MekaPhil may be used for training, which spends B2's parked
   known-answer pool.
4. **Licences confirmed:** EGDB ("feel free to use"; the Zenodo renders are CC BY 4.0),
   IDMT-SMT-Guitar (CC BY-NC-ND 4.0) and GOAT (CC BY-NC 4.0, through a Zenodo access request).
5. **Downloads (later on 2026-10-23, through the user's browser at their request):**
   - Blue Manic "Acomatay", the full multitrack (0.51 GB ZIP, 32 WAVs), as a **reserved test band**
     (ledger `cambridge-new-test-band-bluemanic`). Test first is the ML session applying decision 2
     to this Cambridge band, as told to the user the same day, not a separate user decision. It
     holds **5 DI + amp pairs, not 1**: ElecGtr1 (two amp mics), 2, 6, 7 and 8, 20.2 min of DI at
     44.1 kHz, 24-bit [V]. Stoner rock, so each part's scope is checked by ear. The site's mix
     (Full Preview MP3) is not downloaded yet. Stored in `datasets-cambridge-new/`.
   - EGDB's `audio_DI` folder from the authors' Google Drive (0.46 GB ZIP): 240 clips, 107.5 min,
     44.1 kHz, 16-bit, mono [V]. The Zenodo record holds the BIAS FX2 renders, not the dry DIs
     ([round 1's check](round-1-song-only-matching.md)), so the Drive folder is the DI source.
     Stored in `datasets-egdb/`. Training only (no backing), and only after its DIs pass the
     trusted-data DI checks.
   - GOAT: the user sent the Zenodo access request.

**Still open:**
1. **Stage F into training** (rank 5): two new test bands do not replace stage F's 12.
2. **Braiden Sunshine:** download one song (1.3 GB) to check whether `Ac GTR_TDA-1` pairs with the
   electric's mics.
3. **The 8 refused archives** (Dopapod ×2, Holly Bowling ×4, "Crucial Taunt", Josh Quimby "Ten
   Year Town") stay unread; only Dopapod, a jam band with electric guitar, might matter, and a
   manual check on the site is the user's call.
4. **The Cambridge leads behind the Cloudflare challenge:** listed on 2026-10-25 (above). The user
   approved the download of the 5 new in-scope sessions (2026-10-25); all five are downloaded and,
   by the user's decision the same day, are training bands (above). *Heard 2026-10-26: 1 DI admitted (Empty Signifier
   ElecGtr2DI). Since the scope refinement of that day, the scan's metal sessions outside the held-out sets are
   possible training candidates: 11 sessions from 6 bands (Arcadian Alone, Daimon B ×2, Dark Illusion ×2, Inhumanity
   Vortex, Peppermark ×3, Serapis ×2; V.M.GY is set-3 held out), plus DGX ×2 (hard rock/metal). With the user's yes,
   these 13 were downloaded on 2026-10-26 and are under intake on branch `ml/metal-intake`.*
5. **Disk.** About 113 GB was free on 2026-10-23. Ranks 1 and 3 are downloaded (0.94 + 0.46 GB);
   rank 2 needs 2.4 GB, and the features about 3 GB.

## Metal and hard-rock training intake (2026-10-26)

The user decided on 2026-10-26 that high-gain songs can train, "as long as too heavy songs don't
interfere with the model". Tests stay clean to crunch. 13 Cambridge-MT sessions were downloaded
(checksums in `_zips/sha256-2026-10-26.txt`): Arcadian Alone "The Deathless One", Daimon B "Broken
Again" and "Crying Rivers", Dark Illusion "Dark Illusion" and "Evil Bones", Inhumanity Vortex
"Cybermod", Peppermark "Lua Negra", "Another Feeling" and "Interlude", Serapis "The Dark Abyss" and
"Morbus Animi", and DGX "Redemptive Pain" and "Rest In Hell". V.M.GY was left out on purpose: it is a
set-3 held-out band. None of the 7 bands is held out; set 3 lists five of them only as "not obtained".

The role was recorded before any audio was extracted: ledger `cambridge-new-training-bands-2026-10-26`
and `TRAINING_DOWNLOADS` in `learn/clean_di.py`, every DI row pending until a verified list admits
it. From the file lists, 89 electric DIs: 77 with a named amp track, 12 without (DGX's 11 and one
Peppermark DI). Daimon B "Crying Rivers" has no electric DI: its `ElecGtr*MIDI` tracks are named as
MIDI renders, not DIs. They and DGX's acoustic DIs are kept out of the DI rows (`INTAKE_NOT_DI`).
Peppermark "Another Feeling"'s `34_ElecGtrDI` has no part number (`33_ElecGtr4` by track order). A DI
trains only after T0's checks and the ear, which adds a tone card per amp track (clean, crunch, high
gain or too heavy).

*Extraction and T0's checks (2026-10-26, zero renders; `verify_tracks`' and `clean_di`'s functions
unchanged; outputs in `~/ndsp-presets/learn/trusted-data/intake-2026-10-26/`).* Only the guitar
tracks and Readmes were extracted (manifest `datasets-cambridge-new/manifest-2026-10-26.json`): the
full sessions are about 26 GB, which would take free disk under the 75 GB floor. The rest stays in the
ZIPs. So A6 (bleed) was not run, because it needs every other track of the session. Windows are
picked as on 2026-10-25: DI play share ≥ 0.5 in both halves, up to 5 spread across the song.

- **D3 passes all 89. D2 passes 78 of 89.** By session (DIs, D2 passes): Arcadian Alone 4, 3; Daimon B
  "Broken Again" 6, 6; Dark Illusion "Dark Illusion" 6, 2, and "Evil Bones" 4, 4; Inhumanity Vortex 5,
  4; Peppermark "Lua Negra" 10, 9, "Another Feeling" 14, 12, and "Interlude" 14, 13; Serapis "The Dark
  Abyss" 9, 8, and "Morbus Animi" 6, 6; DGX "Redemptive Pain" 7, 7, and "Rest In Hell" 4, 4.
- Of the 11 D2 fails, 9 are hum, 1 is clipping and 1 is drop-outs. **In 6 of the 9 hum fails the hum is
  not confirmed on the rests** (`hum_unconfirmed_on_rests`; 4 of the 6 Dark Illusion DIs fail D2).
  Sustained low-tuned riffs may read as mains lines here. This looks like a possible miscalibration on
  dense high-gain playing, and the threshold was not changed. The DIs stay out.
- The amp checks inform only (on the DI's own take). A5 fails 38 of 78 pairs: chroma median 0.79
  against a 0.8 line, and onset 0.48, while A1's lag is clean on most. Distortion smears chroma and
  onsets, so A5 looks miscalibrated for high gain. That matters only if an amp track is used, not for
  training DIs. A2 goes to the ear on 72 of 78 (little coherent top
  end). Six DIs read near-zero lag to their amp track (−0.06 to +0.09 ms: Dark Illusion ×3, Peppermark
  "Lua Negra" ElecGtr3, Serapis "The Dark Abyss" ElecGtr1 and DT). That suggests a re-amp or plugin
  render, not a miked cab; the Serapis pair is also brighter than its DI.
- D4 flags 52 of 89, which is expected for driven, compressed metal playing (the ear's flag only).
- The ear pages `listening/trusted-data-ear/part7a-metal/` and `part7b-metal/` (44 cards each, about
  7 MB) hold one DI card per D2-passing DI (78) and one tone card per session with an amp track (10:
  clean, crunch, high gain or too heavy). They are pending. How `lists` reads them is in the
  [design](../trusted-data-t0-design.md#the-metal-intakes-ear-parts-7a-and-7b-2026-10-26).

## Sources

- **Telefunken LFTL:**
  - [session pages and mic charts](https://www.telefunken-elektroakustik.com/livefromthelab/),
    including the Jen Hartswick & Nick Cassarino and Uglybraine charts;
  - Telefunken's Amazon S3 buckets, e.g.
    [Uglybraine](https://season3multitracks.s3.us-east-2.amazonaws.com/UGLYBRAINE_Sometimes.zip),
    [Jen Hartswick & Nick Cassarino "Drowning"](https://season4multitracks.s3.us-east-2.amazonaws.com/Jen+Hartswick+%26+Nick+Cassarino_Drowning.zip)
    and
    [Braiden Sunshine "Live Again"](https://season7multitracks.s3.us-east-2.amazonaws.com/Braiden+Sunshine+-+Live+Again.zip)
    (HTTP HEAD, then a range read of each archive's last 64 kB on 2026-10-23; the S8 and S9
    sessions sit in the `season7multitracks` bucket).
- **Cambridge-MT:**
  - [Hugging Face re-host listing](https://huggingface.co/datasets/kwatcharasupat/mixing-secrets-rawstems)
    (revision b482eb2e);
  - [archived library page](https://web.archive.org/web/20250717000000*/cambridge-mt.com/ms/mtk/)
    (2025-07-17);
  - direct host, e.g.
    [Strobe](https://mtkdata.cambridgemusictechnology.co.uk/MTK021/Strobe_Maya_Full.zip) and
    [The Timezone](https://mtkdata.cambridgemusictechnology.co.uk/MTK017/TheTimezone_GOTGF_Full.zip);
  - [partial 2026 re-host](https://huggingface.co/datasets/fattyyyyyyyyyy/free_multitrack_2026);
  - the 2026-10-23 scan: HTTP HEAD and a range read of the last 64 kB of 132 archives on the
    direct host, e.g.
    [Zeno](https://mtkdata.cambridgemusictechnology.co.uk/MTK001/MR1003_Zeno_Full.zip) and
    [Rod Alexander](https://mtkdata.cambridgemusictechnology.co.uk/MTK019/RodAlexander_Canon_Full.zip);
    the Cloudflare challenge on
    [the library page](https://cambridge-mt.com/ms3/mtk/) and
    [the newer archive host](https://multitracks.cambridge-mt.com/Hollowstate_Hurricane_Full.zip).
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
