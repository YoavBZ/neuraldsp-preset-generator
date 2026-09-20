"""Get audio into the one shape every feature expects, and describe its level.

Two things happen here that the rest of the package then never has to think
about. Audio arrives at 48 kHz float32 with its channel count intact, whatever
the file was; and level is measured once, properly, so that "brighter" is never
confused with "louder".

Level matters more than it looks. A reference is a mastered commercial track and
a candidate is a raw render, so they can differ by 20 dB before anything about
their tone differs at all. Every spectral feature is computed after loudness
normalisation for that reason, and the measured loudness is kept as a feature of
its own rather than thrown away.
"""

from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass
from typing import NamedTuple, Optional

from . import SAMPLE_RATE, require

# Frames quieter than this, relative to the loudest frame, are not the sound —
# they are the gaps between the notes. Averaging them into a long-term spectrum
# measures the silence as much as the tone.
SILENCE_FLOOR_DB = -45.0
FRAME = 2048
HOP = 512

# BS.1770 weights are defined up to five channels and pyloudnorm refuses more.
MAX_METERED_CHANNELS = 5


@dataclass(frozen=True)
class Audio:
    """Decoded audio in the canonical format, plus what identifies it.

    `sha256` is of the file's bytes, not of the samples and never of the path:
    it is what a run record can store about a reference the project must not
    keep a copy of.
    """

    samples: "object"  # np.ndarray, shape (frames, channels), float32
    sample_rate: int
    sha256: str
    source_rate: int
    source_channels: int

    @property
    def frames(self) -> int:
        return int(self.samples.shape[0])

    @property
    def channels(self) -> int:
        return int(self.samples.shape[1])

    @property
    def duration_s(self) -> float:
        return self.frames / float(self.sample_rate)

    def mono(self):
        """Channel-summed, for every feature that is not about the stereo field."""
        import numpy as np

        return np.asarray(self.samples, dtype=np.float64).mean(axis=1)

    def replace(self, samples) -> "Audio":
        import numpy as np

        return Audio(
            samples=np.asarray(samples, dtype=np.float32).reshape(len(samples), -1),
            sample_rate=self.sample_rate,
            sha256=self.sha256,
            source_rate=self.source_rate,
            source_channels=self.source_channels,
        )


