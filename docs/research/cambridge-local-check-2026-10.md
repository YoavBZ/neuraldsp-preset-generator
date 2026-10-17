# The unreached Cambridge-MT sessions hold no fresh DI+amp pair

*Research report, 2026-10-17. Follow-up to route 2 of
[fresh-di-amp-multitracks-2026-10.md](fresh-di-amp-multitracks-2026-10.md). Research, not a
declared plan. No multitrack archive was downloaded.*

Route 2 asked for the track lists of the Cambridge-MT sessions the cloud researcher could not
reach. This check got the lists for **11 of the 15** sessions it named. **None of the 11 has an
electric-guitar DI**, so none gives a DI+amp pair. A wider pass over the same mirror found
**0 new DI+amp candidates** and **2 DI-only sessions** that the repo has never used: Perpetual
Escape "Stop And Rise" and Dunning Kruger "Sascha". Neither is a clean fresh pick. Stop And Rise
is a progressive heavy rock session of unknown gain, and Sascha is a new song from a band already
spent in set 3. Four named sessions and everything added to the site since about mid-2025 are
still unchecked.

## How the lists were read

cambridge-mt.com and multitracks.cambridge-mt.com still answer this Mac with a Cloudflare
challenge (HTTP 403, `cf-mitigated: challenge`), both from `curl` and from a real browser pane.
The challenge asks for a "verify you are human" click, which this check did not do. Two routes
worked without it:

- **The Hugging Face re-host** `kwatcharasupat/mixing-secrets-rawstems` at revision
  `b482eb2e31aa15ff10489b3b23871a1e7a109198`, the same one set 5 used. It keeps the original
  Cambridge file names (for example `16_ElecGtr1.flac`) under stem folders. Its file listing
  came from the Hugging Face API, with no audio fetched. It holds 492 Cambridge sessions plus
  MUSDB18-HQ, and every session in it is also in the June-2025 scraper list
  ([scraper CSV](https://github.com/sai-soum/cambridge-mt_scrapper/blob/HEAD/data/multitrack_website/metadata_with_fine_genre.csv)),
  so it adds nothing newer than that list.
- **The publisher's direct archive host** `mtkdata.cambridgemusictechnology.co.uk`, which is not
  challenged and serves byte ranges. Reading an archive's ZIP central directory (the last few
  tens of kB) gives its file names and exact size. Only older sessions live there.

Track counts in the re-host match the site's "Full" counts for 10 of the 11 sessions. Mipso has
10 files against the site's 11, so one track is missing from the mirror.

## The 15 sessions with no indexed track list

| Session | Genre (site) | Guitar tracks found | Guitar DI? | Size |
|---|---|---|---|---|
| Redwood – Smoker And The Stoner | Alternative Country | `ElecGtr1`–`ElecGtr5`, `ElecGtr3DT`, `ElecGtr5DT`, `AcousticGtr`, `Banjo` | no | 364 MB FLAC |
| Paul Smith & 8 Days A Week Studio – The Weight | Classic Country Rock | `Guitar`, `Acoustic`, `Mando` | no | 302 MB FLAC |
| Xarxa – Cors Desbocats | Catalan Ska Rock | `ElecGtr1`–`ElecGtr5` (only `BassDI` is a DI) | no | 504 MB FLAC |
| Mady & Seus Namorados – Pirarucumbia | Cumbia | `ElecGtr1`–`ElecGtr3` | no | 313 MB FLAC |
| Hazael – Amor Que Lucha | Various Styles | `ElecGtr1`–`ElecGtr3`, five acoustic | no | 410 MB FLAC |
| Hazael – Esto Se Llama Vivir | Various Styles | `ElecGtr1`–`ElecGtr3` | no | 169 MB FLAC |
| Mikaela Davis & Southern Star – Cinderella | Psychedelic Folk Rock | `GTR 1 M80`, `GTR 1 TF29`, `GTR 2 M80`, `GTR 2 TF29` (two mics per guitar; DIs only on bass and harp) | no | 461 MB FLAC |
| Mikaela Davis & Southern Star – Home In The Country | Psychedelic Folk Rock | same layout as Cinderella | no | 365 MB FLAC |
| Mipso – Wallpaper Baby | Indie Folk/Americana | `Acoustic TDP-1`, `Mando`; no electric guitar | no | 160 MB FLAC |
| Erocy – Phantom | Moody Electronic Neo-Soul | none (drums, bass, Rhodes, synths, vocals) | no | 393 MB FLAC |
| Eddie Garrido – A Cry For Normalcy | Latin Jazz/Easy Listening | none (percussion, bass, keys, synths) | no | 143 MB FLAC |
| Escarràs – No Limits | Ska Fusion | not reached | ? | ? |
| FriendZWorldMusic – Triba/Bao Kuku | West African Fusion | not reached | ? | ? |
| Masé Jara – Petit Abisme | Brazilian Jazz | not reached | ? | ? |
| Perpetual Escape – Into My Dreams | Progressive Heavy Rock | not reached (site: 113 tracks in 4 ZIP parts) | ? | about 3.2 GB (earlier report) |

Sizes are the re-host's FLAC totals. The publisher's WAV ZIPs are larger. The four unreached
sessions are not in the re-host, and their archives are only on the challenged host. Escarràs
(55 tracks) is the only one of them likely to hold several electric guitars. Masé Jara has 10
tracks and FriendZ 16, so a DI+amp pair there is unlikely. Into My Dreams is filed under "Progressive Heavy Rock", like the band's four other sessions on
the site. Of those, "Duty & Memories", "Roots Of Mankind" and "Sin Six" have miked guitars with no
DI, and "Stop And Rise" has DIs with no amp tracks (see below).

The two Mikaela Davis sessions are the nearest miss: two microphones on each guitar amp, but no
DI. The mic names (M80, TF29, TF11) are Telefunken models, and Mipso's layout is the same, so
these may be Telefunken-recorded sessions. That doesn't matter here, because none has a DI.

## A wider pass over the re-host

The re-host also allows a second look at every session it holds, not only the 15. A name scan
for an electric-guitar DI found **75 sessions**. Each was checked against the repo's text (all of
`docs/`, `research/` and `learn/` on `origin/main`) by artist and song. Almost all are already
used, excluded or listed in the earlier report. Dark Ride "Dead Enemies" is not named by song in
the repo, but set 3 downloaded it (its local catalogue lists its unpaired DIs), and it is heavy
metal. Six more sessions turned up that the repo does not mention by song:

