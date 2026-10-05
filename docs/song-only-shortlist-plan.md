# How close do generate's presets land? And does a shortlist help?

Declared on 2026-10-05, before any shortlist is generated, rendered or scored.

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
- **The renders are comparable.** Rendered fresh by `scripts/render_shortlists.py`, six
  factory presets across the three amps and the template, through 4 parts' DIs,
  reproduced the stored distances within 0.0002 (log) on all 168 readings. The
  same check runs on every part (see Canaries).

## The runs that write the presets

One agent per song (16), each following the `generate` skill as a user's run would.
`scripts/prepare_shortlist_runs.py` builds each agent's sandbox:

- `plugin/`: an export of the plugin at the declared commit, without `docs/` and
  `tests/`, as an installed plugin is;
- `excerpts/part-N.wav`: the part's 10-second mix crop (`mix.wav`, a unity sum of the
  session's tracks, vocals included), renamed;
- `request.json`: band, song, source, the part's track name, and where in the song
  the excerpt starts;
- `data/`: a data root holding a copy of the user's learned notes, so the run reads
  them as a user's would and writes nothing outside the sandbox.

**The request**, per part, as a user would put it: a Morgan preset for the guitar
part named by its track name in this song, with the excerpt around that time. The
excerpt is called a rough mix of the session, which it is. The agent may:

- use WebSearch and WebFetch (at most 8 searches per song), and download nothing;
- read and run anything under `plugin/` and its sandbox, and read the plugin's
  factory presets (`/Library/Audio/Presets/Neural DSP/Morgan Amps Suite`, not
  `User/`);
- read nothing else on disk. In particular not the validation data, `runs/`, the
  repository or its documents; and on the web, not this project's own repository,
  whose documents discuss these recordings. It does not install presets or write
  learned notes.

It cannot ask a question; where the skill would ask one, it states its assumption.

**What it returns, per part:**
- **G1–G4:** four generated presets, written with `apply_spec.py` from the shipped
  template, on at least two of the three amps. G1 is the one it would deliver today.
- **F1–F4:** four factory presets it would audition, on at least two amps. F1 is its
  first choice.
- A one-line reason for each, the research sources, and the fingerprint's regime and
  caveats.

**Leak audit.** After the runs, every agent transcript is searched for reads outside
the allowed places, and for fetches of the project's repository. A run that read the
validation data, `runs/`, the repository's `docs/` or the project's GitHub pages is
discarded and repeated once with a fresh agent. Both counts are reported.

## Rendering and scoring

- **Render** (`scripts/render_shortlists.py`): per part, one fresh plugin process
  reused within the part, as the panels were. A discarded warm-up, then the template
  with R, G1–G4 and F1–F4 with R, and the template again. R switches off time
  effects, gate, doubler, transpose and the amp's spring reverb, because the amp
  tracks are dry. So the time effects generate chooses are not scored.
- **Score** (`scripts/score_shortlists.py`): the judge, at the recorded lag less the
  52-sample latency. Half A (1.0–5.5 s), half B (5.5–10 s) and the full window;
  both band sets.

## Arms

Each arm gets one distance per part and band set.

**One preset** (the mean of its half-A and half-B distances):
- **G1** (generate today);
- **F1** (the agent's first factory pick);
- **template+R**;
- **random-1**: the mean over the 108 factory presets.

**Best of a list, picked by a perfect ear.** This is an upper bound on what listening
can do. The preset chosen on one half is scored on the other, and both directions are
averaged:
- **G4** and **F4**;
- **random-4**: the exact expectation over every 4-preset subset of the 108, from
  ranks, as `scripts/reach_sets.py` computes it;
- **oracle**: all 108.

## Decisions

Each comparison is a log ratio (negative means the first arm is closer). As in the
kill tests, a comparison **passes** when, under both band sets:
- the median of band medians is at most log 0.9 (10% closer);
- and the first arm is closer on more than half of the parts.

| | Comparison | If it passes | If it fails |
|---|---|---|---|
| D1 | G1 vs template+R | generate's preset is shown closer than its template | generate's report stops implying its preset is closer than the template, and the shortlist with listening becomes the way to get closer |
| D2 | G4 vs random-4 | research adds to a generated shortlist | a generated shortlist is no better than four random factory presets |
| D3 | F4 vs random-4 | research adds to choosing factory presets | the agent's factory picks are no better than random ones |

**What the product shortlist is built from:**
- D2 and D3 both pass: two generated presets and two factory ones.
- Only one passes: four from the source that passed.
- Neither passes: four factory presets across the acceptable amps, chosen for
  spread. The report then says the research is not shown to help the shortlist.

**Reported, not deciding:**
- G4 vs F4, G1 vs F1, G1 vs random-1, random-4 vs template+R (what a shortlist is
  worth at all), and G4 vs the oracle;
- per arm, the band-weighted share of parts within 0.150 of the oracle (the judge's
  validated cut);
- a band sign-flip p for D1–D3;
- which amps G1–G4 and F1–F4 use, against the acceptable amps of
  `docs/reach-sets.json`.

## Canaries

Each must hold, or the run stops and nothing is scored:
- **F renders** (factory presets the panels also rendered) reproduce the stored
  distances within 0.01 (log) on every reading.
- **The template** reproduces its stored distances within 0.01.
- **The repeated template render** in each process drifts under 0.1 dB RMS.

## Afterwards: the listening check (separate, needs the user)

D1–D3 use a perfect ear on the part's own DI. The product plays candidates through
another performance (a DI riff of a similar style), and the user's ear isn't perfect.
A short blind session (about 15 minutes) on parts not used to build the page would
measure that. The user hears the song excerpt and the four shortlisted renders
through another part's DI, then picks one. The judge then scores the pick on the
part's own DI against G1 and the best of the four. That session is declared
separately, after the page exists.

## Limits

- **Development parts:** the same 25 parts the kill tests and amp reach used, and
  mostly clean to edge of breakup.
- **No real songs:** the excerpts are unmixed sums of the stems, 10 seconds long, not
  mastered songs. Real mixes add EQ, compression and reverb, which a run may
  misread.
- **The track name is the only description of the part.** A real user would say
  more ("the crunchy rhythm guitar"), so this understates the request a run
  usually gets.
- **One run per song:** agents vary between runs, and that spread isn't measured.
- **Cross-amp distances** lie outside the range listening validated.
- **Morgan only:** Tone King has no factory panel here.
