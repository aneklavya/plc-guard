# PLCGuard

LLM-assisted detection and repair of security vulnerabilities in PLC code
(IEC 61131-3 Structured Text).

```
ST code ──► rule-based checker ──┐
        └─► LLM detector ────────┼─► findings ─► LLM repair ─► verify ─► patched ST
                                 │                                │
                                 └──────────── retry ◄────────────┘
```

**Full documentation, written to study from: [docs/](docs/README.md).**

## Roadmap

- [x] **Stage 1: Foundations.** ST parser, rule-based checker (8 vulnerability
  classes), labeled benchmark (10 vulnerable/clean pairs), evaluation harness,
  obfuscated-variant robustness test.
- [x] **Stage 2: LLM detector.** Zero-shot structured-JSON prompt, NVIDIA
  Nemotron 3 Ultra (free API; Gemini and OpenRouter also supported), hybrid
  rules+LLM, 3-repeat comparison on both dataset variants, experiment tracking.
- [ ] **Stage 3: LLM repair + verification loop.** Patch generation, re-scan,
  compile check (OpenPLC/MatIEC), retry.
- [ ] **Stage 4: Grow the dataset** to 30+ pairs.
- [ ] **Stage 5: Live demo.** OpenPLC runtime + Modbus attack before/after the
  fix. (Streamlit UI already built, see below.)

## Quick start

```bash
pip install -r requirements.txt
python -m pytest                                   # 85 tests, offline
python -m plcguard scan dataset/programs/04_conveyor_vuln.st
python -m plcguard eval                            # original dataset
python -m plcguard eval --variant obfuscated       # variables renamed v1, v2, ...
```

LLM detector (Stage 2). Put a key in `.env` (see `.env.example`), then:

```bash
python -m plcguard eval --detector llm                          # Gemini (default)
python -m plcguard eval --detector hybrid --variant obfuscated  # rules ∪ LLM
python -m plcguard eval --detector llm --provider openrouter --model <id>
python -m plcguard eval --detector llm --provider nvidia         # free Nemotron (build.nvidia.com)
python -m plcguard models --filter nemotron                      # list NVIDIA model ids
```

The model sees only the numbered program text: no file name, no labels, no
examples from the dataset (zero-shot, temperature 0).

## Web UI

```bash
pip install -r requirements-app.txt
streamlit run app.py                      # http://localhost:8501
```

Scan an example program or your own code with the rules, Nemotron, or both,
optionally with variables renamed, and browse the evaluation results. Example
programs use the cached LLM replies (no API calls). Pasted code calls the
NVIDIA API with the visitor's own key, or with the server's `NVIDIA_API_KEY`,
capped at `PLCGUARD_SESSION_LIMIT` scans per session (default 5) and
`PLCGUARD_DAILY_LIMIT` per day (default 200). Code is analysed, never run.

Docker: `docker build -t plcguard . && docker run -p 8501:8501 --env-file .env plcguard`

AWS (one free-tier EC2 instance, nothing applied yet): see `infra/terraform/`.

```bash
aws ssm put-parameter --name /plcguard/nvidia_api_key --type SecureString --value nvapi-...
cd infra/terraform && terraform init && terraform apply   # prints the URL
terraform destroy                                         # when done
```

## Reproducibility

- **Cached replies.** Every LLM reply is stored in `results/llm_cache/`
  (keyed by provider, model, temperature, prompt and repeat index) and
  committed, so anyone can re-run an evaluation and get the same numbers
  without an API key. `--no-cache` forces fresh calls.
- **Run manifests.** Each report ends with a *Run* section: git commit (and
  whether the tree was dirty), dataset hash, model, temperature, prompt version
  and prompt hash, API calls and cache hits.
- **Experiment log.** Every `eval` appends one line to `results/runs.jsonl`
  (append-only). `python -m plcguard summary` turns the latest run per
  configuration into `results/SUMMARY.md`.
- **Repeats.** `--repeats N` runs the LLM N times and reports mean ± std.
  With 10 vulnerable files, one answer moves recall by 0.1, so single runs
  are not quoted as results.
- **Pinned models.** Versioned model ids only, never `-latest` aliases.
- **Secrets.** Keys live in `.env` (gitignored). `tests/test_secrets.py`
  fails if a key-like string appears in any file git would commit.
- **CI.** `.github/workflows/tests.yml` runs the offline test suite on
  Python 3.11 and 3.13.

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

## Stage 2 results (LLM detector)

Nemotron 3 Ultra, zero-shot, temperature 0, mean ± std of 3 runs:

| Detector | Dataset | Precision | Recall | F1 | Clean files flagged |
|---|---|---|---|---|---|
| Rules | Original | 1.00 | 1.00 | 1.00 | 0/10 |
| Rules | Obfuscated | 1.00 | 0.55 | 0.71 | 0/10 |
| LLM | Original | 0.65 ± 0.07 | 1.00 | 0.79 ± 0.05 | 3.3/10 |
| LLM | Obfuscated | 0.53 ± 0.06 | 1.00 | 0.69 ± 0.05 | 4.7/10 |

The LLM keeps full recall when names are removed, so it is not relying on
them to find bugs. Its weakness is false alarms, which get worse without
names; some of them look like real issues the labels miss. The hybrid
(rules ∪ LLM) equals the LLM alone. Analysis: [docs/04-stage2-llm.md](docs/04-stage2-llm.md).

## Layout

```
plcguard/
  st_parser.py   tokenizer + parser: POUs, VAR/AT declarations, IF/CASE/loops,
                 enclosing-condition contexts for every expression
  rules.py       8 static rules
  taxonomy.py    vulnerability classes, CWE mapping, Finding record
  llm.py         Gemini / OpenRouter / NVIDIA client: disk cache, retry with backoff
  llm_detector.py  prompt, JSON reply parsing, LLM and hybrid detectors
  tracking.py    run manifests, results/runs.jsonl, SUMMARY.md
  evaluate.py    per-type P/R/F1, file-level and line-level scoring
  obfuscate.py   semantics-preserving variable renaming
dataset/         labeled .st programs (see dataset/README.md)
results/         evaluation reports (.md + .json), runs.jsonl, SUMMARY.md, llm_cache/
docs/            study documentation
app.py           Streamlit web UI
infra/terraform/ AWS EC2 deployment (not applied)
tests/
```
