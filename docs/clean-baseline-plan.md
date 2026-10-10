# A fixed clean starting preset: plan

Declared 2026-10-10, before any clean preset is chosen or scored.

## Why

`generate` starts a clean Morgan part from the shipped clean template (template+R in
measurements). The [confirmation](set4-confirmation-results.md) reviewer found the template
weak. Against a fixed clean factory preset, chosen from other bands, the chooser's clean
edge shrank from −0.123 to −0.049. A better fixed clean start is cheap, and helps every
clean song whether or not the chooser runs.

## The choice (development only)

For each amp (PR12, SW50R, AC20), the clean starting preset is the factory preset with:
- the lowest median, over the clean development parts, of the mean of its half-A and
  half-B fixed-level distances (`measfix`, the `flat` judge);
- dry, as measured (reverb, delay, tremolo, doubler and gate off; spring 0; transpose 0).

The clean development parts are those whose distances exist for every candidate:
- set 3's 5 clean development parts (`rescore/distances.json`);
- the sets 1–2 development stem parts that classify clean (18 of the 20 usable)
  (`songs-check/distances.json`, scored as part of the [songs check](songs-check-plan.md)).

Ties are broken by name. The rule runs once, after the songs check is scored, and its
output is committed before the check below.

**Development report:** the chosen preset against template+R on the same parts, with a
leave-band-out choice, so that it is not in-sample.

## The check (fresh material, no new renders)

The held-out clean parts of sets 1–2 used in the confirmation: 13 parts, 8 bands. Their
fixed-level distances for every menu preset already exist (`confirm/distances.json`,
`flat|<amp>|measfix_A/B`). Their rule allows a further declared use; it is recorded in
the ledger. Set 4's two unused clean parts are left unused.

- **Statistic:** per part and amp, the log ratio of the clean preset's distance to
  template+R's, averaged over both halves. A band-clustered 90% interval, as in the
  confirmation.
- **Confirmed** if the 90% interval lies below 0. Then `generate` starts clean Morgan parts
  on that amp from that preset, made dry first, instead of the template.
- **Otherwise** the template stays.
- **Per amp:** reported. The rule applies to the pooled result, and adoption is per amp
  only where that amp's own interval also lies below 0.

An independent reviewer re-derives the result before adoption.

## The choice (2026-10-10, committed before the check)

The rule run on 22 clean development parts from 10 bands: 17 from sets 1–2 and 5 from
set 3. Parts are those where every factory candidate has both halves scored.
- **Of the 20 usable sets 1–2 stem parts,** 18 classify clean.
- **telefunken-Honey-GTR drops out:** its half B is refused for every preset.

(Corrected after review: the first wording said "18 + 4, a set-3 part refused". The
selection itself is unchanged.) The selection is in
`docs/clean-baseline-choice.json`:

| amp | clean starting preset | median distance | runner-up |
|---|---|---|---|
| PR12 | Mark Johnston / Royally Ambient | 4.291 | Jangly Combo Clean, 4.433 |
| SW50R | Mark Johnston / Pedal Platform Clean | 4.274 | Big Tail Clean, 4.440 |
| AC20 | Royce Whittaker / Low-Watt Americana | 4.176 | Gtr Lead FX, 4.619 |
