# Independent declared timing-control verification

**VERIFY with evidence limits. Scientific disposition: FAIL.**

Declaration revision: `3ae99769948cf6a09fc7f32ed8f472b4717d5905`.
All 156 cases were independently derived and persisted in verification JSON before any primary numerical result/progress/input/provenance read. The report retains the derivation digest, precomparison report digest and timestamps. No project numerical functions were imported or called. Only the `di` member of the twelve fixed original prepare NPZs was loaded.

856 checks passed; zero failed. Complete recursive comparison covered all construction and transformed-six-second/prefix hashes, estimates, Pearson correlation and denominator, predicates, actual/derived Calibration fields, first rejection order/messages, truth diagnostics, coverage, counts, accepted mistakes and disposition. Maximum case-field float difference was 3.552713678800501e-14, below the fixed absolute 1e-8 tolerance. Identities, hashes, booleans, integer lags, signs and errors matched exactly. Progress equals result exactly; captured stdout equals progress bytes.

## Scientific result

| Arm | Accepted | Rejected |
|---|---:|---:|
| Identity | 36 | 0 |
| Polarity | 36 | 0 |
| Lowpass | 30 | 6 |
| Tanh | 16 | 20 |
| Mismatch | 0 | 12 |

All 72 required identity/polarity cases were accepted correctly within one sample and with correct polarity. All twelve mismatch negatives were rejected. Every rejection first failed the sharpness requirement. Lowpass/tanh rejections are diagnostic and do not themselves fail the declared gate.

**Seven wrong accepted positives fail the gate.** All are tanh scale cases, arising from three distinct source performances. Signed error means estimated lag minus imposed truth. Six errors are +3 samples and one is +2 samples; absolute and signed ranges are 2–3 and +2–+3 samples, respectively. All seven have correct polarity.

| Source performance | Arm | Imposed shifts (samples) | Signed errors (samples) | Cases |
|---|---|---|---|---:|
| p2-scales-bb-t076 (Bb) | tanh | -128, 0, +128 | +3, +3, +3 | 3 |
| p2-scales-c-t075 (C) | tanh | -128 | +2 | 1 |
| p2-scales-db-t076 (Db) | tanh | -128, 0, +128 | +3, +3, +3 | 3 |

These are seven dependent transform/shift effects on three reused performances. The complete study contains 156 dependent constructed cases from twelve original takes, one player/guitar; it does not contain 156 independent recordings. These counts do not establish a general failure rate across recordings.

## Provenance and stability

The exact 35 inherited plus eight own source/declaration/prerequisite pins matched committed bytes, inherited verification and primary provenance. Original preparation had complete ordered valid coverage and inherited primary oracles below 1e-6. Its saved report matched the archive byte for byte. The existing 36-entry artifact manifest was checked for exact identities; only its twelve prepare NPZs were hashed. All twelve hashes passed before the first load and immediately before each load.

Source, prerequisite, twelve input NPZ and primary evidence hashes were unchanged before/after verification. Python, actual project `.venv` prefix and NumPy/SciPy versions matched the primary helper environment. Commit timestamp 1791475831 preceded primary recorded start 1791475842.537737; recorded elapsed time was 10.783835042268038 seconds within the cooperative 900-second budget. Saved file times were consistent with completion before verification. HEAD remained the declaration revision. This verifier made no Git changes; main's existing archival/navigation edits remained present.

Verifier source SHA256: `f8d9f3764c343891ab9f3a81af69f59077dd3e0e32c0ab2ce5485595e38674ec`.
Verification JSON SHA256: `3b9019877a7f9d1314a8af1a69e7a29b8cba090eb98d118bed0b587e928437d0`.

## Evidence limits

- Positive catalog priors equal imposed truth; this is an optimistic constructed-pair control and does not validate native priors.
- Actual P was not rerun. Its saved composition evidence agrees with the independently derived decisions and fields.
- Installed NumPy/SciPy numerical libraries are shared; project construction, transform, GCC, bandpass, diagnosis, calibration and comparison functions were not called.
- Original preparation QC/oracles are inherited verified evidence, not recomputed here.
- Commit-before-first-access relies on main's attestation and the frozen guard/source, supported by revision and timing evidence. No access audit independently proves first access.
- Saved timing documents a cooperative budget; it does not prove hard interruption of a stuck library call.
- There is no scored interval, threshold tuning, native or model transfer inference, or product claim. The inherited native failure remains closed. Earlier experiments retain their original scientific dispositions.

Writes were limited to the named verifier source, verification JSON and this Markdown report. No additional CPU job/agent, plugin, raw/native audio access, model, rendering, inference, training or network was used. Main owns archival, navigation, commits and next steps.

Pedroza et al., Guitar-TECHS, CC BY 4.0, https://zenodo.org/records/14963133.
