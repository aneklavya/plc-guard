# PLCGuard evaluation: llm_nvidia-nemotron-3-ultra-550b-a55b (original dataset, dev split)

**Micro P / R / F1:** 0.67 / 0.91 / 0.77  
**Vulnerable files detected:** 10/10  
**Clean files falsely flagged:** 2/10  
**Correct line (detected types):** 10/10  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| INPUT_VALIDATION | 2 | 1 | 0 | 0.67 | 1.00 | 0.80 |
| LOGIC_BOMB | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| MISSING_INTERLOCK | 1 | 2 | 1 | 0.33 | 0.50 | 0.40 |
| OOB_INDEX | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNPROTECTED_CRITICAL_VAR | 1 | 1 | 0 | 0.50 | 1.00 | 0.67 |
| UNSAFE_STATE_TRANSITION | 2 | 1 | 0 | 0.67 | 1.00 | 0.80 |

## Mistakes

- `03_maintenance_access_vuln.st`: false positive MISSING_INTERLOCK, UNPROTECTED_CRITICAL_VAR
- `04_conveyor_vuln.st`: missed MISSING_INTERLOCK
- `05_recipe_batch_vuln.st`: false positive INPUT_VALIDATION
- `06_flow_ratio_clean.st`: false positive MISSING_INTERLOCK
- `10_traffic_light_clean.st`: false positive UNSAFE_STATE_TRANSITION

## Run

Tables above are repeat 1 of 3. Across repeats: F1 0.81 ± 0.09, recall 0.97 ± 0.05, precision 0.71 ± 0.12.

- timestamp: `2026-11-21T09:02:27+00:00`
- git_commit: `2b30acf`
- git_dirty: `True`
- dataset_hash: `11c18df898d2`
- split: `dev`
- programs: `20`
- provider: `nvidia`
- model: `nvidia/nemotron-3-ultra-550b-a55b`
- temperature: `0.0`
- prompt_version: `v1`
- prompt_hash: `aa71ce447ba6`
- repeats: `3`
- llm_calls: `160`
- cache_hits: `20`
- wall_seconds: `1111.5`
