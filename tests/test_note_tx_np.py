"""The note transcriber's commands, their numpy parts (`learn/note_tx.py`; `docs/note-transcriber-plan.md`): MuScriptor's
input, and two made-up windows end to end with a stub transcriber (no MuScriptor import) through the screen, the
read's shape and code, and the bridge against a made-up versions.json, with a stub note bank. Every test starts with
`pytest.importorskip("numpy")` (skipped on the light CI runner)."""
import pytest

SR = 48000


def _deps():
    np = pytest.importorskip("numpy")
    for m in ("scipy", "noisereduce", "pyloudnorm", "soundfile"):
        pytest.importorskip(m)
    return np


def _bank():
    np = _deps()
    from learn import note_rebuild as N

    def tone(midi, seconds=5.0, decay=1.5, seed=0):
        t = np.arange(int(seconds * SR)) / SR
        f0 = 440 * 2 ** ((midi - 69) / 12)
        y = sum(np.sin(2 * np.pi * h * f0 * t) / h for h in range(1, 6)) * np.exp(-t / decay)
        y = np.concatenate([np.zeros(int(0.01 * SR)), y])[:len(t)]
        return 0.3 * y / np.abs(y).max() + 1e-4 * np.random.default_rng(seed).standard_normal(len(t))
    return N.Bank(None, loader=lambda s, f: (tone(N.OPEN_STRINGS[s] + f, seed=s * 100 + f), SR))


def _window(shift):
    """A made-up window: chords of three, then single notes; Basic Pitch's events add a ghost two octaves over each
    chord's root (amplitude 0.3 against 0.7); the stub transcriber returns the true notes."""
    from learn import note_rebuild as N
    from learn import pretrain_set as PS

    truth = []
    for k, ch in enumerate([[45, 52, 57], [47, 54, 59], [43, 50, 55], [45, 52, 57]]):
        truth += [{"on": 0.6 + 1.6 * k, "off": 1.9 + 1.6 * k, "pitch": p + shift, "bends": []} for p in ch]
    truth += [{"on": 7.2 + 0.6 * k, "off": 7.7 + 0.6 * k, "pitch": p + shift, "bends": []}
              for k, p in enumerate([64, 62, 60, 59])]
    n = int(round((PS.SEC_S + PS.TRIM_S) * SR))
    di, _ = N.synthesise_redo(truth, n, _bank(), 0.0, "ring-soft", (), 0.0, None, SR, cut=True)
    di = N.at_lufs(di, N.ASSUMED_LUFS, SR)
    ev = [{"on": t["on"], "off": t["off"], "pitch": t["pitch"], "amp": 0.7, "bends": []} for t in truth]
    ev += [{"on": t["on"] + 0.01, "off": t["off"], "pitch": t["pitch"] + 24, "amp": 0.3, "bends": []}
           for t in truth[0:12:3]]
    ms = {"pre_s": 0.0, "notes": [{"on": t["on"] + 0.02, "off": t["off"], "pitch": t["pitch"],
                                   "instrument": "clean_electric_guitar"} for t in truth]}
    return truth, di, ev, ms


def test_ms_input():
    np = _deps()
    from learn import note_tx as X

    x = 0.3 * np.sin(2 * np.pi * 220 * np.arange(SR) / SR)
    y = X.ms_input(x)
    assert y.dtype == np.float32 and len(y) == 16000
    assert float(np.abs(y).max()) == pytest.approx(10 ** (-1 / 20), rel=1e-6)
    assert len(X.ms_input(np.stack([x, x], axis=1))) == 16000           # folded to mono


