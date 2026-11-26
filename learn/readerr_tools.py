"""The note-reading diagnosis's Phase 2b install and fetch (`docs/scratch-readerr-plan.md` section 10; ledger
`preset-ladder` `phase_scratch_readerr_p2b`; the amendment's unit F).

    $MAIN -m learn.readerr_tools tx-move-old                   # once: the old pyenv-built install moved aside
    $MAIN -m learn.readerr_tools tx-python                     # first: the pinned standalone CPython 3.12.16
    $MAIN -m learn.readerr_tools tx-install [--lock A|B]       # the two venvs, from the manifest's locks
    $MAIN -m learn.readerr_tools tx-fetch [--cand ymt3|kong-fl|kong-gaps]   # the three pinned checkpoints

**The manifest** is U4's hand-back as v2 (`MANIFEST`: v1 plus each checkpoint's scanned `pickle_globals`, O9),
read only when its sha256 is `MANIFEST_SHA256`. Every URL, size, sha256, lock line and pinned path comes from it;
nothing is resolved here.

**`tx-python`.** No local Python 3.12 has `_lzma` (librosa imports pooch, which imports lzma), so the venvs get their
own interpreter: python-build-standalone's CPython (`PBS_*`, one release asset pinned by tag, size and the release's
SHA256SUMS sha256), fetched through a partial file, checked, and unpacked with tarfile's data filter under
`python-3.12/` (no `..`, no absolute name, no link leaving the tree, no device). It must then `import lzma, ssl,
sqlite3, ctypes` and report the pinned version; before that, every unpacked symlink's real path must stay inside
the folder. The record is `python-3.12.json`, holding the asset's sha256, which `tx-install` requires.

**`tx-install`.** Each lock gets its own venv (`VENVS`), made by that interpreter (`INTERPRETER`, its version
checked to equal `PYTHON_VERSION`), then `pip install --require-hashes --only-binary :all: --no-deps --no-cache-dir` from the lock's
`require_hashes_lines` (each line checked; torch at the lock's declared version). Lock B also takes the two code
archives (review amendment 7): each is fetched from its commit-pinned URL and checked against the manifest's size and
sha256 and the archive's own commit header; its build files (`setup.py`, `pyproject.toml`, `setup.cfg`) are read and
recorded; then it is **unpacked, never built**: only its import package (and `hf_midi_transcription`'s
`instruments.json`, which the package looks for beside itself) goes to `riley/src/<repo>-<commit>/`, and one `.pth`
file in the venv's site-packages points there. No build code runs, so setuptools (in lock B, hashed) is never called.
The installed set must equal the lock (`pip list`); no upstream package is imported here, since the gate's network
and process refusals must come first (review amendment 7). The record is `install-<lock>.json`.

**`tx-fetch`.** YourMT3+ (kept named `last.ckpt`), `guitar-fl.pth` and `guitar-gaps.pth`, from the manifest's
pinned `resolve/<commit>` URLs to its pinned paths. `mt3.pth` is never fetched (O5). Size and sha256 must equal the
manifest's; a mismatching file, new or already there, is moved aside (`<name>.set-aside-<time>`), never loaded,
never deleted. A file already in place with the right size and sha256 is kept. The record is `fetch-<time>.json`.

**Both** refuse unless main holds `phase_scratch_readerr_xr_outcome` (with a code that runs Phase 2b) and
`phase_scratch_readerr_p2b`, and this file equals origin/main's. Both refuse an existing venv or target, and free disk
that would end under the 31 GB guard; both print free disk before and after. Writes go only under `ROOT`
(`~/ndsp-presets/tools/readerr/`), and never over an existing file.

**For `scratch_readerr` (fixed interface):** `load_manifest()`, `venv_python(lock)`, `checkpoint_path(cand_id)` and
`licence_record(cand_id)`.

The module level is the standard library only; so are the tests.
"""

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

HOME = pathlib.Path(os.path.expanduser("~/ndsp-presets"))
ROOT = HOME / "tools" / "readerr"
MANIFEST = HOME / "handover" / "2026-11-26" / "readerr-download-manifest-v2.json"   # O9: v1 + the audited scan
MANIFEST_SHA256 = "94a84fc9f4e5eb47f7ef6783fa2663d2e1cc120514d0e0f4ef9053e9782c65b1"
PBS_TAG = "20261124"                     # astral-sh/python-build-standalone's release (tag commit 48d61fcd), MPL-2.0
PBS_ASSET = "cpython-3.12.16+20261124-aarch64-apple-darwin-install_only.tar.gz"
PBS_URL = ("https://github.com/astral-sh/python-build-standalone/releases/download/20261124/"
           "cpython-3.12.16%2B20261124-aarch64-apple-darwin-install_only.tar.gz")
