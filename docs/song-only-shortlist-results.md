# Generate's presets and a four-preset shortlist, measured: research not shown to beat the template or a random list

Computed as declared in `docs/song-only-shortlist-plan.md` (with its dated amendments),
on 2026-10-05:
- **Runs:** 16 agents, one per song, 25 development parts, sandboxes at b5dbcbb.
- **Rendered** with `scripts/render_shortlists.py`.
- **Scored** with `research/score_shortlists.py`. `docs/song-only-shortlist.json` is the
  output. The scorer was re-run once after a fix to a reported figure (below); every
  decision and every other reading came out identical.

Figures are log ratios under the recording (default) / union band sets; negative means
the first arm is closer.

## The runs held up, under an amended audit

- **Audit:** `research/audit_shortlist_runs.py` checked every transcript.
  - It found 8 flags, all one kind: a `$` used as a `grep` anchor, or as the variable
    of a loop that only echoed labels, in commands whose paths all stayed in the
    sandbox.
  - No run read the validation data, the results, the repository or GitHub. Every run
    wrote all its generated presets before opening the factory folder.
- **That kind was made excusable only after it had been seen.**
  - The brief forbade any `$`. The amendment was made at 20:41, after the first runs had
    shown these flags and while 7 of the 16 were still running, but before any render or
    score.
  - Under the rules as declared before the runs, the 4 songs with these flags (Signs,
    Long Way Home, Drag Me Down and First Offering; 5 parts) would have been run again.
  - The same amendment removed two false positives: Claude Code's notes naming the
    session folder, and a lone `"/"` string in code.
- **The audit was tightened twice more after the runs.** It now also reads the scripts a
  run writes and then runs (6 runs wrote some: tempo estimates, factory summaries), and
  it no longer passes a `$'…'` as harmless. Re-run on every transcript, it gives the
  same 8 flags.
- **Smaller slips, from the agents' own reports:**
  - Several recursive listings of the factory folder printed the names in `User/`; none
    opened a file there.
  - Some `show.py` calls left out `--data-dir`; the data root then resolved inside the
    sandbox.
  - A few commands used `^` anchors, loops without `$`, or a stray shell variable.
- **`collect`:** all 25 parts passed. Every generated preset re-made exactly from its
  recorded arguments; every list held four presets that differ in what is scored, on
  at least two amps.
- **Canaries:**
  - The template and F renders reproduce the panels within 0.002 (log), over 750
    readings.
  - Every repeat agrees within 0.01.
  - The template's repeat drifts at most 0.052 dB.
  - No generated render was silent or refused.
