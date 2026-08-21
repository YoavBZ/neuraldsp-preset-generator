"""Render several parameter vectors at once, on backends that allow it.

A render is the only expensive thing in this repository — §2's D3 — and the three
places that spend them in bulk all ask for *independent* renders: the screen's two
per parameter, each CMA-ES generation's λ samples, and the re-rank's replicates.
Nothing in any of those depends on the answer to another.

Measured on Morgan through the Swift server, 24 renders per configuration with
four warm-up renders per instance and the single-worker case run again afterwards
to check the baseline had not drifted (it went 4.54 to 4.51 renders/s):

| workers | renders/s | speedup |
|---|---|---|
| 1 | 4.54 | — |
| 2 | 8.77 | 1.94x |
| 4 | 17.24 | 3.82x |

Threads rather than processes: each `AudioUnitRenderer` already owns a separate
Swift subprocess, so the plugin work happens outside this interpreter and the GIL
is released while a worker waits on it. That also means no renderer source had to
change — `match/renderer_au.py` is hashed into calibration provenance, and editing
it would invalidate every committed `eq_basis.json`.

**Order is not timing.** `render_many` returns results in the order it was given
them, whatever order they complete in, because a search that reordered its own
population under load would be a search whose answer depended on machine load.

**Nothing in the search uses this, and `Evaluator.evaluate_many` refuses to let
it — §12j says why.** Spreading a *comparison*
across plugin instances gives it whatever offset separates them: on Tone King,
`/leadAmpMidBite` moves 0.0027 measured within one instance, 0.0214 with the probes
on a second instance and no concurrency at all, and 0.1195 across four — against a
freeze floor near 0.01. Every bulk stage in `match/search.py` is comparison-based,
so none of them can use this on a `reproducible=false` backend. The sound
application is the benchmark, whose targets are independent experiments rather than
comparisons: one instance per target, for the whole of that target.

**Superseded note, kept because it names the mistake.** On a
`reproducible=false` backend the screen's output — which controls clear the freeze
threshold — is a thresholded view of a noisy measurement, and several controls sit
close enough to that threshold for membership to flip. Four attempts to compare
pooled against serial selection contradicted each other: 0 of 3 pairs differing
within each group and 9 of 9 across it, then 0 of 2 across it on a later run, and a
variant sharing one instance between baseline and probes differing by 7. Comparing
thresholded sets was the wrong instrument — it amplifies exactly what the threshold
exists to suppress. What would settle it is a comparison of the *movements*, control
by control, over enough repeats to separate the pool's contribution from the
backend's own spread. Until that exists, treat pooled numbers from a
non-reproducible backend as unvalidated.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple


class PoolError(RuntimeError):
    """The pool cannot be built, or its members do not agree with each other."""


class RendererPool:
    """`workers` renderers, handing out one per concurrent render.

    Built from a factory rather than from instances so the caller does not have to
    know how many it will need before deciding whether to parallelise at all, and
    closed as a unit — a leaked member holds a plugin instance open.
    """

    def __init__(self, factory: Callable[[], Any], workers: int) -> None:
        if workers < 1:
            raise PoolError(f"a pool needs at least one renderer, not {workers}")
        self._members: List[Any] = []
        self._free: "queue.Queue[Any]" = queue.Queue()
        try:
            for _ in range(workers):
                member = factory()
                self._members.append(member)
                self._free.put(member)
        except BaseException:
            self.close()
            raise
        self._verify_agreement()

    # --- the contract that makes results interchangeable --------------------

    def _verify_agreement(self) -> None:
        """Every member must be the same backend, or scores are not comparable.

        A cache key is built from `RenderMetadata`, and the objective is compared
        across candidates that may have been rendered by different members. Two
        members differing in plugin version, sample rate, block size, build or
        quality mode would put two different backends' numbers in one shortlist
        and rank them against each other.
        """
        identities = {self._identity(member) for member in self._members}
        if len(identities) > 1:
            self.close()
            raise PoolError(
                "the renderers in this pool do not describe the same backend, so "
                "their scores cannot be compared: " + "; ".join(
                    sorted(str(identity) for identity in identities))
            )

    @staticmethod
    def _identity(member) -> Tuple:
        metadata = member.metadata()
        return (metadata.renderer_id, metadata.plugin_version, metadata.sample_rate,
                metadata.block_size, metadata.renderer_build, metadata.quality_mode)

    # --- use ----------------------------------------------------------------

    @property
    def workers(self) -> int:
        return len(self._members)

    def metadata(self):
        """The backend all members agree they are."""
        return self._members[0].metadata()

    def render_one(self, di, settings: Mapping, di_sha256: Optional[str] = None):
        """Borrow a member, render, give it back.

        The unit `match.search.Evaluator.evaluate_many` wants: it runs its own
        thread per job so the ~150 ms fingerprint happens beside the render that
        produced it rather than serially afterwards, and it only needs the pool to
        hand out a renderer that nobody else is using. Blocks when every member is
        busy, which is what limits concurrency to `workers`.
        """
        member = self._free.get()
        try:
            return member.render(di, settings, di_sha256=di_sha256)
        finally:
            self._free.put(member)

    def render_many(self, jobs: Sequence[Tuple[Any, Mapping, Optional[str]]]):
        """Run `(di, settings, di_sha256)` jobs, results in the order given.

        A job that raises returns its exception rather than propagating it, because
        one refused vector does not invalidate the others and the caller already
        knows how to record a failed trial — `Evaluator.evaluate` catches exactly
        the same errors one at a time.
        """
        results: List[Any] = [None] * len(jobs)
        errors: List[Optional[BaseException]] = [None] * len(jobs)

        def work(index: int, di, settings, di_sha) -> None:
            member = self._free.get()
            try:
                results[index] = member.render(di, settings, di_sha256=di_sha)
            except BaseException as error:      # noqa: BLE001 — handed back below
                errors[index] = error
            finally:
                self._free.put(member)

        threads = [
            threading.Thread(target=work, args=(index, di, settings, di_sha),
                             daemon=True)
            for index, (di, settings, di_sha) in enumerate(jobs)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return list(zip(results, errors))

    def close(self) -> None:
        for member in self._members:
            close = getattr(member, "close", None)
            if close is not None:
                try:
                    close()
                except BaseException:
                    pass
        self._members = []

    def __enter__(self) -> "RendererPool":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
