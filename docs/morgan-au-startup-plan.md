# Separate Morgan Audio Unit startup readiness

**DECLARED 2026-10-09 after fresh independent source/design approval.**
All 24 synthetic tests pass. Both prior blocked reviews remain preserved. The
closed processing attempt is verified and archived at 5b58a54; no actual startup
probe, compilation or new instance has occurred before this declaration.
Commit this plan, exact sources and approval before the single host execution.

<!-- startup-approval
{
  "status": "DECLARED",
  "review": "docs/research/morgan-au-startup-review-2026-10-09.md",
  "review_sha256": "0eb8576d1cefe6682dbd70bf15a636093c88845f9097deeb7f12488b613b9c43",
  "body_sha256": "26fb892fa0efebc5817e14f13aaebdafac1e5be12f8508ab8adaec2925c7b0a2",
  "pins": {
    "scripts/check_morgan_au_startup.py": "b431139f8fbec7ec928da38bdf2722ddd770be9a056822eca86b97a7e874262f",
    "tests/test_morgan_au_startup.py": "04773714b09a5cfb9a455e042515feddbf1b52cc589d17d3bb2ce63d7a5aaed5",
    "scripts/morgan_au_startup.swift": "32965ad277f34992ba9d6742881b5a2c0def4b4ff781d54bdacf099b21844fd3",
    "packs/morgan/manifest.json": "0d81b1540d76f66f5d75889d8615a2bc30007ab16b2482b461d9bb69d9a67ad0"
  },
  "no_instance_before_declaration": true
}
startup-approval -->

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
Compile only pinned scripts/morgan_au_startup.swift into that directory, in one
attempt with /usr/bin/swiftc -swift-version 5, explicit SDK
/Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk, -O and a new local
module-cache-path under the output directory. No shared binary cache, SDK fallback,
version probe or compiler retry. Reject nonempty DEVELOPER_DIR/SDKROOT/TOOLCHAINS/
MACOSX_DEPLOYMENT_TARGET overrides. Retain exact compile command, raw stdout/stderr
hex plus readable text, return code and binary SHA256. Compilation timeout is
120seconds using subprocess.run(timeout=120); preserve partial compiler output.
Launch only this binary with no arguments. It hardcodes aumf/NMAS/NDSP, schedules
an independent global-queue20second startup deadline, services the main queue
with dispatchMain rather than blocking on a semaphore, handles completion on
the main queue and retains the unit. It reports component version, then
accepts only quit:true. No explicit fullState retrieval, XML decode, bus/audio
configuration, DSP resource allocation, buffers or file access occurs. Native
instantiation may internally initialize plugin state; the host cannot audit that.
Do not load presets or send amp/state/
parameter/input/out/render commands. Send only quit:true during cleanup.
No model, average, waveform, original/render DI, recording/catalog/native/reserved
asset, training, download, registry reset, cache purge or license change.

Read a complete startup line under one30second monotonic deadline with1MiB cap,
not blocking TextIO readline after readiness. Preserve partial bytes even on
EOF/deadline/schema error. Require ready:true and actual nonempty string version
other than unknown/n/a. No claim of live parameter readback or renderability.

Total budget cooperative180seconds. The compilation child has a120second timeout;
this does not establish a hard bound on compiler descendants, filesystem/Git
operations or whole process. No hard whole-process budget is claimed.
Reply waits and cleanup waits are bounded. Quit, stdinclose,
wait10s, kill and secondwait10s are attempted as needed; retain failures and close
streams/logs. Never leave a timeout counted READY. Every instance is stopped or
reported explicitly not reaped. No unrelated process is killed.
The native probe uses _exit(0) after quit: this checks process termination, not
successful Audio Unit destructor/deallocation or teardown handlers.

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
errors, compiler failure and compiler timeout with exact partial output.
All 24 synthetic tests pass. They do not start installed components.
Fresh independent source review precedes declaration. After execution main checks
full stdout/stderr/response/cleanup/source provenance. This metadata-only check
has no numerical model result requiring an independent scientific scorer.

The first blocked review is retained at
research/morgan-au-startup-blocked-review-2026-10-09.md. Its two findings motivated
the dedicated minimal Swift probe and single-attempt compiler path. Fresh review
must cover the corrected sources; that earlier review is not approval.
The second blocked review is retained at
research/morgan-au-startup-blocked-review-v2-2026-10-09.md. Its main-thread
deadlock finding motivated completion-driven control flow and a background quit
reader, with the main queue available throughout. No actual probe has run.