- **The pilot** (Bloomlight, before the brief's last fix) is kept unscored in
  `~/ndsp-presets/runs/shortlists-pilot/`.

## Decisions

| | Comparison | Median of band medians | Closer on | Holds? |
|---|---|---|---|---|
| D1 | G1 better than template+R | −0.059 / −0.031 | 13 / 12 of 25 | **no** |
| D2 | F4 better than G4 | −0.043 / +0.042 | 11 / 10 | no |
| D2 | M4 better than G4 | 0.000 / 0.000 | 7 / 7 | no |
| D3 | G4 not worse than house-4 | +0.048 / −0.078 | 8 / 15 | **no** |
| D3 | G4 better than random-4 | −0.004 / −0.046 | 16 / 16 | **no** |

None is inconclusive under the declared rule. What follows, from the plan's table:

1. **D1:** generate's preset is not shown to land closer than the template it starts
   from. Generate's report must stop implying it is.
2. **D2:** the shortlist stays generated (G). Neither factory picks nor a mix of the two
   did better.
3. **D3:** a researched four-list is not shown to beat four random factory presets, nor
   to match a fixed list tuned on these recordings. The skill must say so.

## Readings (reported, not deciding)

**Choosing among four helps, whoever chose the four.** With a perfect ear (picked on one
half by the judge, scored on the other):

| | Median | Closer on |
|---|---|---|
| G4 vs template+R | −0.198 / −0.183 | 18 / 17 |
| G4 vs G1 | −0.099 / −0.112 | 17 / 20 (inconclusive) |
| F4 vs F1 | −0.174 / −0.206 | 19 / 19 (passes) |
| random-4 vs template+R | −0.059 / −0.041 | 17 / 16 |

**Single presets against a typical factory preset (random-1):**

| | Median | Closer on | p |
|---|---|---|---|
| G1 | −0.015 / −0.057 | 20 / 20 | 0.049 / 0.023 |
| template+R | −0.131 / −0.193 | 20 / 20 | 0.19 / 0.12 |

The p values are band sign-flip tests.

**How near the best factory preset each arm gets** (band-weighted share of parts within
0.150 of the oracle):

| Arm | Share |
|---|---|
| house-4 | 0.61 / 0.46 |
| random-4 clean | 0.52 / 0.49 |
| F4 | 0.48 / 0.44 |
| random-4 | 0.42 / 0.42 |
| G4 | 0.39 / 0.39 |
| template+R | 0.29 / 0.29 |
| F1 | 0.08 / 0.08 |
| G1 | 0.04 / 0.04 |
| random-1 | 0.03 / 0.03 |

- **Headroom closed** (how far from random-4 toward the oracle):

  | Arm | Headroom |
  |---|---|
  | house-4 | 0.61 / 0.47 |
  | F4 | 0.27 / 0.26 |
  | G4 | 0.17 / 0.13 |
  | M4 | 0.01 / −0.01 |
  | template+R | −0.27 / −0.22 |
  | G1 | −0.61 / −0.59 |

- **Amps chosen:**
  - G1 used AC20 on 9 parts, PR12 on 10 and SW50R on 6.
  - Of all list entries, 0.85 / 0.78 (G) and 0.84 / 0.77 (F) were on an amp the clean
    reach sets count acceptable for the part (band-weighted).
  - G1 vs template+R by G1's amp, as medians of band medians:

    | G1's amp | Parts | Median |
    |---|---|---|
    | PR12 | 10 | −0.041 / −0.024 |
    | AC20 | 9 | +0.014 / +0.100 |
    | SW50R | 6 | +0.249 / +0.249 |

    The groups are small.
- **The house lists:**
  - Of the 18 (9 bands × 2 band sets), 8 were three SW50R and one PR12, 7 were two of
    each, and 3 were four SW50R. None held an AC20.
  - Among their presets are a bass preset and two the project counts as high-gain.
  - That is the tuning a fixed list picks up from these parts, and why it is a control,
    not a product.

## What it means

- **Research is not shown to beat the template or chance.**
  - A researched preset beats a typical factory preset (closer on 20 of 25 parts). The
    shipped template does too, and by more. Research's own edits to the template are not
    shown to get closer.
  - A researched four-list does about as well as four random factory presets. It gains
    less from its alternatives than a random list does: −0.10 over its first choice,
    against −0.20 / −0.26 for random-4 over random-1. So its four may simply be too
    alike, rather than badly chosen.
- **Why research had little to work with:**
  - These are mostly clean parts by little-documented bands. Research found a rig for one
    band (Eggy); most runs worked from genre and the session's mic list.
  - The excerpts were 10-second rough mixes, and each part was named only by its track.
- **Choosing among several helps, with a perfect ear.**
  - Picking the best of any four (generated, factory or random) by the judge lands
    closer than one preset: about 18% closer than the template for the generated lists.
    That is the case for an audition page.
  - Whether a real ear captures it, listening through another performance's DI, is
    untested. The separate listening check measures that.
- **For the product:**
  - Generate's wording changes (D1, D3).
  - The shortlist stays generated (D2), as what the skill already writes and what
    follows the request. Its alternatives should differ more.
  - The template is within 0.150 of the best on 29% of parts, more than any single
    pick. Including it in the shortlist is a natural candidate, untested here.

## A fix after the first scoring run

The reported acceptable-amp share first read 1.0. A helper that weights parts by band
turned each part's fraction into a yes or no. Averaging the fractions gives
0.85 / 0.78 and 0.84 / 0.77. This changed no decision and no other reading. The first
run's output is kept as `~/ndsp-presets/runs/shortlists/score-first-run.json`.

## Limits

- **Development parts only,** mostly clean; the house list is tuned to them.
- **No real songs:** 10-second unmixed sums of the stems.
- **Telling the guitars apart:** each part was named only by its track name, the
  session's guitar tracks and a pace. Several agents said they couldn't tell the parts
  apart (Dom McLennon's overlapping excerpts).
- **One run per song:** agent-to-agent spread isn't measured.
- **The perfect ear is an upper bound;** the listening check is the real test.
- **Cross-amp distances** lie outside the range listening validated.
