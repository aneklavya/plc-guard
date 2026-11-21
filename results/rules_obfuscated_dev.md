# PLCGuard evaluation: rules (obfuscated dataset, dev split)

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

- timestamp: `2026-11-21T08:43:00+00:00`
- git_commit: `03f2a89`
- git_dirty: `True`
- dataset_hash: `11c18df898d2`
- split: `dev`
- programs: `20`
- repeats: `1`
- wall_seconds: `0.1`
