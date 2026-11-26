"""Phase 2b's install and fetch (`learn/readerr_tools.py`, the amendment's unit F): the manifest reader and the fixed
interface (`load_manifest`, `venv_python`, `checkpoint_path`, `licence_record`), the lock and URL checks, the disk and
main refusals, the move-aside, the fetch, the archive unpack (never built) and both commands, on a made-up manifest,
fake downloads and a fake interpreter. Pure: standard library only, no network, nothing installed; runs on the light CI
runner. Fixtures use synthetic names only."""
import ast
import hashlib
import io
import json
import os
import pathlib
import re
import tarfile

import pytest

from learn import readerr_tools as RT

REPO = pathlib.Path(__file__).resolve().parents[1]
C1, C2, C3, C4 = "1" * 40, "2" * 40, "3" * 40, "4" * 40


def sha(b):
    return hashlib.sha256(b).hexdigest()


def make_tar(top, commit, files, extra=()):
    """A synthetic GitHub-style archive: a pax commit header, `top/` holding `files` {rel: bytes}."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT,
                      pax_headers={"comment": commit} if commit else None) as t:
        d = tarfile.TarInfo(top)
        d.type = tarfile.DIRTYPE
        t.addfile(d)
        for rel, data in files.items():
            ti = tarfile.TarInfo(f"{top}/{rel}")
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
        for ti in extra:
            t.addfile(ti)
    return buf.getvalue()


HF_FILES = {"hf_midi_transcription/__init__.py": b"x = 1\n", "hf_midi_transcription/model.py": b"y = 2\n",
            "instruments.json": b"{}\n", "pyproject.toml": b"[project]\nname = 'a'\n", "example.py": b"z = 3\n"}
PTI_FILES = {"piano_transcription_inference/__init__.py": b"", "setup.py": b"import setuptools\n",
             "pyproject.toml": b"[project]\n", "resources/a.mid": b"m"}
CKPT = {"ymt3": b"ymt3-weights", "kong-fl": b"fl-weights", "kong-gaps": b"gaps-weights"}


def _pkgs(names):
    return [{"name": n, "version": v, "sha256": sha(f"{n}{v}".encode())} for n, v in names]


def _lock(names, total=1000):
    pkgs = _pkgs(names)
    return {"packages": pkgs, "total_bytes": total,
            "require_hashes_lines": [f"{p['name']}=={p['version']} --hash=sha256:{p['sha256']}" for p in pkgs]}


def make_manifest(root):
    root = pathlib.Path(root)
    tars = {"hf_midi_transcription": make_tar(f"hf_midi_transcription-{C3}", C3, HF_FILES),
            "piano_transcription_inference": make_tar(f"piano_transcription_inference-{C4}", C4, PTI_FILES)}

    def ckpt(i, cand, repo, commit, rel, name):
        return {"id": i, "kind": "model weights", "commit": f"HF {repo} at {commit}",
                "url": f"https://huggingface.co/{repo}/resolve/{commit}/{name}", "size_bytes": len(CKPT[cand]),
                "sha256": sha(CKPT[cand]), "pinned_path": str(root / rel), "license": f"{cand} card licence"}
    items = [
        dict(ckpt("yourmt3-moe-nops", "ymt3", "spaces/org/space", C1, "mt3_checkpoints/yourmt3/run/last.ckpt",
                  "run/checkpoints/last.ckpt"), license="two claims: code A or code B",
             license_notes="no licence covers the weights"),
        {"id": "mr-mt3-mt3pth", "url": f"https://huggingface.co/org/other/resolve/{C1}/mt3.pth", "commit": C1,
         "size_bytes": 5, "sha256": "0" * 64, "pinned_path": str(root / "mt3_checkpoints/mr_mt3/mt3.pth"),
         "license": "MIT"},
        dict(ckpt("guitar-fl", "kong-fl", "org/models", C2, "riley/guitar-fl.pth", "guitar-fl.pth"),
             training_data_license="sold transcriptions; NC assumed", product_license_status="unclear, NC assumed"),
        dict(ckpt("guitar-gaps", "kong-gaps", "org/models", C2, "riley/guitar-gaps.pth", "guitar-gaps.pth"),
             training_data_license="three claims disagree", product_license_status="unclear, NC assumed"),
    ]
    for i, commit in (("hf_midi_transcription", C3), ("piano_transcription_inference", C4)):
        items.append({"id": i, "kind": "code archive", "commit": f"{commit} (head)",
                      "url": f"https://github.com/org/{i}/archive/{commit}.tar.gz", "size_bytes": len(tars[i]),
                      "sha256": sha(tars[i]), "pinned_path": str(root / f"riley/src/{i}-{commit}.tar.gz"),
                      "license": f"{i}: MIT claimed, no LICENSE file"})
    locks = {"A_mt3": _lock([("mt3-infer", "0.2.0"), ("torch", "2.7.1"), ("pretty_midi", "0.2.11.post0")]),
             "B_riley": _lock([("torch", "2.8.0"), ("setuptools", "80.9.0"), ("librosa", "0.11.0")])}
    return {"items": items, "locks": locks}, tars


def write_manifest(tmp_path, man):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(man))
    return p, RT.file_sha(p)


@pytest.fixture
def root(tmp_path, monkeypatch):
    r = (tmp_path / "tools" / "readerr").resolve()
    r.mkdir(parents=True)
    monkeypatch.setattr(RT, "ROOT", r)
    return r


# --- the module ---------------------------------------------------------------------------------------------------------------

def test_module_level_is_standard_library_only():
    tree = ast.parse((REPO / "learn" / "readerr_tools.py").read_text())
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
    import sys
    assert names <= set(sys.stdlib_module_names), names - set(sys.stdlib_module_names)


def test_disk_guard_is_trusted_datas():
    src = (REPO / "learn" / "trusted_data.py").read_text()
    assert float(re.search(r"^DISK_GUARD_GB = ([0-9.]+)", src, re.M).group(1)) == RT.DISK_GUARD_GB == 31.0


def test_writes_only_under_tools_readerr():
    assert RT.ROOT == RT.HOME / "tools" / "readerr"
    assert set(RT.CANDIDATES) == {"ymt3", "kong-fl", "kong-gaps"}
    assert not set(RT.NEVER_FETCH) & set(RT.CANDIDATES.values())


def test_real_manifest_matches_the_pin_when_present():
    if not RT.MANIFEST.exists():
        pytest.skip("U4's manifest is not on this machine")
    man = RT.load_manifest()
    for c in RT.CANDIDATES:
        assert RT.checkpoint_path(c, man, RT.ROOT).is_relative_to(RT.ROOT)
        rec = RT.licence_record(c, man)
        assert set(rec) == set(RT.LICENCE_FIELDS) and all(rec.values())
    assert RT.checkpoint_path("ymt3", man, RT.ROOT).name == "last.ckpt"
    assert RT.MANIFEST.name == "readerr-download-manifest-v2.json"
    for c, i in RT.CANDIDATES.items():                    # O9: each fetched checkpoint carries its scan
        pg = RT.manifest_item(man, i)["pickle_globals"]
        assert pg and all(set(e) == {"member", "globals"} and e["globals"] for e in pg), c
    assert "pickle_globals" not in RT.manifest_item(man, "mr-mt3-mt3pth")
    for lock in RT.LOCKS:
        assert RT.lock_lines(man, lock)
    for i in RT.LOCKS["B"]["archives"]:
        it = RT.manifest_item(man, i)
        assert RT.pinned_url_refusal(it["url"], it["commit"]) is None


# --- the fixed interface ------------------------------------------------------------------------------------------------------

def test_load_manifest_checks_its_sha256(tmp_path):
    man, _ = make_manifest(tmp_path)
    p, s = write_manifest(tmp_path, man)
    assert RT.load_manifest(p, s) == man
    with pytest.raises(SystemExit, match="is not the pinned"):
        RT.load_manifest(p, "f" * 64)
    with pytest.raises(SystemExit, match="no manifest"):
        RT.load_manifest(tmp_path / "none.json", s)


def test_venv_python(root):
    assert RT.venv_python("A") == root / "venv-a" / "bin" / "python"
    assert RT.venv_python("B", root) == root / "venv-b" / "bin" / "python"
    with pytest.raises(SystemExit, match="no lock"):
        RT.venv_python("C")


def test_checkpoint_path(root):
    man, _ = make_manifest(root)
    assert RT.checkpoint_path("ymt3", man) == root / "mt3_checkpoints/yourmt3/run/last.ckpt"
    assert RT.checkpoint_path("kong-gaps", man) == root / "riley/guitar-gaps.pth"
    for bad in ("mr-mt3", "grid-o0.5", "kong"):
        with pytest.raises(SystemExit, match="no checkpoint"):
            RT.checkpoint_path(bad, man)
    RT.manifest_item(man, "guitar-fl")["pinned_path"] = str(root.parent / "elsewhere.pth")
    with pytest.raises(SystemExit, match="is not under"):
        RT.checkpoint_path("kong-fl", man)


def test_licence_record(root):
    man, _ = make_manifest(root)
    y = RT.licence_record("ymt3", man)
    assert y == {"code": "two claims: code A or code B", "weights_data": "no licence covers the weights",
                 "product_status": "unresolved"}
    k = RT.licence_record("kong-fl", man)
    assert list(k) == list(RT.LICENCE_FIELDS)
    assert "hf_midi_transcription: hf_midi_transcription: MIT claimed" in k["code"]
    assert "piano_transcription_inference" in k["code"]
    assert k["weights_data"] == "weights: kong-fl card licence; training data: sold transcriptions; NC assumed"
    assert k["product_status"] == "unclear, NC assumed"
    assert RT.licence_record("kong-gaps+bp", man) == RT.licence_record("kong-gaps", man)
    assert RT.licence_record("ymt3-guitar", man) == y
    for bp in ("bp", "base", "lead-in", "f6", "grid-o0.5-f0.3-l58.0-m1", "shift-k2"):
        assert RT.licence_record(bp, man) == {"code": "Apache-2.0", "weights_data": RT.BP_LICENCE["weights_data"],
                                              "product_status": "usable"}
    for bad in ("kong", "ymt", "mt3", ""):
        with pytest.raises(SystemExit, match="no licence record"):
            RT.licence_record(bad, man)


# --- pure checks ----------------------------------------------------------------------------------------------------------------

def test_pinned_url_refusal():
    ok_hf = f"https://huggingface.co/spaces/org/space/resolve/{C1}/a/b/last.ckpt"
    assert RT.pinned_url_refusal(ok_hf, f"at {C1}") is None
    assert RT.pinned_url_refusal(f"https://huggingface.co/org/m/resolve/{C1}/g.pth", C1) is None
    assert RT.pinned_url_refusal(f"https://github.com/org/r/archive/{C3}.tar.gz", f"{C3} (head)") is None
    assert "commit-pinned" in RT.pinned_url_refusal("https://huggingface.co/org/m/resolve/main/g.pth", C1)
    assert "commit-pinned" in RT.pinned_url_refusal(ok_hf.replace("https", "http"), C1)
    assert "commit-pinned" in RT.pinned_url_refusal(f"https://example.org/{C1}/x", C1)
    assert "not the item's" in RT.pinned_url_refusal(ok_hf, C2)


def test_lock_lines(tmp_path):
    man, _ = make_manifest(tmp_path)
    assert len(RT.lock_lines(man, "A")) == 3
    bad = json.loads(json.dumps(man))
    bad["locks"]["A_mt3"]["require_hashes_lines"][0] = "mt3-infer>=0.2.0"
    with pytest.raises(SystemExit, match="not a hashed pin"):
        RT.lock_lines(bad, "A")
    bad = json.loads(json.dumps(man))
    bad["locks"]["A_mt3"]["packages"][0]["sha256"] = "f" * 64
    with pytest.raises(SystemExit, match="not its package"):
        RT.lock_lines(bad, "A")
    bad = json.loads(json.dumps(man))
    bad["locks"]["B_riley"] = _lock([("torch", "2.7.1")])
    with pytest.raises(SystemExit, match="not the declared 2.8.0"):
        RT.lock_lines(bad, "B")
    bad["locks"]["B_riley"] = _lock([("torch", "2.8.0"), ("Torch", "2.8.0")])
    with pytest.raises(SystemExit, match="twice"):
        RT.lock_lines(bad, "B")
    bad["locks"]["B_riley"]["packages"].pop()
    with pytest.raises(SystemExit, match="lines for"):
        RT.lock_lines(bad, "B")
    del bad["locks"]["B_riley"]
    with pytest.raises(SystemExit, match="no lock B_riley"):
        RT.lock_lines(bad, "B")


def test_installed_refusal(tmp_path):
    man, _ = make_manifest(tmp_path)
    lines = RT.lock_lines(man, "A")
    listed = [{"name": "mt3_infer", "version": "0.2.0"}, {"name": "torch", "version": "2.7.1"},
              {"name": "pretty-midi", "version": "0.2.11.post0"}, {"name": "pip", "version": "25.0.1"}]
    assert RT.installed_refusal(lines, listed) is None
    assert "differ" in RT.installed_refusal(lines, listed[1:])
    assert "differ" in RT.installed_refusal(lines, listed + [{"name": "numpy", "version": "1"}])
    assert "torch" in RT.installed_refusal(lines, [dict(p, version="2.8.0") if p["name"] == "torch" else p
                                                   for p in listed])


def test_disk_refusal():
    assert RT.disk_refusal(40e9, 9e9) is None
    assert RT.disk_refusal(40e9, 9e9 + 1) .startswith("DISK GUARD")
    assert RT.disk_refusal(30e9, 0).startswith("DISK GUARD")


def test_main_refusal():
    good = {"phase_scratch_readerr_xr_outcome": {"code": "XH-both"}, "phase_scratch_readerr_p2b": {}}
    assert RT.main_refusal(good, True) is None
    assert "differs from origin/main" in RT.main_refusal(good, False)
    assert "lacks ['phase_scratch_readerr_p2b']" in RT.main_refusal({RT.XR_OUTCOME: {"code": "XH-both"}}, True)
    for code in ("XH-undecided", "XH-anomaly", "XH-stop", None):
        assert "runs only under" in RT.main_refusal(dict(good, phase_scratch_readerr_xr_outcome={"code": code}), True)
    for code in ("XH-extras", "XH-rest"):
        assert RT.main_refusal(dict(good, phase_scratch_readerr_xr_outcome={"code": code}), True) is None


def test_set_aside_never_deletes(root):
    f = root / "a.pth"
    f.write_bytes(b"bad")
    q = RT.move_aside(f)
    assert not f.exists() and q.read_bytes() == b"bad" and q.name.startswith("a.pth.set-aside-")
    f.write_bytes(b"bad2")
    when = q.name.split("set-aside-")[1]
    assert RT.set_aside_path(f, when).name == f"a.pth.set-aside-{when}-2"
    outside = root.parent / "x"
    outside.write_bytes(b"x")
    with pytest.raises(SystemExit, match="is not under"):
        RT.move_aside(outside)
    assert outside.exists()


def test_write_once_never_over_a_file(root):
    p = RT.write_once_text(root / "a" / "b.txt", "one")
    with pytest.raises(FileExistsError):
        RT.write_once_text(p, "two")
    assert p.read_text() == "one"
    with pytest.raises(SystemExit, match="is not under"):
        RT.write_once_text(root.parent / "c.txt", "x")
    with pytest.raises(SystemExit, match="is not under"):
        RT.write_once_text(root, "x")


# --- the fetch --------------------------------------------------------------------------------------------------------------------

class FakeHTTP:
    def __init__(self, served):
        self.served, self.asked = served, []

    def __call__(self, url, *a, **k):
        self.asked.append(url if isinstance(url, str) else url.full_url)
        return io.BytesIO(self.served[self.asked[-1]])


def test_fetch_checks_size_and_sha256(root):
    url = f"https://huggingface.co/org/m/resolve/{C2}/g.pth"
    data = b"weights"
    rec = RT.fetch(url, root / "riley" / "g.pth", len(data), sha(data), opener=FakeHTTP({url: data}))
    assert rec["sha256"] == sha(data) and (root / "riley" / "g.pth").read_bytes() == data
    assert [p.name for p in (root / "riley").iterdir()] == ["g.pth"]          # the partial is gone
    with pytest.raises(SystemExit, match="exists"):
        RT.fetch(url, root / "riley" / "g.pth", len(data), sha(data), opener=FakeHTTP({url: data}))
    with pytest.raises(SystemExit, match="the manifest's"):
        RT.fetch(url, root / "riley" / "h.pth", len(data), sha(b"other"), opener=FakeHTTP({url: data}))
    assert not (root / "riley" / "h.pth").exists()
    kept = [p for p in (root / "riley").iterdir() if ".set-aside-" in p.name]
    assert len(kept) == 1 and kept[0].read_bytes() == data                   # moved aside, never deleted
    with pytest.raises(SystemExit, match="is not under"):
        RT.fetch(url, root.parent / "g.pth", len(data), sha(data), opener=FakeHTTP({url: data}))


def test_verify_or_aside(root):
    p = root / "c.pth"
    p.write_bytes(b"good")
    assert RT.verify_or_aside(p, 4, sha(b"good")) and p.exists()
    assert not RT.verify_or_aside(p, 4, sha(b"else")) and not p.exists()
    assert [q.read_bytes() for q in root.iterdir()] == [b"good"]


def test_fetch_plan_never_takes_mt3pth(root):
    man, _ = make_manifest(root)
    plan = RT.fetch_plan(man, list(RT.CANDIDATES))
    assert [c for c, _, _ in plan] == ["ymt3", "kong-fl", "kong-gaps"]
    assert all(i["id"] != "mr-mt3-mt3pth" for _, i, _ in plan)
    with pytest.raises(SystemExit, match="no checkpoint"):
        RT.fetch_plan(man, ["mr-mt3-mt3pth"])
    RT.manifest_item(man, "guitar-fl")["url"] = "https://huggingface.co/org/models/resolve/main/guitar-fl.pth"
    with pytest.raises(SystemExit, match="commit-pinned"):
        RT.fetch_plan(man, ["kong-fl"])


def _commands(monkeypatch, root, man, served):
    monkeypatch.setattr(RT, "require_main", lambda: None)
    monkeypatch.setattr(RT, "load_manifest", lambda *a, **k: man)
    monkeypatch.setattr(RT, "free_bytes", lambda: 45e9)
    http = FakeHTTP(served)
    monkeypatch.setattr(RT.urllib.request, "urlopen", http)
    return http


def test_tx_fetch(monkeypatch, root, capsys):
    man, _ = make_manifest(root)
    served = {i["url"]: CKPT[c] for c, i in ((c, RT.manifest_item(man, RT.CANDIDATES[c])) for c in RT.CANDIDATES)}
    http = _commands(monkeypatch, root, man, served)
    gaps = RT.checkpoint_path("kong-gaps", man)
    gaps.parent.mkdir(parents=True)
    gaps.write_bytes(CKPT["kong-gaps"])                  # already in place and right: kept
    fl = RT.checkpoint_path("kong-fl", man)
    fl.write_bytes(b"truncated")                        # already in place and wrong: moved aside, fetched again
    RT.cmd_tx_fetch(type("A", (), {"cand": None})())
    out = capsys.readouterr().out
    assert "FREE DISK before" in out and "FREE DISK after" in out and "PRESENT kong-gaps" in out
    for c in RT.CANDIDATES:
        assert RT.checkpoint_path(c, man).read_bytes() == CKPT[c]
    assert RT.checkpoint_path("ymt3", man).name == "last.ckpt"
    assert len(http.asked) == 2 and all("mt3.pth" not in u for u in http.asked)
    assert [p.read_bytes() for p in fl.parent.iterdir() if ".set-aside-" in p.name] == [b"truncated"]
    rec = json.loads(next(root.glob("fetch-*.json")).read_text())
    assert sorted(g["cand"] for g in rec["fetched"]) == ["kong-fl", "ymt3"] and rec["present"] == ["kong-gaps"]


def test_tx_fetch_disk_guard(monkeypatch, root):
    man, _ = make_manifest(root)
    _commands(monkeypatch, root, man, {})
    monkeypatch.setattr(RT, "free_bytes", lambda: 31e9)
    with pytest.raises(SystemExit, match="DISK GUARD"):
        RT.cmd_tx_fetch(type("A", (), {"cand": "ymt3"})())
    assert not RT.checkpoint_path("ymt3", man).exists()


# --- the archives -----------------------------------------------------------------------------------------------------------------

def test_unpack_archive_takes_only_the_package(root, tmp_path):
    top = f"hf_midi_transcription-{C3}"
    arc = tmp_path / "a.tar.gz"
    arc.write_bytes(make_tar(top, C3, HF_FILES))
    dest = root / "riley" / "src" / top
    got = RT.unpack_archive(arc, top, C3, RT.UNPACK["hf_midi_transcription"], dest)
    files = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
    assert files == ["hf_midi_transcription/__init__.py", "hf_midi_transcription/model.py", "instruments.json"]
    assert got["build_files"]["pyproject.toml"] == {"sha256": sha(HF_FILES["pyproject.toml"]),
                                                    "text": HF_FILES["pyproject.toml"].decode()}
    assert [p.name for p in dest.parent.iterdir()] == [top]                 # no partial folder left
    with pytest.raises(SystemExit, match="exists"):
        RT.unpack_archive(arc, top, C3, RT.UNPACK["hf_midi_transcription"], dest)
    with pytest.raises(SystemExit, match="commit header"):
        RT.unpack_archive(arc, top, C4, RT.UNPACK["hf_midi_transcription"], root / "other")


def test_archive_refusal():
    top, keep = "r-c", ("pkg/",)
    ok = [{"name": "r-c", "type": "dir"}, {"name": "r-c/pkg", "type": "dir"}, {"name": "r-c/pkg/a.py", "type": "file"}]
    assert RT.archive_refusal(ok, {"comment": "c"}, top, "c", keep) is None
    assert "commit header" in RT.archive_refusal(ok, {}, top, "c", keep)
    assert "outside" in RT.archive_refusal(ok + [{"name": "r-c/../x", "type": "file"}], {"comment": "c"}, top, "c",
                                           keep)
    assert "outside" in RT.archive_refusal(ok + [{"name": "/etc/x", "type": "file"}], {"comment": "c"}, top, "c",
                                           keep)
    assert "outside" in RT.archive_refusal(ok + [{"name": "other/x", "type": "file"}], {"comment": "c"}, top, "c",
                                           keep)
    assert "is a other" in RT.archive_refusal(ok + [{"name": "r-c/l", "type": "other"}], {"comment": "c"}, top, "c",
                                              keep)
    assert "has no pkg/" in RT.archive_refusal(ok[:1], {"comment": "c"}, top, "c", keep)


def test_unpack_refuses_a_symlink(root, tmp_path):
    top = f"piano_transcription_inference-{C4}"
    link = tarfile.TarInfo(f"{top}/piano_transcription_inference/evil")
    link.type, link.linkname = tarfile.SYMTYPE, "/etc/passwd"
    arc = tmp_path / "b.tar.gz"
    arc.write_bytes(make_tar(top, C4, PTI_FILES, extra=[link]))
    with pytest.raises(SystemExit, match="is a other"):
        RT.unpack_archive(arc, top, C4, RT.UNPACK["piano_transcription_inference"], root / "x")
    assert not (root / "x").exists()


def test_kept_member():
    keep = RT.UNPACK["hf_midi_transcription"]
    assert RT.kept_member("t/hf_midi_transcription", "t", keep)
    assert RT.kept_member("t/hf_midi_transcription/model.py", "t", keep)
    assert RT.kept_member("t/instruments.json", "t", keep)
    for no in ("t", "t/example.py", "t/pyproject.toml", "t/hf_midi_transcription_x/a.py", "u/instruments.json"):
        assert not RT.kept_member(no, "t", keep)


# --- tx-install on a fake interpreter ---------------------------------------------------------------------------------------------

class FakeRun:
    """Stands in for the pyenv interpreter and the venv's pip: makes the venv's folders, lists the lock."""

    def __init__(self, root, man, wrong_list=False, version="3.12.16"):
        self.root, self.man, self.wrong, self.calls, self.version = root, man, wrong_list, [], version

    def __call__(self, *a):
        a = [str(x) for x in a]
        self.calls.append(a)
        if a[-1] == "import sys; print(sys.version.split()[0])":
            assert a[0] == str(self.root / "python-3.12" / "python" / "bin" / "python3")   # tx-python's, never pyenv's
            return f"{self.version}\n"         # what tx-python's interpreter reports
        if a[-2:-1] == ["venv"]:
            pathlib.Path(a[-1], "bin").mkdir(parents=True)
            return ""
        if "--version" in a:
            return "pip 25.0.1 from x\n"
        if "install" in a:
            assert {"--require-hashes", "--only-binary", ":all:", "--no-deps", "--no-cache-dir"} <= set(a)
            return ""
        if "list" in a:
            lock = "A" if "venv-a" in a[0] else "B"
            pkgs = self.man["locks"][RT.LOCKS[lock]["key"]]["packages"]
            out = [{"name": p["name"], "version": p["version"]} for p in pkgs] + [{"name": "pip", "version": "25"}]
            return json.dumps(out[1:] if self.wrong else out)
        if "sysconfig" in a[-1]:
            site = pathlib.Path(a[0]).parents[1] / "lib" / "python3.12" / "site-packages"
            site.mkdir(parents=True)
            return f"{site}\n"
        raise AssertionError(a)


def _fake_interpreter(root):
    p = root / "python-3.12" / "python" / "bin" / "python3"
    p.parent.mkdir(parents=True)
    p.write_text("")
    (root / "python-3.12.json").write_text(json.dumps({"sha256": RT.PBS_SHA256, "version": RT.PYTHON_VERSION}))


def test_tx_install_lock_b(monkeypatch, root, capsys):
    man, tars = make_manifest(root)
    _fake_interpreter(root)
    served = {RT.manifest_item(man, i)["url"]: tars[i] for i in tars}
    _commands(monkeypatch, root, man, served)
    fake = FakeRun(root, man)
    monkeypatch.setattr(RT, "_run", fake)
    RT.cmd_tx_install(type("A", (), {"lock": "B"})())
    out = capsys.readouterr().out
    assert "FREE DISK before" in out and "FREE DISK after" in out and "INSTALLED lock B" in out
    rec = json.loads((root / "install-B.json").read_text())
    assert rec["packages"] == 3 and rec["python"] == RT.PYTHON_VERSION == "3.12.16"
    assert rec["interpreter"] == str(root / "python-3.12" / "python" / "bin" / "python3")
    pth = pathlib.Path(rec["code"]["pth"]["path"])
    assert pth.name == RT.PTH_NAME and pth.is_relative_to(root / "venv-b")
    roots = pth.read_text().split()
    assert roots == [str(root / f"riley/src/hf_midi_transcription-{C3}"),
                     str(root / f"riley/src/piano_transcription_inference-{C4}")]
    assert (pathlib.Path(roots[1]) / "piano_transcription_inference" / "__init__.py").exists()
    assert not (pathlib.Path(roots[1]) / "setup.py").exists()                 # never built, never unpacked
    pti = rec["code"]["piano_transcription_inference"]
    assert pti["built"] is False and set(pti["build_files"]) == {"setup.py", "pyproject.toml"}
    assert (root / "lock-B.txt").read_text().splitlines() == RT.lock_lines(man, "B")
    with pytest.raises(SystemExit, match="exists"):
        RT.cmd_tx_install(type("A", (), {"lock": "B"})())


def test_tx_install_failure_moves_aside(monkeypatch, root):
    man, _ = make_manifest(root)
    _fake_interpreter(root)
    _commands(monkeypatch, root, man, {})
    monkeypatch.setattr(RT, "_run", FakeRun(root, man, wrong_list=True))
    with pytest.raises(SystemExit, match="differ from the lock"):
        RT.cmd_tx_install(type("A", (), {"lock": "A"})())
    names = sorted(p.name for p in root.iterdir())
    assert not (root / "venv-a").exists() and not (root / "lock-A.txt").exists()
    assert any(n.startswith("venv-a.set-aside-") for n in names)
    assert any(n.startswith("lock-A.txt.set-aside-") for n in names)
    assert not (root / "install-A.json").exists()


def test_tx_install_needs_tx_pythons_interpreter_at_the_pinned_version(monkeypatch, root):
    man, _ = make_manifest(root)
    _commands(monkeypatch, root, man, {})
    fake = FakeRun(root, man)
    monkeypatch.setattr(RT, "_run", fake)
    with pytest.raises(SystemExit, match="run tx-python first"):
        RT.cmd_tx_install(type("A", (), {"lock": "A"})())
    assert not (root / "venv-a").exists() and not fake.calls
    _fake_interpreter(root)
    monkeypatch.setattr(RT, "_run", FakeRun(root, man, version="3.12.13"))
    with pytest.raises(SystemExit, match="not the pinned 3.12.16"):
        RT.cmd_tx_install(type("A", (), {"lock": "A"})())
    assert not (root / "venv-a").exists() and not (root / "lock-A.txt").exists()


def test_tx_install_needs_the_pinned_asset_in_the_record(monkeypatch, root):
    man, _ = make_manifest(root)
    _commands(monkeypatch, root, man, {})
    fake = FakeRun(root, man)
    monkeypatch.setattr(RT, "_run", fake)
    _fake_interpreter(root)
    for rec in ({}, {"sha256": "0" * 64, "version": RT.PYTHON_VERSION}, {"sha256": RT.PBS_SHA256, "version": "3.12.13"}):
        (root / "python-3.12.json").write_text(json.dumps(rec))
        with pytest.raises(SystemExit, match="does not record the pinned asset"):
            RT.cmd_tx_install(type("A", (), {"lock": "A"})())
        assert not fake.calls and not (root / "venv-a").exists()


# --- tx-python on a made-up asset ---------------------------------------------------------------------------------------------

def make_python_tar(extra=(), top="python"):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for rel, data in {"bin/python3.12": b"#!fake\n", "lib/python3.12/os.py": b"x = 1\n"}.items():
            ti = tarfile.TarInfo(f"{top}/{rel}")
            ti.size, ti.mode = len(data), 0o755
            t.addfile(ti, io.BytesIO(data))
        ln = tarfile.TarInfo(f"{top}/bin/python3")
        ln.type, ln.linkname = tarfile.SYMTYPE, "python3.12"
        t.addfile(ln)
        for ti in extra:
            t.addfile(ti)
    return buf.getvalue()


def _python_asset(monkeypatch, root, data, version="3.12.16"):
    monkeypatch.setattr(RT, "require_main", lambda: None)
    monkeypatch.setattr(RT, "free_bytes", lambda: 45e9)
    url = "https://example.invalid/asset.tar.gz"
    monkeypatch.setattr(RT, "PBS_URL", url)
    monkeypatch.setattr(RT, "PBS_SIZE", len(data))
    monkeypatch.setattr(RT, "PBS_SHA256", sha(data))
    http = FakeHTTP({url: data})
    monkeypatch.setattr(RT.urllib.request, "urlopen", http)
    calls = []

    def run(*a):
        calls.append([str(x) for x in a])
        assert a[-1] == RT.PY_CHECK and str(a[0]).endswith("python-3.12/python/bin/python3")
        return version + "\n"
    monkeypatch.setattr(RT, "_run", run)
    return http, calls


def test_tx_python(monkeypatch, root, capsys):
    data = make_python_tar()
    http, calls = _python_asset(monkeypatch, root, data)
    RT.cmd_tx_python(None)
    out = capsys.readouterr().out
    assert "FREE DISK before" in out and "FREE DISK after" in out and "INTERPRETER 3.12.16" in out
    py = root / "python-3.12" / "python" / "bin"
    assert (py / "python3").is_symlink() and (py / "python3").read_bytes() == b"#!fake\n"
    assert (root / "downloads" / RT.PBS_ASSET).read_bytes() == data and len(http.asked) == 1 and len(calls) == 1
    rec = json.loads((root / "python-3.12.json").read_text())
    assert rec["version"] == "3.12.16" and rec["sha256"] == sha(data) and rec["members"] == 3
    assert RT.interpreter() == py / "python3"
    assert [p.name for p in root.iterdir() if "partial" in p.name] == []
    with pytest.raises(SystemExit, match="exists"):
        RT.cmd_tx_python(None)


def test_tx_python_pins():
    assert RT.PYTHON_VERSION == "3.12.16" and RT.PBS_ASSET.startswith("cpython-3.12.16+20261124-aarch64-apple-darwin")
    assert RT.PBS_URL.endswith(RT.PBS_ASSET.replace("+", "%2B")) and f"/download/{RT.PBS_TAG}/" in RT.PBS_URL
    assert RT.PBS_URL.startswith("https://github.com/astral-sh/python-build-standalone/releases/download/")
    assert re.fullmatch(r"[0-9a-f]{64}", RT.PBS_SHA256) and RT.PBS_SIZE == 25399370
    assert {"lzma", "ssl", "sqlite3", "ctypes"} <= set(re.findall(r"\w+", RT.PY_CHECK))


def test_tx_python_refuses_a_bad_tree(monkeypatch, root):
    up = tarfile.TarInfo("python/../evil.py")
    up.size = 0
    esc = tarfile.TarInfo("python/bin/out")
    esc.type, esc.linkname = tarfile.SYMTYPE, "../../../etc/passwd"
    ab = tarfile.TarInfo("python/bin/abs")
    ab.type, ab.linkname = tarfile.SYMTYPE, "/usr/bin/python3"
    dev = tarfile.TarInfo("python/dev0")
    dev.type = tarfile.CHRTYPE
    hard = tarfile.TarInfo("python/bin/h")
    hard.type, hard.linkname = tarfile.LNKTYPE, "other/x"
    for bad, msg in ((up, "outside python/"), (esc, "leaves"), (ab, "absolute"), (dev, "is a other"),
                     (hard, "leaves python/")):
        r = root / bad.name.replace("/", "_")
        monkeypatch.setattr(RT, "ROOT", r)
        r.mkdir()
        _python_asset(monkeypatch, r, make_python_tar(extra=[bad]))
        with pytest.raises(SystemExit, match=msg):
            RT.cmd_tx_python(None)
        assert not (r / "python-3.12").exists() and not (r / "python-3.12.json").exists()


def test_tx_python_wrong_version_or_disk(monkeypatch, root):
    data = make_python_tar()
    _python_asset(monkeypatch, root, data, version="3.12.13")
    with pytest.raises(SystemExit, match="not 3.12.16"):
        RT.cmd_tx_python(None)
    assert not (root / "python-3.12").exists()
    assert any(p.name.startswith("python-3.12.set-aside-") for p in root.iterdir())        # moved aside, not deleted
    r2 = root / "two"
    r2.mkdir()
    monkeypatch.setattr(RT, "ROOT", r2)
    _python_asset(monkeypatch, r2, data)
    monkeypatch.setattr(RT, "free_bytes", lambda: 31e9 + 10)
    with pytest.raises(SystemExit, match="DISK GUARD"):
        RT.cmd_tx_python(None)
    assert not (r2 / "python-3.12").exists()


def _escape_tree(base):
    """python/a/d1 -> .. (python itself), then python/a/x -> d1/../../evil: inside by its letters, outside by its real
    path (d1/.. is python's parent, one more .. leaves the folder)."""
    a = base / "python" / "a"
    a.mkdir(parents=True)
    (a / "ok.py").write_text("")
    os.symlink("..", a / "d1")
    os.symlink("d1/../../evil", a / "x")
    os.symlink("ok.py", a / "fine")


def test_links_outside_reads_real_paths(tmp_path):
    f = tmp_path / "unpacked"
    _escape_tree(f)
    assert RT.links_outside(f) == ["python/a/x"]
    assert RT.tree_refusal([{"name": "python/a/d1", "type": "symlink", "link": ".."},
                            {"name": "python/a/x", "type": "symlink", "link": "d1/../../evil"}], "python") is None


def test_tx_python_refuses_a_link_whose_real_path_leaves(monkeypatch, root):
    extra = []
    for name, link in (("python/a/d1", ".."), ("python/a/x", "d1/../../evil")):
        ti = tarfile.TarInfo(name)
        ti.type, ti.linkname = tarfile.SYMTYPE, link
        extra.append(ti)
    _python_asset(monkeypatch, root, make_python_tar(extra=extra))
    try:          # newer data filters rewrite the target lexically ("../evil", inside); older ones keep it
        RT.cmd_tx_python(None)
    except SystemExit as e:                               # ... and then the real-path walk refuses it
        assert "real path leaves" in str(e) or "refused" in str(e)
        assert not (root / "python-3.12").exists() and not (root / "python-3.12.json").exists()
        assert any(".set-aside-" in p.name for p in root.iterdir())                        # kept, never deleted
    else:
        assert RT.links_outside(root / "python-3.12") == []                                # never an escape in place


def test_tx_python_walk_runs_before_the_version_check(monkeypatch, root):
    _python_asset(monkeypatch, root, make_python_tar())
    real = RT.tarfile.TarFile.extractall

    def extract_then_plant(self, path, *a, **k):          # a link the archive check could not see
        real(self, path, *a, **k)
        _escape_tree(pathlib.Path(path) / "extra")
        (pathlib.Path(path) / "extra" / "python" / "a").rename(pathlib.Path(path) / "python" / "a")
    monkeypatch.setattr(RT.tarfile.TarFile, "extractall", extract_then_plant)
    monkeypatch.setattr(RT, "_run", lambda *a: pytest.fail("the version check ran before the walk"))
    with pytest.raises(SystemExit, match="real path leaves"):
        RT.cmd_tx_python(None)
    assert not (root / "python-3.12").exists()
    assert any(p.name.startswith("python-3.12.set-aside-") for p in root.iterdir())


def _old_install(root, man):
    for lock in ("A", "B"):
        v = root / f"venv-{lock.lower()}"
        (v / "bin").mkdir(parents=True)
        (v / "bin" / "python").write_text("old")
        (root / f"install-{lock}.json").write_text("{}")
        (root / f"lock-{lock}.txt").write_text("x")
    site = root / "venv-b" / "lib" / "python3.12" / "site-packages"
    site.mkdir(parents=True)
    (site / RT.PTH_NAME).write_text("/x\n")
    for i in ("hf_midi_transcription", "piano_transcription_inference"):
        a = RT.manifest_item(man, i)
        d = pathlib.Path(a["pinned_path"]).parent / f"{i}-{a['commit'].split()[0]}"
        d.mkdir(parents=True)
        (d / "k.py").write_text("k")


def test_tx_move_old(monkeypatch, root, capsys):
    man, _ = make_manifest(root)
    monkeypatch.setattr(RT, "require_main", lambda: None)
    monkeypatch.setattr(RT, "load_manifest", lambda *a, **k: man)
    with pytest.raises(SystemExit, match="nothing of the old install"):
        RT.cmd_tx_move_old(None)
    _old_install(root, man)
    (root / "python-3.12").mkdir()                       # the new interpreter is never touched
    keep = pathlib.Path(RT.manifest_item(man, "hf_midi_transcription")["pinned_path"])
    keep.write_bytes(b"archive")                         # nor the checked archives
    RT.cmd_tx_move_old(None)
    rec = json.loads(next(root.glob("move-old-*.json")).read_text())
    froms = [pathlib.Path(m["from"]).name for m in rec["moved"]]
    assert froms[0] == RT.PTH_NAME and len(froms) == 9 and rec["deleted"] == []
    assert pathlib.Path(rec["moved"][0]["to"]).parent == root                 # the .pth leaves the venv first
    for m in rec["moved"]:
        assert not pathlib.Path(m["from"]).exists() and pathlib.Path(m["to"]).exists() and ".set-aside-" in m["to"]
    assert (root / "python-3.12").exists() and keep.read_bytes() == b"archive"
    moved_b = next(pathlib.Path(m["to"]) for m in rec["moved"] if pathlib.Path(m["from"]).name == "venv-b")
    assert (moved_b / "bin" / "python").read_text() == "old"                                # nothing deleted
    with pytest.raises(SystemExit, match="nothing of the old install"):
        RT.cmd_tx_move_old(None)


def test_tree_refusal():
    ok = [{"name": "python/bin/python3", "type": "symlink", "link": "python3.12"},
          {"name": "python/lib/x.pc", "type": "symlink", "link": "../share/y"},
          {"name": "python/bin/python3.12", "type": "file", "link": ""}]
    assert RT.tree_refusal(ok, "python") is None
    assert "leaves python/" in RT.tree_refusal([{"name": "python/a", "type": "symlink", "link": "../b"}], "python")
    assert "leaves the tree" in RT.tree_refusal([{"name": "python/a", "type": "symlink", "link": "../../b"}],
                                                "python")


def test_tx_install_refuses_before_anything(monkeypatch, root):
    man, _ = make_manifest(root)
    _commands(monkeypatch, root, man, {})

    def never(*a):
        raise AssertionError("nothing may run")
    monkeypatch.setattr(RT, "_run", never)
    (root / "venv-a").mkdir()
    with pytest.raises(SystemExit, match="venv-a exists"):
        RT.cmd_tx_install(type("A", (), {"lock": None})())
    (root / "venv-a").rmdir()
    monkeypatch.setattr(RT, "free_bytes", lambda: 31.5e9)
    with pytest.raises(SystemExit, match="DISK GUARD"):
        RT.cmd_tx_install(type("A", (), {"lock": "A"})())
    assert sorted(p.name for p in root.iterdir()) == []
