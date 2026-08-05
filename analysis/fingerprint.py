"""Fingerprint v1 — what a sound is, in the form everything else speaks.

This is the interface. A separated stem of a 1976 master, a two-second render of
white noise, and a DI played through a candidate preset all produce the same
schema, and every producer and consumer in this project speaks it. Features are
added by bumping the version, never by putting an extra key in.

Every field is optional and most carry a confidence, because the schema has to
describe material it cannot fully measure. `harmonic` needs a sustained
monophonic note; `time_fx` needs repeats to find; `spatial` needs two channels.
Absent is a legitimate answer and consumers must handle it — a `None` says the
recording could not support the measurement, which is different from a zero.

Spectral, harmonic and dynamic fields are computed after loudness
normalisation, so they compare a mastered record with a raw render without the
20 dB between them swamping everything. The level itself is kept in `source`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from . import FINGERPRINT_VERSION, require

# How much a match against this kind of reference is worth. A paired DI means
# the same performance through the same notes; a commercial mix means the guitar
# is buried under a band, a bus compressor and a master chain. Reporting a
# number without this alongside it overstates what was measured.
REGIMES = {
    "paired_di": 1.0,
    "isolated_stem": 0.85,
    "separated_stem": 0.55,
    "mix": 0.35,
    "probe": 1.0,
}

DEFAULT_EXCERPT_S = 20.0


class FingerprintError(ValueError):
    """A fingerprint that cannot be read: wrong version, or unknown fields."""


@dataclass
class Fingerprint:
    """The sections of §6.1, each a plain dict so the JSON is the object."""

    source: Dict[str, Any] = field(default_factory=dict)
    spectrum: Dict[str, Any] = field(default_factory=dict)
    dynamics: Dict[str, Any] = field(default_factory=dict)
    harmonic: Dict[str, Any] = field(default_factory=dict)
    time_fx: Dict[str, Any] = field(default_factory=dict)
    modulation: Dict[str, Any] = field(default_factory=dict)
    spatial: Dict[str, Any] = field(default_factory=dict)
    cepstral: Dict[str, Any] = field(default_factory=dict)
    fingerprint_version: int = FINGERPRINT_VERSION

    SECTIONS = ("source", "spectrum", "dynamics", "harmonic", "time_fx",
                "modulation", "spatial", "cepstral")

    # --- serialisation ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"fingerprint_version": self.fingerprint_version}
        for name in self.SECTIONS:
            data[name] = getattr(self, name)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fingerprint":
        version = data.get("fingerprint_version")
        if version != FINGERPRINT_VERSION:
            raise FingerprintError(
                f"fingerprint version {version!r}, expected {FINGERPRINT_VERSION}. "
                "Fingerprints from a different version are not compared or merged."
            )
        unknown = set(data) - set(cls.SECTIONS) - {"fingerprint_version"}
        if unknown:
            # An ad-hoc key is how two versions of a schema quietly diverge.
            raise FingerprintError(
                f"unknown field(s) {sorted(unknown)}. Add features by bumping "
                "fingerprint_version, not by adding keys."
            )
        return cls(
            **{name: dict(data.get(name) or {}) for name in cls.SECTIONS},
            fingerprint_version=version,
        )

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)

    @classmethod
    def from_json(cls, text: str) -> "Fingerprint":
        return cls.from_dict(json.loads(text))

    # --- convenience --------------------------------------------------------

    @property
    def regime(self) -> str:
        return str(self.source.get("regime", "probe"))

    @property
    def regime_confidence(self) -> float:
        return REGIMES.get(self.regime, 0.3)

    def band_db(self, centre_hz: float) -> Optional[float]:
        """The long-term level of one third-octave band, or None."""
        centres = self.spectrum.get("band_centres_hz") or []
        levels = self.spectrum.get("band_db") or []
        for centre, level in zip(centres, levels):
            if abs(centre - centre_hz) < 0.51:
                return float(level)
        return None

    def caveats(self) -> list:
        """Everything a report has to say out loud about this measurement."""
        notes = []
        if self.regime in ("mix", "separated_stem"):
            notes.append(
                f"reference regime is {self.regime}: the guitar is not isolated, "
                "so the spectrum includes whatever else is playing"
            )
        if float(self.harmonic.get("confidence") or 0.0) < 0.5:
            notes.append(
                "no sustained monophonic note was found, so distortion character "
                "(HNR, odd/even, fizz) is unmeasured"
            )
        if float(self.time_fx.get("delay_confidence") or 0.0) < 0.3:
            notes.append("no delay repeat was detected above the noise")
        if float(self.time_fx.get("rt60_confidence") or 0.0) < 0.4:
            notes.append("reverb decay is uncertain: release segments disagree")
        if (self.modulation.get("am_rate_hz") is not None
                and float(self.modulation.get("am_confidence") or 0.0) < 0.75):
            notes.append(
                f"the {self.modulation['am_rate_hz']:.1f} Hz amplitude modulation is not a "
                "clean sine, so it is more likely the rate the notes are being played at "
                "than a tremolo"
            )
        if int(self.source.get("channels") or 1) < 2:
            notes.append("mono source: stereo width is not measured")
        return notes


def fingerprint(audio, regime: str = "probe",
                excerpt_s: Optional[float] = DEFAULT_EXCERPT_S) -> Fingerprint:
    """Measure an `io.Audio` into a Fingerprint v1.

    Long files are reduced to their most continuously active excerpt first: a
    four-minute track holds one guitar tone and three minutes of other things,
    and averaging the fade-out into the spectrum describes the fade-out.
    """
    require("fingerprinting")

    from . import features as F
    from .io import loudness_lufs, normalise, true_peak_dbtp

    if regime not in REGIMES:
        raise FingerprintError(
            f"unknown regime {regime!r}. One of: {', '.join(sorted(REGIMES))}"
        )

    if excerpt_s:
        from .io import excerpt as take_excerpt

        audio = take_excerpt(audio, excerpt_s)

    loudness = loudness_lufs(audio)
    source = {
        "sha256": audio.sha256,
        "sample_rate": audio.sample_rate,
        "channels": audio.channels,
        "duration_s": round(audio.duration_s, 4),
        "lufs_i": None if loudness is None else round(loudness, 2),
        "true_peak_dbtp": None if true_peak_dbtp(audio) is None else round(true_peak_dbtp(audio), 2),
        "regime": regime,
        "source_sample_rate": audio.source_rate,
        "source_channels": audio.source_channels,
    }

    # Everything below this line sees loudness-normalised audio, which is what
    # makes two fingerprints comparable at all.
    levelled = normalise(audio)
    mono = levelled.mono()
    rate = levelled.sample_rate

    bands = F.third_octave_bands(mono, rate)
    spectrum = dict(bands)
    spectrum["tilt_db_per_decade"] = F.spectral_tilt(bands["band_centres_hz"], bands["band_db"])
    spectrum.update(F.spectral_statistics(mono, rate))
    spectrum.update(F.corner_frequencies(bands["band_centres_hz"], bands["band_db"]))

    return Fingerprint(
        source=source,
        spectrum=spectrum,
        dynamics=F.dynamics(mono, rate, samples_2d=levelled.samples),
        harmonic=F.harmonic(mono, rate),
        time_fx=F.time_effects(mono, rate),
        modulation=F.modulation(mono, rate),
        spatial=F.spatial(levelled.samples, rate),
        cepstral=F.cepstral(mono, rate),
    )


def fingerprint_file(path, regime: str = "probe",
                     excerpt_s: Optional[float] = DEFAULT_EXCERPT_S) -> Fingerprint:
    """Load and fingerprint in one call."""
    from .io import load

    return fingerprint(load(path), regime=regime, excerpt_s=excerpt_s)
