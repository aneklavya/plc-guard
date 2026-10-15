# PLCGuard benchmark dataset

Paired IEC 61131-3 Structured Text programs: each scenario has a `_vuln.st`
version with one or more labeled vulnerabilities and a `_clean.st` version
that fixes them while keeping the same control behaviour.

## Labels

`labels.json` lists every program with its vulnerability types. Each
vulnerability is located by a `snippet`, a piece of text that matches exactly
one line of the file, rather than a hard-coded line number, so editing a
program doesn't silently break its labels (`tests/test_dataset.py` enforces
this).

## Address conventions (OpenPLC)

| Location | Meaning | Treated as |
|---|---|---|
| `%IX`, `%IW` | physical digital / analog inputs | sensor data |
| `%QX` | digital outputs (coils); `%QX1.x` used for HMI command bits | actuators / commands |
| `%QW` | analog outputs | actuator setpoints |
| `%MW`, `%MD`, `%ML` | memory = Modbus holding registers | **network-writable, untrusted** |

## Vulnerability classes

| Type | CWE | Example in dataset |
|---|---|---|
| INPUT_VALIDATION | CWE-20 | 01, 09 |
| MISSING_INTERLOCK | CWE-693 | 02, 04 |
| HARDCODED_CREDENTIAL | CWE-798 | 03 |
| LOGIC_BOMB | CWE-511 | 04 |
| OOB_INDEX | CWE-129 | 05 |
| DIV_BY_ZERO | CWE-369 | 06 |
| UNSAFE_STATE_TRANSITION | CWE-1245 | 07, 10 |
| UNPROTECTED_CRITICAL_VAR | CWE-284 | 08 |

## Variants

`python -m plcguard eval --variant obfuscated` renames every variable to
`v1, v2, ...` (same logic, same addresses) to measure how much a detector
relies on naming.
