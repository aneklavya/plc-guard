# PLCGuard evaluation: hybrid_nvidia-nemotron-3-ultra-550b-a55b (obfuscated dataset)

**Micro P / R / F1:** 0.58 / 1.00 / 0.73  
**Vulnerable files detected:** 10/10  
**Clean files falsely flagged:** 3/10  
**Correct line (detected types):** 11/11  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| INPUT_VALIDATION | 2 | 2 | 0 | 0.50 | 1.00 | 0.67 |
| LOGIC_BOMB | 1 | 1 | 0 | 0.50 | 1.00 | 0.67 |
| MISSING_INTERLOCK | 2 | 4 | 0 | 0.33 | 1.00 | 0.50 |
| OOB_INDEX | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNPROTECTED_CRITICAL_VAR | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNSAFE_STATE_TRANSITION | 2 | 1 | 0 | 0.67 | 1.00 | 0.80 |

## Mistakes

- `03_maintenance_access_vuln.st`: false positive INPUT_VALIDATION, MISSING_INTERLOCK
- `04_conveyor_clean.st`: false positive LOGIC_BOMB
- `07_burner_sequence_vuln.st`: false positive MISSING_INTERLOCK
- `07_burner_sequence_clean.st`: false positive MISSING_INTERLOCK
- `08_boiler_trip_vuln.st`: false positive INPUT_VALIDATION, MISSING_INTERLOCK
- `10_traffic_light_clean.st`: false positive UNSAFE_STATE_TRANSITION

## Run

Tables above are repeat 1 of 3. Across repeats: F1 0.69 ± 0.05, recall 1.00 ± 0.00, precision 0.53 ± 0.06.

- timestamp: `2026-10-24T04:06:42+00:00`
- git_commit: `f90ac55`
- git_dirty: `True`
- dataset_hash: `98d73f944c19`
- provider: `nvidia`
- model: `nvidia/nemotron-3-ultra-550b-a55b`
- temperature: `0.0`
- prompt_version: `v1`
- prompt_hash: `aa71ce447ba6`
- repeats: `3`
- llm_calls: `0`
- cache_hits: `60`
- wall_seconds: `0.1`
