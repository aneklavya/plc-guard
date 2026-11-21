# PLCGuard results summary

Latest run per configuration, generated from `results/runs.jsonl` by `python -m plcguard summary`. Mean ± std over repeated runs. Dataset `11c18df898d2` only.

| Detector | Model | Prompt | Variant | Split | Runs | Precision | Recall | F1 | Clean flagged | Errors | Commit | Dataset |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rules | - | - | obfuscated | all | 1 | 0.79 | 0.45 | 0.58 | 0.0/30 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| llm | nvidia/nemotron-3-ultra-550b-a55b | v1 | original | all | 3 | 0.60 ± 0.06 | 0.97 | 0.74 ± 0.05 | 6.7 ± 2.1/30 | 0.0 | 2b30acf+dirty | 11c18df898d2 |
| rules | - | - | original | all | 1 | 0.71 | 0.61 | 0.66 | 2.0/30 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| rules | - | - | obfuscated | dev | 1 | 1.00 | 0.55 | 0.71 | 0.0/10 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| llm | nvidia/nemotron-3-ultra-550b-a55b | v1 | original | dev | 3 | 0.71 ± 0.12 | 0.97 ± 0.05 | 0.81 ± 0.09 | 2.3 ± 0.6/10 | 0.0 | 2b30acf+dirty | 11c18df898d2 |
| rules | - | - | original | dev | 1 | 1.00 | 1.00 | 1.00 | 0.0/10 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| rules | - | - | obfuscated | heldout | 1 | 0.69 | 0.41 | 0.51 | 0.0/20 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| llm | nvidia/nemotron-3-ultra-550b-a55b | v1 | original | heldout | 3 | 0.55 ± 0.05 | 0.97 ± 0.03 | 0.70 ± 0.04 | 4.3 ± 1.5/20 | 0.0 | 2b30acf+dirty | 11c18df898d2 |
| rules | - | - | original | heldout | 1 | 0.53 | 0.41 | 0.46 | 2.0/20 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