PBS_SIZE = 25399370
PBS_SHA256 = "431b99a9c2cdd37ad9b06e425be0e520d2dbce0552abe454257abef592fe3634"   # the release's SHA256SUMS line
PBS_SUMS_SHA256 = "7e902de89fdcf79ad073be6d44445fd6ec9fa5592f008612852dae85874fee6a"   # that SHA256SUMS file, as read
PBS_TOP = "python"                       # the archive's one top folder
PYTHON_VERSION = "3.12.16"               # the newest 3.12 in that release; every locked wheel admits it
PY_DIR_NAME = "python-3.12"
PY_DIR = ROOT / PY_DIR_NAME             # (as configured; the code reads ROOT when it runs)
INTERPRETER = PY_DIR / PBS_TOP / "bin" / "python3"
PY_CHECK = "import lzma, ssl, sqlite3, ctypes, sys; print(sys.version.split()[0])"
REPO = pathlib.Path(__file__).resolve().parents[1]
OWN_FILE = "learn/readerr_tools.py"
LEDGER = "docs/dev-test-ledger.json"
LEDGER_ID = "preset-ladder"
PHASE = "phase_scratch_readerr_p2b"
XR_OUTCOME = "phase_scratch_readerr_xr_outcome"
XR_CODES_RUN = ("XH-both", "XH-extras", "XH-rest")      # section 9h: the codes under which Phase 2b's downloads run
NEEDS = (XR_OUTCOME, PHASE)

DISK_GUARD_GB = 31.0                     # trusted_data.DISK_GUARD_GB (a test holds them equal)
VENV_PROXY_BYTES = 857916 * 1024         # MuScriptor's measured torch venv: the installed size allowed for one venv

LOCKS = {   # the manifest's lock, the venv's folder, torch's declared version, the code archives it takes
    "A": {"key": "A_mt3", "venv": "venv-a", "torch": "2.7.1", "archives": ()},
    "B": {"key": "B_riley", "venv": "venv-b", "torch": "2.8.0",
          "archives": ("hf_midi_transcription", "piano_transcription_inference")},
}
UNPACK = {   # what of each archive is unpacked (paths below the archive's top folder); nothing else
    "hf_midi_transcription": ("hf_midi_transcription/", "instruments.json"),
    "piano_transcription_inference": ("piano_transcription_inference/",),
}
BUILD_FILES = ("setup.py", "pyproject.toml", "setup.cfg")
PTH_NAME = "readerr-src.pth"

CANDIDATES = {"ymt3": "yourmt3-moe-nops", "kong-fl": "guitar-fl", "kong-gaps": "guitar-gaps"}   # id -> manifest item
CANDIDATE_LOCK = {"ymt3": "A", "kong-fl": "B", "kong-gaps": "B"}
NEVER_FETCH = ("mr-mt3-mt3pth",)         # O5: the file mt3-infer's mr_mt3 loads is the original MT3 checkpoint
CODE_ITEMS = {"ymt3": ("yourmt3-moe-nops",),
              "kong-fl": ("hf_midi_transcription", "piano_transcription_inference"),
              "kong-gaps": ("hf_midi_transcription", "piano_transcription_inference")}
BP_LICENCE = {"code": "Apache-2.0", "weights_data": "in the wheel",
              "product_status": "usable"}                                       # section 5
SECTION5_STATUS = {"ymt3": "unresolved"}   # section 5, where the manifest records no product status
BP_IDS = ("bp", "base", "lead-in", "f6")
BP_PREFIXES = ("grid-", "shift-k")       # scratch_readerr's Basic Pitch candidate ids (grid_id, SHIFT_ID)
LICENCE_FIELDS = ("code", "weights_data", "product_status")

HF_URL = re.compile(r"^https://huggingface\.co/(?:spaces/)?[\w.-]+/[\w.-]+/resolve/([0-9a-f]{40})/[\w./=@+-]+$")
GH_URL = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+/archive/([0-9a-f]{40})\.tar\.gz$")
LOCK_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9.!+_-]+) --hash=sha256:([0-9a-f]{64})$")
CHUNK = 1 << 20
USER_AGENT = "readerr-tools/1 (python-urllib)"


def refuse(msg):
    raise SystemExit(f"readerr_tools: {msg}")


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def stamp():
    return time.strftime("%Y%m%d-%H%M%S")


# --- the manifest and the fixed interface --------------------------------------------------------------------------------

def load_manifest(path=None, sha256=None):
    """U4's manifest, refused unless its sha256 is `MANIFEST_SHA256` (or `sha256`, for a test's made-up one)."""
    p = pathlib.Path(path) if path else MANIFEST
    want = sha256 or MANIFEST_SHA256
    if not p.is_file():
        refuse(f"no manifest at {p}")
    got = file_sha(p)
    if got != want:
        refuse(f"the manifest's sha256 {got[:12]} is not the pinned {want[:12]}")
    return json.loads(p.read_text())


def manifest_item(man, item_id):
    hits = [i for i in man.get("items", []) if i.get("id") == item_id]
    if len(hits) != 1:
        refuse(f"the manifest holds {len(hits)} items with id {item_id!r}")
    return hits[0]


