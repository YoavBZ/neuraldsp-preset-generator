"""The synthetic backend: `analysis/refchain.py` behind the `Renderer` protocol.

The only renderer that runs in CI, and the only one that is exactly reproducible.
Everything M3 and M4 build is developed against this, with the ground-truth
parameters in hand, before the real plugin's per-render variation and 0.29 s cost
are allowed to complicate the picture.

It is not a model of Morgan. It shares Morgan's topology, parameter names, kinds,
units and ranges, which is enough for a search space and an inversion to be
written against it — and not enough for any number measured here to be reported
as a fact about the plugin.
"""

from __future__ import annotations

from typing import Mapping, Optional

from analysis import SAMPLE_RATE

from .renderer import RenderMetadata, Renderer

# Bumped when the chain's DSP changes in a way that alters its output. It is in
# the cache key, so an entry rendered by an older chain is never served for a
# newer one -- the same reason the real backends carry a plugin version.
CHAIN_BUILD = "refchain-1"


class SyntheticRenderer(Renderer):
    """Render a DI through the synthetic chain."""

    renderer_id = "synthetic"

    def __init__(self, sample_rate: int = SAMPLE_RATE, block_size: int = 512,
                 quality_mode: str = "standard"):
        self.sample_rate = int(sample_rate)
        self.block_size = int(block_size)
        self.quality_mode = quality_mode

    def metadata(self) -> RenderMetadata:
        return RenderMetadata(
            renderer_id=self.renderer_id,
            sample_rate=self.sample_rate,
            block_size=self.block_size,
            plugin_version=CHAIN_BUILD,
            renderer_build=CHAIN_BUILD,
            quality_mode=self.quality_mode,
            # The one backend that can say this truthfully.
            reproducible=True,
            band_noise_db=0.0,
            notes=("synthetic chain: mirrors Morgan's topology, models none of its DSP",),
        )

    def _render(self, di, settings: Optional[Mapping]):
        from analysis import refchain

        return refchain.render(di, settings, sample_rate=self.sample_rate)

    def parameter_specs(self):
        from analysis import refchain

        return refchain.parameter_specs()

    def to_spec(self, settings: Optional[Mapping] = None, name: str = "Synthetic"):
        """The settings as a spec `apply_spec.py` accepts.

        On the protocol's synthetic implementation rather than the protocol itself
        because it is the same mapping in both directions here. For a real backend
        the parameter edits and the preset are different encodings of one spec,
        which is why the optimiser emits a spec and never preset bytes.
        """
        from analysis import refchain

        return refchain.to_spec(settings, name=name)
