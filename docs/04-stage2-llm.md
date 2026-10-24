# 4. Stage 2: the LLM detector

**Question:** can an LLM find the same vulnerabilities as the rules, and does
it keep working when variable names carry no meaning?

## How the detector works (`llm_detector.py`)

1. **Number the lines.** The program is sent as a listing like
   ` 9 | IF hmi_start THEN`, so the model can report line numbers.
2. **System prompt.** It tells the model:
   - its role (security auditor for industrial control systems);
   - the deployment: what `%IX`, `%QX`, `%QW`, `%MW` mean, and that `%M`
     registers are network-writable and therefore untrusted;
   - *"Variable names may be meaningless, so reason from the data flow and the
     physical role a variable plays"*;
   - the 8 allowed classes with their definitions and CWEs;
   - rules: report only real problems, an empty list is valid, one finding per
     problem, **reply with JSON only** in a fixed shape:
     `{"findings": [{"type", "line", "variable", "explanation"}]}`.
3. **Parse the reply** (`parse_response`). Strip `<think>...</think>` blocks
   (reasoning models emit them) and Markdown code fences, then `json.loads`.
   If the model added prose anyway, fall back to the outermost `{...}`.
   Unknown class names are dropped rather than crashing.

### Key evaluation choices

- **Zero-shot.** The prompt contains *no examples* from the dataset. With only
  20 programs, putting even one in the prompt would leak test data into the
  model's input (this is called **data contamination** / **test leakage**).
- **No file names, no labels.** File names contain `_vuln` / `_clean`.
- **Temperature 0.** Asks for the most likely answer, which reduces (but, as
  we found, does not remove) randomness.
- **Prompt is versioned and hashed** (`PROMPT_VERSION = "v1"`, plus a hash of
  the exact text in every run manifest), so any change to the prompt is a
  visible, separate experiment.

### The hybrid detector

`HybridDetector` returns the **union** of rule findings and LLM findings. The
idea: rules are precise, the LLM has high recall, so combine them.

## Providers (`llm.py`)

One small client supports three providers, chosen with `--provider`:

| Provider | Endpoint | Key variable | Notes |
|---|---|---|---|
| `nvidia` (current) | `integrate.api.nvidia.com/v1` (OpenAI-compatible) | `NVIDIA_API_KEY` (`nvapi-...`) | Free at build.nvidia.com |
| `gemini` | Google Generative Language API | `GEMINI_API_KEY` | Free tier was unreliable (see decision log) |
| `openrouter` | `openrouter.ai/api/v1` (OpenAI-compatible) | `OPENROUTER_API_KEY` | Free models with `:free` suffix |

"OpenAI-compatible" means the request and response look like OpenAI's chat
completions API, so NVIDIA and OpenRouter share the same code path.

Robustness features:

- **Disk cache.** Every reply is stored in `results/llm_cache/<sha256>.json`,
  keyed by provider, model, temperature, both prompts and the repeat index.
  Re-running costs nothing and gives identical numbers. Details in
  [Reproducibility](05-reproducibility.md).
