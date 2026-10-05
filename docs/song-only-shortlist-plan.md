# How close do generate's presets land? And does a shortlist help?

Declared on 2026-10-05, before any shortlist is generated, rendered or scored. Revised
the same day after an independent review, still before any run.

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
general-purpose subagents, each told to follow its sandbox's brief. Each follows the
`generate` skill as a user's run would. `scripts/prepare_shortlist_runs.py` builds
the sandboxes in `~/shortlist-sandboxes`, outside the data root and outside any
checkout:

- `plugin/`: an export of the plugin at the declared commit. It leaves out `docs/`,
  `tests/`, every script the skills don't use, and the files that link the project's
  repository (README, `SECURITY.md`, `.claude-plugin/`). So nothing in it names where
  the validation data or the results live. An installed plugin does carry `docs/`; it
  is left out here because two documents the skill links discuss development parts.
  The brief says the gap is deliberate.
- `excerpts/part-N.wav`: the part's 10-second mix crop (`mix.wav`, a unity sum of the
  session's tracks, vocals included), renamed.
- `request.json`:
  - band, song, source, and where in the song the excerpt starts;
  - the session's guitar tracks;
  - the part's track name;
  - **how the part plays**, measured from its DI: its pace in notes a second (against
    the thirds of the DI library), and whether it plays through the excerpt. This is
    playing only, nothing about tone, and stands in for what a user would say about
    the part.
- `data/`: a data root holding a copy of the user's learned notes.
- `bin/python-audio`: the interpreter with the analysis extra.

`parts-map.json`, which says which part each `part-N` is, stays in
`~/ndsp-presets/runs/shortlists`.

**The request,** per part, as a user would put it: a Morgan preset for the guitar part
named by its track name in this song, with the excerpt around that time. The excerpt
is called a rough mix of the session, which it is. **The brief allows:**
- reading and running the sandbox's plugin, and reading the plugin's factory presets
  (not `User/`);
- WebSearch and WebFetch, at most 8 searches and 12 fetches per song;
- **no** github.com, downloads, other files on disk, the Skill tool (it would load the
  installed copy), installing presets or writing learned notes;
- every Bash command starts with `cd` into the sandbox, since each starts in this
  repository otherwise; Read, Grep and Glob get absolute paths in the sandbox or the
  factory folder;
- **no questions:** where the skill would ask, the run states its assumption.

**What it returns, per part:**
- **G1–G4:** four distinct generated presets, written with `apply_spec.py` from the
  shipped template, on at least two of the three amps, with the arguments used. G1 is
  the one it would deliver today.
- **F1–F4:** four distinct factory presets it would audition, on at least two amps.
  F1 is its first choice.
- A one-line reason for each, the research sources, and the fingerprint's regime and
  caveats.

**`collect` checks the results** before anything is rendered:
- **Generated presets:** each is re-made from the shipped template with its recorded
  arguments and must match, so a generated preset can't be a factory preset in
  disguise, and none may equal one.
- **Factory presets:** names must match the folder exactly.
- **Lists:** four distinct entries on at least two amps; all 25 parts present.

A failure is fixed by re-running that song's agent once.

**Leak control is by instruction and audit, not enforcement.** After the runs,
`scripts/audit_shortlist_runs.py` searches every tool call and result in every
transcript. A run is flagged when:
- a Bash command doesn't start with `cd` into its sandbox, or names the data root, a
  checkout of this project (other than the interpreter the brief names), `~/.claude`,
  the home folder or a parent folder;
- a Read, Grep or Glob has no path, or one outside the sandbox and factory folder;
- it fetches github.com, or calls the Skill tool or a nested agent;
- a result (a file, a search, a page) names this project, its repository or the
  validation data.

A flag on a Bash command that only breaks the `cd` rule is judged by reading the
command (never its result): a command that reads nothing outside the sandbox stands.

A flagged run is discarded and repeated once with a fresh agent. If the repeat is
flagged too, that song's parts are left out. If more than 5 parts are left out, the
measurement is void. All counts are reported.

## Rendering and scoring

