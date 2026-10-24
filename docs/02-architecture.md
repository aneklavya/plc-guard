# 2. Architecture

## The pipeline

```
                  ┌──────────────┐
 .st program ───► │ st_parser.py │──► POUs, variables, assignments, contexts
                  └──────┬───────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
   ┌────────────┐               ┌─────────────────┐     ┌────────┐
   │  rules.py  │               │ llm_detector.py │ ──► │ llm.py │ ──► NVIDIA / Gemini / OpenRouter
   │ 8 checks   │               │ prompt + parse  │ ◄── │ cache  │
   └─────┬──────┘               └────────┬────────┘     └────────┘
         │      Finding(type, line,      │
         └──────► message, variable) ◄───┘
                         │
                         ▼
                  ┌──────────────┐     ┌──────────────┐
                  │ evaluate.py  │ ──► │ tracking.py  │ ──► results/*.md, *.json, runs.jsonl, SUMMARY.md
                  │ vs labels    │     │ manifests    │
                  └──────────────┘     └──────────────┘
```

Every detector is just a function `source_code -> list[Finding]`. That one
shared interface is what makes it easy to compare them: the evaluator does not
care whether findings came from rules, an LLM, or both.

## Files

| File | Role |
|---|---|
| `plcguard/taxonomy.py` | The 8 `VulnType`s, their descriptions and CWE ids, and the `Finding` record every detector returns. |
| `plcguard/st_parser.py` | Tokeniser and a small recursive-descent parser for ST. Not a full grammar, only what the checks need. |
| `plcguard/rules.py` | The 8 rule-based checks and `check(source)`, which runs them all. |
| `plcguard/obfuscate.py` | Renames every declared variable to `v1, v2, ...` without changing the logic. |
| `plcguard/evaluate.py` | Loads the labeled dataset and scores a detector: precision, recall, F1, per type and overall. |
| `plcguard/llm.py` | Minimal HTTP client for three providers, with a disk cache and retry/backoff. Standard library only. |
| `plcguard/llm_detector.py` | Builds the prompt, parses the model's JSON reply into `Finding`s; also the hybrid detector. |
| `plcguard/tracking.py` | Run manifests (git commit, dataset hash, prompt hash ...), the append-only run log, the summary table. |
| `plcguard/__main__.py` | Command line: `scan`, `eval`, `summary`, `models`. |
| `app.py` | Streamlit web UI. |
| `dataset/` | 20 labeled `.st` programs and `labels.json`. |
| `results/` | Reports, the run log, and `llm_cache/` (every LLM reply ever received). |
| `tests/` | 85 offline tests (parser, rules, dataset integrity, LLM parsing with fake replies, tracking, secret scan). |
| `infra/terraform/` | AWS infrastructure as code (not applied). |
| `.github/workflows/tests.yml` | CI: runs the tests on every push. |

## The `Finding` record

```python
@dataclass(frozen=True)
class Finding:
    vuln_type: VulnType   # one of the 8 classes
    line: int             # where the problem is most visible
    message: str          # one-sentence explanation
    rule: str = ""        # which rule fired, or "nvidia:<model>" for the LLM
    variable: str = ""    # the variable involved
    source: str = "rules" # "rules" or "llm"
```

## Design choices worth knowing

- **No dependencies in the core package.** HTTP calls use `urllib`, JSON uses
  `json`. Anyone can clone and run it without dependency problems, and CI
  stays fast. Only the web UI needs Streamlit (`requirements-app.txt`).
- **Detectors never see labels or file names.** File names contain `_vuln` and
  `_clean`, which would give the answer away. The evaluator passes only the
  source code.
- **Labels locate bugs by snippet, not line number.** See
  [Stage 1](03-stage1-rules.md#the-dataset).

Next: [Stage 1](03-stage1-rules.md)
