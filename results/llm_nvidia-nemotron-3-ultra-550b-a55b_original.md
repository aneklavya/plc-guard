# PLCGuard evaluation: llm_nvidia-nemotron-3-ultra-550b-a55b (original dataset)

**Micro P / R / F1:** 0.61 / 1.00 / 0.76  
**Vulnerable files detected:** 10/10  
**Clean files falsely flagged:** 4/10  
**Correct line (detected types):** 11/11  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| INPUT_VALIDATION | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| LOGIC_BOMB | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| MISSING_INTERLOCK | 2 | 4 | 0 | 0.33 | 1.00 | 0.50 |
| OOB_INDEX | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNPROTECTED_CRITICAL_VAR | 1 | 1 | 0 | 0.50 | 1.00 | 0.67 |
| UNSAFE_STATE_TRANSITION | 2 | 2 | 0 | 0.50 | 1.00 | 0.67 |

## Mistakes

- `03_maintenance_access_vuln.st`: false positive MISSING_INTERLOCK, UNPROTECTED_CRITICAL_VAR
- `06_flow_ratio_vuln.st`: false positive MISSING_INTERLOCK
- `06_flow_ratio_clean.st`: false positive MISSING_INTERLOCK
- `07_burner_sequence_clean.st`: false positive MISSING_INTERLOCK
- `08_boiler_trip_clean.st`: false positive UNSAFE_STATE_TRANSITION
- `10_traffic_light_clean.st`: false positive UNSAFE_STATE_TRANSITION

## Run

Tables above are repeat 1 of 3. Across repeats: F1 0.79 ± 0.05, recall 1.00 ± 0.00, precision 0.65 ± 0.07.

- timestamp: `2026-10-24T03:32:24+00:00`
- git_commit: `f90ac55`
- git_dirty: `True`
- dataset_hash: `98d73f944c19`
- provider: `nvidia`
- model: `nvidia/nemotron-3-ultra-550b-a55b`
- temperature: `0.0`
- prompt_version: `v1`
- prompt_hash: `aa71ce447ba6`
- repeats: `3`
- llm_calls: `61`
- cache_hits: `1`
- wall_seconds: `1864.7`