def under_root(path, root=None):
    """(Pure.) `path` as an absolute path, refused unless it sits strictly below `root` (`ROOT`)."""
    r = pathlib.Path(root or ROOT).resolve()
    p = pathlib.Path(path).resolve()
    if p == r or r not in p.parents:
        refuse(f"{p} is not under {r}")
    return p


def venv_python(lock, root=None):
    """The venv's interpreter for lock "A" (mt3-infer: `ymt3`) or "B" (the Riley models: `kong-fl`, `kong-gaps`)."""
    if lock not in LOCKS:
        refuse(f"no lock {lock!r} (A or B)")
    return pathlib.Path(root or ROOT) / LOCKS[lock]["venv"] / "bin" / "python"


def checkpoint_path(cand_id, man=None, root=None):
    """The candidate's pinned checkpoint path, from the manifest (under `ROOT`). Only `ymt3`, `kong-fl`,
    `kong-gaps`."""
    if cand_id not in CANDIDATES:
        refuse(f"no checkpoint for {cand_id!r} ({', '.join(CANDIDATES)})")
    item = manifest_item(man if man is not None else load_manifest(), CANDIDATES[cand_id])
    if not item.get("pinned_path"):
        refuse(f"the manifest pins no path for {cand_id}")
    return under_root(item["pinned_path"], root)


def transcriber_of(cand_id):
    """(Pure.) The transcriber a candidate id belongs to (`ymt3`, `kong-fl`, `kong-gaps`; also their variants
    `<id>+bp` and `<id>-<setting>`), "bp" for scratch_readerr's Basic Pitch candidates, else None."""
    if cand_id in BP_IDS or cand_id.startswith(BP_PREFIXES):
        return "bp"
    for t in sorted(CANDIDATES, key=len, reverse=True):
        if cand_id == t or cand_id.startswith((t + "+", t + "-")):
            return t
    return None


def licence_record(cand_id, man=None):
    """`{"code", "weights_data", "product_status"}`, copied from the manifest's items (section 5's value where the
    manifest records none). Basic Pitch's settings get Apache-2.0. A variant (`+bp`, a setting) takes its
    transcriber's record."""
    t = transcriber_of(cand_id)
    if t is None:
        refuse(f"no licence record for {cand_id!r}")
    if t == "bp":
        return dict(BP_LICENCE)
    man = man if man is not None else load_manifest()
    w = manifest_item(man, CANDIDATES[t])
    if t == "ymt3":
        code = w["license"]
        weights = w["license_notes"]
    else:
        code = "; ".join(f"{i}: {manifest_item(man, i)['license']}" for i in CODE_ITEMS[t])
        weights = f"weights: {w['license']}; training data: {w['training_data_license']}"
    status = w.get("product_license_status") or SECTION5_STATUS[t]
    return {"code": code, "weights_data": weights, "product_status": status}


# --- pure checks ------------------------------------------------------------------------------------------------------------

def pinned_url_refusal(url, commit):
    """(Pure.) Why `url` is not a commit-pinned Hugging Face `resolve/` or GitHub `archive/` URL for `commit`."""
    m = HF_URL.match(url or "") or GH_URL.match(url or "")
    if not m:
        return f"not a commit-pinned https URL: {url!r}"
    if m.group(1) not in (commit or ""):
        return f"the URL's commit {m.group(1)[:12]} is not the item's"
    return None


def lock_lines(man, lock):
    """(Pure.) The lock's checked `require_hashes_lines`: each `name==version --hash=sha256:<64 hex>`, one a package
    in the same order as `packages`, torch at the declared version, no repeats."""
    entry = man.get("locks", {}).get(LOCKS[lock]["key"])
    if not entry:
        refuse(f"the manifest has no lock {LOCKS[lock]['key']}")
    lines, pkgs = entry.get("require_hashes_lines") or [], entry.get("packages") or []
    if not lines or len(lines) != len(pkgs):
        refuse(f"lock {lock}: {len(lines)} lines for {len(pkgs)} packages")
    names = []
    for line, p in zip(lines, pkgs):
        m = LOCK_LINE.match(line)
        if not m:
            refuse(f"lock {lock}: not a hashed pin: {line!r}")
        if (m.group(1), m.group(2), m.group(3)) != (p["name"], p["version"], p["sha256"]):
            refuse(f"lock {lock}: {line!r} is not its package's entry")
        names.append(canon(m.group(1)))
    if len(set(names)) != len(names):
        refuse(f"lock {lock}: a package is pinned twice")
    torch = [p["version"] for p in pkgs if canon(p["name"]) == "torch"]
    if torch != [LOCKS[lock]["torch"]]:
        refuse(f"lock {lock}: torch {torch} is not the declared {LOCKS[lock]['torch']}")
    return lines


def canon(name):
    """(Pure.) A package name as pip compares them."""
    return re.sub(r"[-_.]+", "-", name).lower()


