"""The Audio Unit backend's translation layer, without an Audio Unit.

Nothing here starts a plugin: CI cannot, and the parts worth testing are the ones
between a settings dict and the bytes that reach the plugin's state. Those are
where a mistake is silent — a key spelled one way arrives at a control, spelled
another way it is dropped and the plugin renders whatever it booted with, and
both produce audio and a number.

`scripts/audit_manifest.py` is what checks this backend against the running
plugin. It is a script rather than a test precisely because CI can never run it.
"""

from __future__ import annotations

import json

import pytest

from match.renderer_au import AudioUnitError, AudioUnitRenderer


def renderer(pack_id: str = "morgan", **kwargs) -> AudioUnitRenderer:
    """A renderer that will never start a server.

    `_xml_state` is what `_ensure_server` would have learned from the plugin's
    ready line, so setting it here exercises the state path without one.
    """
    made = AudioUnitRenderer(pack_id, **kwargs)
    made._xml_state = True
    return made


# --- key spellings ----------------------------------------------------------
# Three callers spell the same parameter three ways. A spelling this failed to
# recognise would not raise: the control would simply never be written.

@pytest.mark.parametrize("spelling", [
    "sw50rAmp/sw50rVolume",
    ("sw50rAmp", "sw50rVolume"),
])
def test_module_key_arrives_however_it_is_spelled(spelling):
    command = renderer()._edit_command({spelling: 82.0})
    assert command["edits"] == [
        {"module": "sw50rAmp", "key": "sw50rVolume", "value": "0.82"}
    ]


@pytest.mark.parametrize("spelling", ["selectedAmp", "/selectedAmp", ("", "selectedAmp")])
def test_selected_amp_becomes_the_servers_own_command(spelling):
    """`selectedAmp` is not an attribute of any module element.

    It has to leave as the server's `selectAmp`, and it has to happen for every
    spelling: writing a control on an amp that is not selected is a silent no-op,
    so missing this would put every render on the wrong amp without failing.
    """
    command = renderer()._edit_command({spelling: 2})
    assert command["selectAmp"] == 2
    assert command["edits"] == []


def test_a_parameter_the_pack_does_not_declare_is_refused():
    with pytest.raises(AudioUnitError, match="not a parameter"):
        renderer()._edit_command({"sw50rAmp/sw50rNonesuch": 1.0})


def test_a_key_that_is_not_a_pair_is_refused():
    with pytest.raises(AudioUnitError, match="not a module/key pair"):
        renderer()._edit_command({("a", "b", "c"): 1.0})


# --- values -----------------------------------------------------------------

def test_human_values_are_translated_the_way_the_pack_translates_them():
    """A rotation is a percent; the plugin stores the fraction."""
    command = renderer()._edit_command({
        "sw50rAmp/sw50rVolume": 50.0,          # rotation -> 0.5
        "sw50rAmp/sw50rBright": True,          # switch -> "true"
        "parameters/gateThreshold": -60.0,     # metered -> passes through
    })
    stored = {edit["key"]: edit["value"] for edit in command["edits"]}
    assert stored["sw50rVolume"] == "0.5"
    assert stored["sw50rBright"] == "true"
    assert stored["gateThreshold"] == "-60"


def test_an_illegal_value_is_refused_rather_than_clamped():
    """A backend that quietly clamped would render one thing and report another."""
    with pytest.raises(AudioUnitError):
        renderer()._edit_command({"sw50rAmp/sw50rVolume": 140.0})


def test_pack_warnings_are_collected_once_not_discarded():
    """The pack's rule is that a note with nowhere to go becomes an error.

    A search would turn one warning into several hundred, so they are kept
    uniquely rather than either raised or dropped.
    """
    made = renderer()
    spec = made._pack().parameters["delay/delaySyncNote"]
    assert spec.members, "this test needs a selector to provoke a note"
    for _ in range(3):
        made._stored(made._pack(), spec, 4)
    assert len(made.warnings) == len(set(made.warnings))


# --- what the backend says it is --------------------------------------------

def test_parameter_specs_cover_the_pack_and_exclude_read_only():
    specs = renderer().parameter_specs()
    pack = renderer()._pack()
    assert ("sw50rAmp", "sw50rVolume") in specs
    assert ("", "selectedAmp") in specs
    read_only = [(s.module, s.key) for s in pack.parameters.values() if not s.writable]
    assert read_only, "this test needs at least one read-only parameter to exclude"
    for key in read_only:
        assert key not in specs


def test_the_search_can_see_every_parameter_this_backend_declares():
    """The regression that made this backend necessary to catch.

    `match.search._supported_keys` flattens `(module, key)` to a path and compares
    it against `Dimension.path`. `("", "selectedAmp")` flattens to `/selectedAmp`
    while the dimension is `selectedAmp`, so the amp selector was dropped from
    every render's settings — silently, because writing an unselected amp's
    controls is a no-op rather than an error.
    """
    from match import search, space as space_module

    supported = search._supported_keys(renderer())
    assert "selectedAmp" in supported
    assert "/selectedAmp" not in supported

    space = space_module.build("morgan", amp="sw50r")
    live = {dimension.path for dimension in space.dimensions}
    assert live & supported == live, sorted(live - supported)


def test_metadata_does_not_claim_to_be_reproducible():
    """A reused instance is not a function of its inputs, and the committing rule
    downstream reads exactly this flag."""
    made = renderer()
    made._plugin_version = "1.1.1"
    metadata = made.metadata()
    assert metadata.reproducible is False
    assert metadata.band_noise_db > 0.0
    assert not metadata.resolves_band_difference(metadata.band_noise_db / 2)
    assert metadata.plugin_version == "1.1.1"


