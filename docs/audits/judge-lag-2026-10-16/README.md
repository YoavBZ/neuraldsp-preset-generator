# judge_lag audit (2026-10-16)

The question: are the three large judge_lags wrong? They are Drag_Me_Down-ElecGtr4 966,
Today's_The_Day-ElecGtr10 672 and femme-elecgtr3 573, with +52 included. **They are right.**

- **Real session offsets:** these amp tracks sit 12–20 ms behind their DIs throughout their
  sessions. The full-session whitened GCC shows it; the catalogue and docs/validation-lags.json
  agree; and femme is already flagged `late_amp_track`.
- **The measure DI keeps the raw DI's timing,** because `eq_to` is zero-phase.
- **Some DIs sit on the recording's timeline instead:** C′'s rebuild and `flatref`. That is where a
  "−2 samples" reading comes from.
- **`aligned_distance` uses a fixed lag:**
  - ±25 samples moves d by at most 0.005;
  - "fixing" these three lags to the recording timeline would worsen them by 0.19–0.52.
- **No reported result changes.**

Scripts: `gcc.py`, `gcc2.py`, `judge_lags.py` and `session.py`. Outputs: `out-*.txt` and
`judge_lags_*.json`.
