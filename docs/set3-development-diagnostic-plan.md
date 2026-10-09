# Set 3 development diagnostic after failed confirmation

Drafted 2026-10-08. Review and commit before computing the new diagnostic.
This reuses development results already inspected in earlier research; it is an
exploratory routing decision, not a new accuracy confirmation. Revised after the
independent design review, before computing this diagnostic.

## Question

Can the existing preset menu improve on a strong constant if the clean guitar
signal is known? How much does choosing through the rebuilt signal lose? This
distinguishes a pipeline/ranking gap from a menu or measurement limit before more
training or knob search. True-versus-rebuilt changes the signal, input level,
DI-derived scoring mask and alignment convention. It does not isolate waveform
recovery, level, alignment or mask effects from each other.

## Inputs and exclusions

- Only the 33 declared development parts across 11 bands in `validation-set3.json`.
- Existing `~/ndsp-presets/learn/direc/phase2-set3/distances.json` only; no audio,
  network inference, plugin renders, downloads or training in this first diagnostic.
- SW50R primary; PR12 and AC20 reported separately as diagnostics. Both recording
  and union band sets. Do not choose an amp from held-out results.
- Do not open reserved score files, audio or stems from any set. Set 3's spent
  confirmation is recorded separately and cannot become a tuning set.
- Reject input slugs outside development, missing parts, missing candidate keys,
  inconsistent menus or malformed distances. Null distances represent refusals;
  finite nonnegative distances are valid raw scores, but logs require positive values.
  Zero can win a raw comparison, but is separately log-unscorable, prevents a
  log-based gate, and is never replaced by epsilon or a new choice after seeing B.
- Hash input distance file, validation metadata, diagnostic plan and script in output.
- Before score computation, prepare and commit `set3-development-diagnostic-menus.json`
  from installed factory preset metadata, without reading score values or loading the
  plugin. Validate every row against those candidate IDs per amp, shared across both
  band sets. An everywhere-missing candidate must fail, not redefine the menu.

## Comparisons

For each amp and band set, keep the same candidate menu including template+R.
Selections use minimum valid half-A distance, lexicographic preset ID for ties.

1. **True average-balanced DI selection:** choose using `measure_A`, evaluate the
   chosen preset using `measure_B`. This is an unavailable-input positive control,
   not a proposed product requiring the user to record a DI.
2. **Rebuilt-DI selection:** choose using `net_A`, evaluate using `measure_B`.
3. **Constant:** independently for each evaluated band's exclusion, choose a factory
   preset using minimum median raw `measure_A` over all parts of other development
   bands; ties lexicographic. A factory candidate is eligible only when every
   training-part score is finite and nonnegative. List excluded candidates and why;
   if no eligible candidate remains, mark the band unscorable. Template+R is ineligible.
4. **Half-B hindsight best:** minimum valid `measure_B`. This is a descriptive bound
   for the current menu and measure only; never use it to choose a product preset.
   With any refused B candidate, it is only the best scorable candidate, not a bound
   over the full menu. Report coverage explicitly.
5. **Inclusive constant fairness control:** the same leave-band-out constant rule
   with template+R eligible. The headroom claim must survive this comparison too.
   Both constants optimize pooled-part raw medians (equal training-part weights),
   whereas evaluation weights bands equally. They are declared baselines, not the
   strongest possible constants for every objective.

Report true-DI and rebuilt-DI selections against constant and template, true-DI
against rebuilt-DI, and half-B hindsight against true-DI and constant. Include exact
selection agreement over all 33 parts, missing selections separately, and refusals;
agreement alone is not a quality result. Gains
are paired log distance ratios, median of band medians. Joint wins give each band
equal weight with all its original parts retained in the denominator; ties/refusals
are zero wins. Raw zero distances may win even though their log is unscorable.
List null refusals separately from nonpositive log-unscorable comparisons.
Available-case ratios
are descriptive whenever required comparisons are refused.

Enumerate all 2^11 two-sided sign flips of band medians (absolute sum statistic,
1e-12 tail tolerance). This is an exploratory sensitivity statistic: independence
and symmetric band effects are assumptions, and leave-band-out constants share
fitting data, so the nominal p is not established as calibrated inference. Routing
uses p < 0.1 only as a declared heuristic. Report actual available bands; if a whole
band has no ratio, no sign-flip statistic is reported. Partial-part ratios remain
descriptive. Report effects by band. Gain-class results, if added, are descriptive only. No
unannounced subsets, alternate constants or other timing analyses in this diagnostic.

## Routing rules, not shipping gates

Apply independently by amp, under both band sets, with no required true-DI/constant/
template refusal:

- **Menu/measurement headroom observed:** true-DI selection beats each declared
  constant by at least 5% in band-median ratio, exploratory sign-flip statistic < 0.1,
  and beats each constant and template together on a band-weighted share strictly
  above 0.5. No required true-DI/constant/template refusal or log-unscorable value is
  allowed. Both recording and union must meet this heuristic. Secondary amps cannot
  rescue SW50R.
- **Pipeline gap observed:** separately, true-DI selection beats rebuilt-DI selection
  by at least 5%, exploratory sign-flip statistic < 0.1, with complete paired ratios,
  under both band sets. Headroom alone supplies no affirmative reason for DI training.
  If headroom exists but rebuilt selection has refusals, first diagnose those failures
  on development data. If headroom and a complete pipeline gap exist, declare a small
  level/mask/alignment intervention before attributing the gap to reconstruction.
  No long training starts on this numerical result alone.
- **If not established:** defer longer DI training. The hindsight bound says whether
  the scored menu contains better options but choosing on half A fails, or whether
  even its half-B best offers little room. Little room cannot distinguish inadequate
  coverage from an insensitive measure. These are descriptive distinctions; declare any
  next intervention before running it. Expand knobs only after a synthetic positive
  control and evidence that current menu coverage limits the objective.

No pass here authorizes shipping. Heavy-tone listening remains necessary; six-band
reserved confirmation failed and is not repeated. Any future confirmation needs
fresh reserved data declared before use.

## Verification and execution

An independent agent reviews design and decision-driving code before execution,
then recomputes constants, selections, band effects and routing conclusions from
the development input without importing the production diagnostic implementation.
Synthetic checks cover leakage, incomplete menus, ties, invalid/zero distances,
refusal denominators and exact sign flips. Commit the reviewed plan and code before
running. Write a new result artifact; do not overwrite existing experiments.

**Declared 2026-10-08:** independent fresh-context design/code review approved
after the six design clarifications and frozen-menu validation fix. All 19 synthetic
tests passed before execution. Candidate IDs were prepared from factory metadata
only (45 SW50R, 35 PR12, 31 AC20); no diagnostic scores were computed before this
declaration's commit. The user authorized autonomous continuation on development
data; no new reserved-set use is requested or authorized here.
