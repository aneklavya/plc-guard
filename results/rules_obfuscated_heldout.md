# PLCGuard evaluation: rules (obfuscated dataset, heldout split)

**Micro P / R / F1:** 0.69 / 0.41 / 0.51  
**Vulnerable files detected:** 12/20  
**Clean files falsely flagged:** 0/20  
**Correct line (detected types):** 9/9  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| INPUT_VALIDATION | 4 | 4 | 0 | 0.50 | 1.00 | 0.67 |
| LOGIC_BOMB | 1 | 0 | 1 | 1.00 | 0.50 | 0.67 |
| MISSING_INTERLOCK | 0 | 0 | 3 | 0.00 | 0.00 | 0.00 |
| OOB_INDEX | 1 | 0 | 1 | 1.00 | 0.50 | 0.67 |
| UNPROTECTED_CRITICAL_VAR | 0 | 0 | 3 | 0.00 | 0.00 | 0.00 |
| UNSAFE_STATE_TRANSITION | 0 | 0 | 3 | 0.00 | 0.00 | 0.00 |

## Mistakes

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

## Run

- timestamp: `2026-11-21T08:43:00+00:00`
- git_commit: `03f2a89`
- git_dirty: `True`
- dataset_hash: `11c18df898d2`
- split: `heldout`
- programs: `40`
- repeats: `1`
- wall_seconds: `0.1`