| Session | Genre (site) | Guitar tracks | Kind | ZIP | In scope? |
|---|---|---|---|---|---|
| Perpetual Escape – Stop And Rise | Progressive Heavy Rock | `ElecGtr01DI`–`ElecGtr09DI`, each with a `…DIDT` double except `04`; `ElecGtr12DI`, `ElecGtr13DI`; `ElecGtr10`, `ElecGtr11` have no DI; `SlideGtr`, 2 acoustic | **DI-only** (13 DIs, 19 files) | 657 MB, [direct](https://mtkdata.cambridgemusictechnology.co.uk/MTK017/PerpetualEscape_StopAndRise_Full.zip) | unknown gain; the band's genre suggests heavy |
| Dunning Kruger – Sascha | Indie Rock | `Gtr1`–`Gtr7`, `Gtr8DI` | **DI-only** (1 DI, no `Gtr8` amp track; its length matches no other guitar) | 579 MB, [direct](https://mtkdata.cambridgemusictechnology.co.uk/MTK005/DunningKruger_Sascha_Full.zip) | likely clean (band stratum is clean); band already spent |
| SkalyVan – Agony / All To End | Metalcore | `ElecGtr1DI`–`ElecGtr5DI` (Agony adds `ElecGtr1DTDI`) | DI-only | challenged host | no (metal) |
| SkalyVan – A Picture Of S\*\*t | Metalcore | `ElecGtr2DI` + `ElecGtr2DIDT`; `ElecGtr1`, `ElecGtr3`–`7` | DI-only for part 2 | challenged host | no (metal) |
| Szymon Skiba – Some Trashy Thrash, I Guess | Metal Instrumental | `ElecGtrDI1`–`ElecGtrDI4` | DI-only | challenged host | no (metal) |

The two direct-link file lists above were read from the publisher's archives. The others come
from the re-host.

**Stop And Rise** is the larger find. It has 13 played guitar parts as DIs, plus doubles, and no
amp tracks for them, so it can only be a known-target test: re-amp the DIs through our own
plugins and match the result. The site files it under "Progressive Heavy Rock", the same label
set 3 used when it put the band's other sessions on its heavy-genre "not obtained" list. Its gain
is unknown until someone listens, and some parts may be clean or crunch. It has never been used
in the repo.

**Sascha** is a third song from Dunning Kruger, whose "EnDance" and "Japan Song" are set 3
held-out and marked spent ("excluded from further tuning, training, or confirmation",
`docs/set3-heldout-use-ledger.json`). Whether a new song from a spent band counts as fresh is the
ML session's call. It gives one DI-only part at most.

## What this changes

- **New DI+amp candidates: 0.** The route-2 hope of "a few" fresh pairs is not met for the 11
  sessions that could be read.
- **New DI-only candidates: 2** (Stop And Rise, Sascha), both with caveats. These join the
  earlier report's DI-only route 3 (Strobe "Maya", The Apprehended, MekaPhil, The Timezone
  "GOTGF").
- **Still unchecked:** Escarràs "No Limits", FriendZWorldMusic "Triba/Bao Kuku", Masé Jara
  "Petit Abisme", Perpetual Escape "Into My Dreams", and every session added since about
  mid-2025. Reaching them needs someone to pass the Cloudflare check in a browser by hand. After
  that, the session pages give the ZIP links, and the ZIP central directories give the track
  names without a full download. Escarràs is the one worth that effort first.

**Same-take note.** Neither DI-only candidate needs the same-take test, since there is no amp
track to pair. If the unchecked sessions turn up name pairs, the earlier warnings still apply:
run the waveform same-take test on each pair (set 5 rejected 28 of 59 declared DIs), and prefer
the publisher archive over the re-host, whose tracks are trimmed to different lengths.

**Licence.** Same as the rest of the library: each session's Readme grants use "for educational
purposes only", with no commercial use without the copyright holders' permission. The re-host's
dataset card restricts it to non-commercial research and educational use. No session here has a
CC licence or an explicit ML permission.