def installed_refusal(lines, listed):
    """(Pure.) Why `pip list`'s [{name, version}] is not exactly the lock (plus the venv's own pip), or None."""
    want = {canon(LOCK_LINE.match(x).group(1)): LOCK_LINE.match(x).group(2) for x in lines}
    got = {canon(p["name"]): p["version"] for p in listed}
    got.pop("pip", None)
    if got != want:
        diff = sorted(k for k in set(want) | set(got) if want.get(k) != got.get(k))
        return f"the venv's packages differ from the lock: {diff[:8]}"
    return None


def disk_refusal(free_bytes, need_bytes, guard_gb=DISK_GUARD_GB):
    """(Pure.) Why free disk would end under the guard after `need_bytes` more, or None."""
    after = (free_bytes - need_bytes) / 1e9
    if after < guard_gb:
        return f"DISK GUARD: {free_bytes / 1e9:.1f} GB free less {need_bytes / 1e9:.2f} GB is under {guard_gb:.0f} GB"
    return None


def main_refusal(entry, own_identical):
    """(Pure.) Why Phase 2b may not install or fetch: main's `preset-ladder` entry must hold the xr- outcome with a
    code that runs Phase 2b, and this declaration; this file must equal origin/main's."""
    if not own_identical:
        return f"{OWN_FILE} differs from origin/main's (or is not on main): run from merged code"
    missing = [k for k in NEEDS if k not in (entry or {})]
    if missing:
        return f"main's ledger lacks {missing}"
    code = (entry[XR_OUTCOME] or {}).get("code")
    if code not in XR_CODES_RUN:
        return f"main's xr- outcome is {code!r}: Phase 2b runs only under {', '.join(XR_CODES_RUN)}"
    return None


def set_aside_path(path, when):
    """(Pure.) Where a mismatching file is moved: `<name>.set-aside-<when>`, numbered if that is taken."""
    p = pathlib.Path(path)
    q = p.with_name(f"{p.name}.set-aside-{when}")
    n = 1
    while q.exists() or q.is_symlink():
        n += 1
        q = p.with_name(f"{p.name}.set-aside-{when}-{n}")
    return q


def move_aside(path, root=None):
    """Move `path` (a file or folder under `ROOT`) aside, never deleting it. -> the new path."""
    p = under_root(path, root)
    q = set_aside_path(p, stamp())
    os.rename(p, q)
    print(f"MOVED ASIDE: {p} -> {q}")
    return q


def archive_refusal(members, pax, top, commit, keep):
    """(Pure.) Why a code archive may not be unpacked: its commit header must be `commit`; every member must sit in
    `top/`, be a plain file or folder, and have no `..`; each `keep` prefix must be present."""
    if (pax or {}).get("comment") != commit:
        return f"the archive's commit header {(pax or {}).get('comment')!r} is not {commit[:12]}"
    for m in members:
        name = m["name"]
        parts = pathlib.PurePosixPath(name).parts
        if name.startswith("/") or ".." in parts or not parts or parts[0] != top:
            return f"member {name!r} is outside {top}/"
        if m["type"] not in ("file", "dir"):
            return f"member {name!r} is a {m['type']}"
    for k in keep:
        if not any(m["name"] == f"{top}/{k.rstrip('/')}" or m["name"].startswith(f"{top}/{k}") for m in members):
            return f"the archive has no {k}"
    return None


def kept_member(name, top, keep):
    """(Pure.) Whether an archive member is unpacked: it is one of `keep` (below `top/`) or inside one."""
    rel = name[len(top) + 1:] if name.startswith(top + "/") else None
    if not rel:
        return False
    return any(rel == k.rstrip("/") or (k.endswith("/") and rel.startswith(k)) for k in keep)


# --- the writes (only under ROOT, never over a file) -------------------------------------------------------------------------

def write_once_text(path, text, root=None):
    p = under_root(path, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "x") as f:
        f.write(text)
    return p


def write_once_json(path, obj, root=None):
    return write_once_text(path, json.dumps(obj, indent=1) + "\n", root)


def fetch(url, dest, size, sha256, root=None, opener=None):
    """Stream `url` to `dest` (under `ROOT`, not existing) through a fresh partial file; the result must have `size`
    bytes and `sha256`, else it is moved aside and the fetch refuses. -> {"url", "path", "size", "sha256"}."""
    dest = under_root(dest, root)
    if dest.exists() or dest.is_symlink():
        refuse(f"{dest} exists")
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = under_root(dest.with_name(f"{dest.name}.partial-{stamp()}"), root)
    opener = opener or (lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": USER_AGENT}),
                                                         timeout=60))
    h, n = hashlib.sha256(), 0
    with opener(url) as r, open(part, "xb") as f:
        for b in iter(lambda: r.read(CHUNK), b""):
            f.write(b)
            h.update(b)
            n += len(b)
    got = h.hexdigest()
    if (n, got) != (size, sha256):
        q = move_aside(part, root)
        refuse(f"{url}: {n} bytes, sha256 {got[:12]}; the manifest's {size}, {sha256[:12]} (kept at {q})")
    os.link(part, dest)          # fails if dest appeared meanwhile: never over a file
    os.unlink(part)              # dest holds the same bytes
    return {"url": url, "path": str(dest), "size": n, "sha256": got}