def test_two_made_up_windows_end_to_end():
    np = _deps()
    from learn import note_rebuild as N
    from learn import note_transcribe as T
    from learn import note_tx as X
    from learn import note_versions as NV

    bank = _bank()
    wins = {"w1": _window(0), "w2": _window(2)}
    truths = {k: w[0] for k, w in wins.items()}
    dis = {k: w[1] for k, w in wins.items()}
    known = {k: w[2] for k, w in wins.items()}
    ms = {k: w[3] for k, w in wins.items()}

    # stage a: the screen
    rows = X.list_rows(known, ms, ms, dis, truths)
    assert [r["key"] for r in rows] == ["w1", "w2"] and all(r["timing"]["tx-ms"]["notes"] == 16 for r in rows)
    bp_f = [r["figures"]["tx-bp"] for r in rows]
    assert all((f["matched"], f["ref"], f["est"]) == (16, 16, 20) for f in bp_f)
    assert all(r["figures"]["tx-vote"]["est"] == 16 and r["figures"]["tx-veto"]["est"] == 16 for r in rows)
    screen = X.summarise_screen(rows)
    d = screen["numbers"]["lists"]["diff"]["tx-vote"]["precision"]
    assert d["mean"] == pytest.approx(0.2) and screen["readings"]["tx-vote"]["lists"]["precision_raised"]
    assert screen["screen"] == "lists-go"

    # stage b: the read (the same windows standing in for the real DIs; the checks on the "development" windows)
    real = [dict(r, set="real", group="P1", kind="chords", cluster=f"P1|chords|{r['key']}") for r in rows]
    goat = []
    for k in ("w1", "w2"):
        bp, _ = T.timed_notes({"events": known[k], "pre_s": 0.0}, dis[k])
        m, _ = T.timed_notes(X.ms_events(ms[k]), dis[k])
        notes, reps = X.arm_notes(bp, m, m)
        row = X.window_row("goat", k, k, "goat", None, None, notes, reps)
        row["checks"] = X.goat_checks(notes, dis[k], bank, [t["on"] for t in truths[k]], 0.0,
                                      lambda jobs, notes=notes: [notes[a] for _, a in jobs], None)
        goat.append(row)
    ck = goat[0]["checks"]
    assert set(ck) == set(X.ALL_ARMS) and "ring-soft" not in ck["tx-ms-free"]     # tx-ms-free: notes only
    assert set(ck["tx-vote"]["ring-soft"]) == set(T.AUDIO_CHECKS) and set(ck["tx-vote"]["ring-on"]) == {
        "judge-accepts", "ring-kept"}
    read = X.summarise_read(rows, real, goat)
    assert {"numbers", "checks", "readings", "code", "flags", "recommendation", "unpaired_share"} <= set(read)
    assert read["code"] == "TXR-vote" and read["unpaired_share"] == 0.0
    assert read["checks"]["tx-vote"]["playing-covered"] >= read["checks"]["tx-bp"]["playing-covered"] - 1

    # the bridge: the stored nv-asis rebuilt first, then only the winner's versions against made-up stored distances
    bp1, _ = T.timed_notes({"events": known["w1"], "pre_s": 0.0}, dis["w1"])
    y0, _ = N.rebuild_redo("tr-di", bp1, len(dis["w1"]), bank, dis["w1"], X.DECIDING_RING, finish=None)
    stored, _, _ = NV.build_versions(dis["w1"], truths["w1"], bp1, bank, None, which=("nv-asis",))
    assert X.reproduce_refusal(stored[X.DECIDING_RING]["nv-asis"], NV.floored_logmel(dis["w1"], y0)) is None
    todo = []
    for k in ("w1", "w2"):
        bp, _ = T.timed_notes({"events": known[k], "pre_s": 0.0}, dis[k])
        m, _ = T.timed_notes(X.ms_events(ms[k]), dis[k])
        todo.append((k, dis[k], bp, m))
    built = X.bridge_builds("TXR-vote", 1.0, todo, bank, None)
    assert set(built["w1"]) == {"ring-soft", "ring-on"} and set(built["w1"]["ring-soft"]) == {"bv-asis", "bv-loud"}
    assert all(np.isfinite(v) for b in built.values() for r in b.values() for v in r.values())
    vw = [{"set": "lists", "cluster": k, "key": k, "d": {r: {"nv-hand": 3.0, "nv-asis": 4.0, "nv-loud": 9.0 + i}
                                                         for r in ("ring-soft", "ring-on")}}
          for i, k in enumerate(("w1", "w2"))]
    body = X.bridge_body(vw, built, "NV-loud", 1.0, "TXR-vote")
    assert (body["difference"]["built"], body["difference"]["stored"]) == ("bv-loud", "nv-loud")
    assert body["readings"]["lists"] in ("the winner adds", "loudness alone stays")
    assert {"bv-asis-nv-hand", "bv-asis-nv-asis", "bv-loud-nv-loud"} <= set(body["numbers"]["ring-soft"]["lists"])
    ends = X.bridge_builds("TXR-ends", None, todo[:1], bank, None, rings=(X.DECIDING_RING,))
    assert set(ends["w1"][X.DECIDING_RING]) == {"bv-ends"}
