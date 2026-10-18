"""The learn-owned bounded render server (`learn/au_render_server_bounded.swift`): it must stay the
shipped server plus a bounded decoded-DI cache, and `knob_ceiling.Renderer` must run it, while the
shipped server and its build identity stay untouched (pretrain-set plan, amendment 2)."""

import pathlib
import re
import shutil
import sys

import pytest

from learn import knob_ceiling as K

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHIPPED = ROOT / "scripts" / "au_render_server.swift"


def _without_bounded_blocks(text):
    text = re.sub(r"\A// LEARN-OWNED COPY.*?// END OF LEARN-OWNED HEADER\n", "", text, count=1, flags=re.S)
    return re.sub(r"[ \t]*// BOUNDED-CACHE BEGIN.*?// BOUNDED-CACHE END[^\n]*\n", "", text, flags=re.S)


def test_bounded_server_is_the_shipped_server_plus_the_marked_cache_blocks():
    bounded = K.BOUNDED_SERVER_SOURCE.read_text()
    assert _without_bounded_blocks(bounded) == SHIPPED.read_text().replace(
        "var excitationCache: [String: [[Float]]] = [:]\n", "", 1)
    assert bounded.count("// BOUNDED-CACHE BEGIN") == 2


def test_bounded_cache_keeps_a_handful_and_touches_every_render():
    bounded = K.BOUNDED_SERVER_SOURCE.read_text()
    kept = int(re.search(r"let EXCITATION_CACHE_KEPT = (\d+)", bounded).group(1))
    assert kept == K.DI_FILES_KEPT                            # the same bound as the DI files on disk
    # the touch follows the cache fill, so the DI being rendered is the most recent and never evicted
    assert bounded.index("excitationCache[cacheKey] = channels") < bounded.index("touchExcitation(cacheKey)")
    assert bounded.index("touchExcitation(cacheKey)") < bounded.index("let source = channels!")


def test_renderer_runs_the_bounded_binary_and_removes_its_build_directory(monkeypatch):
    made = {}

    def fake_build(directory):
        path = pathlib.Path(directory) / K.BOUNDED_SERVER_SOURCE.stem
        path.write_text("binary")
        made["dir"] = pathlib.Path(directory)
        return path

    class FakeAU:
        def __init__(self, pack_id, **kw):
            made["kw"] = kw
            self.closed = False

        def close(self):
            self.closed = True

    monkeypatch.setattr(K, "build_bounded_server", fake_build)
    monkeypatch.setattr(K, "renderer_class", lambda: FakeAU)
    rr = K.Renderer()
    assert made["kw"]["binary"] == made["dir"] / "au_render_server_bounded"
    assert made["kw"]["isolate"] is True and made["kw"]["process_policy"] == "reuse"
    assert made["dir"].exists()
    rr.close()
    assert rr.r.closed and not made["dir"].exists()


def test_a_failed_build_leaves_no_directory(monkeypatch, tmp_path):
    seen = []

    def failing(directory):
        seen.append(pathlib.Path(directory))
        raise RuntimeError("swiftc failed")

    monkeypatch.setattr(K, "build_bounded_server", failing)
    with pytest.raises(RuntimeError):
        K.Renderer()
    assert seen and not seen[0].exists()


def test_the_shipped_renderer_still_builds_the_shipped_server():
    from match import renderer_au

    assert renderer_au.SERVER_SOURCE == SHIPPED
    assert "excitationOrder" not in SHIPPED.read_text()


@pytest.mark.skipif(sys.platform != "darwin" or shutil.which("swiftc") is None,
                    reason="needs swiftc on macOS")
def test_bounded_server_compiles(tmp_path):
    binary = K.build_bounded_server(tmp_path)
    assert binary.exists() and binary.stat().st_size > 0