def verify_or_aside(path, size, sha256, root=None):
    """A file already in place: True if it has `size` and `sha256`; otherwise it is moved aside (False)."""
    p = under_root(path, root)
    if p.is_file() and not p.is_symlink() and p.stat().st_size == size and file_sha(p) == sha256:
        return True
    move_aside(p, root)
    return False


def unpack_archive(archive, top, commit, keep, dest, root=None):
    """Unpack only `keep` from a checked archive into `dest` (not existing), through a fresh partial folder, with
    tarfile's data filter. Nothing is built. -> {"build_files": {name: {sha256, text}}, "unpacked": [paths]}."""
    dest = under_root(dest, root)
    if dest.exists() or dest.is_symlink():
        refuse(f"{dest} exists")
    with tarfile.open(archive, "r:gz") as t:
        ms = t.getmembers()
        desc = [{"name": m.name, "type": "file" if m.isfile() else "dir" if m.isdir() else "other"} for m in ms]
        why = archive_refusal(desc, t.pax_headers, top, commit, keep)
        if why:
            refuse(f"{archive}: {why}")
        build = {}
        for m in ms:
            rel = m.name[len(top) + 1:]
            if m.isfile() and rel in BUILD_FILES:
                data = t.extractfile(m).read()
                build[rel] = {"sha256": hashlib.sha256(data).hexdigest(), "text": data.decode("utf-8", "replace")}
        part = under_root(dest.with_name(f"{dest.name}.partial-{stamp()}"), root)
        part.mkdir(parents=True)
        chosen = [m for m in ms if kept_member(m.name, top, keep)]
        t.extractall(part, members=chosen, filter="data")
    os.rename(part / top, dest)
    part.rmdir()                 # empty: its one folder was moved out
    return {"build_files": build, "unpacked": sorted(m.name[len(top) + 1:] for m in chosen)}


# --- main's ledger -----------------------------------------------------------------------------------------------------------

def _git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)


def main_entry():
    """main's `preset-ladder` ledger entry (origin/main, as fetched)."""
    r = _git("show", f"origin/main:{LEDGER}")
    if r.returncode:
        refuse(f"cannot read origin/main's ledger: {r.stderr.strip()[:200]}")
    tests = [t for t in json.loads(r.stdout)["tests"] if t.get("test_id") == LEDGER_ID]
    if len(tests) != 1:
        refuse(f"origin/main's ledger holds {len(tests)} {LEDGER_ID} entries")
    return tests[0]


def own_identical():
    return (_git("cat-file", "-e", f"origin/main:{OWN_FILE}").returncode == 0
            and _git("diff", "--quiet", "origin/main", "--", OWN_FILE).returncode == 0)


def require_main():
    why = main_refusal(main_entry(), own_identical())
    if why:
        refuse(why)


def free_bytes():
    return shutil.disk_usage(str(HOME if HOME.exists() else pathlib.Path.home())).free


def print_free(when):
    print(f"FREE DISK {when}: {free_bytes() / 1e9:.1f} GB (guard {DISK_GUARD_GB:.0f} GB)")


# --- the commands ------------------------------------------------------------------------------------------------------------

def _run(*a):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True)
    if r.returncode:
        refuse(f"{' '.join(map(str, a))[:160]}: {r.stderr.strip()[-800:]}")
    return r.stdout