def test_the_plugin_version_is_in_the_cache_key():
    """Results from two plugin versions are never merged."""
    from match.renderer import cache_key

    made = renderer()
    made._plugin_version = "1.1.1"
    one = cache_key(made.metadata(), "abc", {"sw50rAmp/sw50rVolume": 50.0})
    made._plugin_version = "1.2.0"
    two = cache_key(made.metadata(), "abc", {"sw50rAmp/sw50rVolume": 50.0})
    assert one != two


def test_a_pack_with_no_audio_unit_is_refused_with_a_reason():
    made = renderer()
    made._pack_cache = _PackWithoutAudioUnit()
    with pytest.raises(AudioUnitError, match="audio_unit"):
        made._au_triple()


class _PackWithoutAudioUnit:
    pack_id = "draft"
    display_name = "Draft"
    audio_unit: dict = {}
    parameters: dict = {}


# --- the server's replies ---------------------------------------------------

def test_a_failed_render_is_reported_with_the_servers_own_reason():
    made = renderer()
    made._process = _FakeServer(['{"ok":false,"error":"no <nope> element"}'])
    with pytest.raises(AudioUnitError, match="no <nope> element"):
        made._exchange({"out": "/tmp/x.wav"})


def test_a_server_that_stopped_replying_is_not_read_as_an_empty_render():
    made = renderer()
    made._process = _FakeServer([""])
    with pytest.raises(AudioUnitError, match="stopped replying"):
        made._exchange({"out": "/tmp/x.wav"})


def test_a_non_json_reply_is_named_rather_than_swallowed():
    made = renderer()
    made._process = _FakeServer(["dyld: Library not loaded\n"])
    with pytest.raises(AudioUnitError, match="not JSON"):
        made._exchange({"out": "/tmp/x.wav"})


class _FakeServer:
    """Just enough of `subprocess.Popen` to answer one command."""

    def __init__(self, lines):
        self._lines = list(lines)
        self.returncode = 0
        self.stdin = self
        self.stdout = self
        self.written = []

    def write(self, text):
        self.written.append(text)

    def flush(self):
        pass

    def readline(self):
        return self._lines.pop(0) if self._lines else ""

    def poll(self):
        return None if self._lines else 1


# --- audio in and out -------------------------------------------------------

def test_a_render_shorter_than_its_input_is_not_padded_up():
    """Silence added to the tail would be a measurement of the padding.

    `_read_render` trims to the DI's length and never extends to it, so a short
    render stays visibly short instead of being made to look complete.
    """
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    import tempfile
    import pathlib

    made = renderer()
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "short.wav"
        sf.write(str(path), np.zeros((1000, 2), dtype=np.float32), 48000, subtype="FLOAT")
        audio = made._read_render(path, frames=4096)
    assert audio.shape == (1000, 2)


def test_a_render_at_the_wrong_sample_rate_is_refused():
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    import tempfile
    import pathlib

    made = renderer()
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "wrong.wav"
        sf.write(str(path), np.zeros((512, 2), dtype=np.float32), 44100, subtype="FLOAT")
        with pytest.raises(AudioUnitError, match="44100"):
            made._read_render(path, frames=512)


def test_one_di_is_written_once_however_many_renders_use_it():
    """A search renders hundreds of candidates through one DI."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("soundfile")

    made = renderer()
    try:
        di = np.zeros(2048, dtype=np.float32)
        first = made._di_file(di)
        assert made._di_file(di) == first
        assert made._di_file(np.ones(2048, dtype=np.float32)) != first
    finally:
        made.close()


# --- the record-state path --------------------------------------------------

def test_a_record_state_pack_rewrites_the_blob_rather_than_editing_xml(tmp_path):
    """Tone King's state is a binary `PARAM` record, not a document.

    The server has nothing to edit in place — it answers `edits` on a non-XML
    plugin with an error — so each render re-writes the plugin's own base blob
    from a pristine copy. The blob here is built by the format's own fixtures
    rather than taken from the plugin, because no plugin state is committed.
    """
    from format.parser import parse
    from format.structured import build
    from tests.test_records import preset, record

    made = AudioUnitRenderer("toneking", workdir=tmp_path)
    made._xml_state = False
    made._base_state = preset(record("ampReverb", 0.25), record("ampTremoloDepth", 0.5))

    command = made._record_command({"/ampReverb": 0.75})
    assert "state" in command and "edits" not in command

    import pathlib

    written = build(parse(pathlib.Path(command["state"]).read_bytes()))
    values = {parameter.key: parameter.value for parameter in written.parameters}
    assert values["ampReverb"] == "0.75", values
    # The parameter that was not asked for keeps the value the plugin booted with.
    assert values["ampTremoloDepth"] == "0.5", values


def test_each_record_render_starts_from_the_plugins_own_state(tmp_path):
    """Two renders in a row must not compose.

    The server's XML path re-edits a pristine document for exactly this reason;
    the record path has to match it, or a search's renders would depend on the
    order they were asked for.
    """
    from format.parser import parse
    from format.structured import build
    from tests.test_records import preset, record

    made = AudioUnitRenderer("toneking", workdir=tmp_path)
    made._xml_state = False
    made._base_state = preset(record("ampReverb", 0.25), record("ampTremoloDepth", 0.5))

    made._record_command({"/ampReverb": 0.75})
    second = made._record_command({"/ampTremoloDepth": 0.1})

    import pathlib

    written = build(parse(pathlib.Path(second["state"]).read_bytes()))
    values = {parameter.key: parameter.value for parameter in written.parameters}
    assert values["ampReverb"] == "0.25", "the first render's edit leaked into the second"
    assert values["ampTremoloDepth"] == "0.1", values
