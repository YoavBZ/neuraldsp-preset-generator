# Record-match listening check 1: does our distance rank presets the way the ear does?

Declared 2026-10-19, before any render or any look at the chosen directions' arm scores; the user
approved the test that day. Development only (stage F's parts, fifth use; ledger entry
`record-match-listening`). Built and scored by `learn/record_match_listening.py`. Descriptive: no
pass or fail.

## Question

Each trial plays the record's isolated guitar (the part's amp track) and four presets rendered
through the same true DI. The listener ranks the four by closeness of tone to the record. We
compare that ranking with the held-half judge's ranking (`knob_ceiling.judge`, the distance every
arm A and direct-model reading uses).

## The four arms (one direction per part)

- **S:** the starting preset for the part's amp and gain class (`knob_ceiling.START`, checked
  against arm B's stored copy).
- **H:** arm A's stored shrunk answer (`arm-a-mega53/F/H/<part>/<amp>/<search>.json`, `output`).
- **D:** the existing direct model's stored answer (`direct-existing/predictions.json`).
- **C:** a "best possible" ceiling: `knob_ceiling.knob_search` from S over `knob_ceiling.space`,
  150 renders (K_S's budget and seed 20261013), scoring the judge on the **search** half through
  the true raw DI against the true amp track. Its best setting is judged and played on the held
  half. It is an upper reference, not a product arm.

## The choice rule (declared before any arm score of these directions is read)

1. **Eligible parts:** stage F's 21. A part is dropped if either half's bleed flag
   (`docs/audits/bleed-2026-10-16/bleed-table.json`) is moderate or high (Quicksand ElecGtr2,
   Russian Cream, She's Gone, Strangest Places), or if the record is active (100 ms frames within
   25 dB of the crop's loudest) on under 80% of both halves (colour-me-red elecgtr03).
2. **Guitar exposure:** the rest are walked in order of stage F's stored htdemucs guitar SNR in
   the mix (`report-F.json`, highest first; a separation measure, not an arm score). A part is
   taken if its band is not yet used and its class has fewer than 3 parts. The walk stops at 5,
   so each class has at least 2.
3. **Held half:** the more active half; on a tie, `random.Random(20261019)` in walk order.
4. **Amp:** the one whose starting preset is closest to the record on the **search** half (the
   other half): the smallest raw-DI judge of S stored by `direct-existing` (`groups/…json`,
   `raw.S`). The held half's scores are not used.

Applied to the stored inputs (`choose`, zero renders; the command asserts the parts) this gives,
as part (band, class): held half, amp: Signs ElecGtr3 (Zeno, crunch): B, AC20; get-out-of-bed
elecgtr2 (Magician's Nephew, crunch): A, AC20; Gym Hours GTR_2 (Dom McLennon, clean): A, SW50R;
Today's The Day ElecGtr07 (Eat The Feeder, crunch): A, PR12; magilla elecgtr1 (Turbosauro, clean):
B, SW50R. Three crunch and two clean.
While inspecting the file layout, one stored group (Signs, AC20) was printed in full, before this
rule was written; nothing else of these directions' arm scores was read.

## Renders (about 780)

Per part, in one process per part's shard (at most 3 processes): one discarded priming render
after the process start and after every amp or DI change, then C's 150-render search, then S, H, D
and C's best once each. Everything goes through `knob_ceiling.Renderer` (isolate=True) and the
part's raw DI (`di.wav`, one gain to −22.9 LUFS, as `direct-existing`'s test 2). The first 0.25 s
of every render is zeroed (the played halves start at 1.0 s or later, so no played audio is touched). **Plumbing check:** S, H and D's fresh held-half judges must match
`direct-existing`'s stored raw-DI judges within 0.005 (|log|), and C's re-render its search
record; S's
check runs on the search's first render, so a miss costs 2 renders. A miss stops that part and the
shard goes on. Disk guard 31 GB.

## The page

- **6 trials:** the 5 parts in a seeded order, then a repeat of one of trials 1–4 with a new letter
  order, for consistency. Seed `random.Random(20261020)` (trial order, letter order per trial, the
  repeat). Each trial plays the held half (4.5 s): **Record** (`reference.wav`), then A–D (S, H, D,
  C in that trial's random order).
- Every clip of a trial is level-matched to one loudness with the Record: −20 LUFS, or lower for
  the whole trial if a clip would otherwise peak above 0.9 (the builder asserts a spread under
  0.1 LU). 20 ms fades, AAC data
  URIs each padded with a random-length mp4 `free` box (as `build_bleed_damage`). The page names
  no part, band, amp, preset or arm; the key is in `private/key.json`.
- **Questions:** rank A–D from closest to furthest from the Record's guitar tone (ignore timing
  and performance), and "how close is the closest?" (very close / somewhat / not close).
- **Answer line,** built by the page: `1 B>D>A>C very; 2 A>C>B>D some; …` (closest first; the
  last word is very, some or not; `?` for unanswered).

Output: `~/ndsp-presets/listening/record-match-1/record-match.html`.

    .venv/bin/python -m learn.record_match_listening choose
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.record_match_listening render --shard i/3
    .venv/bin/python -m learn.record_match_listening build
    .venv/bin/python -m learn.record_match_listening score --answers "1 B>D>A>C very; …"

## Reading (descriptive)

On the 5 main trials (the repeat is reported only as consistency):

- Each arm's mean rank (1 = closest).
- How often C, H and D are each ranked above S (of 5).
- **Agreement with the judge:** per trial, Spearman's ρ between the listener's ranks and the
  judge's held-half ranks of the same 4 renders; their mean, and how many trials have ρ > 0. With
  4 items one trial's ρ is coarse (a random order has ρ ≥ 0.8 one time in 6); the mean over 5 is
  the summary, and no threshold is set.
- The closeness answers per trial, beside the judge's held-half distance of the listener's top
  pick and of C.
- **The repeat:** ρ between the two rankings of the same part, and whether the closeness answer
  matched.

## Limits

Five parts; one amp each; the record is the amp track (it may carry a little bleed, flagged low).
C is fitted to the judge on the other half, so a listener preferring C is partly a check of the
judge itself. Stage F's directions were scored by earlier steps; this is a development reading.
