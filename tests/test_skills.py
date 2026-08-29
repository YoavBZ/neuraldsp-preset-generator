"""The skill documents are the interface, and nothing else executes them.

An agent reads `skills/*/SKILL.md`, follows it literally, and never compiles it.
So every path, command and flag in that prose is an unverified claim about the
repository: rename a script, move a pack file, drop a flag, and the skill keeps
confidently instructing the agent to do the old thing. The failure surfaces in
front of a user, mid-task, with no test having gone red first.

These tests treat the documents as executable contracts — the paths must
resolve, the commands must run, the flags must exist, and the flow the generate
skill describes must actually produce a preset. The reference files the skills
link to are included, because a skill that says "see preset-spec.md" has
delegated its instructions there.

Two claims in `skills/generate/SKILL.md` are newer than the rest and were the
reason this file exists: that the pack can be detected from a template's own
header rather than assumed, and that `show.py` reports `tone_knowledge.exists`
so a pack with no `tone.md` is recognised instead of guessed at. Both are
pinned below.

Nothing here needs the plugin, the network, or a preset library: commands that
do are skipped by name, with a reason, so `pytest -rs` lists what went
unchecked.
"""

from __future__ import annotations

import ast
import functools
import hashlib
import inspect
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys

import pytest

from packs.loader import detect_pack, list_packs, load_pack
from packs.timing import note_ms

ROOT = pathlib.Path(__file__).parent.parent
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
SCRIPTS = ROOT / "scripts"
EXAMPLE = ROOT / "samples" / "Example_Clean_PR12.xml"

# The pack the documented examples are written against. Taken from the loader's
# own default rather than spelled out here, so renaming the reference pack moves
# these tests with it.
REFERENCE_PACK = inspect.signature(load_pack).parameters["pack_id"].default

FENCE = re.compile(r"```(\w*)\n(.*?)```", re.S)
PLUGIN_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w<>/.\-]+)")
MD_LINK = re.compile(r"\]\((?!https?://)([^)#]+)\)")
BARE_FILE = re.compile(r"`([\w\-]+\.(?:py|json|md|xml))`")
FLAG = re.compile(r"--[a-z][a-z0-9-]*")


def linked_docs(skill: pathlib.Path) -> list:
    """The reference files a skill sends the agent to read."""
    return [
        (skill.parent / target).resolve()
        for target in MD_LINK.findall(skill.read_text())
        if target.endswith(".md")
    ]


# Skills first, then everything they link to. Deliberately not transitive:
# docs/measuring-against-the-plugin.md is a maintainer's procedure for a machine
# with the Audio Unit installed, not part of the path an agent follows.
DOCS = list(SKILLS)
for _skill in SKILLS:
    for _doc in linked_docs(_skill):
        if _doc not in DOCS:
            DOCS.append(_doc)

DOC_IDS = {
    doc: (doc.parent.name if doc.name == "SKILL.md" else doc.name) for doc in DOCS
}


# --- paths a skill names --------------------------------------------------
#
# A pack directory holds three files and only one of them is guaranteed. The
# generate skill says so itself — "a bootstrapped pack has no recipes.json at
# all" — so requiring these of every pack would fail on exactly the case the
# skill was written to handle. They are required of the reference pack instead,
# which keeps "optional" from decaying into "absent everywhere".
COMMITTED_OPTIONAL = {
    "tone.md": "a bootstrapped pack has none; show.py reports tone_knowledge.exists",
    "recipes.json": "a bootstrapped pack has none; the skill tells the agent to say so",
}
GENERATED_OPTIONAL = {
    "observed.json": "built from the user's own presets, absent on a fresh clone",
    "learned-tones.md": "appended by past runs, absent until one has something to say",
    ".learned-tones.md.lock": "serialises local note appends, absent until first use",
}
OPTIONAL_PER_PACK = {**COMMITTED_OPTIONAL, **GENERATED_OPTIONAL}
# Runtime artifacts named by the skills but deliberately absent from a clone.
GENERATED_OUTPUTS = {"summary.json"}


def plugin_paths(text: str) -> set:
    """`${CLAUDE_PLUGIN_ROOT}/…` references, with `<id>` expanded per pack."""
    found = set()
    for rel in PLUGIN_REF.findall(text):
        if "<id>" in rel:
            found.update(rel.replace("<id>", pack) for pack in list_packs())
        else:
            found.add(rel)
    return found


@pytest.mark.parametrize("doc", DOCS, ids=DOC_IDS.get)
def test_every_plugin_path_a_document_names_exists(doc):
    """A skill that points at a file that moved sends the agent nowhere, and the
    agent has no way to tell a typo from a file it lacks permission to read."""
    missing = []
    for rel in sorted(plugin_paths(doc.read_text())):
        if (ROOT / rel).exists():
            continue
        if pathlib.PurePath(rel).name in OPTIONAL_PER_PACK and _is_pack_file(rel):
            continue  # documented as optional; covered for the reference pack below
        missing.append(rel)
    assert not missing, f"{DOC_IDS[doc]} names missing paths: {missing}"


def _is_pack_file(rel: str) -> bool:
    parts = pathlib.PurePath(rel).parts
    return len(parts) == 3 and parts[0] == "packs" and parts[1] in list_packs()


