# Generate's presets and a four-preset shortlist, measured: no gain from research

Computed as declared in `docs/song-only-shortlist-plan.md` (with its dated amendments),
on 2026-10-05:
- **Runs:** 16 agents, one per song, 25 development parts, sandboxes at b5dbcbb.
- **Rendered** with `scripts/render_shortlists.py`.
- **Scored** with `scripts/score_shortlists.py`. `docs/song-only-shortlist.json` is the
  output. The scorer was re-run once after a fix to a reported figure (below); every
  decision and reading came out identical.

## The runs held up

- **Audit:** every transcript was checked by `scripts/audit_shortlist_runs.py`. There
  were 8 flags, all of the excusable kind: a `$` used as a `grep` anchor or a loop's own
  echo variable, in commands whose paths all stayed in the sandbox. No run read the
  validation data, the results, the repository or GitHub, and none was redone or
  excluded.
- **Smaller slips, by the agents' own reports:**
  - Several recursive listings of the factory folder printed the names in `User/`; none
    opened a file there.
  - Some `show.py` calls left out `--data-dir`; the data root then resolved inside the
    sandbox.
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

Log ratios, default / union bands; negative means the first arm is closer.

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
3. **D3:** a researched shortlist is not shown to beat four random factory presets, or a
   fixed list tuned on these recordings. The skill must say so.

## Readings (reported, not deciding)

**Hearing four helps, even if research doesn't pick them.** With a perfect ear (picked
on one half, scored on the other):

| | Median | Closer on |
|---|---|---|
| G4 vs template+R | −0.198 / −0.183 | 18 / 17 |
| G4 vs G1 | −0.099 / −0.112 | 17 / 20 (inconclusive) |
| F4 vs F1 | −0.174 / −0.206 | 19 / 19 (passes) |
| random-4 vs template+R | −0.059 / −0.041 | 17 / 16 |

**How near the best factory preset each arm gets** (band-weighted share of parts within
0.150 of the oracle):

| Arm | Share |
|---|---|
| house-4 | 0.61 / 0.46 |
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
  | template+R | −0.27 / −0.22 |
  | G1 | −0.61 / −0.59 |

- **A single generated preset vs a typical factory preset:** G1 is closer than random-1
  on 20 of 25 parts, but only by −0.015 / −0.057.
- **Amps chosen:**
  - G1 used AC20 on 9 parts, PR12 on 10 and SW50R on 6.
  - Of all list entries, 0.85 / 0.78 (G) and 0.84 / 0.77 (F) were on an amp the clean
    reach sets count acceptable for the part (band-weighted).
  - By G1's amp, G1 vs template+R had medians of −0.10 (PR12, 10 parts), −0.01 (AC20,
    9) and +0.08 (SW50R, 6). Descriptive only; the groups are small.
- **The house list** most often held two SW50R and two PR12 factory presets, among them
  a bass preset and a high-gain one. That is the tuning a fixed list picks up from these
  parts, and why it is a control, not a product.

## What it means

- **Research doesn't pick better presets than chance here.** Generate's researched
  preset does about as well as the shipped template, and its four-preset list about as
  well as four random factory presets.
  - These are mostly clean parts by little-documented bands. Research found a rig for
    one band (Eggy); most runs worked from genre and the session's mic list.
  - Excerpts were 10-second rough mixes, and the part was named only by its track.
- **Choosing among several does help.** A perfect ear choosing from four is about 18%
  closer than the template, and about 10% closer than the agent's own first choice. Any
  of the lists (G, F, random) gains from being heard.
  - That is the case for the audition page.
  - Whether a real ear captures it, listening through another performance's DI, is
    what the separate listening check measures.
- **For the product:**
  - Generate's wording changes (D1, D3).
  - The shortlist stays generated (D2): it is what the skill already writes and it
    follows the request. But nothing here says research beats a varied random set.
  - The template sits within 0.150 of the best on 29% of parts, more than any single
    pick. Including it in the shortlist is a natural candidate, untested here.

## A fix after the first scoring run

The reported acceptable-amp share first read 1.0. A helper that weights parts by band
turned each part's fraction into a yes or no. Averaging the fractions gives
0.85 / 0.78 and 0.84 / 0.77. This changed no decision and no other reading; the first
run's output is kept as `~/ndsp-presets/runs/shortlists/score-first-run.json`.

## Limits

- Development parts only, mostly clean; the house list is tuned to them.
- **No real songs:** 10-second unmixed sums of the stems.
- **Telling the guitars apart:** the part named only by its track name, the session's
  guitar tracks and a pace. Several agents said they couldn't tell the parts apart
  (Dom McLennon's overlapping excerpts).
- **One run per song:** agent-to-agent spread isn't measured.
- **The perfect ear is an upper bound;** the listening check is the real test.
- **Cross-amp distances** lie outside the range listening validated.
