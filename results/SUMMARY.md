# PLCGuard results summary

Latest run per configuration, generated from `results/runs.jsonl` by `python -m plcguard summary`. Mean ± std over repeated runs. Dataset `11c18df898d2` only.

| Detector | Model | Prompt | Variant | Split | Runs | Precision | Recall | F1 | Clean flagged | Errors | Commit | Dataset |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rules | - | - | obfuscated | all | 1 | 0.79 | 0.45 | 0.58 | 0.0/30 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| rules | - | - | original | all | 1 | 0.71 | 0.61 | 0.66 | 2.0/30 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| rules | - | - | obfuscated | dev | 1 | 1.00 | 0.55 | 0.71 | 0.0/10 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| rules | - | - | original | dev | 1 | 1.00 | 1.00 | 1.00 | 0.0/10 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| rules | - | - | obfuscated | heldout | 1 | 0.69 | 0.41 | 0.51 | 0.0/20 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
| rules | - | - | original | heldout | 1 | 0.53 | 0.41 | 0.46 | 2.0/20 | 0.0 | 03f2a89+dirty | 11c18df898d2 |