@pytest.mark.parametrize("filename", sorted(COMMITTED_OPTIONAL))
def test_optional_pack_files_are_present_where_the_examples_assume_them(filename):
    """`tone.md` and `recipes.json` may be absent on a drafted pack, but the
    reference pack is what every documented example reads from — if they went
    missing there, "optional" would be hiding a broken skill rather than
    describing a bootstrapped one."""
    path = ROOT / "packs" / REFERENCE_PACK / filename
    assert path.exists(), f"pack {REFERENCE_PACK} is missing {filename}"


@pytest.mark.parametrize("filename", sorted(GENERATED_OPTIONAL))
def test_files_the_skills_write_are_ignored_by_git(filename):
    """In a clone the data root *is* the repo root, so an agent following step 7
    of the generate skill writes `packs/<id>/learned-tones.md` inside the
    checkout. Anything the skills write there has to be ignored, or the user's
    own notes and preset values turn up in `git status` and eventually in a
    commit."""
    rules = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert f"packs/*/{filename}" in rules, (
        f".gitignore has no rule for packs/*/{filename}, which the tools write "
        f"into the repo whenever no data root is configured"
    )


@pytest.mark.parametrize("doc", DOCS, ids=DOC_IDS.get)
def test_relative_links_resolve(doc):
    """Extends the skill-only check to the files the skills delegate to: a dead
    link one hop further along is just as far off the path the agent follows."""
    missing = [
        target
        for target in MD_LINK.findall(doc.read_text())
        if not (doc.parent / target).resolve().exists()
    ]
    assert not missing, f"{DOC_IDS[doc]} links to missing files: {missing}"


# Skill bodies only: the reference files also name presets that live in the
# user's own plugin folder (`Default.xml`), which this repo cannot vouch for.
@pytest.mark.parametrize("doc", SKILLS, ids=DOC_IDS.get)
def test_filenames_named_in_prose_exist_somewhere(doc):
    """Prose names files without a directory — "run `show.py` on it first",
    "the pack has no `recipes.json`". Renaming one of those leaves the sentence
    reading perfectly while pointing at nothing."""
    known = {p.name for p in ROOT.glob("*") if p.is_file()}
    for directory in ("scripts", "packs", "format", "samples", "reference", "docs"):
        known.update(p.name for p in (ROOT / directory).rglob("*") if p.is_file())
    known.update(OPTIONAL_PER_PACK)  # may legitimately not exist yet
    known.update(GENERATED_OUTPUTS)
    missing = sorted(set(BARE_FILE.findall(doc.read_text())) - known)
    assert not missing, f"{DOC_IDS[doc]} names files that do not exist: {missing}"


PARAM_PATH = re.compile(r"`([a-z][A-Za-z0-9]*)/([a-z][A-Za-z0-9]*)`")
PARAM_KEY = re.compile(r"`([a-z]+[A-Z][A-Za-z0-9]*)`")


@pytest.mark.parametrize("doc", SKILLS, ids=DOC_IDS.get)
def test_parameter_names_a_skill_mentions_are_real(doc):
    """The edit skill translates "tighter low end" into named parameters —
    `reverb/reverbLowCut`, `delayHighCut`, `tremoloRate`. Those names are the
    instruction: an agent writes what the sentence says, and the writer refuses
    a key the template doesn't have. A renamed parameter would leave the advice
    reading perfectly and failing every time it is followed.
    """
    pack = load_pack(REFERENCE_PACK)
    keys = {spec.key for spec in pack.parameters.values()}
    modules = {spec.module for spec in pack.parameters.values()}
    text = doc.read_text()

    unknown = [
        f"{module}/{key}"
        for module, key in PARAM_PATH.findall(text)
        if pack.get(module, key) is None
    ]
    # Bare camelCase names are written for a module the sentence already names
    # ("the live amp's own reverb knob"), so either half is a real reference.
    unknown += [
        name for name in PARAM_KEY.findall(text) if name not in keys | modules
    ]
    assert not unknown, (
        f"{DOC_IDS[doc]} names parameters {REFERENCE_PACK} does not have: {unknown}"
    )


# --- commands a skill shows -----------------------------------------------

NEEDS_THE_PLUGIN = ("au_probe", "au_render", "swiftc", "audit_manifest.py")
NEEDS_A_PRESET_FOLDER = (
    "Audio/Presets",
    "Documents/Neural",
    "<user preset folder>",
)
AUDIO_PLACEHOLDERS = (
    "REFERENCE.wav",
    "PROBE.wav",
    "PROBE_DI.wav",
    "TEMPLATE_RENDER.wav",
    "CANDIDATE_RENDER.wav",
)


def needs_audio_fixture(command: str) -> bool:
    """Whether materialising this command requires the optional audio stack."""
    return any(placeholder in command for placeholder in AUDIO_PLACEHOLDERS)


@functools.lru_cache(maxsize=None)
def analysis_is_available() -> bool:
    """Whether the optional stack needed by documented audio commands exists."""
    from analysis import AnalysisUnavailable, require

    try:
        require("testing documented audio commands")
    except AnalysisUnavailable:
        return False
    return True


def commands_in(doc: pathlib.Path) -> list:
    """Every runnable line of every ```bash block, continuations joined."""
    commands = []
    for lang, block in FENCE.findall(doc.read_text()):
        if lang != "bash":
            continue
        for line in block.replace("\\\n", " ").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                commands.append(line)
    return commands


