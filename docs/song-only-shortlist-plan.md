# How close do generate's presets land? And does a shortlist help?

Declared on 2026-10-05, before any shortlist is generated, rendered or scored. It was
revised twice the same day after independent reviews, still before any run.

The product's main promise, "give it a song, get a preset that sounds like it", has
never been measured. The `generate` skill researches a song and writes one preset;
nothing has checked how close that preset is to the recording. This plan measures
that, and measures the product change proposed next: a shortlist of four presets
across Morgan's amps, from which the user picks by ear on an audition page.

It needs a DI for scoring only. The runs that write the presets get the song alone.

## Parts and baselines

- **Parts.** The 25 development parts amp reach used (`docs/amp-reach-results.md`):
  a clear recorded lag, and a DI that plays in both halves. 9 bands, 16 songs.
  Crops cut by rule 1 (`~/ndsp-presets/references/validation-crops`), as the panels
  were.
- **Baselines** come from the judge distances amp reach stored
  (`~/ndsp-presets/runs/kill/amp-reach.json`) for the 108 factory presets of the
  three amps (44 SW50R, 34 PR12, 30 AC20) and the template, all with the rule set R.
- **The renders are comparable.** Fresh renders by `scripts/render_shortlists.py` (six
  factory presets across the three amps, plus the template, through 4 parts' DIs)
  reproduced the stored distances within 0.0002 (log) on all 168 readings. The
  same check runs on every part (see Canaries).

## The runs that write the presets

**How they run.** One agent per song (16), launched from this session as
general-purpose subagents. Each is told only to read and follow its sandbox's
`BRIEF.md`, and follows the `generate` skill as a user's run would.
`scripts/prepare_shortlist_runs.py prepare` builds the sandboxes in
`~/shortlist-sandboxes`, outside the data root and outside any checkout:

- **`plugin/`:** an export of the plugin at the declared commit. It leaves out
  `docs/`, `tests/`, every script the skills don't use, and the files that name or
  link the project (README, `SECURITY.md`, `pyproject.toml`, `.claude-plugin/`).
  Nothing in it names the validation data or the results; `packs/paths.py` names the
  default data root, `~/ndsp-presets`. An installed plugin does carry `docs/`; it is
  left out here because two documents the skill links discuss development parts. The
  brief says the gap is deliberate.
- **`excerpts/part-N.wav`:** the part's 10-second mix crop (`mix.wav`, a unity sum of
  the session's tracks, vocals included), renamed.
- **`request.json`:**
  - band, song, source, and where in the song the excerpt starts;
  - the guitar tracks in the session's mix;
  - the part's track name;
  - **how the part plays**, measured from its DI: its pace in notes a second (against
    the thirds of the DI library), and whether it plays through the excerpt. This is
    playing only, nothing about tone, and stands in for what a user would say about
    the part.
- **`data/`:** a data root holding a copy of the user's learned notes.
- **`bin/python-audio`:** the interpreter with the analysis extra.

`parts-map.json` stays in `~/ndsp-presets/runs/shortlists`. It records which part each
`part-N` is, and a hash of each sandbox's plugin.

**The request,** per part, as a user would put it: a Morgan preset for the guitar part
named by its track name in this song, with the excerpt around that time. The excerpt
is called a rough mix of the session, which it is. **The brief allows:**
- reading and running the sandbox's plugin;
- reading the plugin's factory presets (not `User/`), but only after G1–G4 are written
  for every part;
- WebSearch, with github.com and githubusercontent.com blocked, and WebFetch: at most 8
  searches and 12 fetches per song.

**It forbids:**
- github.com, downloads, and reaching the web from Bash;
- the Skill tool (it would load the installed copy);
- other files on disk, and writing outside the sandbox (no `/tmp`);
- installing presets or writing learned notes.

**How commands are written:**
- Every Bash command starts with `cd` into the sandbox, since each starts in this
  repository otherwise. It has no other `cd`, no `..` out of the sandbox, no `~`,
  `$HOME` or command substitution.
- Read, Grep and Glob get absolute paths in the sandbox or the factory folder.
- JSON files are written with the Write tool.
- **No questions:** where the skill would ask, the run states its assumption.

**What it returns, per part, in this order:**
1. **G1:** the preset it would deliver today, written with `apply_spec.py` from the
   shipped template as the skill says, with the arguments used.
2. **G2–G4:** three alternatives written the same way. G1–G4 are on at least two of
   the three amps, and differ in amp, gain, drive, EQ or cab, not only in time effects.
3. **F1–F4:** four factory presets it would audition, on at least two amps; F1 is its
   first choice. These come only after G1–G4, so the generated presets are written
   before any factory preset is read.
4. A one-line reason for each, the research sources, and the fingerprint's regime and
   caveats.

**`collect` checks the results** before anything is rendered:
- **The sandbox's plugin** still hashes as built.
- **Generated presets:** each is re-made from a clean export of the declared commit
  with its recorded arguments, and must match. So a generated preset can't be a
  factory preset in disguise, or the product of an edited copy of the tools.
- **Factory presets:** names must match the folder exactly.
- **Within a list:** four entries that differ in what is scored, meaning the selected
  amp's modules and the shared ones less what R switches off. Two presets differing
  only in, say, reverb would sound alike. Each list is on at least two amps, and no
  generated preset sounds as a factory one does.
- **Coverage:** all parts present, apart from excluded songs (below).

A run that fails these is redone once (`redo`, below).

**Leak control is by instruction and audit, not enforcement.** After the runs,
`scripts/audit_shortlist_runs.py` checks every tool call and result in every
transcript against what the brief allows, and flags:
- **Bash:** a command that doesn't open with `cd` into its sandbox, changes directory
  again, uses shell expansion, reaches the network or a search tool (`curl`, `wget`,
  `mdfind`, `git`, a URL, …), or holds any path that resolves outside the sandbox,
  the factory folder, the interpreter or the system's folders. That includes `..`,
  `~` and paths inside quoted code.
- **Files:** a Read, Write, Edit, Grep or Glob with no path, a path that resolves
  outside the sandbox (writes) or the sandbox and factory folder (reads), a factory
  `User/` path, or a pattern that climbs out.
- **Web:** a WebSearch without the github block, a github fetch, or more searches or
  fetches than allowed.
- **Order:** the factory folder opened before every G1–G4 was written.
- **Never:** the Skill tool or a nested agent.
- **Results:** text naming this project, its repository or the validation data.

**What a flag means.** A run stands only if every flag is one of these, judged by
reading the flagged call (and, for a search, the listing):
- a write outside the sandbox that reads nothing;
- a Bash command that breaks only the `cd` rule and touches nothing outside;
- at most 2 searches or fetches over the limit;
- a search listing naming the project that was not opened.

Any other flag discards the run, and `prepare_shortlist_runs.py redo SONG` builds that
song a fresh sandbox (the flagged one moved aside) for one new agent. If the repeat is
flagged too, the song is excluded (`collect --exclude SONG`). More than 5 parts
excluded voids the measurement; `collect` and the scorer both refuse it. All counts
are reported.

## Rendering and scoring

- **Render** (`scripts/render_shortlists.py`):
  - every preset is checked against the hash `collect` recorded;
  - one fresh plugin process per part, reused within the part;
  - a discarded warm-up; then the template with R, G1–G4 and F1–F4 with R, and the
    template again;
  - then G1–G4 and F1–F4 again in reverse order, which is each render's repeat;
  - every render's peak is recorded; non-finite audio stops the run;
  - R switches off time effects, gate, doubler, transpose and the amp's spring reverb,
    because the amp tracks are dry. So the time effects generate chooses are not
    scored.
- **Score** (`scripts/score_shortlists.py`): the judge, at the recorded lag less the
  52-sample latency. Half A (1.0–5.5 s), half B (5.5–10 s) and the full window;
  both band sets.

## Arms

Each arm gets one distance per part and band set.

**One preset** (the mean of its half-A and half-B distances):
- **G1** (generate today);
- **F1** (the agent's first factory pick);
- **template+R**;
- **random-1**: the median over the 108 factory presets.

**Best of a list, picked by a perfect ear.** This is an upper bound on what listening
can do. The preset chosen on one half is scored on the other, and both directions are
averaged:
- **G4** and **F4**;
- **M4**: {G1, G2, F1, F2}, the mixed shortlist;
- **house-4**, the control without research: a fixed list of four factory presets, the
  same for every song.
  - **How it's built:** for each part, greedily on the other bands' parts of all 25
    stored ones. Each step adds the preset that most lowers the median of band medians
    of log(list / the part's random-1).
  - **How strong it is:** on the stored data it is already about 10% closer than
    random-4 (−0.096 under both band sets; 22 and 20 of 25 parts), and closes about
    half of random-4's distance to the oracle.
  - **What it isn't:** something a product could ship. It is tuned to these mostly
    clean parts, and a fixed list can't follow a song's genre.
- **random-4**: the median, over 50,000 random 4-lists from the 108, of the list's
  distance. The median, not the mean, because a single draw beats the mean more often
  than not. It matched exact enumeration to 5 decimals in review.
- **random-4 clean**: the same over the 55 clean presets (reported);
- **oracle**: all 108.

**A refused render:**
- A G preset whose render is silent on both passes, or refused by the judge, counts
  as a loss: log ratio +5 against its arm, on whichever side of a comparison it
  stands. Two refused arms tie. It is never the pick of a list.
- A refused template or F render stops the run, and so does silence on one pass only
  (Canaries).

## Decisions

Each comparison is a log ratio (negative means the first arm is closer). Two kinds,
each required under both band sets:
- **"Better"**, as in the kill tests: the median of band medians is at most log 0.9
  (10% closer), and the first arm is closer on more than half the parts. The 10% bar
  sits below the judge's validated 0.150 cut, as it did in the kill tests.
- **"Not worse"**: the median is at most 0, and the first arm is closer on at least
  half the parts.

**Too close to call.** A comparison is **inconclusive** when moving its median by 0.03,
or its count by one part, would change the verdict under either band set. It then
takes its "doesn't hold" branch, labelled inconclusive.

| | Comparison | Holds (passes, conclusively) | Doesn't hold |
|---|---|---|---|
| D1 | G1 better than template+R | generate's preset is shown closer than its template | generate's report stops implying its preset is closer than the template |
| D2 | F4 better than G4; M4 better than G4 | the shortlist is built from factory presets, or two of each (M4). If both hold, the one with the better worse-band median | the shortlist stays generated (G), which is what generate already writes and what follows the research |
| D3 | S4 not worse than house-4; S4 better than random-4 | the skill may say the shortlist did as well as a list tuned on these recordings, or better than a random one | it says that hasn't been shown on these mostly clean parts |

S is the source D2 chose.

**What the stored data says before the run** (from the reviews):
- **D1 is demanding:** no single factory preset, used for every part, passes it
  against the template. The best is −0.06.
- **D3's "better than random-4"** needs S4 to close about two-thirds of the way from
  random-4 to the oracle (oracle vs random-4: −0.19 / −0.22). house-4 closes about
  half.
- **The oracle beats house-4** by only −0.14 / −0.17, so "better than house-4" could
  hardly hold. That is why D3 asks only "not worse".
- **Chance of a false "holds"** when two arms are equally good: about 2.7% for single
  presets and 0.1% for 4-lists.

**Reported, not deciding:**
- **Each list against its first choice** (G4 vs G1, F4 vs F1, M4 vs G1): the gain a
  perfect ear makes by hearing four. On the stored data, random-4 beats random-1 by
  −0.20 / −0.26, so this is expected to hold for any varied list. Whether a real ear
  gains it is the listening check's question.
- **Each list (G4, F4, M4) against house-4 and random-4**, so the choice of S hides
  nothing.
- **Single presets and baselines:** G1 vs F1, G1 vs random-1, G4 and F4 vs
  template+R, random-4 vs template+R, house-4 vs random-4, S4 vs random-4 clean, S4
  vs the oracle.
- **Headroom closed:** per arm, the median of band medians of the share of the way
  from random-4 to the oracle.
- **Near the answer:** per arm, the band-weighted share of parts within 0.150 of the
  oracle (the judge's validated cut).
- **Detail:** band sign-flip p's; the house lists.
- **Amps:** which amps G1–G4 and F1–F4 use, and the band-weighted share of entries on
  an amp the clean menus' reach sets count acceptable for the part
  (`docs/reach-sets.json`).
- **Refusals:** refused and silent G renders, with the judge's reasons.

There are three decisions and several readings on the same 25 parts, with no
correction for multiple comparisons. The "too close to call" rule is the only guard.

## Canaries

Each must hold, or the run stops and nothing is scored:
- **Against the panels:** the template and F renders reproduce the stored distances
  within 0.01 (log) on every reading. None may be refused here or in the panel.
- **Repeats:** every G and F render's repeat, made in reverse order in the same
  process, agrees within 0.01 on every reading. Neither pass may be silent while the
  other isn't.
- **The template's repeat** in each process drifts under 0.1 dB RMS.
- **Coverage:** the renders cover exactly the manifest's parts.

## Afterwards: the listening check (separate, needs the user)

D2 and D3 use a perfect ear on the part's own DI. The product plays candidates through
another performance (a DI riff of a similar pace), and a real ear isn't perfect. A
short blind session (about 15 minutes) on parts not used to build the page would
measure that. The user hears the song excerpt and the four shortlisted renders
through another part's DI, then picks one. The judge then scores the pick on the
part's own DI against the first choice and the best of the four. That session is
declared separately, after the page exists, and it decides whether the audition page
is the main path or an option.

## Limits

- **Development parts:** the same 25 parts the kill tests and amp reach used, and
  mostly clean to edge of breakup. The house list is tuned to them.
- **No real songs:** the excerpts are unmixed sums of the stems, 10 seconds long, not
  mastered songs. Real mixes add EQ, compression and reverb, which a run may
  misread.
- **The excerpt holds every mic of the part:** a Cambridge mix includes the part's
  second mic (Mic2 or Far), but the judge scores one (for Passing Ships ElecGtr6, the
  reference itself is Mic2).
- **Telling the guitars apart:**
  - 17 of the 25 parts share a song with other development parts.
  - Dom McLennon's GTR 1 and GTR 2 excerpts overlap.
  - All 25 parts play through their whole excerpt, so the description adds only a
    pace, and two parts of one song can read alike.
  - The track name, the session's guitar tracks and the pace are less than a user
    would say ("the crunchy rhythm guitar on the left"). So the runs may describe the
    song more than the part.
- **One run per song:** agents vary between runs, and that spread isn't measured.
- **What the agents can see:** they run as subagents of this session. Besides the
  brief, they see:
  - the repository's five latest commit titles, which name amp-level findings ("a set
    of amps") but never a part;
  - the user's memory index, which names the data root;
  - the installed plugin's skills, which the brief forbids invoking.

  The amps the runs choose are reported.
- **Leak control** is by instruction and audit, as above.
- **Cross-amp distances** lie outside the range listening validated.
- **Morgan only:** Tone King has no factory panel here.