def install_lock(man, lock):
    """One venv: refused if it or its files exist; pip from the checked lock lines; lock B's archives unpacked, not
    built; the installed set checked; `install-<lock>.json` written once. On any failure what this run made (the
    venv, the lock file, an unpacked folder) is moved aside, never deleted; checked archives stay."""
    cfg = LOCKS[lock]
    venv = under_root(ROOT / cfg["venv"])
    record = under_root(ROOT / f"install-{lock}.json")
    lock_file = under_root(ROOT / f"lock-{lock}.txt")
    for p in (venv, record, lock_file):
        if p.exists() or p.is_symlink():
            refuse(f"{p} exists")
    lines = lock_lines(man, lock)
    archives = [manifest_item(man, i) for i in cfg["archives"]]
    for a in archives:
        why = pinned_url_refusal(a["url"], a["commit"])
        if why:
            refuse(f"{a['id']}: {why}")
        under_root(a["pinned_path"])
    need = man["locks"][cfg["key"]]["total_bytes"] + VENV_PROXY_BYTES + sum(a["size_bytes"] for a in archives)
    why = disk_refusal(free_bytes(), need)
    if why:
        refuse(why)
    interp = interpreter()
    version = _run(interp, "-I", "-c", "import sys; print(sys.version.split()[0])").strip()
    if version != PYTHON_VERSION:
        refuse(f"{interp} is Python {version}, not the pinned {PYTHON_VERSION}")
    made = []
    try:
        made.append(write_once_text(lock_file, "\n".join(lines) + "\n"))
        made.append(venv)
        _run(interp, "-I", "-m", "venv", venv)
        py = venv_python(lock)
        pip = (py, "-I", "-m", "pip")
        pip_version = _run(*pip, "--version").split()[1]
        _run(*pip, "install", "--isolated", "--disable-pip-version-check", "--require-hashes", "--only-binary",
             ":all:", "--no-deps", "--no-cache-dir", "-r", lock_file)
        listed = json.loads(_run(*pip, "list", "--isolated", "--disable-pip-version-check", "--format", "json"))
        why = installed_refusal(lines, listed)
        if why:
            refuse(why)
        code = {}
        if archives:
            code = unpack_code(py, archives, made)
    except BaseException:
        for p in reversed(made):
            if p.exists() or p.is_symlink():
                move_aside(p)
        raise
    rec = {"plan": "docs/scratch-readerr-plan.md section 10", "ledger": f"{LEDGER_ID} {PHASE}",
           "made": time.strftime("%Y-%m-%d %H:%M:%S"), "lock": lock, "manifest_sha256": MANIFEST_SHA256,
           "lock_file_sha256": file_sha(lock_file), "packages": len(lines), "interpreter": str(interp),
           "python": version, "pip": pip_version, "venv": str(venv), "listed": listed, "code": code,
           "installed_bytes": sum(f.stat().st_size for f in venv.rglob("*") if f.is_file() and not f.is_symlink()),
           "free_gb_after": free_bytes() / 1e9}
    write_once_json(record, rec)
    print(f"INSTALLED lock {lock}: {len(lines)} packages, {rec['installed_bytes'] / 1e6:.0f} MB, "
          f"record sha256 {file_sha(record)}")


def unpack_code(py, archives, made):
    """Lock B's code archives: each checked (an archive already in place is kept only with the manifest's size and
    sha256, else moved aside and fetched again), its build files recorded, its import package unpacked (never
    built), then one `.pth` file in the venv's site-packages listing the unpacked folders. -> the record."""
    site = under_root(_run(py, "-I", "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])").strip())
    code, roots = {}, []
    for a in archives:
        commit = a["commit"].split()[0]
        arc = under_root(a["pinned_path"])
        if not ((arc.exists() or arc.is_symlink()) and verify_or_aside(arc, a["size_bytes"], a["sha256"])):
            fetch(a["url"], arc, a["size_bytes"], a["sha256"])
        top = f"{a['id']}-{commit}"
        dest = under_root(arc.parent / top)
        if dest.exists() or dest.is_symlink():
            refuse(f"{dest} exists")
        made.append(dest)
        got = unpack_archive(arc, top, commit, UNPACK[a["id"]], dest)
        code[a["id"]] = dict(got, commit=commit, archive_sha256=a["sha256"], unpacked_to=str(dest), built=False)
        roots.append(str(dest))
    pth = write_once_text(site / PTH_NAME, "".join(r + "\n" for r in roots))
    code["pth"] = {"path": str(pth), "lines": roots}
    return code


def interpreter(root=None):
    """The venvs' interpreter (tx-python's), refused unless tx-python has run."""
    d = pathlib.Path(root or ROOT) / PY_DIR_NAME
    p = d / PBS_TOP / "bin" / "python3"
    rec = d.parent / f"{PY_DIR_NAME}.json"
    if not rec.is_file() or not p.exists():
        refuse(f"no interpreter at {p} (run tx-python first)")
    got = json.loads(rec.read_text())
    if got.get("sha256") != PBS_SHA256 or got.get("version") != PYTHON_VERSION:
        refuse(f"{rec.name} does not record the pinned asset's sha256 {PBS_SHA256[:12]} and version {PYTHON_VERSION}")
    under_root(p, root)                  # its link resolves inside ROOT
    return p.absolute()                  # the path itself, not the link's target (a venv keeps it as given)


def tree_refusal(members, top):
    """(Pure.) Why an interpreter archive may not be unpacked: every member sits in `top/`, with no `..` and no
    absolute name; it is a file, a folder or a link; a link's target is relative and stays inside `top/`."""
    for m in members:
        name, kind, link = m["name"], m["type"], m.get("link")
        parts = pathlib.PurePosixPath(name).parts
        if name.startswith("/") or ".." in parts or not parts or parts[0] != top:
            return f"member {name!r} is outside {top}/"
        if kind not in ("file", "dir", "symlink", "hardlink"):
            return f"member {name!r} is a {kind}"
        if kind in ("symlink", "hardlink"):
            base = pathlib.PurePosixPath(name).parent if kind == "symlink" else pathlib.PurePosixPath()
            if not link or link.startswith("/"):
                return f"link {name!r} -> {link!r} is absolute or empty"
            resolved = []
            for part in (base / link).parts:
                if part == "..":
                    if not resolved:
                        return f"link {name!r} -> {link!r} leaves the tree"
                    resolved.pop()
                elif part != ".":
                    resolved.append(part)
            if not resolved or resolved[0] != top:
                return f"link {name!r} -> {link!r} leaves {top}/"
    return None


