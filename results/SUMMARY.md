# PLCGuard results summary

Latest run per configuration, generated from `results/runs.jsonl` by `python -m plcguard summary`. Mean ± std over repeated runs.

| Detector | Model | Variant | Runs | Precision | Recall | F1 | Clean flagged | Errors | Commit | Dataset |
|---|---|---|---|---|---|---|---|---|---|---|
| hybrid | nvidia/nemotron-3-ultra-550b-a55b | obfuscated | 3 | 0.53 ± 0.06 | 1.00 | 0.69 ± 0.05 | 4.7 ± 1.5/10 | 0.0 | f90ac55+dirty | 98d73f944c19 |
| llm | nvidia/nemotron-3-ultra-550b-a55b | obfuscated | 3 | 0.53 ± 0.06 | 1.00 | 0.69 ± 0.05 | 4.7 ± 1.5/10 | 0.0 | f90ac55+dirty | 98d73f944c19 |
| rules | - | obfuscated | 1 | 1.00 | 0.55 | 0.71 | 0.0/10 | 0.0 | f90ac55+dirty | 98d73f944c19 |
| hybrid | nvidia/nemotron-3-ultra-550b-a55b | original | 3 | 0.65 ± 0.07 | 1.00 | 0.79 ± 0.05 | 3.3 ± 0.6/10 | 0.0 | f90ac55+dirty | 98d73f944c19 |
| llm | nvidia/nemotron-3-ultra-550b-a55b | original | 3 | 0.65 ± 0.07 | 1.00 | 0.79 ± 0.05 | 3.3 ± 0.6/10 | 0.0 | f90ac55+dirty | 98d73f944c19 |
| rules | - | original | 1 | 1.00 | 1.00 | 1.00 | 0.0/10 | 0.0 | f90ac55+dirty | 98d73f944c19 |
