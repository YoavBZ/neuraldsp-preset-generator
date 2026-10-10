# A crunch starting preset, and the ML chooser on crunch: plan

Declared 2026-10-10, before any crunch preset is chosen or scored.

## Why

- **Heavy metal is now out of scope** ([roadmap](ROADMAP.md), "Scope").
- **The driven starting presets `generate` uses for crunch songs** (Wall Of Doom, Vintage
  Metal, Dirty Coil Rhythm) were chosen on heavy set-3 material, and may be too heavy
  for crunch.
- **On clean parts, a fixed preset chosen by rule** captured the ML chooser's whole edge
  ([clean results](clean-baseline-results.md)). Crunch is where the chooser might still
  add value, so this tests both questions.

## Material (fixed-level measure, `flat` judge, existing renders only)

- **Development crunch parts** (whole-session gain class "crunch"): 13 parts from 6
  bands.
  - set 3: 11 parts (`rescore/distances.json`);
  - sets 1–2: Prodigal ElecGtr5 and Today's The Day ElecGtr10 (`songs-check/distances.json`).
- **Held-out crunch parts:** the 7 sets 1–2 parts classed crunch in the confirmation
  (Forkupines 4, Lights Off Clarity 2, The Maybe Next Years 1; 3 bands;
  `confirm/distances.json`). Their rule allows a further declared use, which is recorded
  in the ledger.
- **Set 4's crunch parts are not used:** their sessions are metal, which is out of scope.

## The choice (development only)

Per amp, the factory preset with the lowest median, over the development crunch parts
where every factory candidate has both halves, of the mean of its half-A and half-B
distances. Ties are broken by name, and the presets are used dry as measured. The choice
is committed before the check.

## The checks (held-out crunch parts)

The statistic is a per part-amp log ratio averaged over both halves, with a
band-clustered 90% interval.

1. **Crunch preset against the shipped driven preset** (the product's current crunch
   start). **Adopted** for crunch songs if the pooled interval lies below 0. Otherwise
   the shipped preset stays.
2. **The ML chooser against the crunch preset:** the confirmation's picks (3 kHz cut,
   and uncut), both directions. **ML adds value on crunch** if the pooled interval lies
   below 0. Otherwise it is not shown to.

**Also reported:**
- each against template+R;
- the oracle against the crunch preset (headroom);
- the same comparisons on development, in-sample for the preset and so biased in its
  favour.

## Power, honestly

Three held-out bands give a t-interval with 2 degrees of freedom: very wide. A pass needs
a large, consistent effect, and "not shown" is the likely outcome for anything modest.
This is a quick check, not a confirmation. A result that matters would need fresh crunch
material in scope: rock, blues and indie sessions with DIs.
