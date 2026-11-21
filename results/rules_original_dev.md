# PLCGuard evaluation: rules (original dataset, dev split)

**Micro P / R / F1:** 1.00 / 1.00 / 1.00  
**Vulnerable files detected:** 10/10  
**Clean files falsely flagged:** 0/10  
**Correct line (detected types):** 11/11  
**Parse errors:** 0

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| DIV_BY_ZERO | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| HARDCODED_CREDENTIAL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| INPUT_VALIDATION | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| LOGIC_BOMB | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| MISSING_INTERLOCK | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| OOB_INDEX | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNPROTECTED_CRITICAL_VAR | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNSAFE_STATE_TRANSITION | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |

## Run

- timestamp: `2026-11-21T08:42:59+00:00`
- git_commit: `03f2a89`
- git_dirty: `True`
- dataset_hash: `11c18df898d2`
- split: `dev`
- programs: `20`
- repeats: `1`
- wall_seconds: `0.1`
