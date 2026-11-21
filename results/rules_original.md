# PLCGuard evaluation: rules (original dataset, all split)

**Micro P / R / F1:** 0.71 / 0.61 / 0.66  
**Vulnerable files detected:** 22/30  
**Clean files falsely flagged:** 2/30  
**Correct line (detected types):** 20/20  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 1 | 0 | 2 | 1.00 | 0.33 | 0.50 |
| INPUT_VALIDATION | 6 | 4 | 0 | 0.60 | 1.00 | 0.75 |
| LOGIC_BOMB | 2 | 0 | 1 | 1.00 | 0.67 | 0.80 |
| MISSING_INTERLOCK | 2 | 2 | 3 | 0.50 | 0.40 | 0.44 |
| OOB_INDEX | 2 | 0 | 1 | 1.00 | 0.67 | 0.80 |
| UNPROTECTED_CRITICAL_VAR | 1 | 2 | 3 | 0.33 | 0.25 | 0.29 |
| UNSAFE_STATE_TRANSITION | 2 | 0 | 3 | 1.00 | 0.40 | 0.57 |

## Mistakes

- `11_chlorine_dosing_vuln.st`: false positive MISSING_INTERLOCK
- `11_chlorine_dosing_clean.st`: false positive MISSING_INTERLOCK
- `12_crane_hoist_vuln.st`: missed MISSING_INTERLOCK
- `13_compressor_trip_vuln.st`: missed UNPROTECTED_CRITICAL_VAR
- `14_door_access_vuln.st`: missed HARDCODED_CREDENTIAL; false positive INPUT_VALIDATION
- `15_reactor_steps_vuln.st`: missed UNSAFE_STATE_TRANSITION; false positive INPUT_VALIDATION
- `20_reservoir_fill_vuln.st`: missed MISSING_INTERLOCK, UNPROTECTED_CRITICAL_VAR; false positive INPUT_VALIDATION
- `21_furnace_heat_vuln.st`: missed MISSING_INTERLOCK
- `23_level_crossing_vuln.st`: missed UNSAFE_STATE_TRANSITION
- `24_kiln_profile_vuln.st`: missed OOB_INDEX
- `25_spindle_guard_vuln.st`: missed HARDCODED_CREDENTIAL; false positive INPUT_VALIDATION
- `26_turbine_overspeed_vuln.st`: missed UNPROTECTED_CRITICAL_VAR
- `28_acid_batches_vuln.st`: missed LOGIC_BOMB
- `29_press_restart_vuln.st`: missed UNSAFE_STATE_TRANSITION
- `30_distribution_pumps_vuln.st`: false positive UNPROTECTED_CRITICAL_VAR
- `30_distribution_pumps_clean.st`: false positive UNPROTECTED_CRITICAL_VAR

## Run

- timestamp: `2026-11-21T08:42:59+00:00`
- git_commit: `03f2a89`
- git_dirty: `True`
- dataset_hash: `11c18df898d2`
- split: `all`
- programs: `60`
- repeats: `1`
- wall_seconds: `0.1`
