# 5. Reproducibility and MLOps

**MLOps** is the engineering practice around running ML experiments reliably:
knowing exactly which code, data and settings produced a number, and being
able to produce it again. For a research demo this matters more than scores:
a professor will trust a modest result they can reproduce over a great one
they cannot.

## The problems and the fixes

| Problem | Fix in PLCGuard |
|---|---|
| LLM APIs cost money/quota and change over time; re-running gives different answers. | **Response cache** committed to git (`results/llm_cache/`). Anyone can reproduce every number with no API key. |
| "Which code produced this table?" | **Run manifest** in every report: git commit, whether the working tree had uncommitted changes (`git_dirty`), Python version. |
| "Was the dataset the same?" | **Dataset hash**: SHA-256 of `labels.json` and every `.st` file (line endings normalised so Windows and Linux agree). |
| "Was the prompt the same?" | **Prompt version and prompt hash** in the manifest. |
| One LLM run is noisy. | **`--repeats N`**: N independent samples, report mean ± sample standard deviation. |
| Results get overwritten and forgotten. | **Append-only log** `results/runs.jsonl`; `summary` builds `results/SUMMARY.md` from the latest run per configuration. |
| An API key gets committed by accident. | **`tests/test_secrets.py`** scans every file git would commit for key patterns (Google `AIza...`, OpenRouter `sk-or-v1-...`, NVIDIA `nvapi-...`, OpenAI-style `sk-...`) and checks `.env.example` stays empty and `.env` is gitignored. |
| Code works on my machine only. | **CI** (`.github/workflows/tests.yml`): on every push GitHub runs the 85 offline tests on Python 3.11 and 3.13, then a rules evaluation. |
| A model alias silently changes. | **Pinned model ids**, never `-latest`. |

## How the cache works

```python
digest = sha256(json.dumps([provider, model, temperature, system, user, sample]))
results/llm_cache/<digest>.json  →  {"provider", "model", "temperature", "sample", "response"}
```

- Same inputs → same file → no network call.
- Any change (new prompt, new model, different code) → new hash → a real call.
- `sample` is the repeat index, so repeat 1, 2, 3 are *different* cache
  entries and therefore genuinely independent samples.
- The web UI reads this same cache, which is why scanning an example program
  there is instant and free.

## How repeats are reported

`tracking.aggregate` computes, for precision, recall, F1, clean-files-flagged
and errors: the mean, the **sample** standard deviation (n−1 denominator,
`statistics.stdev`), and the raw values. The Markdown report shows repeat 1 in
full, and the *Run* section gives the mean ± std across repeats.

## A run manifest, annotated

```text
timestamp:      2026-10-24T03:32:24+00:00   when it ran (UTC)
git_commit:     f90ac55                      code version (see note below)
git_dirty:      True                         uncommitted changes existed
dataset_hash:   98d73f944c19                 exact dataset
provider/model: nvidia / nemotron-3-ultra-550b-a55b
temperature:    0.0
prompt_version: v1, prompt_hash: aa71ce447ba6
repeats:        3
llm_calls: 61, cache_hits: 1                 61 requests for 60 replies = 1 retry
wall_seconds:   1864.7                       about 31 minutes
```

**Note on commit hashes.** The Stage 2 runs were made before the history was
rewritten on 2026-10-24 (see the [decision log](07-decision-log.md)), so
`runs.jsonl` refers to old hashes. Old `f90ac55` = new `8f050a8` (Stage 1);
old `ec719be` = new `9e15a33` (Stage 2). The files are identical; only commit
messages changed. `git_dirty: True` is honest: those runs used Stage 2 code
that was not committed yet.

## Tests

| File | What it checks |
|---|---|
| `test_parser.py` | Tokeniser and parser on tricky ST constructs. |
| `test_rules.py` | Each rule fires on its bad pattern and stays quiet on the fixed one. |
| `test_dataset.py` | Every label snippet matches exactly one line; every program parses. |
| `test_llm_detector.py` | Prompt contents, JSON parsing (fences, prose, `<think>`), caching, retry/backoff, missing-key errors, NVIDIA endpoint. Uses fake HTTP replies, so it is offline. |
| `test_tracking.py` | Manifests, dataset hash, aggregation, summary table. |
| `test_secrets.py` | No API keys in committable files. |

Next: [Web UI and deployment](06-web-ui-and-deployment.md)
