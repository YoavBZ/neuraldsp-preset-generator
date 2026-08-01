"""Compare two offline renders band by band.

Goertzel rather than an FFT because it needs no third-party package: this has to
run on a stock Python so that a measurement can be reproduced without setting up
an environment first. Companion to scripts/au_render.swift; see
docs/measuring-against-the-plugin.md.

    python3 scripts/spectrum_diff.py off.wav on.wav
"""
import math, struct, sys

def samples(path):
    d = open(path, "rb").read()
    i = d.find(b"data")
    body = d[i+8:]
    n = len(body)//4
    v = struct.unpack("<%df" % n, body[:n*4])
    return v[::2]  # left channel of the interleaved pair

def goertzel(x, f, sr=48000.0):
    """Magnitude at one frequency, averaged over blocks to smooth noise."""
    N = 4096
    total, blocks = 0.0, 0
    k = int(0.5 + N * f / sr)
    actual = k * sr / N          # the bin actually measured, not the one asked for
    w = 2.0 * math.pi * k / N
    coeff = 2.0 * math.cos(w)
    for start in range(0, len(x) - N + 1, N):
        s1 = s2 = 0.0
        for i in range(start, start + N):
            s0 = x[i] + coeff * s1 - s2
            s2, s1 = s1, s0
        power = s1*s1 + s2*s2 - coeff*s1*s2
        total += power
        blocks += 1
    return (math.sqrt(total / blocks) if blocks else 0.0), actual

BLOCK = 4096   # the Goertzel window, and therefore the analysis grid


def nearest_bin(f, sr=48000.0, n=BLOCK):
    """The closest frequency that lands exactly on a Goertzel bin centre."""
    return round(n * f / sr) * sr / n


def harmonics(path, fundamental, count=8, sr=48000.0):
    """Harmonic distortion of one render, as a percentage.

    "Break-up" is not a shape in the spectrum, it is the amp generating
    harmonics that were not in the input. Feed a sine, measure the energy at
    2f, 3f, ... against the energy at f, and the number rises as the amp starts
    to clip. Absolute values depend on the input level, so only compare runs
    made at the same level.
    """
    # THE FUNDAMENTAL MUST LAND ON A BIN CENTRE. Off-centre, the fundamental
    # leaks into the harmonic bins and the result is dominated by that leakage:
    # a mathematically pure sine at 220 Hz reads 1.606% here, amplitude
    # independent, which is exactly the size of the "clean" readings this was
    # first used to publish. On a bin centre it reads 0.000%, and because a
    # harmonic of a bin-centred tone is itself bin-centred, every harmonic is
    # clean too. Refuse rather than silently returning noise.
    exact = nearest_bin(fundamental, sr)
    if abs(fundamental - exact) > 1e-9:
        raise ValueError(
            f"{fundamental} Hz is not on a analysis bin centre (bin width "
            f"{sr / BLOCK:.5f} Hz), so its own leakage would be reported as "
            f"distortion.\n  Use {exact:.5f} Hz — and render the test tone at "
            f"that frequency too, not just analyse at it."
        )
    x = samples(path)
    fund, _ = goertzel(x, fundamental, sr)
    if fund <= 0:
        return 0.0
    power = 0.0
    for n in range(2, count + 1):
        f = fundamental * n
        if f >= sr / 2:
            break
        mag, _ = goertzel(x, f, sr)
        power += mag * mag
    return 100.0 * math.sqrt(power) / fund


def thd_report():
    """python3 scripts/spectrum_diff.py --thd 220 a.wav b.wav ..."""
    freq = float(sys.argv[2])
    print(f"analysing at {freq:.5f} Hz\n")
    print(f"{'file':<28} {'THD %':>8}")
    for path in sys.argv[3:]:
        print(f"{path.split('/')[-1]:<28} {harmonics(path, freq):>8.2f}")


def compare_report():
    a, b = samples(sys.argv[1]), samples(sys.argv[2])
    print(f"{sys.argv[1]}: peak {max(abs(v) for v in a):.5f}   "
          f"{sys.argv[2]}: peak {max(abs(v) for v in b):.5f}\n")
    print(f"{'bin Hz':>8}  {'OFF dB':>9} {'ON dB':>9} {'ON-OFF':>9}")
    for f in (60, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300):
        (ma, actual), (mb, _) = goertzel(a, f), goertzel(b, f)
        da = 20*math.log10(ma) if ma > 0 else -999
        db_ = 20*math.log10(mb) if mb > 0 else -999
        print(f"{actual:>7.0f}   {da:>8.2f}  {db_:>8.2f}  {db_-da:>+8.2f}")
    
    


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--thd":
        thd_report()
    else:
        compare_report()