def load(path, target_rate: int = SAMPLE_RATE) -> Audio:
    """Read a file into the canonical format."""
    require("loading audio")
    import numpy as np
    import soundfile as sf

    path = pathlib.Path(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()

    try:
        samples, rate = sf.read(str(path), dtype="float32", always_2d=True)
    except sf.LibsndfileError as e:
        # libsndfile decodes WAV, AIFF, FLAC and Ogg, and no compressed Apple or
        # MPEG format. A reference bounced out of a DAW is usually fine; one
        # exported from a phone, a streaming service or a stem-separation tool is
        # routinely .m4a or .mp3, and "Format not recognised" tells that person
        # nothing about what to do next. Naming the converter is the whole fix —
        # this deliberately does not shell out to one, because a decode nobody
        # asked for is a decode nobody can check.
        raise ValueError(
            f"{path} is not audio this can read ({e}).\n"
            f"  libsndfile handles WAV, AIFF, FLAC and Ogg. Compressed formats "
            f"(.m4a, .mp3, .aac) have to be converted first — 48 kHz, which is "
            f"what everything here measures at:\n"
            f"    afconvert -f WAVE -d LEI16@48000 {path.name!r} out.wav   # macOS\n"
            f"    ffmpeg -i {path.name!r} -ar 48000 out.wav                # anywhere\n"
            f"  A lossy source is still worth measuring, but the codec has "
            f"already moved the high end, so treat the top bands as the codec's "
            f"as much as the amp's."
        ) from e
    # A float WAV can hold NaN and ±inf — a corrupt bounce, a blown-up plugin in a DAW —
    # and nothing downstream survives it. `scripts/match_preset.py` grew a guard for a
    # reference that cannot be measured, and it caught silence and refused it in a
    # sentence; the non-finite branch went all the way to a covariance eigendecomposition
    # and came back as `error: Eigenvalues did not converge`, naming neither the file nor
    # the cause. Refused here, where the file is still in hand, because every caller
    # downstream would have to repeat the check. (Integer formats cannot express it, so
    # this only ever fires on float subtypes.)
    bad = int(np.count_nonzero(~np.isfinite(samples)))
    if bad:
        total = samples.size or 1
        counted = (f"1 sample that is not finite" if bad == 1
                   else f"{bad} samples that are not finite")
        raise ValueError(
            f"{path} contains {counted} "
            f"({100.0 * bad / total:.2g}% of the file): NaN or infinity, which "
            f"no measurement here can be made from.\n"
            f"  That usually means a corrupt export or a plugin that blew up during the "
            f"bounce. Re-export the file and check it plays."
        )
    source_rate, source_channels = int(rate), int(samples.shape[1])
    if source_rate != target_rate:
        samples = resample(samples, source_rate, target_rate)
    return Audio(
        samples=np.ascontiguousarray(samples, dtype=np.float32),
        sample_rate=target_rate,
        sha256=digest,
        source_rate=source_rate,
        source_channels=source_channels,
    )


def from_samples(samples, sample_rate: int = SAMPLE_RATE) -> Audio:
    """Wrap an array that never was a file — a render held in memory, or a
    fixture a test just synthesised."""
    require("wrapping audio")
    import numpy as np

    array = np.asarray(samples, dtype=np.float32)
    if array.ndim == 1:
        array = array[:, None]
    return Audio(
        samples=np.ascontiguousarray(array),
        sample_rate=int(sample_rate),
        sha256=hashlib.sha256(array.tobytes()).hexdigest(),
        source_rate=int(sample_rate),
        source_channels=int(array.shape[1]),
    )


def resample(samples, source_rate: int, target_rate: int):
    """Polyphase resampling at the exact rational ratio, so 44100 → 48000 is
    147/160 and not a float approximation of it."""
    require("resampling")
    from fractions import Fraction

    import numpy as np
    from scipy import signal

    ratio = Fraction(int(target_rate), int(source_rate)).limit_denominator(1000)
    resampled = signal.resample_poly(
        np.asarray(samples, dtype=np.float64), ratio.numerator, ratio.denominator, axis=0
    )
    return np.asarray(resampled, dtype=np.float32)


def loudness_lufs(audio: Audio) -> Optional[float]:
    """Integrated loudness, ITU-R BS.1770 / EBU R128.

    Returns None for material shorter than the 400 ms gating block or for
    digital silence, rather than the -inf that a meter reports there.

    BS.1770 defines its channel weights for up to five channels, and a meter
    refuses more. Rather than fail the whole fingerprint on a six-channel file —
    the exit criterion is a valid Fingerprint v1 for *any* input — such material
    is metered on the channel-**averaged** fold, which is the signal every
    spectral feature is computed from anyway. That is an approximation of the
    standard rather than the standard, so `Fingerprint.caveats()` says so.
    Normalisation matters more here than strict conformance: without it, nothing
    downstream compares a mastered record with a raw render at all.

    Averaged, not summed, and the difference is not cosmetic: because it divides
    by the channel count, adding one silent channel to a five-channel file moves
    the reported loudness by about 9 dB on identical audio — three units of
    "wrong" at `compare._level`'s 3 dB scale. Both this docstring and
    `caveats()` used to say "summed" while the code averaged. The number to
    distrust across a channel-count change is this one; `normalise()` is
    self-consistent, so the spectral path is unaffected.
    """
    require("loudness metering")
    import numpy as np

    if audio.duration_s < 0.4:
        return None
    import pyloudnorm

    data = np.asarray(audio.samples, dtype=np.float64)
    if audio.channels > MAX_METERED_CHANNELS:
        data = audio.mono()

    meter = pyloudnorm.Meter(audio.sample_rate)
    with np.errstate(divide="ignore", invalid="ignore"):
        try:
            value = float(meter.integrated_loudness(data))
        except ValueError:
            # A meter that still refuses this material tells us the loudness is
            # unmeasurable, which is a legitimate answer. It is not a reason to
            # lose the other forty fields.
            return None
    return None if not np.isfinite(value) else value


def true_peak_dbtp(audio: Audio) -> Optional[float]:
    """Peak after 4× oversampling: a signal can exceed its sample peak between
    samples, and a render that looks like it has headroom may not."""
    require("peak metering")
    import numpy as np
    from scipy import signal

    data = np.asarray(audio.samples, dtype=np.float64)
    if data.size == 0:
        return None
    upsampled = signal.resample_poly(data, 4, 1, axis=0)
    peak = float(np.abs(upsampled).max())
    return None if peak <= 0 else float(20.0 * np.log10(peak))


def normalise(audio: Audio, target_lufs: float = -23.0) -> Audio:
    """Scale to a fixed loudness so that what follows compares tone, not level.

    Silent or unmeasurable material is returned unchanged: there is no gain that
    makes silence -23 LUFS, and pretending otherwise would put a division by
    zero into every downstream feature.
    """
    require("loudness normalisation")
    import numpy as np

    measured = loudness_lufs(audio)
    if measured is None:
        return audio
    gain = 10.0 ** ((target_lufs - measured) / 20.0)
    return audio.replace(np.asarray(audio.samples, dtype=np.float64) * gain)


def frame_rms_db(mono, frame: int = FRAME, hop: int = HOP):
    """Per-frame RMS in dB, the basis of every gate and envelope below."""
    require("framing")
    import numpy as np

    mono = np.asarray(mono, dtype=np.float64)
    if len(mono) < frame:
        mono = np.pad(mono, (0, frame - len(mono)))
    count = 1 + (len(mono) - frame) // hop
    windows = np.lib.stride_tricks.as_strided(
        mono, shape=(count, frame), strides=(mono.strides[0] * hop, mono.strides[0])
    )
    rms = np.sqrt((windows**2).mean(axis=1))
    return 20.0 * np.log10(rms + 1e-12)


def active_frames(mono, frame: int = FRAME, hop: int = HOP, floor_db: float = SILENCE_FLOOR_DB):
    """Boolean mask of the frames worth measuring, relative to the loudest one.

    Relative rather than absolute, because the input may be a quiet render or a
    loud master and the gaps between notes are what this excludes either way.
    """
    require("gating")
    import numpy as np

    levels = frame_rms_db(mono, frame, hop)
    if not np.isfinite(levels).any():
        return np.zeros(len(levels), dtype=bool)
    return levels > (levels.max() + floor_db)


def excerpt(audio: Audio, seconds: float) -> Audio:
    """The most continuously active window of the requested length.

    A four-minute track holds one guitar tone and three minutes of other
    things. Fingerprinting the loudest sustained stretch is both faster and more
    representative than averaging the whole file, including its fade-out.
    """
    start, end = excerpt_bounds(audio, seconds)
    if start == 0 and end == audio.frames:
        return audio
    return audio.replace(audio.samples[start:end])


def excerpt_bounds(audio: Audio, seconds: float) -> tuple[int, int]:
    """Frame bounds selected by :func:`excerpt`, without losing provenance.

    The old API returned only the samples. That made a run impossible to reproduce
    from its report: ``--excerpt 30`` could mean any dense 30-second stretch in a
    four-minute song, but neither its start nor its end survived fingerprinting.
    Keeping selection in one function also prevents the reported bounds and the
    samples actually measured from drifting apart.
    """
    selection = excerpt_selection(audio, seconds)
    return selection.start, selection.end


#: Above this share of tied-for-best windows, the chosen one is the earliest of
#: many equals rather than a distinguished pick.
_TIE_SHARE_WORTH_REPORTING = 0.5

#: …and only worth reporting when the source is enough longer than the window
#: that the choice actually excluded something. A 30 s file measured with a 20 s
#: window has eleven candidates that almost entirely overlap; saying they tied is
#: true and useless, and a caveat that fires on ordinary material teaches people
#: to skip the caveats that matter.
_MIN_SOURCE_MULTIPLE = 2.0


class Selection(NamedTuple):
    """Which window was measured, and the evidence for how it was picked.

    A tuple so ``start, end`` unpacking and ``[:2]`` keep working, named so the
    policy and its supporting counts do not have to be remembered by position.
    """

    start: int
    end: int
    policy: str
    active_fraction: Optional[float] = None
    tied_windows: Optional[int] = None
    candidate_windows: Optional[int] = None


def excerpt_selection(audio: Audio, seconds: float,
                      start_s: Optional[float] = None) -> tuple:
    """Which window to measure, and how honestly it was chosen.

    Returns ``(start_frame, end_frame, policy, active_fraction)``.

    The activity ranking underneath this is a **broadband** RMS gate
    (:func:`active_frames`): it answers "is there sound here", not "is the
    instrument you care about here". On a mastered, continuously-playing mix
    almost every frame passes, every window scores the same, and ``argmax``
    returns the first one — so the selection degenerates into "the start of the
    file" while still calling itself most-continuously-active.

    That is not hypothetical. On a five-minute mastered ballad, 98% of frames
    were active and 29,642 of ~30,255 candidate windows tied at the maximum, so
    the chosen window was the bass intro, with no guitar in it at all. Every
    number measured from it described an upright bass, and nothing said so.

    The fix is not a cleverer ranking — a broadband gate cannot become
    instrument-aware — but refusing to overstate what happened. Every policy
    below reports only what is true of the selection it names, and ``start_s``
    is the way to choose a window deliberately instead.
    """
    require("excerpt selection")
    import numpy as np

    wanted = int(seconds * audio.sample_rate)
    if wanted <= 0:
        # A window shorter than one frame is not a window; nothing was ignored.
        return Selection(0, audio.frames, "full_source")
    if audio.frames <= wanted:
        # Nothing to select — but say so rather than dropping an explicit
        # request on the floor. Someone who clips a 15 s reference and asks to
        # start 5 s in to skip a count-in would otherwise measure the count-in,
        # with the report calling it `full_source` and no caveat anywhere.
        return Selection(0, audio.frames,
                         "explicit_window_ignored_short_source"
                         if start_s else "full_source")

    mono = audio.mono()
    active = active_frames(mono).astype(np.float64)
    fraction = float(active.mean()) if len(active) else None

    if start_s is not None:
        # Clamped rather than refused, because asking for the last 20 seconds of
        # a file by eye is an ordinary thing to get slightly wrong. But a clamp
        # is recorded, not swallowed: `--excerpt-start 300` on a 60 s file used
        # to measure 40-60 s and report it as the window the user named, which
        # is a whole match budget spent on a window nobody chose.
        requested = int(float(start_s) * audio.sample_rate)
        start = max(0, min(requested, audio.frames - wanted))
        return Selection(start, start + wanted,
                         "explicit_window" if start == requested
                         else "explicit_window_clamped",
                         fraction)

    span = max(1, wanted // HOP)
    if len(active) <= span:
        return Selection(0, wanted, "most_continuously_active", fraction)

    density = np.convolve(active, np.ones(span), mode="valid")
    # Tolerance rather than equality: the convolution of a 0/1 array with ones
    # is integral in exact arithmetic, and comparing floats for equality to
    # decide a user-visible caveat is not a thing to rely on.
    tied = int(np.count_nonzero(density >= density.max() - 0.5))
    candidates = len(density)
    start = int(np.argmax(density)) * HOP
    start = min(start, audio.frames - wanted)

    # Report the tie, and only the tie. An earlier version called this case
    # "uninformative" and had the caveat say the ranking chose nothing — which
    # is false whenever the plateau is merely large: on ten seconds of silence
    # followed by fifty of playing, the ranking lands exactly on the first note
    # and 31 of 41 windows still tie, because they all sit inside the music.
    # What is true in every case that reaches here is that the window is the
    # earliest of several that scored the same.
    tie_share = tied / candidates
    long_enough = audio.frames >= _MIN_SOURCE_MULTIPLE * wanted
    policy = ("activity_tie"
              if tie_share > _TIE_SHARE_WORTH_REPORTING and long_enough
              else "most_continuously_active")
    return Selection(start, start + wanted, policy, fraction, tied, candidates)
