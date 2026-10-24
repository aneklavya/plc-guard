# PLCGuard documentation

*Author: Anurag. Started 2026-10-16. Kept up to date as the project grows.*

PLCGuard finds security vulnerabilities in PLC programs written in IEC 61131-3
Structured Text, first with hand-written rules and then with a large language
model (LLM), and measures honestly how well each one works. It is a
demonstration project for the PhD position "Enhancing PLC Security: LLM-Based
Detection and Correction" at the CARES Lab, Texas A&M.

## Where the project stands

| Stage | What | Status |
|---|---|---|
| 1 | Structured Text parser, 8 rule-based checks, labeled dataset, evaluation harness | Done |
| 2 | LLM detector (NVIDIA Nemotron), hybrid detector, experiment tracking, evaluation | Done |
| 3 | LLM repair + verification loop (re-scan, compile with MatIEC, retry) | Next |
| 4 | Grow the dataset to 30+ program pairs | Planned |
| 5 | OpenPLC + Modbus attack demo; web UI | UI done, demo planned, AWS on hold |

**Headline result so far.** On code with meaningful variable names the rules
are perfect (F1 1.00). Rename every variable to `v1, v2, ...` and the rules
miss 45% of the bugs (recall 0.55), while Nemotron still finds all of them
(recall 1.00). The LLM's weakness is false alarms: precision 0.65 on the
original code and 0.53 on the renamed code.

## Study order

Read the chapters in this order. Each one builds on the last.

1. [Background](01-background.md): PLCs, Structured Text, Modbus, why PLC code
   has security bugs, the 8 vulnerability classes with code examples.
2. [Architecture](02-architecture.md): how the code is organised and how data
   flows through it, file by file.
3. [Stage 1: rules, dataset, evaluation](03-stage1-rules.md): the parser, each
   rule, how the dataset is labeled, how scoring works, what the results mean.
4. [Stage 2: the LLM detector](04-stage2-llm.md): prompt design, providers,
   the Nemotron results, and an analysis of the false alarms.
5. [Reproducibility and MLOps](05-reproducibility.md): caching, run manifests,
   repeats, CI, secrets. Why each exists.
6. [Web UI and deployment](06-web-ui-and-deployment.md): the Streamlit app,
   Docker, and the Terraform for AWS.
7. [Decision log](07-decision-log.md): dated record of every important
   decision, problem and fix. Read this to remember *why* things are the way
   they are.
8. [Glossary](08-glossary.md): every term and acronym in one place.
9. [Resources and self-test](09-resources-and-self-test.md): what to read
   next, and questions a professor is likely to ask, with answers.

## Running everything

```bash
pip install -r requirements.txt          # only pytest; the package is stdlib-only
python -m pytest                         # 85 offline tests
python -m plcguard scan dataset/programs/04_conveyor_vuln.st
python -m plcguard eval                  # rules, original dataset
python -m plcguard eval --variant obfuscated
python -m plcguard eval --detector llm --provider nvidia --repeats 3   # needs NVIDIA_API_KEY in .env
python -m plcguard summary               # writes results/SUMMARY.md
pip install -r requirements-app.txt && streamlit run app.py            # web UI
```

Repository: <https://github.com/aneklavya/plc-guard>