@functools.lru_cache(maxsize=None)
def plugin_is_available() -> bool:
    """Whether this machine can actually run a plugin command.

    Asked of the machine rather than of the command's spelling. `swiftc` present
    and at least one pack's Audio Unit installed and instantiable — `auval`
    exits nonzero for an Audio Unit that is missing or unlicensed, which is
    exactly the distinction that matters here.

    Cached because `auval` takes a second or two and the answer cannot change
    inside one run.
    """
    if shutil.which("swiftc") is None or shutil.which("auval") is None:
        return False
    for pack_dir in sorted((ROOT / "packs").glob("*/manifest.json")):
        try:
            unit = json.loads(pack_dir.read_text()).get("audio_unit") or {}
        except (OSError, json.JSONDecodeError):
            continue
        triple = [unit.get("type"), unit.get("subtype"), unit.get("manufacturer")]
        if not all(triple):
            continue
        try:
            probe = subprocess.run(["auval", "-v", *triple],
                                   capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired):
            return False
        if probe.returncode == 0:
            return True
    return False


def skip_reason(command: str):
    """Why this command cannot run in CI, or None if it can."""
    if any(marker in command for marker in NEEDS_THE_PLUGIN):
        # By capability, not by spelling. These commands used to skip on the one
        # machine that could run them — a substring match on `swiftc` or
        # `/tmp/au_probe` cannot tell "no plugin here" from "the plugin is right
        # here", so the documented plugin commands were verified nowhere at all.
        if not plugin_is_available():
            return "needs the licensed Audio Unit installed on macOS"
    if any(marker in command for marker in NEEDS_A_PRESET_FOLDER):
        return "reads or writes the user's own Neural DSP preset folder"
    if needs_audio_fixture(command) and not analysis_is_available():
        return "needs the optional analysis and match extras"
    if re.match(r"python3? +\"?\$\{CLAUDE_PLUGIN_ROOT\}", command):
        return None
    # A Swift build, or one of the helpers it produces, is runnable wherever the
    # plugin is — and those two commands are precisely the ones no machine was
    # checking, because they skipped on the spelling of `swiftc` before anything
    # asked whether swiftc was installed.
    first = command.split()[0]
    if first == "swiftc" or pathlib.Path(first).name in BUILT_HELPERS:
        return None if plugin_is_available() else (
            "needs the licensed Audio Unit installed on macOS"
        )
    return "not an invocation of a bundled script"


ALL_COMMANDS = [(doc, command) for doc in DOCS for command in commands_in(doc)]


@pytest.fixture
def sandbox(tmp_path):
    """A working directory holding a template and a spec, with no route home.

    HOME is redirected so a stray `~` in a documented command cannot reach the
    user's own files, and the data-root variables are cleared so a run is not
    steered by whatever the developer happens to have exported.
    """
    # Lower-case on purpose: a temporary path that itself looked like a
    # placeholder would trip the unsubstituted-placeholder guard below.
    template = tmp_path / "template.xml"
    template.write_bytes(EXAMPLE.read_bytes())
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(documented_spec()))
    return Sandbox(tmp_path, template, spec)


