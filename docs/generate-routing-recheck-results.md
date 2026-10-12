# Does the new routing rule help? Re-check results

Run 2026-10-12 (night) as declared in
[generate-routing-recheck-plan.md](generate-routing-recheck-plan.md), committed with its
run map and code before any run. Numbers in `generate-routing-recheck-results.json`;
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
  stays. The old skill's rerun landed within 0.005 of run 1, so the difference is not
  run noise.
- **Where it came from:** clean parts routed clean rose from 12 of 22 to 16 of 22
  (crunch from 10 to 6).
- **A new error, small:** 2 of 12 crunch parts were routed clean (none before). No
  high-gain part was routed clean (13 heavier, 3 crunch).
- **The second start:** every one of the 49 new runs wrote one (none of the old
  runs): a crunch start beside a clean route (19), a clean start beside a crunch route
  (11), a crunch start beside a heavier route (19). The agents treated every class as
  a guess, as the inputs documented nothing about the part. With both starts, the
  better of the two had no clean-against-not-clean regret on any part (0.000), the
  most a user who listens to both can get.
- **No agent asked** whether the part was clean, so the "question answered" reading
  equals the primary one.

## Audit

All 83 runs wrote a result; none was excluded: each loaded only its arm's plugin
(0.7.105 or 0.7.106) on `claude-opus-5-5`, and no tool call touched the project's
data, repository, GitHub page or these results. Run folders and plugin folders had
neutral names, so no agent could see its arm.

## Limits

The routing text was written from run 1's misroutes on these same parts, so the gain is
an optimistic, in-sample estimate. The inputs documented nothing about the part, so
this measured the "guess" path: the agents routed more carefully and always wrote a
second start, but the "documented sound" path is untested. One run per arm per input.
Development parts.
