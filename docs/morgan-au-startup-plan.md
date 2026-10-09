# Separate Morgan Audio Unit startup readiness

**DRAFT: source preparation only. No plugin construction authorized.**

Main requires fresh independent source/design review and commit before this
one-time infrastructure check. This does not reopen the failed processing study.
Declaration metadata belongs above the frozen body. Add a startup-approval HTML
JSON block with status DECLARED, review docs/research/morgan-au-startup-review-2026-10-09.md,
review_sha256, body_sha256, exact pins for the five SOURCES, and
no_instance_before_declaration:true. Review must attest Verdict: APPROVE and all
five pin hashes plus body hash. Plan/review/sources must match committed HEAD.
Execute only after the earlier stopped-attempt verification/archive is complete.

## Frozen design

Question: can one Morgan Audio Unit server start in the approved host execution
context, report an actual version, then shut down? This is operational readiness,
not model performance, audio quality, old timing, transfer or product validation.
The processing attempt declared df68127 remains closed INCONCLUSIVE. A READY
startup cannot authorize repeating it, changing its path or tuning its rules.

Use helper project Python explicitly OUTSIDE its process sandbox with approval:
/Users/yoavbz/.codex/bin/neuraldsp-safe python-file scripts/check_morgan_au_startup.py
No CLI arguments, arbitrary commands, paths or overrides are accepted. Fixed
exclusive output tmp/morgan-au-startup-20261009, one instance only, no retries.
Compile pinned scripts/au_render_server.swift using pinned scripts/_swift.py into
that directory; cache use follows that existing helper. Retain compile output,
server binary, exact launch arguments, raw startup reply/partial hex and stderr.
Launch exactly aumf NMAS NDSP --settle 0. Do not load presets or send amp/state/
parameter/input/out/render commands. Send only quit:true during cleanup.
No model, average, waveform, original/render DI, recording/catalog/native/reserved
asset, training, download, registry reset, cache purge or license change.

Read a complete startup line under one30second monotonic deadline with1MiB cap,
not blocking TextIO readline after readiness. Preserve partial bytes even on
EOF/deadline/schema error. Require ready:true and actual nonempty string version
other than unknown/n/a. No claim of live parameter readback or renderability.

Total budget cooperative180seconds, compilation cooperative120seconds. Native
compilation cannot be forcibly interrupted by these checks; no hard whole-process
budget is claimed. Reply waits and cleanup waits are bounded. Quit, stdinclose,
wait10s, kill and secondwait10s are attempted as needed; retain failures and close
streams/logs. Never leave a timeout counted READY. Every instance is stopped or
reported explicitly not reaped. No unrelated process is killed.

READY requires successful startup/version, unchanged declared sources/HEAD,
clean shutdown with returncode0, no original/cleanup/evidence errors, and final
report publication within budget and process exit0 in the retained execution log.
A result file alone is never authoritative: pending, provisional or failure
records, any logged error or a nonzero/missing exit code preclude READY.
All other outcomes INCONCLUSIVE. Preserve
original error plus cleanup diagnostics and partial bytes. Result is staged
before publication; finalization failure withdraws authority into provisional
files and records failure. Withdrawal and failure-log errors are retained
independently in stderr while the original exception is re-raised. Close the
stderr handle even if flushing or syncing fails. No downstream ML gate uses
this readiness result.

Synthetic tests use generated real pipes and process/compiler stand-ins, covering
complete/partial/EOF/oversize replies, draft rejection, exact onlyquit commands,
wait failure/kill/reaping, brokenstdin cleanup, launchlog failure, source drift,
invalid ready/version, finite JSON, exact committed approval/source/review
matching, final publication timeouts, and simultaneous withdrawal/failure-log
errors. All 22 synthetic tests pass. They do not start installed components.
Fresh independent source review precedes declaration. After execution main checks
full stdout/stderr/response/cleanup/source provenance. This metadata-only check
has no numerical model result requiring an independent scientific scorer.
