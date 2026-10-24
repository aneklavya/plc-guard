# 7. Decision log

Dated record of decisions, problems and fixes, newest last. When you forget
*why* something is the way it is, look here.

### 2026-10-16: Project goal and plan
- Build PLCGuard as a demo for the CARES Lab PhD position (LLM-based detection
  and correction of PLC vulnerabilities). Five incremental stages, each
  committed and evaluated.
- **Why:** the professor will judge research ability, so honest evaluation
  (including weaknesses) matters more than high scores.

### 2026-10-16: Stage 1 design
- Own lightweight ST parser instead of a full grammar: only what the checks
  need, no dependencies.
- Labels locate bugs by **snippet**, not line number, so edits don't silently
  break them.
- Vulnerable/clean **pairs** to measure false positives on near-identical code.
- **Obfuscated variant** (rename to `v1, v2, ...`) to measure name dependence.
- Result: F1 1.00 original, recall 0.55 obfuscated. The drop, not the 1.00,
  is the finding. Committed as Stage 1.

### 2026-10-16: LLM provider without paid credits
- No Claude/OpenAI budget. Client built for Gemini (free key) and OpenRouter
  (free models), standard library only.
- Disk cache and retry/backoff from day one, because free tiers are slow and
  rate-limited.

### 2026-10-19: Gemini free tier problems
- `gemini-2.5-*`: 404 for new users. `3.8-flash`, `3.7-flash`: 503 overloaded.
  Pro models: 429 (zero free quota). `gemini-3.5-flash` worked but slowly:
  about 13 replies before a 60-call run stalled.
- Added MLOps tracking (manifests, `runs.jsonl`, `--repeats`, summary),
  secret-leak test and CI while waiting.
- A key was once pasted into `.env.example` by mistake; `test_secrets.py`
  now catches that.

### 2026-10-24: Switched to NVIDIA Nemotron (free)
- Added `nvidia` provider (OpenAI-compatible endpoint). Added `<think>`
  stripping, `models` command, `nvapi-` secret pattern, 2 tests.
- Of 20 listed Nemotron models, most returned 404 for the free key and one
  returned 503. Working: `nemotron-3-ultra-550b-a55b` (chosen: largest and
  fastest) and `nemotron-3.5-lightning-30b-a3b`.
- **Lesson:** a model being listed by `/v1/models` doesn't mean your key can
  call it. Always smoke-test one file before a long run.

### 2026-10-24: Stage 2 evaluation
- 3 repeats × 20 programs × 2 variants = 120 calls, about 30 s each,
  about 65 minutes total, 1 retry.
- Recall 1.00 on both variants; precision 0.65 / 0.53. Hybrid identical to LLM.
- Added rules runs to the log so `SUMMARY.md` shows all four configurations.

### 2026-10-24: GitHub
- First pushed to `aneklavya/PLCGuard`. Then, at my request, commits must
  not list an AI assistant as co-author. The history was rewritten to remove
  those lines (files unchanged), the old repo was deleted, and the clean
  history was pushed to **`aneklavya/plc-guard`** (public).
- Hash mapping: `f90ac55` → `8f050a8` (Stage 1), `ec719be` → `9e15a33`
  (Stage 2). Old hashes still appear in `results/runs.jsonl`.

### 2026-10-24: Web UI first, AWS later
- Built the Streamlit UI now (originally planned for Stage 5) so results can
  be shown, not just read.
- Visitors can't burn my NVIDIA quota: examples use the cache; live scans are
  capped per session/day; bring-your-own-key is unlimited.
- AWS: Terraform written and validated (`terraform validate`), **not applied**.
  Decided to leave deployment for later. Key goes through SSM Parameter
  Store, not Terraform, to keep it out of the state file.

### 2026-10-24: Documentation
- Started `docs/`. Every future change updates the relevant chapter and adds
  an entry here.