class Sandbox:
    def __init__(self, path, template, spec):
        self.path = path
        self.template = template
        self.spec = spec
        self._runs = 0
        self._audio = None
        self._verdict_run = None
        self._audition_run = None
        self._blind_key = None

    def out(self) -> pathlib.Path:
        self._runs += 1
        return self.path / f"out{self._runs}.xml"

    def audio_pair(self):
        """Create a deterministic reference and the exact DI behind it lazily."""
        if self._audio is None:
            from analysis import refchain
            from tests import fixtures_audio as fx

            probe = self.path / "probe.wav"
            reference = self.path / "reference.wav"
            di = fx.plucks(seconds=2.0, gap=0.9, seed=5)
            fx.write_wav(probe, di)
            fx.write_wav(reference, refchain.render(di, {
                "sw50rAmp/sw50rVolume": 72.0,
                "sw50rAmp/sw50rTreble": 35.0,
            }))
            self._audio = reference, probe
        return self._audio

    def run_dir(self) -> pathlib.Path:
        return self.path / "match-run"

    def verdict_run(self) -> pathlib.Path:
        """A minimal completed match run for the independently tested logger command."""
        if self._verdict_run is not None:
            return self._verdict_run

        from match.store import Run, Store, Trial

        directory = self.path / "verdict-run"
        directory.mkdir()
        reference_sha = "a" * 64
        with Store(str(directory / "trials.sqlite3")) as store:
            store.start_run(Run(
                run_id="documented-run", pack="morgan",
                reference_sha=reference_sha, regime="probe",
                loss_profile="unpaired-v1", renderer_id="synthetic",
            ))
            trial = store.add_trial(
                "documented-run",
                Trial(
                    params={"sw50rAmp/sw50rVolume": 62.0},
                    objectives={"total": 0.4, "timbre": 0.3},
                    fingerprint={"spectrum": {
                        "band_centres_hz": [100.0], "band_db": [0.0],
                    }},
                ),
            )
        summary = {
            "schema": "tone-match-summary-v1", "run_id": "documented-run",
            "pack": "morgan", "loss_profile": "unpaired-v1",
            "reference": {
                "regime": "probe", "regime_confidence": 1.0,
                "excerpt": {"start_s": 0.0, "duration_s": 1.0},
                "fingerprint": {
                    "source": {"sha256": reference_sha},
                    "spectrum": {"band_centres_hz": [100.0], "band_db": [0.0]},
                },
            },
            "renderer": {"renderer_id": "synthetic", "plugin_version": None,
                         "renderer_build": "test", "reproducible": True,
                         "band_noise_db": 0.0},
            "starting_point": {
                "score": 0.8, "objectives": {"total": 0.8},
                "settings": {"sw50rAmp/sw50rVolume": 50.0},
            },
            "shortlist": [{
                "rank": 1, "trial_id": trial.trial_id, "score": 0.4,
                "objectives": {"total": 0.4, "timbre": 0.3},
                "fingerprint_delta": [{
                    "centre_hz": 100.0, "target_db": 0.0,
                    "candidate_db": 0.0, "delta_db": 0.0,
                }],
                "changes": [],
            }],
        }
        (directory / "summary.json").write_text(json.dumps(summary))
        (directory / "match-1.json").write_text(json.dumps({
            "name": "match 1", "parameters": [{
                "module": "sw50rAmp", "key": "sw50rVolume", "value": 62.0,
            }],
        }))
        self._verdict_run = directory
        return directory

    def audition_run(self) -> pathlib.Path:
        """A real synthetic match run for the independently tested exporter."""
        if self._audition_run is not None:
            return self._audition_run
        reference, probe = self.audio_pair()
        directory = self.path / "audition-run"
        completed = subprocess.run([
            sys.executable, str(ROOT / "scripts" / "match_preset.py"),
            "--template", str(self.template),
            "--reference", str(reference),
            "--reference-mode", "paired_di",
            "--probe-di", str(probe),
            "--amp", "sw50r",
            "--budget", "60",
            "--shortlist", "1",
            "--renderer", "synthetic",
            "--out-dir", str(directory),
        ], cwd=ROOT, capture_output=True, text=True)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        self._audition_run = directory
        return directory

    def blind_key(self) -> pathlib.Path:
        """Make a valid key without requiring the optional audio stack.

        The logger verifies bytes and records a verdict; audio rendering belongs
        to the exporter's independently exercised command.  Keeping this fixture
        byte-only makes that separation true in the lightweight CI matrix too.
        """
        if self._blind_key is not None:
            return self._blind_key
        run_dir = self.verdict_run()
        audition_dir = run_dir / "audition-candidate-1"
        audition_dir.mkdir()
        montage = audition_dir / "audition.flac"
        montage.write_bytes(b"documented blind audition")
        from match.store import Store, Trial
        from match.verdict import candidate_binding_sha256, validate_candidate

        validated = validate_candidate(run_dir, 1)
        audition_di_sha = "d" * 64
        audition_render_sha = "e" * 64
        with Store(str(run_dir / "trials.sqlite3")) as store:
            audition_trial = store.add_trial("documented-run", Trial(
                params=dict(validated.trial.params), di_sha=audition_di_sha,
                render_sha=audition_render_sha,
                objectives=dict(validated.trial.objectives or {}),
                fingerprint=dict(validated.trial.fingerprint or {}),
            ))
        summary_path = run_dir / "summary.json"
        spec_path = run_dir / "match-1.json"
        settings = validated.summary["starting_point"]["settings"]
        self._blind_key = audition_dir / "audition.flac.key.json"
        self._blind_key.write_text(json.dumps({
            "schema": "rab-audition-v1",
            "blind_key": {"A": "second", "B": "first"},
            "output": {
                "path": str(montage),
                "sha256": hashlib.sha256(montage.read_bytes()).hexdigest(),
            },
            "match": {
                "schema": "match-audition-1",
                "run_dir": str(run_dir),
                "run_id": validated.run.run_id,
                "source_trial_id": validated.trial.trial_id,
                "audition_trial_id": audition_trial.trial_id,
                "audition_render_sha256": audition_render_sha,
                "candidate_rank": 1,
                "roles": {"first": "template", "second": "candidate"},
                "renderer": validated.summary["renderer"],
                "excerpt": validated.summary["reference"]["excerpt"],
                "probe_di": {"audio_sha256": audition_di_sha},
                "binding": {
                    "candidate_context_sha256": candidate_binding_sha256(validated),
                    "summary_sha256": hashlib.sha256(
                        summary_path.read_bytes()).hexdigest(),
                    "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                    "template_settings_sha256": hashlib.sha256(json.dumps(
                        settings, sort_keys=True, separators=(",", ":"),
                        allow_nan=False,
                    ).encode("utf-8")).hexdigest(),
                },
            },
        }))
        return self._blind_key

    def build(self, helper: str) -> pathlib.Path:
        """Compile one of the documented Swift helpers into this sandbox.

        On demand rather than in order: the documentation builds a helper in one
        command and uses it in the next, and a test that relied on those two
        running in that order would pass or fail on pytest's collection order.
        """
        import sys as _sys

        _sys.path.insert(0, str(ROOT / "scripts"))
        from _swift import compile_swift

        binary = self.path / helper
        if not binary.exists():
            built, error = compile_swift(ROOT / "scripts" / f"{helper}.swift", binary)
            assert built is not None and built.returncode == 0, (
                f"could not build {helper}.swift:\n{error}"
            )
        return binary

    def run(self, argv) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["HOME"] = str(self.path)
        for var in ("NDSP_PRESET_DATA", "CLAUDE_PLUGIN_DATA"):
            env.pop(var, None)
        return subprocess.run(
            argv, capture_output=True, text=True, cwd=str(self.path), env=env
        )


