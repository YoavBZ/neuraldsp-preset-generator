# Part locator: where in the song does the target guitar play? Plan (development)

Declared 2026-10-13, before any locator code. Asked for by the product session and agreed by
the ML session.

## Why

When the user gives a song but no time, `generate` has to guess where the target electric
guitar plays. On 2026-10-13's end-to-end run (Long Road Out of Eden) it guessed a window from
the mix and got the part wrong. A locator that ranks candidate windows by how clearly the
electric guitar plays would let `generate` choose, or ask the user to choose, a good excerpt.
It ships only with the user's OK for the PyTorch and separator download.

## The tool (descriptive, offline)

**Input:** a song file. Optionally, a hint ("the lead", "the rhythm guitar").

**Output:** ranked 10-s windows, each with:
- **guitar presence:** the separated electric-guitar stem's level relative to the mix, and its
  activity;
- **exposure:** the guitar stem's share of the mix's energy in the 1–4 kHz band (how audible
  the guitar is);
- **a coarse clean or driven reading** per window, with a confidence. This is descriptive only;
  it does not route the class.

**Separation:** `htdemucs_6s`'s guitar stem, the separator already in use (MIT). No new model.
A stated rule turns these features into a single score per window. Nothing is fitted on
development first; any weighting is set on a disjoint calibration subset (below).

## Ground truth (development multitracks only)

- **The sessions:** the development sessions of sets 1–2 and set 3 that have full-length tracks
  on disk (the DI and amp track of each electric-guitar part, and a mix). The mix is the
  session's own, or the sum of its tracks by set 4's mix rule if absent.
- **Truth per part:** the frames where that part's DI is active, within 30 dB of its loudest
  frame. A window "contains the part" if the DI is active in at least 60% of its frames.
- **The target guitar is ambiguous** in multi-guitar songs, so two readings are given:
  - **any-guitar:** the window contains some electric-guitar part;
  - **target:** the window contains the part the session marks as the main or lead guitar,
    where the catalog says so. Otherwise the target reading is skipped for that song.

## Measures

**Hit@k:** the share of songs where at least one of the top-k windows (k = 1, 3) contains the
part, for any-guitar and for target.

**Baselines:**
- random windows;
- the loudest 10 s of the mix;
- the song's middle;
- `generate`'s current behaviour, where recorded from routing runs.

**The bar (declared): the locator is useful if:**
- any-guitar Hit@1 is at least 0.8;
- target Hit@3 is at least 0.7;
- both beat every baseline by at least 0.15.

**Calibration:** the clean or driven reading is checked against each part's set-3 gain class,
as accuracy plus a confusion table (descriptive).

**Split:** development bands are split by sorted name into calibration (one third: thresholds
and weights only) and evaluation (two thirds: the reported numbers). Band-clustered bootstrap
intervals are reported.

## Hygiene and cost

- **Development data only.** Sets 1–2 held out, set 4, set 5 and set 6 are untouched.
- **No renders.** Separation runs on the CPU or MPS, coordinated with E1's training. It starts
  after E1's training finishes, or on the CPU at low priority.
- **Reviews:** an independent reviewer checks this plan before code, and the result before it
  is reported.
- **Interface:** an interface proposal goes to the product session before the tool is wired in.