- **Render** (`scripts/render_shortlists.py`):
  - one fresh plugin process per part, reused within the part;
  - a discarded warm-up; then the template with R, G1–G4 and F1–F4 with R, and the
    template again;
  - then G1–G4 and F1–F4 again in reverse order, which is each render's repeat;
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
- **house-4**, the control without research: a fixed list of four factory presets,
  the same for every song. For each part it is built greedily on the other bands'
  parts only: each step adds the preset that most lowers the median of band medians
  of log(list / the part's random-1). On the stored data it is already about 10%
  closer than random-4 (−0.096 under both band sets; 22 and 20 of 25 parts). It is a
  strong bar, and one a product couldn't ship as is: it is tuned to these mostly clean
  parts, and a fixed list can't follow a song's genre;
- **random-4**: the median, over 50,000 random 4-lists from the 108, of the list's
  distance. The median, not the mean, so that one agent's list is compared with a
  typical random list rather than an average a single draw beats more often than not;
- **random-4 clean**: the same over the 55 clean presets (reported);
- **oracle**: all 108.

A G preset whose render is silent or refused by the judge counts as a loss: log ratio
+5. It is never the pick of a list. A refused template or F render stops the run
(Canaries).

## Decisions

Each comparison is a log ratio (negative means the first arm is closer). As in the
kill tests, a comparison **passes** when, under both band sets:
- the median of band medians is at most log 0.9 (10% closer);
- and the first arm is closer on more than half of the parts.

**Too close to call.** A comparison is **inconclusive** when, under either band set,
its median is within 0.03 of log 0.9, or the parts it's closer on are within one of
half. An inconclusive comparison takes its "doesn't hold" branch and is reported as
inconclusive.

| | Comparison | Holds (passes, conclusively) | Doesn't hold |
|---|---|---|---|
| D1 | G1 vs template+R | generate's preset is shown closer than its template | generate's report stops implying its preset is closer than the template |
| D2 | F4 vs G4; M4 vs G4 | the shortlist is built from factory presets, or two of each (M4). If both hold, the one with the better worse-band median | the shortlist stays generated (G), which is what generate already writes and what follows the research |
| D3 | S4 vs its first choice (G1, or F1 when S = F) | even a perfect ear gains 10% from hearing four: the audition page is the main path | the page is offered, but generate still delivers its first choice as the answer |
| D4 | S4 vs house-4; S4 vs random-4 | the skill may say the shortlist landed closer than a fixed list, or a random one | it says the research isn't shown to beat that list on these mostly clean parts |

S is the source D2 chose.

**Reported, not deciding:**
- G4 vs G1, F4 vs F1, G1 vs F1, G1 vs random-1, F4 vs G4, M4 vs G4;
- G4 and F4 vs template+R, random-4 vs template+R, house-4 vs random-4;
- S4 vs random-4 clean, and S4 vs the oracle;
- per arm, the band-weighted share of parts within 0.150 of the oracle (the judge's
  validated cut);
- band sign-flip p's;
- the house lists;
- which amps G1–G4 and F1–F4 use, and the share on amps `docs/reach-sets.json`
  counts acceptable for the part;
- refused or silent G renders.

There are four decisions and several readings on the same 25 parts, with no
correction for multiple comparisons. The "too close to call" band is the only guard.

## Canaries

Each must hold, or the run stops and nothing is scored:
- **Against the panels:** the template and F renders reproduce the stored distances
  within 0.01 (log) on every reading. None may be refused here or in the panel.
- **Repeats:** every G and F render's repeat, made in reverse order in the same
  process, agrees within 0.01 on every reading.
- **The template's repeat** in each process drifts under 0.1 dB RMS.

## Afterwards: the listening check (separate, needs the user)

D2–D4 use a perfect ear on the part's own DI. The product plays candidates through
another performance (a DI riff of a similar pace), and a real ear isn't perfect. A
short blind session (about 15 minutes) on parts not used to build the page would
measure that. The user hears the song excerpt and the four shortlisted renders
through another part's DI, then picks one. The judge then scores the pick on the
part's own DI against the first choice and the best of the four. That session is
declared separately, after the page exists.

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
  - The track name, the session's guitar list and the pace are less than a user
    would say ("the crunchy rhythm guitar on the left"), so the runs may describe
    the song more than the part.
- **One run per song:** agents vary between runs, and that spread isn't measured.
- **What the agents can see:** they run as subagents of this session. Besides the
  brief, they see the repository's five latest commit titles and the user's memory
  index. The titles name amp-level findings ("a set of amps"), never a part. The
  amps the runs choose are reported.
- **Leak control** is by instruction and audit, as above.
- **Cross-amp distances** lie outside the range listening validated.
- **Morgan only:** Tone King has no factory panel here.
