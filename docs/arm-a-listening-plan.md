# Arm A listening check 1: is arm A's preset closer to the record than S?

Declared 2026-10-16, before any render; the user approved the test that day. Development
only: a repeat use of step 3's parts (ledger entry `arm-a-listening`). Built and scored by
`learn/build_arm_a_listening.py`. The reading is descriptive. There is no pass or fail.

## What is compared

- **Arm A:** its adopted current best, "3-C′ shrunk halfway"
  ([arm-a-levers-results.md](arm-a-levers-results.md)). That is the rebuilt-DI search stopped
  after its 52-render main stage, with its continuous moves shrunk halfway to S. The settings
  are the stored ones (`levers/early/lever-shrink-0.5/<part>/<amp>/<search>.json`). The builder
  checks that they equal the lever recomputed from the replayed main stage.
- **S:** the starting preset for the part's amp and gain class (`knob_ceiling.START`, taken
  from the plugin's menu). The builder checks it against arm B's stored copy (`menu_S`).

## Trials

- **8 trials,** drawn from the 142 scored directions (the readout's 2 drops removed):
  - **Only audible pairs.** Only directions where the judge's held-half |log(d_armA / d_S)| is
    at least 0.03 are eligible: 118 of 142. **This filter favours directions where the two
    differ audibly**, so the trials are not a random sample of all directions. The judge's
    sign is reported per trial.
  - **The draw.** The eligible directions are sorted, then shuffled with
    `random.Random(20261026)`. A walk through them takes a direction when its band is not yet
    used (at most one per band) and its amp's quota is not yet full: PR12 3, SW50R 3, AC20 2.
    The walk stops at 8.
- **1 catch trial.** It is the next direction in the same walk from a band not yet used, any
  amp. A and B are the same S render.
  - The page says this kind of trial may appear, and that "same" is a valid answer.
  - It describes consistency only. It never discards an answer.
  - Its position is drawn from trials 2–9 with the same RNG.
- **Each trial plays the held half** (4.5 s):
  - **The record:** the part's `reference.wav`, cut to the held half.
  - **A and B:** arm A's settings and S, both rendered through the part's measure DI
    (`knob_ceiling.measure_di`, `Renderer` with isolate=True). The first 0.25 s (the isolate
    fade-in) is zeroed, and the result is cut to the same held half.
  - Every clip is level-matched to −20 LUFS, with a 20 ms fade.
  - **Arm A's letter is random but balanced.** It is A on exactly 4 of the 8 test trials. The
    positions are shuffled with `random.Random(20261027)`. So a preference for a position can't
    lean towards either arm.
    - A first version drew a coin per trial. With this seed it put arm A on A in 7 of the 8
      trials. It was replaced before any render or answer.
- **The question:** "Which is closer to the record?" The answers are A, B or Same. The answer
  line at the bottom reads like "1A 2B 3S …", where S means Same.
- **Blinding:**
  - The key (parts, amps, letters, judge values) is in `private/key.json`, beside the page.
  - The page names no part, amp or preset.
  - The builder re-judges each render and records its deviation from the stored judge value.
- **Renders:** 8 × (warm-up, S, arm A) + the catch trial (warm-up, S) = 26. They run in one
  CPU process.

## Reading (descriptive)

- **Arm A's share:** of the 8 trials, how many chose arm A, with an exact (Clopper–Pearson)
  90% interval. The denominator is the trials answered A or B. "Same" answers are counted and
  reported separately. The share with "same" counted as not-arm-A is also given.
- **Agreement with the judge's sign** on the trials answered A or B.
- **Per amp:** arm A / S / same counts.
- **The catch trial's answer,** as a note on consistency.

Output: `~/ndsp-presets/listening/arm-a-1/arm-a-listening.html` (key in `private/key.json`).

    .venv/bin/python -m learn.build_arm_a_listening build
    .venv/bin/python -m learn.build_arm_a_listening score --answers "1A 2B 3S ..."
