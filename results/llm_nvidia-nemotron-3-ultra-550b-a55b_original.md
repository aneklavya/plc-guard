# PLCGuard evaluation: llm_nvidia-nemotron-3-ultra-550b-a55b (original dataset, all split)

**Micro P / R / F1:** 0.60 / 0.97 / 0.74  
**Vulnerable files detected:** 30/30  
**Clean files falsely flagged:** 5/30  
**Correct line (detected types):** 32/32  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| INPUT_VALIDATION | 6 | 6 | 0 | 0.50 | 1.00 | 0.67 |
| LOGIC_BOMB | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| MISSING_INTERLOCK | 4 | 11 | 1 | 0.27 | 0.80 | 0.40 |
| OOB_INDEX | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNPROTECTED_CRITICAL_VAR | 4 | 3 | 0 | 0.57 | 1.00 | 0.73 |
| UNSAFE_STATE_TRANSITION | 5 | 1 | 0 | 0.83 | 1.00 | 0.91 |

## Mistakes

- `03_maintenance_access_vuln.st`: false positive MISSING_INTERLOCK, UNPROTECTED_CRITICAL_VAR
- `04_conveyor_vuln.st`: missed MISSING_INTERLOCK
- `05_recipe_batch_vuln.st`: false positive INPUT_VALIDATION
- `06_flow_ratio_clean.st`: false positive MISSING_INTERLOCK
- `10_traffic_light_clean.st`: false positive UNSAFE_STATE_TRANSITION
- `13_compressor_trip_vuln.st`: false positive INPUT_VALIDATION
- `14_door_access_vuln.st`: false positive INPUT_VALIDATION, MISSING_INTERLOCK
- `14_door_access_clean.st`: false positive MISSING_INTERLOCK
- `15_reactor_steps_vuln.st`: false positive INPUT_VALIDATION
- `19_mixer_ramp_vuln.st`: false positive MISSING_INTERLOCK, UNPROTECTED_CRITICAL_VAR
- `20_reservoir_fill_vuln.st`: false positive INPUT_VALIDATION
- `23_level_crossing_clean.st`: false positive MISSING_INTERLOCK
- `24_kiln_profile_vuln.st`: false positive INPUT_VALIDATION
- `25_spindle_guard_vuln.st`: false positive MISSING_INTERLOCK
- `26_turbine_overspeed_vuln.st`: false positive MISSING_INTERLOCK
- `27_chiller_valve_vuln.st`: false positive MISSING_INTERLOCK, UNPROTECTED_CRITICAL_VAR
- `28_acid_batches_vuln.st`: false positive MISSING_INTERLOCK
- `28_acid_batches_clean.st`: false positive MISSING_INTERLOCK

## Run

Tables above are repeat 1 of 3. Across repeats: F1 0.74 ± 0.05, recall 0.97 ± 0.00, precision 0.60 ± 0.06.

- timestamp: `2026-11-21T09:02:27+00:00`
- git_commit: `2b30acf`
- git_dirty: `True`
- dataset_hash: `11c18df898d2`
- split: `all`
- programs: `60`
- provider: `nvidia`
- model: `nvidia/nemotron-3-ultra-550b-a55b`
- temperature: `0.0`
- prompt_version: `v1`
- prompt_hash: `aa71ce447ba6`
- repeats: `3`
- llm_calls: `160`
- cache_hits: `20`
- wall_seconds: `1111.5`
