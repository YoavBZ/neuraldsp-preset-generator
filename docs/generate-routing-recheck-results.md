# Does the new routing rule help? Re-check results

Run 2026-10-12 (night) as declared in
[generate-routing-recheck-plan.md](generate-routing-recheck-plan.md); the plan, run map
and runner were committed before any run, the analysis code was not (see Audit). Numbers in `generate-routing-recheck-results.json`;
code `research/generate_routing.py` (`recheck-*`).

## Verdict: the rule helps

The new `generate` (0.7.106, #175) against the skill before it (0.7.105), the same 34
clean and crunch development parts, one prompt for both, run interleaved on the same
model, scored with [part 1](generate-routing-results.md)'s truth and regret:

| | regret | 90% interval |
|---|---|---|
| new skill, its primary route | 0.059 | 0.017 to 0.111 |
| old skill, rerun | 0.140 | 0.078 to 0.207 |
| run 1 (old skill, earlier) | 0.135 | 0.082 to 0.191 |
| the label (ceiling) | 0.020 | 0.002 to 0.044 |
| **new minus old, paired** (decides) | **−0.081** | **−0.134 to −0.033** |
| old rerun minus run 1 (noise, upper bound) | +0.005 | −0.026 to +0.039 |

- **Decided by the declared rule:** the upper bound is below 0, so the routing text
  stays. Robust: dropping any one band leaves new minus old between −0.058 and −0.086;
  no band's mean difference is positive; against run 1 instead it is −0.076 (−0.134 to
  −0.021). The old rerun's mean landed within 0.005 of run 1's, but they differ on 4 of
  34 parts (2 each way), so run noise is real and the paired interval carries the claim.
- **Which parts:** 12 changed route; 8 improved and 1 got worse; most of the gain is
  three clean parts the new skill routed clean.
- **Where it came from:** clean parts routed clean rose from 12 of 22 to 16 of 22
  (crunch from 10 to 6).
- **A new error, small:** 2 of 12 crunch parts were routed clean (none before), costing
  0 and 0.023. No high-gain part was routed clean (13 heavier, 3 crunch).
- **The second start:** every one of the 49 new runs wrote one (none of the old
  runs): a crunch start beside a clean route (19), a clean start beside a crunch route
  (11), a crunch start beside a heavier route (19), as the skill now asks for any route
  that is not clean, and for a guessed clean one. With both starts, the better of the
  two had no clean-against-not-clean regret on any part (0.000), assuming the user
  picks the better by ear. That is partly by construction: a clean and a crunch start
  together always span the two groups; a crunch-and-heavier pair (19 runs) gives no
  protection on this measure, and scored 0 only because those routes were already
  right.
- **No agent asked** whether the part was clean, so the "question answered" reading
  equals the primary one.

## Audit

**A late commit, stated plainly.** The plan, run map and runner were committed before
the runs; the analysis (`recheck_analyze`, the second-start matching, the leak and
exclusion rules) was committed at 23:11, about eight minutes after the first runs
started (under the message "Listening pages: practice marked on sitting 1 only"), and
the results commit fixed a crash in the second-start count. The regret and decision
code copies part 1's, which was committed earlier, and an independent re-derivation
with its own code reproduced every number, so the decision does not rest on the late
code.

All 83 runs wrote a result; none was excluded: each loaded only its arm's plugin
(0.7.105 or 0.7.106) on `claude-opus-5-5`, and no tool call touched the project's
data, repository, GitHub page or these results. Run folders and plugin folders had
neutral names, and the prompts were identical, so nothing named the arm (an agent could read its plugin version).

## Limits

The routing text was written from run 1's misroutes on these same parts, so the gain is
an optimistic, in-sample estimate. The change is a bundle: the routing text and the
second start came together, and agents may route clean more readily knowing a crunch
start is written too; the test cannot separate them. The inputs named only song and
time, but agents read public pages about these multitracks, so the "documented sound"
path was partly exercised that way. The new skill's text tells an agent that a routing
study exists; that is part of the change, not a leak. The run sessions had two
connectors and a messaging socket available, none used; they should be off next time. One run per arm per input.
Development parts.