def links_outside(folder):
    """Every symlink under `folder` (files and folders alike, never followed) whose `os.path.realpath` lies outside
    the folder's own real path. -> [relative paths], sorted."""
    top = os.path.realpath(folder)
    bad = []
    for d, dirs, files in os.walk(folder, followlinks=False):
        for n in dirs + files:
            p = os.path.join(d, n)
            if os.path.islink(p):
                r = os.path.realpath(p)
                if os.path.commonpath([top, r]) != top:
                    bad.append(os.path.relpath(p, folder))
    return sorted(bad)


def old_targets(man, root=None):
    """(Pure but for `exists`.) What `tx-move-old` moves, in order: venv-b's `.pth` file first (so it is inactive
    wherever venv-b goes), the two venvs, their install records and lock files, and the two unpacked code folders.
    -> [paths that exist]."""
    r = pathlib.Path(root or ROOT)
    cands = sorted((r / LOCKS["B"]["venv"] / "lib").glob(f"python*/site-packages/{PTH_NAME}"))
    for lock in LOCKS:
        cands += [r / LOCKS[lock]["venv"], r / f"install-{lock}.json", r / f"lock-{lock}.txt"]
    for i in LOCKS["B"]["archives"]:
        a = manifest_item(man, i)
        cands.append(pathlib.Path(a["pinned_path"]).parent / f"{a['id']}-{a['commit'].split()[0]}")
    return [under_root(c, root) for c in cands if c.exists() or c.is_symlink()]


def cmd_tx_move_old(_args):
    """Move aside, never delete, the old pyenv-built install (`old_targets`), each with `move_aside`'s timestamp;
    refused when nothing matches. -> move-old-<time>.json, what moved where."""
    require_main()
    man = load_manifest()
    todo = old_targets(man)
    if not todo:
        refuse("nothing of the old install is there to move aside")
    moved = []
    for p in todo:
        if p.name == PTH_NAME:           # out of the venv first, so it is inactive and its record stays true
            q = set_aside_path(under_root(ROOT / f"{LOCKS['B']['venv']}.{PTH_NAME}"), stamp())
            os.rename(p, q)
            print(f"MOVED ASIDE: {p} -> {q}")
        else:
            q = move_aside(p)
        moved.append({"from": str(p), "to": str(q)})
    rec = {"plan": "docs/scratch-readerr-plan.md section 10j", "ledger": f"{LEDGER_ID} {PHASE}",
           "made": time.strftime("%Y-%m-%d %H:%M:%S"), "moved": moved, "deleted": []}
    out = write_once_json(ROOT / f"move-old-{stamp()}.json", rec)
    print(f"MOVED ASIDE {len(moved)} items; record {out} sha256 {file_sha(out)}")


def _kind(m):
    return ("file" if m.isfile() else "dir" if m.isdir() else "symlink" if m.issym() else
            "hardlink" if m.islnk() else "other")