def documented_spec() -> dict:
    """The spec example from reference/preset-spec.md, used as-is.

    Substituting an invented spec for the one the documentation shows would
    leave the documented example itself untested — and it is the thing an agent
    copies.
    """
    for _, block in FENCE.findall((ROOT / "reference" / "preset-spec.md").read_text()):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "parameters" in parsed:
            return parsed
    raise AssertionError("reference/preset-spec.md no longer shows a full spec example")


# Placeholders the documents use for "a file you supply". Anything left looking
# like a placeholder after substitution fails the test rather than being run,
# so a new one cannot slip through as a real filename.
LEFTOVER = re.compile(
    r"\$\{|<[a-z ]+>|\b[A-Z][A-Z_]+\.(xml|json|wav|flac)\b|"
    r"\b[A-Z][A-Z_]+_SECONDS\b"
)


# Helpers the documentation tells the reader to build into /tmp and then run.
# Redirected into the sandbox: a test must not depend on, or leave behind, a
# fixed path outside its own directory.
BUILT_HELPERS = ("au_probe", "au_render_server", "au_render", "au_silence_check")


def materialise(command: str, sandbox: Sandbox) -> list:
    """Turn a documented command into an argv the test can actually run."""
    text = command.replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))
    is_blind_verdict = "log_blind_verdict.py" in text
    is_verdict = "log_match_verdict.py" in text or is_blind_verdict
    is_export = "export_match_audition.py" in text
    if is_blind_verdict:
        text = text.replace(
            "RUN_DIR/audition-candidate-1/audition.flac.key.json",
            str(sandbox.blind_key()))
        text = text.replace("LISTENER", "documentation-blind-test")
    if is_export:
        text = text.replace("RUN_DIR", str(sandbox.audition_run()))
    if is_verdict:
        if not is_blind_verdict:
            text = text.replace("RUN_DIR", str(sandbox.verdict_run()))
        text = text.replace("LISTENER", "documentation-test")
    for placeholder in ("PRESET.xml", "TEMPLATE.xml"):
        text = text.replace(placeholder, str(sandbox.template))
    text = text.replace("/tmp/spec.json", str(sandbox.spec))
    if ("REFERENCE.wav" in text or "PROBE.wav" in text
            or "PROBE_DI.wav" in text):
        reference, probe = sandbox.audio_pair()
        text = text.replace("REFERENCE.wav", str(reference))
        text = text.replace("PROBE.wav", str(probe))
        text = text.replace("PROBE_DI.wav", str(probe))
        # The audition command needs two already-rendered alternatives. Their tone
        # is irrelevant to this documentation test; existing deterministic audio
        # exercises the command and keeps every placeholder explicit.
        text = text.replace("TEMPLATE_RENDER.wav", str(probe))
        text = text.replace("CANDIDATE_RENDER.wav", str(reference))
        text = text.replace("START_SECONDS", "0")
        text = text.replace("DURATION_SECONDS", "1")
    # Each documented command is tested independently, so the apply preview uses
    # the known-valid spec instead of depending on the match command running first.
    text = text.replace("RUN_DIR/match-1.json", str(sandbox.spec))
    text = text.replace("RUN_DIR", str(sandbox.run_dir()))
    for placeholder in ("NEW.xml", "OUT.xml", "MATCHED.xml"):
        if placeholder in text:
            text = text.replace(placeholder, str(sandbox.out()))
    for helper in BUILT_HELPERS:
        text = text.replace(f"/tmp/{helper}", str(sandbox.path / helper))
        # The documented build line is written to be run from the repository
        # root. The sandbox deliberately is not there, so the source is resolved
        # the same way `${CLAUDE_PLUGIN_ROOT}` is.
        text = text.replace(f"scripts/{helper}.swift",
                            str(ROOT / "scripts" / f"{helper}.swift"))
    argv = shlex.split(text, comments=True)
    assert argv, command
    leftover = [token for token in argv if LEFTOVER.search(token)]
    assert not leftover, (
        f"unsubstituted placeholder(s) {leftover} — add them to materialise() "
        f"rather than letting the command run against a literal filename"
    )
    if argv[0] in ("python", "python3"):
        if is_verdict:
            # The real command intentionally follows the user's configured data
            # root. This sandbox has cleared those variables, so pin it here instead
            # of letting a documentation test write into the repository checkout.
            argv.extend(["--data-dir", str(sandbox.path / "user-data")])
        return [sys.executable, *argv[1:]]
    # A Swift build, or one of the helpers it produces. Both are documented
    # verbatim and both are now run on a machine that has the plugin, which is
    # the only place they can be checked at all.
    if argv[0] == "swiftc" or pathlib.Path(argv[0]).parent == sandbox.path:
        if argv[0] != "swiftc":
            sandbox.build(pathlib.Path(argv[0]).name)
        return argv
    raise AssertionError(f"unrunnable documented command: {command}")


