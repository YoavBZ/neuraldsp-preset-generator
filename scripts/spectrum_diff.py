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
    w = 2.0 * math.pi * k / N
    coeff = 2.0 * math.cos(w)
    for start in range(0, len(x) - N, N):
        s1 = s2 = 0.0
        for i in range(start, start + N):
            s0 = x[i] + coeff * s1 - s2
            s2, s1 = s1, s0
        power = s1*s1 + s2*s2 - coeff*s1*s2
        total += power
        blocks += 1
    return math.sqrt(total / blocks) if blocks else 0.0

a, b = samples(sys.argv[1]), samples(sys.argv[2])
print(f"{sys.argv[1]}: peak {max(abs(v) for v in a):.5f}   "
      f"{sys.argv[2]}: peak {max(abs(v) for v in b):.5f}\n")
print(f"{'freq':>8}  {'OFF dB':>9} {'ON dB':>9} {'ON-OFF':>9}")
for f in (60, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300):
    ma, mb = goertzel(a, f), goertzel(b, f)
    da = 20*math.log10(ma) if ma > 0 else -999
    db_ = 20*math.log10(mb) if mb > 0 else -999
    print(f"{f:>7}   {da:>8.2f}  {db_:>8.2f}  {db_-da:>+8.2f}")
