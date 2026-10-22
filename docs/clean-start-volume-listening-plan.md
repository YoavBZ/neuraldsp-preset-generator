# Are the turned-down clean starts closer by ear? Listening plan

Declared 2026-10-22, before any trial is built; revised after an independent review. Follows
[clean-start-breakup-results.md](clean-start-breakup-results.md): on the open-chord riff the
SW50R and AC20 clean baselines break up and play clean turned down (`sw50rVolume` 15,
`ac20Volume` 10), so `generate` (0.7.117) sets those volumes for a part documented as fully
clean. Whether the turned-down starts are also closer to real clean recordings was left
untested; the user agreed to check it by ear, PR12 included.

## The question

Through each clean part's own DI, does the listener hear the turned-down clean start as
closer in tone to the recorded guitar than the clean start as shipped? Per amp, both
options dry (`--recipe dry/<amp>`, IRs stripped), differing only in the amp's volume:

| amp | as shipped | turned down |
|---|---|---|
| PR12 (`Royally Ambient`) | `pr12Volume` 49.2 | 35 |
| SW50R (`Pedal Platform Clean`) | `sw50rVolume` 35.2 | 15 |
| AC20 (`Low-Watt Americana`) | `ac20Volume` 30 | 10 |

PR12's 35 was chosen before this plan, on the chord riff, as the highest volume tried (35,
25, 15: -21.4, -26.6, -30.5 dB) whose linearity residual reaches the PR12 template's
(-19.0; the shipped baseline reads -17.7); recorded in
[clean-start-breakup-results.md](clean-start-breakup-results.md). The grid is coarse: a
value near 40-45 might also reach the template and change the tone less. SW50R's and AC20's
are the values `generate` now uses.

## Trials

**Parts.** The 13 clean development parts of the starting-preset listening check (its C and
X blocks, `docs/starting-preset-listening-parts.json`: already screened for DI activity and
low-end energy; nothing held out, nothing from sets 5 or 6), each on all three amps: 39
main trials. Its three clean control parts supply the practice trial and two hidden
references. These parts are labelled clean, not documented as fully clean: some may carry
slight breakup, which the turned-down start removes. The decision uses all 13; to see
whether the rule's scope matters, each amp's share is also reported on the cleaner and the
more driven half of the parts, split at the median of a margin from stored scores only (per
part, the mean over amps and halves of log d(clean start) - log d(crunch start); higher means
the crunch start sat closer to the record), declared here before any trial is built.

**Format** (the starting-preset check's): half B (5.5-10 s) of the reference (the part's
recorded amp track) and of the two renders of its measfix DI, aligned at the judge's lag; R,
A, B played twice, each replayable alone; every clip at one integrated level with a shared
true-peak guard, 10-ms fades, mono, AAC in one phone page per sitting. The question: which of
A and B is closer **in tone** to the reference: A, B or "?". The page names no preset, amp,
setting or part.

**Controls and checks:**
- **Practice (1, unscored, first).**
- **Hidden reference (2):** one in each sitting; one option is the reference itself; missing
  or not answering it voids that sitting.
- **Reversed taste (up to 2, reported, not voiding):** the turned-down option is always the
  cleaner one, and the listener knows the parts are clean, so a plain preference for less
  distortion would give the hypothesised result. On development crunch parts (the
  starting-preset check's spare and K crunch parts, in that file's order), one on SW50R and
  one on AC20, the first where the judge prefers the shipped start on half B by more than
  0.15 (log ratio, fresh renders), chosen by rule at build time.
- **Repeats (3, one per amp):** drawn from sitting 1, repeated in sitting 2 with A and B
  swapped; excluded from the readings; consistency reported where both are decided.
- Sittings balanced by amp: each amp's 13 parts split 6/7 between the sittings; the
  turned-down option is A on half of each amp's trials in each sitting (rounded). The seed is
  drawn at build time and kept only in the private key, so the order cannot be recomputed
  from committed files. No part twice in a row; two sittings of about 23 trials.
- A clip that sounds broken or silent is reported and that trial presented again;
  unanswered trials are left out.

**Renders.** One Morgan process (`isolate=True`, a priming render after each amp change), as
agreed with the ML session. First the shipped options must reproduce their stored judge
distances on half B, the half played (`flat|measfix`, |Δ log| < 0.005), or the build stops;
half A is reported, not checked (the stored scores were made without `isolate`, whose
carry-over reaches 2-3 s into a render, so half A can move while half B cannot). If half B
fails with `isolate`, the build is rerun without it (`--no-isolate`) and the results say so.
Each clip's levelling gain is kept in the key; the turned-down render is quieter, so it gets
more gain (and its hiss with it); the median gap per amp is reported. The key (in a
private folder only the scorer reads) holds each trial's judge log ratio on the exact clip
played; its SHA-256 is committed before the first sitting; the answer sheet's SHA-256 is
committed before the key is read.

## Readings and decision

No pass/fail bars (user rule, 2026-10-16): each reading is an effect size with its count.

- **Per amp:** of the decided trials, the share where the listener chose the turned-down
  start, with its exact 95% interval and a two-sided sign test p for reference.
- **Pooled, descriptive only** (each part appears three times, and two pairs of parts are
  from the same song): the same, plus the reading without the same-song pairs, and how many
  parts got 0, 1, 2 or 3 turned-down picks.
- **Cleaner and more driven records:** each amp's share on each half (above).
- **Secondary:** the judge's choice per trial (lower half-B distance) and ear-judge agreement,
  split by margin (over 0.15 or not). The shipped baselines were chosen by the judge as
  closest on development clean parts, likely including these, so the judge favours them here.

Decision, per amp, on the best estimate; a tie keeps what `generate` ships today (the
turned-down rule for SW50R and AC20, the shipped volume for PR12):
- **SW50R, AC20:** if the turned-down start is chosen in at least half of that amp's decided
  trials, `generate`'s rule stays; if in fewer, the rule goes back to saying the start may
  break up, without changing the volume.
- **PR12:** if the turned-down start (35) is chosen in more than half of PR12's decided
  trials, `generate` sets `pr12Volume` 35 for a part documented as fully clean; otherwise
  nothing changes.
- With no decided trials for an amp, or both sittings void: no reading, no change.
- The results say these are clean development parts, one listener, in-sample, not blind to
  the hypothesis; the rule's scope stays "documented as fully clean". With 13 trials an amp's
  decision can rest on one trial; the interval says how much.

## Limits

One listener; 13 parts from development; half B only; the parts' own DIs, not the shipped
riffs. A part that breaks up slightly in the record may favour the shipped start, which is
the point of including PR12 and of reporting per part.