@pytest.mark.parametrize(
    "doc,command",
    ALL_COMMANDS,
    ids=[f"{DOC_IDS[d]}:{c.split()[0]}:{i}" for i, (d, c) in enumerate(ALL_COMMANDS)],
)
def test_every_documented_command_runs(doc, command, sandbox):
    """The commands are copied verbatim by an agent, so a stale flag or a
    renamed script is a failure the user watches happen."""
    reason = skip_reason(command)
    if reason:
        pytest.skip(f"{command.split()[0]}…: {reason}")
    result = sandbox.run(materialise(command, sandbox))
    assert result.returncode == 0, f"{command}\n{result.stderr}"


def test_the_skills_own_commands_are_all_exercised():
    """Guard on the guard: every skip above is judged by a substring, so a new
    command that happens to match one would vanish from the suite silently.
    The skill bodies are the part that must never go unchecked."""
    from_skills = [(doc, command) for doc, command in ALL_COMMANDS if doc in SKILLS]
    assert from_skills, "no commands extracted from the skill bodies"
    unrun = [
        (DOC_IDS[doc], command, skip_reason(command))
        for doc, command in from_skills
        if skip_reason(command)
        and skip_reason(command) != "needs the optional analysis and match extras"
    ]
    assert not unrun, f"skill commands are not being run: {unrun}"


def test_audio_fixture_commands_skip_cleanly_without_the_extra(monkeypatch):
    """The lightweight CI matrix must skip before NumPy-backed fixture creation."""
    monkeypatch.setattr(
        sys.modules[__name__], "analysis_is_available", lambda: False
    )
    commands = [command for _, command in ALL_COMMANDS if needs_audio_fixture(command)]
    assert commands, "no documented audio commands found"
    assert {
        skip_reason(command) for command in commands
    } == {"needs the optional analysis and match extras"}


def test_audio_skill_commands_are_exercised_when_the_extra_is_installed():
    """The bare job may skip audio; the analysis job must execute those commands."""
    if not analysis_is_available():
        pytest.skip("needs the optional analysis and match extras")
    unrun = [
        (DOC_IDS[doc], command, skip_reason(command))
        for doc, command in ALL_COMMANDS
        if doc in SKILLS
        and needs_audio_fixture(command)
        and skip_reason(command)
    ]
    assert not unrun, f"audio skill commands are not being run: {unrun}"


INLINE_JSON = re.compile(r"`(\{[^`]*\})`")


def _as_spec(text: str):
    """A spec, an entry of one, or None for anything else quoted as JSON."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None  # a fragment quoted from a manifest, or `{amp}`
    if not isinstance(parsed, dict):
        return None
    if "parameters" in parsed:
        return parsed
    if {"module", "key", "value"} <= set(parsed):
        return {"parameters": [parsed]}
    return None  # a note value, a manifest entry: real JSON, not a spec


def spec_examples() -> list:
    """Every JSON example in the documents that an agent could hand to the
    writer — fenced blocks and the one-liners quoted inline in prose."""
    examples = []
    for doc in DOCS:
        text = doc.read_text()
        candidates = [
            (f"block{i}", block)
            for i, (lang, block) in enumerate(FENCE.findall(text))
            if lang == "json"
        ]
        candidates += [
            (f"inline{i}", found) for i, found in enumerate(INLINE_JSON.findall(text))
        ]
        for label, candidate in candidates:
            spec = _as_spec(candidate)
            if spec is not None:
                examples.append((doc, label, spec))
    return examples


SPEC_EXAMPLES = spec_examples()


@pytest.mark.parametrize(
    "doc,label,spec",
    SPEC_EXAMPLES,
    ids=[f"{DOC_IDS[d]}:{label}" for d, label, _ in SPEC_EXAMPLES],
)
def test_every_json_example_is_a_spec_the_writer_accepts(doc, label, spec, sandbox):
    """The JSON examples are what an agent pattern-matches when writing a spec.
    A key that no longer exists, or a member name that was renamed, is rejected
    only at the moment the agent runs the writer."""
    path = sandbox.path / f"{label}.json"
    path.write_text(json.dumps(spec))
    result = sandbox.run([
        sys.executable, str(SCRIPTS / "apply_spec.py"),
        "--template", str(sandbox.template), "--spec", str(path),
        "--out", str(sandbox.out()), "--dry-run",
    ])
    assert result.returncode == 0, f"{DOC_IDS[doc]} {label}:\n{result.stderr}"


def test_the_documented_examples_were_actually_found():
    """Every extractor here fails open: a regex that stops matching produces an
    empty corpus and a green run. These are the counts that make the rest of
    the file mean something."""
    assert SPEC_EXAMPLES, "no JSON spec examples extracted from the documents"
    assert ALL_COMMANDS, "no shell commands extracted from the documents"
    assert DOCUMENTED_SCRIPTS, "no ${CLAUDE_PLUGIN_ROOT} script invocations found"


# --- flags a skill mentions -----------------------------------------------


def _add_argument_flags(node) -> set:
    return {
        arg.value
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and getattr(call.func, "attr", None) == "add_argument"
        for arg in call.args
        if isinstance(arg, ast.Constant)
        and isinstance(arg.value, str)
        and arg.value.startswith("--")
    }


@functools.lru_cache(maxsize=None)
def _helper_flags() -> dict:
    """Flags added by the shared helpers in scripts/_cli.py, by function name."""
    tree = ast.parse((SCRIPTS / "_cli.py").read_text())
    return {
        node.name: _add_argument_flags(node)
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


@functools.lru_cache(maxsize=None)
def flags_of(script: str) -> frozenset:
    """Every long flag a script defines, read from its argparse calls."""
    tree = ast.parse((SCRIPTS / script).read_text())
    flags = _add_argument_flags(tree)
    helpers = _helper_flags()
    for call in ast.walk(tree):
        if isinstance(call, ast.Call) and getattr(call.func, "id", None) in helpers:
            flags |= helpers[call.func.id]
    return frozenset(flags)


# A script named by a document but missing from the repo is the path tests'
# failure to report; excluding it here keeps that failure from arriving as an
# unrelated FileNotFoundError out of every flag test at once.
DOCUMENTED_SCRIPTS = sorted(
    {
        pathlib.PurePath(rel).name
        for doc in DOCS
        for rel in plugin_paths(doc.read_text())
        if rel.startswith("scripts/") and rel.endswith(".py") and (ROOT / rel).exists()
    }
)


@pytest.mark.parametrize("script", DOCUMENTED_SCRIPTS)
def test_flag_extraction_agrees_with_argparse(script):
    """Reading the flags out of the source is only useful if it sees what
    argparse assembles — `show.py` gets `--data-dir` from a helper in _cli.py,
    so a naive read of the file alone would miss it and pass anything."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--help"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    usage = result.stdout.split("\n\n")[0]
    assert set(FLAG.findall(usage)) == set(flags_of(script)), script


