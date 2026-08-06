"""The real backend: an installed Audio Unit, driven through the batched Swift server.

This is the one renderer whose numbers are facts about the plugin. Everything
M1-M4 measured came from `SyntheticRenderer`, which shares Morgan's topology and
models none of its DSP; the gap between the two is what M5 exists to write down.

Three things shape the implementation, and all three are measurements rather than
preferences:

**One process, many renders.** `scripts/au_render.swift` renders once and exits,
and `instantiate` alone is 1250 ms of its 2030 ms. `scripts/au_render_server.swift`
instantiates once and then reads commands, which takes a render to about 291 ms
steady state. A 300-render search is 90 seconds rather than 10 minutes, and that
difference is what makes searching against the plugin possible at all.

**No settle.** The 200 ms pause after writing state was a guess. The same state at
0/5/10/25/50/100/200/400 ms produces byte-identical output, for a switch and for a
mic change that reloads an impulse response, so this passes `--settle 0` and hands
the search back a fifth of its wall clock. (Measured on Morgan's XML state path.
`settle_ms` is still a constructor argument, because that measurement has not been
repeated on a record-state plugin.)

**A reused instance does not repeat itself.** Two renders of identical parameters
from one instance sit about -17 dB apart relative to the signal, through `reset`,
reallocation and warm-up alike. So `metadata()` reports `reproducible=False` and a
`band_noise_db` floor, and `match.search` raises its sensitivity screen to match.
Nothing measured here may be committed as a fact without saying that beside it.

Two state paths, because the two packs store state differently. Morgan's is a
JUCE XML document and the server edits attributes in it. Tone King's is a binary
`PARAM` record, which the server cannot edit, so this reads the plugin's own base
blob once through `au_probe dumpraw` and re-writes it through `format.structured`
for each render. `state_path` in the pack manifest is not consulted: the plugin is
asked what its state is, rather than told.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .renderer import REUSED_INSTANCE_BAND_NOISE_DB, RenderError, RenderMetadata, Renderer

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVER_SOURCE = PLUGIN_ROOT / "scripts" / "au_render_server.swift"
PROBE_SOURCE = PLUGIN_ROOT / "scripts" / "au_probe.swift"

# The server renders in fixed blocks, so its output runs to the next whole block
# past the input. Trimming back to the DI's own length is what makes this backend
# and the synthetic one return the same shape for the same input; the discarded
# remainder is the plugin's response to the zero padding after the signal ends,
# never the signal itself.
BLOCK_FRAMES = 512


class AudioUnitError(RenderError):
    """The backend could not be set up or driven at all.

    A subclass of `RenderError` so a caller that already handles "no audio came
    back" handles a dead server too, and a distinct type so a caller that wants to
    tell a failed render from a failed *host* can.
    """


class AudioUnitRenderer(Renderer):
    """Render a DI through an installed Audio Unit, one server process per instance.

    The server is started lazily and kept: starting it costs about 1.1 s, and a
    search that paid that per render would spend 80% of its budget on startup.
    Close it with `close()` or use the instance as a context manager. An instance
    that is simply dropped closes its server in `__del__`, which is a backstop
    rather than the intended path — a leaked process holds a plugin instance.
    """

    renderer_id = "swift"

    def __init__(self, pack_id: str = "morgan", *, settle_ms: float = 0.0,
                 isolate: Optional[bool] = None, amplitude: float = 1.0,
                 warmup_s: float = 0.0, sample_rate: int = 48000,
                 block_size: int = BLOCK_FRAMES, quality_mode: str = "standard",
                 band_noise_db: float = REUSED_INSTANCE_BAND_NOISE_DB,
                 binary: Optional[pathlib.Path] = None,
                 workdir: Optional[pathlib.Path] = None):
        self.pack_id = pack_id
        self.settle_ms = float(settle_ms)
        # None means "find out". Some plugins render silence on their first
        # allocation of render resources and render normally after a deallocate/
        # reallocate cycle. Tone King is one: it returned exact zeros from the
        # Swift helpers for months, which was recorded as a property of bare
        # instantiation, and it renders at 0.153 peak once the resources have been
        # cycled. Measured both ways round — `realloc` after the state write and
        # `isolate` before it both work, so it is the reallocation that matters
        # and not the state write. Morgan never needs it. Rather than encode a
        # rule from two plugins, this tries without and reacts to the symptom.
        self.isolate = bool(isolate) if isolate is not None else False
        self._isolate_decided = isolate is not None
        self.amplitude = float(amplitude)
        self.warmup_s = float(warmup_s)
        self.sample_rate = int(sample_rate)
        self.block_size = int(block_size)
        self.quality_mode = quality_mode
        self.band_noise_db = float(band_noise_db)

        self._binary = pathlib.Path(binary) if binary else None
        self._owns_workdir = workdir is None
        self._workdir = pathlib.Path(workdir) if workdir else pathlib.Path(
            tempfile.mkdtemp(prefix="au-render-"))
        self._process: Optional[subprocess.Popen] = None
        self._log = None
        self._plugin_version: Optional[str] = None
        self._xml_state: Optional[bool] = None
        self._base_state: Optional[bytes] = None
        self._di_files: Dict[str, pathlib.Path] = {}
        self._pack_cache = None
        self._render_index = 0
        self._isolate_note: Optional[str] = None
        # Warnings the pack raised while translating a value — a guessed kind, a
        # selector whose members are unknown. Collected rather than discarded: the
        # pack's own rule is that a note with nowhere to go becomes an error, and a
        # search would otherwise turn one warning into several hundred.
        self.warnings: List[str] = []

    # --- the protocol -------------------------------------------------------

    def metadata(self) -> RenderMetadata:
        """What produced a render, and whether it can be trusted to repeat.

        Starts the server if it is not running, because the plugin version is one
        of the answers and the component is the only authority on it. Callers ask
        for metadata before rendering anything — `match_preset.py` records it on
        the run — so paying 1.1 s here rather than reporting "unknown" is the
        trade this makes.
        """
        self._ensure_server()
        notes = [
            f"{self.pack_id} through {self._au_triple_text()}, one reused plugin "
            f"instance in a batched server",
        ]
        if self.settle_ms == 0.0:
            notes.append(
                "no settle after the state write: 0/5/10/25/50/100/200/400 ms "
                "measured byte-identical on Morgan's XML state path"
            )
        if self._isolate_note:
            notes.append(self._isolate_note)
        elif self.isolate:
            notes.append(
                "isolate: render resources are deallocated around the state write, "
                "which is the ordering scripts/au_render.swift uses"
            )
        return RenderMetadata(
            renderer_id=self.renderer_id,
            sample_rate=self.sample_rate,
            block_size=self.block_size,
            plugin_version=self._plugin_version or "unknown",
            renderer_build=self._renderer_build(),
            quality_mode=self.quality_mode,
            # A reused instance is not a function of its inputs. Only a fresh
            # process is bit-exact, and this one deliberately is not fresh.
            reproducible=False,
            band_noise_db=self.band_noise_db,
            notes=tuple(notes),
        )

    def _render(self, di, settings: Optional[Mapping]):
        import numpy as np

        self._ensure_server()
        frames = int(np.asarray(di).shape[0])
        audio = self._one_render(di, settings, frames)
        if self._isolate_decided:
            return audio

        # The first render decides how this plugin has to be driven. Silence here
        # is the symptom Tone King showed for months and which was written down as
        # "a property of the bare instantiation": it is not, it is the plugin's
        # first allocation of render resources. One render is spent finding out,
        # and only on a backend that came back silent — so a plugin that works,
        # like Morgan, pays nothing.
        self._isolate_decided = True
        if not float(np.abs(audio).max() if len(audio) else 0.0) == 0.0:
            return audio

        # On a *fresh* instance. Retrying inside the same one does not work:
        # once this plugin has rendered silently it stays silent however the next
        # render is ordered, so the difference only shows up when the resources
        # are cycled from the first render onwards. Measured — the same retry
        # without the restart comes back silent, and would have concluded that
        # isolating does not help.
        self._restart_server()
        self.isolate = True
        retried = self._one_render(di, settings, frames)
        if float(np.abs(retried).max() if len(retried) else 0.0) == 0.0:
            # Still silent, so isolating was not the answer. Put it back rather
            # than paying for a deallocation on every render for no reason, and
            # return the silence: it is a legitimate result that the caller has to
            # interpret, not an error to raise.
            self.isolate = False
            return audio
        self._isolate_note = (
            "this plugin rendered silence until its render resources were "
            "deallocated and reallocated, so every render now cycles them"
        )
        return retried

    def _one_render(self, di, settings: Optional[Mapping], frames: int):
        out_path = self._workdir / f"render-{self._render_index}.wav"
        self._render_index += 1
        command: Dict[str, Any] = {
            "out": str(out_path),
            "input": str(self._di_file(di)),
            "amplitude": self.amplitude,
        }
        if self.settle_ms:
            command["settle"] = self.settle_ms
        if self.isolate:
            command["isolate"] = True
        if self.warmup_s:
            command["warmup"] = self.warmup_s
        command.update(self._state_command(settings))

        self._exchange(command)
        try:
            return self._read_render(out_path, frames)
        finally:
            out_path.unlink(missing_ok=True)

    def parameter_specs(self) -> Dict[Tuple[str, str], Any]:
        """Every parameter of this pack the plugin can be written through.

        Keyed `(module, key)`, which is what `match.invert` matches against, and
        what `match.search` flattens into paths. Read-only parameters are left out
        because writing one is refused by the pack rather than ignored by the
        plugin; everything else the manifest declares is here, and it is
        `match.space` — not this backend — that decides what may be *searched*.
        """
        pack = self._pack()
        return {
            (spec.module, spec.key): spec
            for spec in pack.parameters.values()
            if spec.writable
        }

    def eq_basis(self, amp: str, analysis_centres):
        """This pack's measured equaliser, if `measure_eq_basis.py` has been run.

        The file describes this plugin at this version, which is why the backend
        is what answers for it: the same question asked of the synthetic chain has
        a different and equally correct answer.
        """
        from match.invert import measured_basis

        return measured_basis(self.pack_id, amp, analysis_centres)

    def to_spec(self, settings: Optional[Mapping] = None, name: str = "Matched"):
        """The settings as a spec `apply_spec.py` accepts.

        The same mapping this backend renders from, so a search's winner is
        written to a preset by the validated path rather than from preset bytes
        this class invented.
        """
        from match import space as space_module

        space = space_module.build(self.pack_id)
        return space.to_spec(settings or {}, name=name)

    # --- state --------------------------------------------------------------

    def _state_command(self, settings: Optional[Mapping]) -> Dict[str, Any]:
        """This parameter set, in whichever form the plugin's state takes."""
        if self._xml_state:
            return self._edit_command(settings)
        return self._record_command(settings)

    def _edit_command(self, settings: Optional[Mapping]) -> Dict[str, Any]:
        """Attribute edits for a JUCE XML state document.

        `selectedAmp` is pulled out and sent as the server's own `selectAmp`,
        because it is not an attribute of any module element and because writing a
        control on an amp that is not selected is a silent no-op — the amp has to
        be chosen before the edits mean anything.
        """
        pack = self._pack()
        edits = []
        command: Dict[str, Any] = {}
        for path, value in self._normalised(settings):
            module, key = path
            spec = self._spec(pack, module, key)
            # Through the pack even here. `selectedAmp` is an enum, and an enum
            # arrives as either a stored index or one of the plugin's own display
            # names — `match.invert` emits `'SW50R'`, because that is what
            # `space.to_spec` and `apply_spec.py` consume. Converting it with
            # `int(float(...))` instead of asking the pack turned every inversion
            # into a failed render: the search saw an unscorable trial rather than
            # an error, and reported it as "a silent render, or no dimension the
            # loss profile weights".
            stored = self._stored(pack, spec, value)
            if not module and key == "selectedAmp":
                command["selectAmp"] = int(float(stored))
                continue
            edits.append({"module": module, "key": key, "value": stored})
        command["edits"] = edits
        return command

    def _record_command(self, settings: Optional[Mapping]) -> Dict[str, Any]:
        """A whole rewritten state blob, for a plugin whose state is not XML.

        Tone King keeps a binary `PARAM` record rather than a document, so there
        is nothing for the server to edit in place. The plugin's own state is read
        once and every render re-writes it from that pristine copy, which keeps
        renders order-independent for the same reason the server's XML path does.
        """
        from format.parser import parse
        from format.structured import build, set_parameter
        from format.writer import write

        pack = self._pack()
        preset = build(parse(self._base_state_blob()))
        for (module, key), value in self._normalised(settings):
            spec = self._spec(pack, module, key)
            set_parameter(preset, module, key, self._stored(pack, spec, value))
        path = self._workdir / f"state-{self._render_index}.bin"
        path.write_bytes(write(preset.tokens))
        return {"state": str(path)}

    def _normalised(self, settings: Optional[Mapping]):
        """Settings as `((module, key), value)`, however the caller spelled them.

        `match.search` sends `"module/key"` strings and bare `"selectedAmp"`;
        `match.invert` sends `"/selectedAmp"`; a test may send tuples. All three
        have to arrive at the same parameter, because a key this failed to
        recognise would be silently left at whatever the plugin booted with.
        """
        for raw_key, value in (settings or {}).items():
            if isinstance(raw_key, str):
                module, _, key = raw_key.rpartition("/")
            else:
                parts = tuple(raw_key)
                if len(parts) == 1:
                    module, key = "", parts[0]
                elif len(parts) == 2:
                    module, key = parts
                else:
                    raise AudioUnitError(
                        f"{raw_key!r} is not a module/key pair"
                    )
            yield (module, key), value

    def _spec(self, pack, module: str, key: str):
        spec = pack.parameters.get(f"{module}/{key}" if module else f"/{key}")
        if spec is None:
            raise AudioUnitError(
                f"{module}/{key} is not a parameter of {pack.display_name}.\n"
                f"  This backend writes the plugin's own state; it cannot invent a "
                f"control. Check the spelling against packs/{self.pack_id}/manifest.json."
            )
        return spec

    def _stored(self, pack, spec, value) -> str:
        """The human value as the string the plugin stores.

        Through the pack, so an illegal value fails here for the same reason and
        with the same message it would fail in `apply_spec.py`. A backend that
        quietly clamped would render something the caller did not ask for and
        report the number they did.
        """
        from packs.loader import PackError

        notes: List[str] = []
        try:
            stored = pack.to_stored(spec, value, warnings=notes)
        except PackError as e:
            raise AudioUnitError(str(e)) from e
        for note in notes:
            if note not in self.warnings:
                self.warnings.append(note)
        return stored

    def _base_state_blob(self) -> bytes:
        """The plugin's state as it boots, read once through `au_probe dumpraw`."""
        if self._base_state is not None:
            return self._base_state
        binary = self._workdir / "au_probe"
        if not binary.exists():
            self._compile(PROBE_SOURCE, binary)
        prefix = self._workdir / "base"
        triple = self._au_triple()
        result = subprocess.run(
            [str(binary), triple["type"], triple["subtype"], triple["manufacturer"],
             "dumpraw", str(prefix)],
            capture_output=True, text=True)
        blob = prefix.with_suffix(".jucePluginState.bin")
        if result.returncode != 0 or not blob.exists():
            raise AudioUnitError(
                f"could not read {self.pack_id}'s state through au_probe dumpraw "
                f"(exit {result.returncode}).\n  {result.stderr.strip()}"
            )
        self._base_state = blob.read_bytes()
        return self._base_state

    # --- the server ---------------------------------------------------------

    def _ensure_server(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        if self._process is not None:
            raise AudioUnitError(
                f"the render server exited with status {self._process.returncode}. "
                f"Its stderr is in {self._workdir / 'server.log'}."
            )
        binary = self._binary
        if binary is None:
            binary = self._workdir / "au_render_server"
            if not binary.exists():
                self._compile(SERVER_SOURCE, binary)
        triple = self._au_triple()
        self._log = open(self._workdir / "server.log", "ab")
        self._process = subprocess.Popen(
            [str(binary), triple["type"], triple["subtype"], triple["manufacturer"],
             "--settle", "0" if not self.settle_ms else str(self.settle_ms)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            # To a file, not a pipe. The server logs a CoreAudio warning on every
            # render, and a pipe nobody drains fills after a few hundred of them
            # and deadlocks the search at whatever render that happens to be.
            stderr=self._log, text=True, bufsize=1)
        ready = self._readline()
        if not ready.get("ready"):
            raise AudioUnitError(
                f"the render server did not come up: {ready!r}\n"
                f"  Check {self._workdir / 'server.log'}."
            )
        self._plugin_version = ready.get("version") or None
        self._xml_state = bool(ready.get("xml_state"))

    def _restart_server(self) -> None:
        """A new plugin instance, keeping everything already learned about it.

        The workdir and the base state survive, so the DI does not have to be
        written again and `au_probe dumpraw` does not have to run again.
        """
        process, self._process = self._process, None
        if process is not None and process.poll() is None:
            try:
                if process.stdin is not None:
                    process.stdin.write('{"quit":true}\n')
                    process.stdin.flush()
                    process.stdin.close()
                process.wait(timeout=10)
            except (BrokenPipeError, ValueError, subprocess.TimeoutExpired):
                process.kill()
                process.wait()
        self._ensure_server()

    def _exchange(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """One command, one reply, with a dead server reported as such."""
        process = self._process
        assert process is not None and process.stdin is not None
        try:
            process.stdin.write(json.dumps(command) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, ValueError) as e:
            raise AudioUnitError(
                f"the render server closed its input ({e}). Its stderr is in "
                f"{self._workdir / 'server.log'}."
            ) from e
        reply = self._readline()
        if not reply.get("ok"):
            raise AudioUnitError(
                f"render failed: {reply.get('error', reply)}"
            )
        return reply

    def _readline(self) -> Dict[str, Any]:
        process = self._process
        assert process is not None and process.stdout is not None
        line = process.stdout.readline()
        if not line:
            status = process.poll()
            raise AudioUnitError(
                f"the render server stopped replying (exit status {status}). Its "
                f"stderr is in {self._workdir / 'server.log'}."
            )
        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            raise AudioUnitError(
                f"the render server said {line.strip()!r}, which is not JSON ({e})"
            ) from e

    def _compile(self, source: pathlib.Path, output: pathlib.Path) -> None:
        sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
        from _swift import compile_swift

        built, error = compile_swift(source, output)
        if built is None or built.returncode != 0:
            raise AudioUnitError(f"could not build {source.name}:\n{error}")

    # --- audio in and out ---------------------------------------------------

    def _di_file(self, di) -> pathlib.Path:
        """The DI on disk, written once per distinct signal.

        A search renders hundreds of candidates through one DI. Writing and
        re-decoding it each time would be most of the wall clock the batched
        server exists to save.
        """
        import numpy as np
        import soundfile as sf

        array = np.ascontiguousarray(np.asarray(di, dtype=np.float32))
        if array.ndim == 1:
            array = array[:, None]
        digest = hashlib.sha256(array.tobytes()).hexdigest()
        path = self._di_files.get(digest)
        if path is None:
            path = self._workdir / f"di-{digest[:16]}.wav"
            sf.write(str(path), array, self.sample_rate, subtype="FLOAT")
            self._di_files[digest] = path
        return path

    def _read_render(self, path: pathlib.Path, frames: int):
        import numpy as np
        import soundfile as sf

        if not path.exists():
            raise AudioUnitError(
                f"the render server reported success but wrote no file at {path}"
            )
        samples, rate = sf.read(str(path), dtype="float32", always_2d=True)
        if int(rate) != self.sample_rate:
            raise AudioUnitError(
                f"{path} came back at {rate} Hz, not the {self.sample_rate} Hz this "
                f"backend renders at"
            )
        # Never padded up: a render shorter than its input is a finding, not
        # something to hide behind zeros.
        return np.ascontiguousarray(samples[:frames], dtype=np.float32)

    # --- lifecycle ----------------------------------------------------------

    def _au_triple(self) -> Dict[str, str]:
        pack = self._pack()
        triple = dict(pack.audio_unit or {})
        missing = [f for f in ("type", "subtype", "manufacturer") if not triple.get(f)]
        if missing:
            raise AudioUnitError(
                f"packs/{self.pack_id}/manifest.json declares no {', '.join(missing)} "
                f"for its Audio Unit, so there is no plugin to render through.\n"
                f"  A bootstrapped draft pack has no `audio_unit` block; only a pack "
                f"that has been audited against the installed plugin does."
            )
        return triple

    def _au_triple_text(self) -> str:
        triple = self._au_triple()
        return f"{triple['type']} {triple['subtype']} {triple['manufacturer']}"

    def _pack(self):
        if self._pack_cache is None:
            from packs.loader import load_pack

            self._pack_cache = load_pack(self.pack_id)
        return self._pack_cache

    def _renderer_build(self) -> str:
        """The harness's own identity, so a change to it invalidates the cache.

        The Swift source rather than the compiled binary: the binary is rebuilt
        into a fresh temporary directory on most runs, so its hash would change
        without the harness changing and throw away every cache entry.
        """
        digest = hashlib.sha256(SERVER_SOURCE.read_bytes()).hexdigest()
        return f"au_render_server-{digest[:12]}"

    def close(self) -> None:
        """Stop the server and let go of the plugin instance."""
        process, self._process = self._process, None
        if process is not None and process.poll() is None:
            try:
                if process.stdin is not None:
                    process.stdin.write('{"quit":true}\n')
                    process.stdin.flush()
                    process.stdin.close()
                process.wait(timeout=10)
            except (BrokenPipeError, ValueError, subprocess.TimeoutExpired):
                process.kill()
                process.wait()
        if self._log is not None:
            self._log.close()
            self._log = None
        if self._owns_workdir:
            shutil.rmtree(self._workdir, ignore_errors=True)

    def __enter__(self) -> "AudioUnitRenderer":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