- **Retry with backoff.** HTTP 429 (rate limited) and 500/502/503/504 are
  retried up to 6 times, waiting as long as the server's `Retry-After` header
  (or Gemini's `retryDelay`) says, else 2 s, 4 s, 8 s, ... up to 60 s.
- **`python -m plcguard models --filter nemotron`** lists the model ids a key
  can see. Being *listed* does not mean you can *call* it: most listed
  Nemotron models returned 404 for our free key.

### Which model and why

`nvidia/nemotron-3-ultra-550b-a55b`: Nemotron 3 Ultra, NVIDIA's largest open
model. "550b-a55b" means a **Mixture-of-Experts** model with 550 billion
parameters in total, of which about 55 billion are active for each token. It
was the strongest model that actually answered on the free tier, and it
replied fastest in a quick test. The full evaluation averaged about 30 s per
call.

## Results (3 repeats each, mean ± std)

| Detector | Code | Precision | Recall | F1 | Clean files flagged |
|---|---|---|---|---|---|
| Rules | original | 1.00 | 1.00 | 1.00 | 0 / 10 |
| Rules | obfuscated | 1.00 | 0.55 | 0.71 | 0 / 10 |
| Nemotron | original | 0.65 ± 0.07 | 1.00 ± 0.00 | 0.79 ± 0.05 | 3.3 / 10 |
| Nemotron | obfuscated | 0.53 ± 0.06 | 1.00 ± 0.00 | 0.69 ± 0.05 | 4.7 / 10 |
| Hybrid | either | identical to Nemotron | | | |

Localisation: in 65 of 66 cases (11 bugs × 3 runs × 2 variants) the LLM's
finding was within ±1 line of the labeled line.

## What the results mean

1. **Renaming does not hurt the LLM's recall.** It found all 11 labeled bugs
   in all 6 runs, including the five the rules lose on renamed code. This
   supports the claim that it reasons about what a variable *does*.
2. **Precision is the problem, and renaming makes it worse.** False positives
   over 3 runs: 18 on original code, 30 on renamed code. So names *do* help
   the LLM, not to find bugs but to recognise safe code. Clearest example:
   in `04_conveyor_clean.st`, `maint_due_lamp := cycle_count > 864000` is
   obviously a maintenance reminder lamp. Renamed to `v6 := v7 > 864000`, the
   model called it a LOGIC_BOMB.
3. **The hybrid adds nothing here.** Every bug the rules find, the LLM also
   finds, and the rules have no false positives, so the union equals the LLM.
   A better combination would use rules to *filter* LLM findings, not to add
   to them.
4. **Temperature 0 is not deterministic.** F1 varies by ±0.05 between
   identical runs (server-side batching and floating point make LLM outputs
   vary slightly). This is why every LLM number is a mean of 3 runs.

## A closer look at the false positives

Which classes: `MISSING_INTERLOCK` is about half of all false positives
(8 of 18 original, 15 of 30 renamed), then `UNSAFE_STATE_TRANSITION` and
`INPUT_VALIDATION`. The model never false-alarms on DIV_BY_ZERO, OOB_INDEX or
HARDCODED_CREDENTIAL.

Reading the explanations shows they are not all simply wrong. This is
preliminary and still needs careful manual adjudication:

- **Possibly a missing label.** In `03_maintenance_access_vuln.st` the PIN is
  read from `%MW10`, a network-writable register; the model flagged that as
  well as the hard-coded PIN. That is arguably a real second weakness the
  label does not include.
- **Arguably a domain-correct concern.** In `07_burner_sequence_clean.st` the
  model said the sequence should prove *no flame* before purging. Burner
  management standards do require a false-flame check, so this "false
  positive" may be a real gap in the "clean" program. Similarly, remote reset
  of a boiler trip from an HMI bit (`08_boiler_trip_clean.st`) is discouraged
  in safety practice.
- **Over-cautious and generic.** In `06_flow_ratio_*.st` the model demands an
  e-stop interlock for an analog dosing output in a program that has no safety
  inputs at all. That is a boilerplate concern, not a finding.

**Lesson:** a small hand-labeled dataset has label noise, and an LLM can find
things the labeler did not think of. A good paper separates "wrong" from
"right but unlabeled" by having findings adjudicated, ideally by someone other
than the labeler.

## Limitations to state up front

- 20 programs and 11 bugs is small: one answer moves recall by about 0.09.
- The programs are short and synthetic, written by the same person who wrote
  the rules.
- One model, one prompt. No comparison with smaller or other models yet.
- The labels may be incomplete (see above).

## Next experiments

- **Prompt v2** aimed at precision (e.g. require citing the exact missing
  check; tell the model a clean program is likely). Compare against v1.
- **Rules as a filter** for LLM findings, instead of a union.
- **Smaller model** (`nemotron-3.5-lightning-30b-a3b`) for a size comparison.
- Then Stage 3: repair.

Next: [Reproducibility](05-reproducibility.md)
