# PLCGuard

LLM-assisted detection and repair of security vulnerabilities in PLC code
(IEC 61131-3 Structured Text).

```
ST code ──► rule-based checker ──┐
        └─► LLM detector ────────┼─► findings ─► LLM repair ─► verify ─► patched ST
                                 │                                │
                                 └──────────── retry ◄────────────┘
```

## Roadmap

- [x] **Stage 1: Foundations.** ST parser, rule-based checker (8 vulnerability
  classes), labeled benchmark (10 vulnerable/clean pairs), evaluation harness,
  obfuscated-variant robustness test.
- [ ] **Stage 2: LLM detector.** Structured-JSON prompts, API model + local
  open model (PyTorch/HuggingFace), hybrid rules+LLM, comparison on both
  dataset variants.
- [ ] **Stage 3: LLM repair + verification loop.** Patch generation, re-scan,
  compile check (OpenPLC/MatIEC), retry.
- [ ] **Stage 4: Grow the dataset** to 30+ pairs.
- [ ] **Stage 5: Live demo.** OpenPLC runtime + Modbus attack before/after the
  fix, Streamlit UI.

## Quick start

```bash
pip install -r requirements.txt
python -m pytest                                   # 60 tests
python -m plcguard scan dataset/programs/04_conveyor_vuln.st
python -m plcguard eval                            # original dataset
python -m plcguard eval --variant obfuscated       # variables renamed v1, v2, ...
```

## Stage 1 results (rule-based checker)

| Dataset | Precision | Recall | F1 | Clean files falsely flagged |
|---|---|---|---|---|
| Original | 1.00 | 1.00 | 1.00 | 0/10 |
| Obfuscated (variables renamed) | 1.00 | 0.55 | 0.71 | 0/10 |

The perfect score on the original set is not the finding, because the rules
and the dataset were written together. The finding is the drop on the
obfuscated set. Rules that track **data flow** (input validation, array
indices, division, logic bombs) survive renaming. Rules that rely on
**variable names** to know what is a pump, an e-stop, a password or a trip
point (interlock, credential, critical variable, state bypass) fail
completely. Understanding what a variable *means* in the physical process is
the gap an LLM is meant to close, and Stage 2 measures whether it does.

## Layout

```
plcguard/
  st_parser.py   tokenizer + parser: POUs, VAR/AT declarations, IF/CASE/loops,
                 enclosing-condition contexts for every expression
  rules.py       8 static rules
  taxonomy.py    vulnerability classes, CWE mapping, Finding record
  evaluate.py    per-type P/R/F1, file-level and line-level scoring
  obfuscate.py   semantics-preserving variable renaming
dataset/         labeled .st programs (see dataset/README.md)
results/         evaluation reports (.md + .json)
tests/
```
