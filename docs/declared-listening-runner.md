# Running a declared listening test

`scripts/run_declared_listening.py` executes a committed test from a clean
worktree. It never reads answers or prints a step's output. Its console output
contains only part/step names and exit codes; the full logs, command arrays,
output hashes, timestamps and `pip freeze` text stay in a new private run
directory. The new directory must be below this worktree's Git-ignored
`runs/` directory, because the fresh-render CLI requires it. `--parallel N`
runs at most N parts at once, each in its own directory.

The declaration must contain the existing `held-out-listening-test-v1` block
and one `declared-listening-commands-v1` JSON block with the same `test_id`.
All nine named steps are required. Each step declares an argv array, a list of
output files to hash, and the primary output whose absence permits one
byte-identical rerun. Match primary outputs must be `match-1.json`; the rerun
uses the same output directory and preserves any earlier trial store.
Commands invoke tracked `scripts/*.py` files through `{python}` without a
shell. The runner expands `{repo}`, `{declaration}`, `{run}`, `{source}`,
`{song}`, `{part}`, `{slug}` and `{test_id}` as well.

For a future SW50R test, this is the command-block shape. It is an example,
**not** a declaration or authorization to reopen the held-out parts:

```json
{
  "schema": "declared-listening-commands-v1",
  "test_id": "NEW-COMMITTED-TEST-ID",
  "template": "samples/SW50R_Atlas_Topology.xml",
  "steps": {
    "crops": {
      "argv": ["{python}", "scripts/build_validation_crops.py", "--source", "{source}", "--song", "{song}", "--part", "{part}", "--declaration", "{declaration}", "--out-dir", "{run}/crops"],
      "outputs": ["{run}/crops/record.json", "{run}/crops/di.wav", "{run}/crops/reference.wav", "{run}/crops/mix.wav", "{run}/crops/backing.wav"],
      "primary_output": "{run}/crops/record.json"
    },
    "di_match": {
      "argv": ["{python}", "scripts/match_preset.py", "--template", "samples/SW50R_Atlas_Topology.xml", "--reference", "{run}/crops/reference.wav", "--reference-mode", "paired_di", "--excerpt", "0", "--probe-di", "{run}/crops/di.wav", "--loss-profile", "unpaired-v3", "--pack", "morgan", "--amp", "sw50r", "--renderer", "swift", "--process-policy", "fresh", "--budget", "300", "--shortlist", "3", "--seed", "0", "--out-dir", "{run}/with-di"],
      "outputs": ["{run}/with-di/match-1.json", "{run}/with-di/summary.json", "{run}/with-di/trials.sqlite3"],
      "primary_output": "{run}/with-di/match-1.json"
    },
    "no_di_match": {
      "argv": ["{python}", "scripts/match_preset.py", "--template", "samples/SW50R_Atlas_Topology.xml", "--reference", "{run}/crops/reference.wav", "--reference-mode", "isolated_stem", "--excerpt", "0", "--search-without-di", "--loss-profile", "unpaired-v3", "--pack", "morgan", "--amp", "sw50r", "--renderer", "swift", "--process-policy", "fresh", "--budget", "300", "--shortlist", "3", "--seed", "0", "--out-dir", "{run}/no-di"],
      "outputs": ["{run}/no-di/match-1.json", "{run}/no-di/summary.json", "{run}/no-di/trials.sqlite3"],
      "primary_output": "{run}/no-di/match-1.json"
    },
    "di_preset": {
      "argv": ["{python}", "scripts/apply_spec.py", "--template", "samples/SW50R_Atlas_Topology.xml", "--spec", "{run}/with-di/match-1.json", "--out", "{run}/with-di.xml"],
      "fallback_argv": ["{python}", "scripts/copy_declared_template.py", "--template", "samples/SW50R_Atlas_Topology.xml", "--out", "{run}/with-di.xml"],
      "summary": "{run}/with-di/summary.json",
      "outputs": ["{run}/with-di.xml"],
      "primary_output": "{run}/with-di.xml"
    },
    "no_di_preset": {
      "argv": ["{python}", "scripts/apply_spec.py", "--template", "samples/SW50R_Atlas_Topology.xml", "--spec", "{run}/no-di/match-1.json", "--out", "{run}/no-di.xml"],
      "fallback_argv": ["{python}", "scripts/copy_declared_template.py", "--template", "samples/SW50R_Atlas_Topology.xml", "--out", "{run}/no-di.xml"],
      "summary": "{run}/no-di/summary.json",
      "outputs": ["{run}/no-di.xml"],
      "primary_output": "{run}/no-di.xml"
    },
    "first_render": {
      "argv": ["{python}", "scripts/render_listening_guitar.py", "--pack", "morgan", "--di", "{run}/crops/di.wav", "--preset", "{run}/with-di.xml", "--preroll-s", "0", "--out", "{run}/first.wav"],
      "outputs": ["{run}/first.wav", "{run}/first.wav.render.json"],
      "primary_output": "{run}/first.wav",
      "applied_settings_record": "{run}/first.wav.render.json"
    },
    "second_render": {
      "argv": ["{python}", "scripts/render_listening_guitar.py", "--pack", "morgan", "--di", "{run}/crops/di.wav", "--preset", "{run}/no-di.xml", "--preroll-s", "0", "--out", "{run}/second.wav"],
      "outputs": ["{run}/second.wav", "{run}/second.wav.render.json"],
      "primary_output": "{run}/second.wav",
      "applied_settings_record": "{run}/second.wav.render.json"
    },
    "manifest": {
      "argv": ["{python}", "scripts/build_declared_listening_manifest.py", "--crop-record", "{run}/crops/record.json", "--first-render", "{run}/first.wav.render.json", "--second-render", "{run}/second.wav.render.json", "--out", "{run}/audition.json"],
      "outputs": ["{run}/audition.json"],
      "primary_output": "{run}/audition.json"
    },
    "audition": {
      "argv": ["{python}", "scripts/build_backed_audition.py", "--manifest", "{run}/audition.json", "--out-dir", "{run}/audition"],
      "outputs": ["{run}/audition/audition.flac"],
      "primary_output": "{run}/audition/audition.flac"
    }
  }
}
```

A test whose parts are all second-set crops with vocal tracks can play them
without the singing: it adds `--instrumental` to the manifest step's argv and lists `{run}/crops/mix_instrumental.wav` and
`{run}/crops/backing_instrumental.wav` among the crops step's outputs; the
reference and the backing are then the crop's vocal-free mix and backing, always
together.

If a match summary has a caveat beginning `nothing beat the preset you started
from`, the preset step runs its declared `fallback_argv` instead, and the
runner checks that its output is byte-identical to `template`. If the two
render records contain identical `applied_settings`, the part is complete
without a manifest or audition. No private key is read or hashed by the runner.

The frozen `docs/heldout-listening-sw50r.md` predates this command-block
format. It is intentionally not runnable through this tool, and its archived
run cannot gain a retrospective `execution.json`.

The runner records execution, not the declared test's outcome. A future test
also needs its own committed result rules and evidence checks in
`summarize_declared_listening.py` before its aggregate outcome can be reported;
that summarizer currently implements only the frozen SW50R test.