@pytest.mark.parametrize(
    "doc,command",
    ALL_COMMANDS,
    ids=[f"{DOC_IDS[d]}:{i}" for i, (d, c) in enumerate(ALL_COMMANDS)],
)
def test_flags_used_in_a_command_exist_in_that_script(doc, command):
    """A flag that was renamed still reads fine in prose; the script exits 2."""
    scripts = [
        pathlib.PurePath(token).name
        for token in shlex.split(command, comments=True)
        if token.endswith(".py")
    ]
    if len(scripts) != 1 or scripts[0] not in DOCUMENTED_SCRIPTS:
        pytest.skip(f"not a single bundled-script invocation: {command.split()[0]}…")
    unknown = sorted(set(FLAG.findall(command)) - set(flags_of(scripts[0])))
    assert not unknown, f"{scripts[0]} has no {unknown} ({DOC_IDS[doc]})"


@pytest.mark.parametrize("doc", DOCS, ids=DOC_IDS.get)
def test_flags_mentioned_in_prose_exist(doc):
    """Prose mentions flags outside any command block — "pass `--strip-irs`",
    "drop `--dry-run`". Those are instructions too."""
    known = set().union(*(flags_of(script) for script in DOCUMENTED_SCRIPTS))
    unknown = sorted(set(FLAG.findall(doc.read_text())) - known)
    assert not unknown, (
        f"{DOC_IDS[doc]} mentions flags no documented script defines: {unknown}"
    )


# --- the flow the generate skill describes --------------------------------


def test_the_documented_generate_flow_produces_a_loadable_preset(sandbox):
    """Every piece of the generate skill has a test somewhere; the sequence it
    prescribes had none. This walks it end to end — bundled template, explicit
    `selectedAmp`, a delay time computed with packs/timing.py, preview, then
    apply with `--strip-irs` — and checks the file that comes out is one the
    plugin could load.
    """
    apply_spec = str(SCRIPTS / "apply_spec.py")

    # Step 3: "compute milliseconds from the tempo with packs/timing.py and
    # write delay/delayTime" — a dotted eighth at 96 BPM.
    delay_ms = note_ms(96, "1/8 dotted")

    # Step 4/5: the bundled example is the default template, and selectedAmp is
    # set explicitly because the skill says any template can produce any amp.
    spec = sandbox.path / "generate.json"
    spec.write_text(json.dumps({
        "name": "Documented Flow",
        "parameters": [
            {"module": "", "key": "selectedAmp", "value": "SW50R"},
            {"module": "sw50rAmp", "key": "sw50rVolume", "value": 62},
            {"module": "delay", "key": "delayActive", "value": True},
            {"module": "delay", "key": "delayTime", "value": delay_ms},
        ],
    }))
    out = sandbox.path / "Documented Flow.xml"
    argv = [
        sys.executable, apply_spec,
        "--template", str(ROOT / "samples" / "Example_Clean_PR12.xml"),
        "--spec", str(spec), "--strip-irs", "--out", str(out),
    ]

    preview = sandbox.run([*argv, "--dry-run"])
    assert preview.returncode == 0, preview.stderr
    assert "SW50R" in preview.stdout, "the change list is what the user approves"
    assert not out.exists(), "a preview that writes is not a preview"

    written = sandbox.run(argv)
    assert written.returncode == 0, written.stderr
    assert out.exists()

    from format.parser import parse, parse_file
    from format.structured import build
    from format.writer import write

    raw = out.read_bytes()
    assert write(parse(raw)) == raw, "the preset must round-trip byte-exact"

    preset = build(parse_file(str(out)))
    assert preset.preset_name == "Documented Flow"
    assert preset.by_path[("", "selectedAmp")].value == "2"        # SW50R
    assert preset.by_path[("delay", "delayTime")].value == "468.75"
    assert preset.by_path[("cabParameters", "leftChosenIRFilePath")].value == ""

    # "Verify before you claim success": re-run show.py on the output.
    shown = sandbox.run([sys.executable, str(SCRIPTS / "show.py"), str(out)])
    assert shown.returncode == 0, shown.stderr
    report = json.loads(shown.stdout)
    assert report["pack"] == REFERENCE_PACK
    assert report["name"] == "Documented Flow"


