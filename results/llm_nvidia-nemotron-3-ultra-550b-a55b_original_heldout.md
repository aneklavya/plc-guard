# PLCGuard evaluation: llm_nvidia-nemotron-3-ultra-550b-a55b (original dataset, heldout split)

**Micro P / R / F1:** 0.58 / 1.00 / 0.73  
**Vulnerable files detected:** 20/20  
**Clean files falsely flagged:** 3/20  
**Correct line (detected types):** 22/22  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| INPUT_VALIDATION | 4 | 5 | 0 | 0.44 | 1.00 | 0.62 |
| LOGIC_BOMB | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| MISSING_INTERLOCK | 3 | 9 | 0 | 0.25 | 1.00 | 0.40 |
| OOB_INDEX | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNPROTECTED_CRITICAL_VAR | 3 | 2 | 0 | 0.60 | 1.00 | 0.75 |
| UNSAFE_STATE_TRANSITION | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |

## Mistakes

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

Tables above are repeat 1 of 3. Across repeats: F1 0.70 ± 0.04, recall 0.97 ± 0.03, precision 0.55 ± 0.05.

- timestamp: `2026-11-21T09:02:27+00:00`
- git_commit: `2b30acf`
- git_dirty: `True`
- dataset_hash: `11c18df898d2`
- split: `heldout`
- programs: `40`
- provider: `nvidia`
- model: `nvidia/nemotron-3-ultra-550b-a55b`
- temperature: `0.0`
- prompt_version: `v1`
- prompt_hash: `aa71ce447ba6`
- repeats: `3`
- llm_calls: `160`
- cache_hits: `20`
- wall_seconds: `1111.5`
