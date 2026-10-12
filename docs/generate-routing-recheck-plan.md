# Does the new routing rule help? Re-check plan

Declared 2026-10-12 (night), before any re-run; revised after an independent review.
Follows [generate-routing-results.md](generate-routing-results.md) ("run 1"): after
it, `generate` (#175) chooses the gain class from the part's own documented sound
rather than the song's genre, may ask the user whether the part is clean or driven,
and writes a second starting point when the part is not clean or its class is a
guess. The routing rule is unmeasured.

## Design

Two arms, run together on Claude Code 2.1.280 with `--model claude-opus-5-5` (each
transcript's init event is checked; a run on another version or model is excluded and
reported), interleaved in a seeded random order:
- **old:** the skill before #175, the scrubbed plugin copy run 1 used
  (`~/gtr-session/plugin`, 0.7.105);
- **new:** the skill at main `1d2ae4c` (its plugin folders unchanged since #175's
  `4de9304`, checked), scrubbed the same way into its own folder.

Both arms get the same inputs as run 1 (`generate-routing-runs.json`): all 49 for the
new arm (high-gain runs kept, to see whether the new text sends heavy parts to clean),
and the 34 runs that contain a clean or crunch part for the old arm. Blinding is run
1's (sandboxed `claude -p`, neutral folders, its own data folder, messaging off), with
"generate-routing" added to the audit markers; each transcript's init event must show
only the inline plugin at its arm's version, or the run is excluded and reported.

**One prompt for both arms,** byte-identical between them: run 1's prompt with two
changes. "Don't install the preset … write the preset to ./out/" becomes "write
whatever you would install to ./out/ instead of installing it", and the result keys
add a neutral `"outputs"`: each file written to ./out/ and the starting preset it was
built from. The second start is read from the files in ./out/ (matched to the dry
baselines), self-report only as a cross-check.

**A run that ends on a question** (the new rule may ask whether the part is clean) is
resumed once with a fixed non-answer: "I can't say; decide yourself." (identical
across arms, part of the prompt for blinding). The resumed session's result.json is
the one used and both parts of its transcript are audited; a run still without one
counts as a failed route and is reported, not dropped. The ask rate is reported, and so is, report only, the regret those runs would have had if the user
had answered with the part's label: the product with the question.

Truth, regret and bootstrap are part 1's exactly (`research/generate_routing.py
analyze`). The analysis changes (new run folders, second runs map, outputs-based
second start) are committed before any run.

## Readings

- **Primary route:** each arm's regret, and **new minus old, paired per part**
  (decides). Run 1 is secondary; old minus run 1 is the noise figure, which also holds the prompt
change and run 1's older model snapshot, so it is an upper bound on run noise.
- **Two starts (report):** the regret of the better of the files actually written, per
  arm; how often a second start was written.
- **Guards (report):** clean-against-crunch confusion and the count of crunch and
  high-gain parts routed clean, per arm.

## Decision

On new minus old, per part, band-weighted, 90% band bootstrap:
- **The rule helps** if the upper bound is below 0: recorded; no change.
- **The rule hurts** if the lower bound is above 0: revert the routing text (step 1's
  class-question sentence, step 4's "choose the class from the part's own documented
  sound" bullet, and the "mix's measurements are not the guitar's drive" bullet in
  `reference/reading-a-reference.md`), keeping the second start, which run 1 justified.
- Otherwise **undecided**: reported; no change.

The bar is zero, not 0.05, on purpose: either action is cheap to reverse. The smallest
effect the test can show is about ±0.07 to 0.08 (two noisy runs, 15 bands), against at
most 0.115 to win, so "helps" needs about two thirds of the misroute cost removed;
undecided is likely and is not a failure.

## Limits

The routing text was written from run 1's misroutes on these very parts and quotes
their figures, so a favourable result is optimistic. The inputs document nothing
about the part, so the "documented sound" path is barely exercised; the test mostly
measures the guess path. One run per arm per input. Development parts, used again.