# --- the two claims the newest guidance rests on --------------------------


@pytest.mark.parametrize("pack_id", list_packs())
def test_a_pack_is_detected_from_a_presets_own_header(pack_id):
    """"Detect the pack from the template's own header rather than assuming" is
    only sound advice while every pack round-trips through its own header. A
    second pack whose header collided with the first would make detection pick
    one arbitrarily, and the skill would still be telling the agent to trust it.
    """
    pack = load_pack(pack_id)
    detected = detect_pack(pack.file_header)
    assert detected is not None, f"{pack.file_header!r} detects as no pack"
    assert detected.pack_id == pack_id


@pytest.mark.parametrize(
    "header,expected", [("morgan", "morgan"), ("neural_dsp_toneking", "toneking")]
)
def test_the_headers_the_guidance_relies_on(header, expected):
    """The two plugins that exist today, spelled out: the guidance stopped
    assuming a single pack when the second one landed, and these are the exact
    strings that make the difference."""
    detected = detect_pack(header)
    assert detected is not None and detected.pack_id == expected


def test_the_bundled_example_identifies_itself(sandbox):
    """The default template must be detectable without --pack, or the skill's
    "detect it from the template" instruction has no starting point."""
    result = sandbox.run([sys.executable, str(SCRIPTS / "show.py"), str(EXAMPLE)])
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["file_header"] == load_pack(REFERENCE_PACK).file_header
    assert report["pack"] == REFERENCE_PACK
    assert report["tone_knowledge"]["exists"] is True
    assert report["tone_knowledge"]["path"].endswith(f"packs/{REFERENCE_PACK}/tone.md")


@pytest.fixture(scope="module")
def drafted_plugin_root(tmp_path_factory):
    """A copy of the plugin whose only pack is a freshly bootstrapped draft.

    The two committed packs both ship a tone.md, so the case the skill added
    guidance for — a pack nobody has characterised yet — cannot be reached
    without building one. It is drafted here by the documented route,
    bootstrap_pack.py, into a throwaway plugin directory: the scripts derive
    their root from __file__, so a copy is a working installation and the real
    packs/ directory is never touched.
    """
    root = tmp_path_factory.mktemp("plugin")
    # Skip a developer's own preset library and generated catalog: they can be
    # thousands of files, and none of them is what is being tested.
    skip = shutil.ignore_patterns("templates", "__pycache__", "*.xml",
                                   "observed.json", "learned-tones.md*")
    for name in ("scripts", "packs", "format"):
        shutil.copytree(ROOT / name, root / name, ignore=skip)
    # bootstrap_pack.py refuses to redraft a reviewed pack, and rightly so; the
    # copy has none, which is what an unsupported plugin looks like.
    shutil.rmtree(root / "packs" / REFERENCE_PACK)

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "bootstrap_pack.py"),
         "--preset", str(EXAMPLE), "--pack-id", "drafted"],
        capture_output=True, text=True, cwd=str(root),
    )
    assert result.returncode == 0, result.stderr
    return root


def test_show_reports_no_tone_knowledge_for_a_bootstrapped_pack(
    drafted_plugin_root, tmp_path
):
    """The generate skill tells the agent to read `tone_knowledge.exists` and
    refuse to map a tonal description when it is false. If the field ever
    reported a path's existence loosely — or stopped being emitted — the agent
    would fall back to inventing the mapping, which is the one failure this
    project exists to prevent."""
    result = subprocess.run(
        [sys.executable, str(drafted_plugin_root / "scripts" / "show.py"),
         str(EXAMPLE), "--pack", "drafted", "--data-dir", str(tmp_path)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)

    assert report["pack"] == "drafted"
    assert report["tone_knowledge"]["exists"] is False
    assert not pathlib.Path(report["tone_knowledge"]["path"]).exists()
    assert report["learned_notes"]["exists"] is False
    assert report["learned_notes"]["path"].startswith(str(tmp_path)), (
        "learned notes belong under the data root, not in the plugin directory"
    )


def test_a_bootstrapped_pack_has_no_recipes_and_says_so(drafted_plugin_root, tmp_path):
    """The other half of the same guidance: "a bootstrapped pack has no
    recipes.json at all". The agent finds that out by asking for one, so the
    refusal has to be a sentence it can relay, not a traceback."""
    assert not (drafted_plugin_root / "packs" / "drafted" / "recipes.json").exists()

    result = subprocess.run(
        [sys.executable, str(drafted_plugin_root / "scripts" / "apply_spec.py"),
         "--template", str(EXAMPLE), "--pack", "drafted",
         "--recipe", "amp/pr12-clean", "--out", str(tmp_path / "out.xml"), "--dry-run"],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 2
    assert "No recipes for pack 'drafted'" in result.stderr
    assert "Traceback" not in result.stderr
