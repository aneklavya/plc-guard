# PLCGuard evaluation: rules (obfuscated dataset)

**Micro P / R / F1:** 1.00 / 0.55 / 0.71  
**Vulnerable files detected:** 6/10  
**Clean files falsely flagged:** 0/10  
**Correct line (detected types):** 6/6  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| INPUT_VALIDATION | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| LOGIC_BOMB | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| MISSING_INTERLOCK | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| OOB_INDEX | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNPROTECTED_CRITICAL_VAR | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| UNSAFE_STATE_TRANSITION | 1 | 0 | 1 | 1.00 | 0.50 | 0.67 |

## Mistakes

- `02_pump_station_vuln.st`: missed MISSING_INTERLOCK
- `03_maintenance_access_vuln.st`: missed HARDCODED_CREDENTIAL
- `04_conveyor_vuln.st`: missed MISSING_INTERLOCK
- `07_burner_sequence_vuln.st`: missed UNSAFE_STATE_TRANSITION
- `08_boiler_trip_vuln.st`: missed UNPROTECTED_CRITICAL_VAR

## Run

- timestamp: `2026-10-24T04:07:07+00:00`
- git_commit: `f90ac55`
- git_dirty: `True`
- dataset_hash: `98d73f944c19`
- repeats: `1`
- wall_seconds: `0.0`