def cmd_tx_python(_args):
    """The pinned standalone CPython: refused if its folder or record exists; fetched (or an archive in place kept
    only with the pinned size and sha256); checked; unpacked through a partial folder with the data filter; then
    `PY_CHECK` must report PYTHON_VERSION. A failure after the unpack moves the folder aside. -> python-3.12.json."""
    require_main()
    dest, record = under_root(ROOT / PY_DIR_NAME), under_root(ROOT / f"{PY_DIR_NAME}.json")
    for p in (dest, record):
        if p.exists() or p.is_symlink():
            refuse(f"{p} exists")
    print_free("before")
    arc = under_root(ROOT / "downloads" / PBS_ASSET)
    if not ((arc.exists() or arc.is_symlink()) and verify_or_aside(arc, PBS_SIZE, PBS_SHA256)):
        why = disk_refusal(free_bytes(), PBS_SIZE)
        if why:
            refuse(why)
        fetch(PBS_URL, arc, PBS_SIZE, PBS_SHA256)
    with tarfile.open(arc, "r:gz") as t:
        ms = t.getmembers()
        why = tree_refusal([{"name": m.name, "type": _kind(m), "link": m.linkname} for m in ms], PBS_TOP)
        if why:
            refuse(f"{PBS_ASSET}: {why}")
        unpacked = sum(m.size for m in ms)
        why = disk_refusal(free_bytes(), unpacked)
        if why:
            refuse(why)
        part = under_root(dest.with_name(f"{dest.name}.partial-{stamp()}"))
        part.mkdir(parents=True)
        try:
            t.extractall(part, filter="data")
        except (tarfile.TarError, OSError) as e:       # the data filter's refusals included
            q = move_aside(part)
            refuse(f"{PBS_ASSET}: the unpack refused ({type(e).__name__}: {e}); kept at {q}")
    os.rename(part, dest)
    try:
        bad = links_outside(dest)
        if bad:
            refuse(f"links whose real path leaves {dest.name}/: {bad[:4]}")
        version = _run(dest / PBS_TOP / "bin" / "python3", "-I", "-c", PY_CHECK).strip()
        if version != PYTHON_VERSION:
            refuse(f"the unpacked interpreter is {version}, not {PYTHON_VERSION}")
    except BaseException:
        move_aside(dest)
        raise
    rec = {"plan": "docs/scratch-readerr-plan.md section 10j", "ledger": f"{LEDGER_ID} {PHASE}",
           "made": time.strftime("%Y-%m-%d %H:%M:%S"), "release": PBS_TAG, "asset": PBS_ASSET, "url": PBS_URL,
           "size": PBS_SIZE, "sha256": PBS_SHA256, "sha256sums_sha256": PBS_SUMS_SHA256, "members": len(ms),
           "unpacked_bytes": unpacked, "version": version, "check": PY_CHECK, "path": str(dest / PBS_TOP),
           "free_gb_after": free_bytes() / 1e9}
    write_once_json(record, rec)
    print(f"INTERPRETER {version} at {dest / PBS_TOP}: lzma, ssl, sqlite3, ctypes import; record sha256 "
          f"{file_sha(record)}")
    print_free("after")


def cmd_tx_install(args):
    require_main()
    man = load_manifest()
    locks = [args.lock] if args.lock else list(LOCKS)
    for lock in locks:      # every target refused up front, before anything is made
        for p in (ROOT / LOCKS[lock]["venv"], ROOT / f"install-{lock}.json", ROOT / f"lock-{lock}.txt"):
            if p.exists() or p.is_symlink():
                refuse(f"{p} exists")
    print_free("before")
    for lock in locks:
        install_lock(man, lock)
    print_free("after")


def fetch_plan(man, cands, root=None):
    """(Pure but for `exists`.) [(cand, item, path)] for the candidates' checkpoints; refused for any never-fetched
    item or an unpinned URL."""
    out = []
    for c in cands:
        if c not in CANDIDATES:
            refuse(f"no checkpoint for {c!r}")
        item = manifest_item(man, CANDIDATES[c])
        if item["id"] in NEVER_FETCH:
            refuse(f"{item['id']} is never fetched")
        why = pinned_url_refusal(item["url"], item["commit"])
        if why:
            refuse(f"{c}: {why}")
        out.append((c, item, checkpoint_path(c, man, root)))
    return out


def cmd_tx_fetch(args):
    require_main()
    man = load_manifest()
    plan = fetch_plan(man, [args.cand] if args.cand else list(CANDIDATES))
    print_free("before")
    todo = []
    for c, item, path in plan:
        if path.exists() or path.is_symlink():
            if verify_or_aside(path, item["size_bytes"], item["sha256"]):
                print(f"PRESENT {c}: {path} (size and sha256 the manifest's)")
                continue
        todo.append((c, item, path))
    why = disk_refusal(free_bytes(), sum(i["size_bytes"] for _, i, _ in todo))
    if why:
        refuse(why)
    got = []
    for c, item, path in todo:
        print(f"FETCH {c}: {item['size_bytes']:,} B from {item['url']}")
        got.append(dict(fetch(item["url"], path, item["size_bytes"], item["sha256"]), cand=c))
    rec = {"plan": "docs/scratch-readerr-plan.md section 10", "ledger": f"{LEDGER_ID} {PHASE}",
           "made": time.strftime("%Y-%m-%d %H:%M:%S"), "manifest_sha256": MANIFEST_SHA256, "fetched": got,
           "present": [c for c, _, _ in plan if c not in {g["cand"] for g in got}], "free_gb_after": free_bytes() / 1e9}
    write_once_json(ROOT / f"fetch-{stamp()}.json", rec)
    print_free("after")


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(prog="readerr_tools", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("tx-move-old", help="move the old pyenv-built venvs, records and unpacked code aside")
    m.set_defaults(func=cmd_tx_move_old)
    t = sub.add_parser("tx-python", help="the pinned standalone CPython 3.12 the venvs are made from")
    t.set_defaults(func=cmd_tx_python)
    a = sub.add_parser("tx-install", help="the two venvs from the manifest's locks, on tx-python's interpreter")
    a.add_argument("--lock", choices=sorted(LOCKS))
    a.set_defaults(func=cmd_tx_install)
    f = sub.add_parser("tx-fetch", help="the three pinned checkpoints (never mt3.pth)")
    f.add_argument("--cand", choices=sorted(CANDIDATES))
    f.set_defaults(func=cmd_tx_fetch)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
