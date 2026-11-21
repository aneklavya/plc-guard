# PLCGuard evaluation: rules (obfuscated dataset, all split)

**Micro P / R / F1:** 0.79 / 0.45 / 0.58  
**Vulnerable files detected:** 18/30  
**Clean files falsely flagged:** 0/30  
**Correct line (detected types):** 15/15  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 0 | 0 | 3 | 0.00 | 0.00 | 0.00 |
| INPUT_VALIDATION | 6 | 4 | 0 | 0.60 | 1.00 | 0.75 |
| LOGIC_BOMB | 2 | 0 | 1 | 1.00 | 0.67 | 0.80 |
| MISSING_INTERLOCK | 0 | 0 | 5 | 0.00 | 0.00 | 0.00 |
| OOB_INDEX | 2 | 0 | 1 | 1.00 | 0.67 | 0.80 |
| UNPROTECTED_CRITICAL_VAR | 0 | 0 | 4 | 0.00 | 0.00 | 0.00 |
| UNSAFE_STATE_TRANSITION | 1 | 0 | 4 | 1.00 | 0.20 | 0.33 |

## Mistakes

- `02_pump_station_vuln.st`: missed MISSING_INTERLOCK
- `03_maintenance_access_vuln.st`: missed HARDCODED_CREDENTIAL
- `04_conveyor_vuln.st`: missed MISSING_INTERLOCK
- `07_burner_sequence_vuln.st`: missed UNSAFE_STATE_TRANSITION
- `08_boiler_trip_vuln.st`: missed UNPROTECTED_CRITICAL_VAR
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

- timestamp: `2026-11-21T08:42:59+00:00`
- git_commit: `03f2a89`
- git_dirty: `True`
- dataset_hash: `11c18df898d2`
- split: `all`
- programs: `60`
- repeats: `1`
- wall_seconds: `0.1`
