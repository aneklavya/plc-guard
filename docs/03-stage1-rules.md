# 3. Stage 1: parser, rules, dataset, evaluation

Stage 1 builds the baseline everything else is compared against: a
conventional static checker, a labeled benchmark, and an honest way to score.

## The parser (`st_parser.py`)

A full IEC 61131-3 grammar is huge. The parser only understands what the
security checks need:

1. **Tokeniser.** One regular expression splits the source into tokens of six
   kinds: `ident`, `number`, `typed` (e.g. `T#60s`, `DT#2027-01-01`),
   `string`, `location` (e.g. `%MW10`), `op`. Comments `(* *)`, `//` and
   `{ }` are dropped. Each token remembers its line number.
2. **Recursive-descent parser.** One method per construct: `parse_pou`,
   `parse_var_block`, `parse_if`, `parse_case`, `parse_for`, `parse_while`,
   `parse_repeat`. It produces a `POU` object with:
   - `vars`: every declaration, with its type, `AT` location, initial value
     and whether it is `CONSTANT`;
   - `assignments`: every `target := value`;
   - `sites`: every expression (conditions, call arguments, values);
   - `case_selectors`: variables used in `CASE x OF` (state machines);
   - `loop_vars`: `FOR` loop counters.
3. **Contexts.** The most important idea. For every assignment the parser
   records the chain of enclosing conditions it runs under. In

   ```pascal
   IF steam_pressure < 100 THEN
     IF hmi_reset THEN tripped := FALSE; END_IF;
   END_IF;
   ```

   the assignment `tripped := FALSE` has two contexts: `steam_pressure < 100`
   and `hmi_reset`. That lets a rule ask "is this value checked anywhere on the
   path to this line?", which is a light form of **data-flow / control-flow
   analysis**.

Helpers used by the rules: `identifiers(tokens)`, `compared(name, tokens)`
(does `name` appear next to `<`, `>`, `<=`, `>=`, `=`, `<>`?), `clamped(name,
tokens)` (is it wrapped in `LIMIT`, `MIN` or `MAX`?), `index_expressions`.

## The 8 rules (`rules.py`)

| Rule | How it decides | Relies on names? |
|---|---|---|
| INPUT_VALIDATION | A non-BOOL `%M` variable (network-writable) appears in an assigned value, and is neither compared in an enclosing condition nor clamped with `LIMIT/MIN/MAX`. | No (data flow) |
| OOB_INDEX | An array index uses a variable that is not a `FOR` counter and is not compared anywhere on its path. | No |
| DIV_BY_ZERO | The token after `/` or `MOD` is a variable that is not compared on its path. | No |
| LOGIC_BOMB | An `IF` gated by a number ≥ 10,000 or a date literal assigns a `%Q` output that is also assigned elsewhere outside that branch. | No |
| MISSING_INTERLOCK | A `%QX` output **whose name looks like an actuator** (`pump`, `motor`, `valve`, ...) is driven by values that never reach, within 3 dependency hops, **a name that looks like a safety signal** (`estop`, `high`, `overload`, `trip`, ...). | **Yes** |
| HARDCODED_CREDENTIAL | A variable **named like a secret** (`pin`, `pwd`, `password`, `key`, ...) is compared with or initialised to a literal. | **Yes** |
| UNSAFE_STATE_TRANSITION | A `CASE` selector is assigned from a network-writable variable, or a transition is guarded by a variable **named like a bypass** (`skip`, `bypass`, `force`, `override`). | Partly |
| UNPROTECTED_CRITICAL_VAR | A non-constant `%M` variable **named like a safety parameter** (`trip`, `limit`, `max`, `min`, `cutoff`, ...). | **Yes** |

The naming dependency is deliberate and documented in the module docstring.
It is how real-world pattern checkers work, and it is exactly the weakness the
LLM is supposed to fix.

## The dataset

`dataset/programs/` has **10 scenarios × 2 versions = 20 programs**: each
scenario has a `_vuln.st` and a `_clean.st` that does the same job safely.
There are **11 labeled vulnerabilities** (scenario 04 has two).

| # | Scenario | Labeled vulnerability |
|---|---|---|
| 01 | Tank level | INPUT_VALIDATION: valve setpoint from HMI copied to output |
| 02 | Pump station | MISSING_INTERLOCK: pump ignores low level and overload |
| 03 | Maintenance access | HARDCODED_CREDENTIAL: `hmi_pin = 4711` |
| 04 | Conveyor | LOGIC_BOMB after 864,000 scans + MISSING_INTERLOCK inside it |
| 05 | Recipe batch | OOB_INDEX: recipe index from HMI |
| 06 | Flow ratio | DIV_BY_ZERO: divide by a flow that can be 0 |
| 07 | Burner sequence | UNSAFE_STATE_TRANSITION: `hmi_skip_purge` skips the purge |
| 08 | Boiler trip | UNPROTECTED_CRITICAL_VAR: `trip_pressure AT %MW20` |
| 09 | Heater power | INPUT_VALIDATION: HMI percentage scaled without a check |
| 10 | Traffic light | UNSAFE_STATE_TRANSITION: `phase := hmi_force_phase` |

**Why pairs?** A clean twin tests false positives on code that looks almost
the same. A detector that just says "vulnerable" to everything would score
100% recall on the `_vuln` files and get caught on the `_clean` ones.

**Labels locate bugs by snippet.** `labels.json` stores a piece of text
(e.g. `pump_run := run_latch;`) that must match exactly one line, instead of a
line number. If a program is edited, the label follows the code, and
`tests/test_dataset.py` fails if a snippet stops matching exactly one line.

## The robustness test: obfuscation (`obfuscate.py`)

`--variant obfuscated` renames every declared variable to `v1, v2, ...` with
the same types, addresses and logic. Example (scenario 02, vulnerable):

```pascal
(* original *)                         (* obfuscated *)
IF hmi_stop THEN                       IF v2 THEN
  run_latch := FALSE;                    v6 := FALSE;
END_IF;                                END_IF;
pump_run := run_latch;                 v5 := v6;
```

A detector that understands the program should score the same on both. One
that keys on names will not. This is a standard way to test whether a code
model is reasoning or pattern-matching on identifiers.

## Scoring (`evaluate.py`)

Scoring is **per (program, vulnerability type)**: for each program, the set
of types the detector reported is compared with the set of labeled types.

- **True positive (TP):** type reported and labeled.
- **False positive (FP):** type reported but not labeled (including anything
  reported on a clean file).
- **False negative (FN):** type labeled but not reported.

Then:

- **Precision** = TP / (TP + FP): of what it reported, how much was right.
- **Recall** = TP / (TP + FN): of the real bugs, how many it found.
- **F1** = 2·P·R / (P + R): one number that is high only if both are high.

"Micro" means TP/FP/FN are summed over all types first, then P/R/F1 computed
once. The report also gives per-type numbers, **file-level** detection (how
many vulnerable files got any finding; how many clean files got any finding),
and **localisation**: for a correctly detected type, was some finding of that
type within ±1 line of the labeled snippet?

## Stage 1 results

| Dataset | Precision | Recall | F1 | Clean files flagged |
|---|---|---|---|---|
| Original | 1.00 | 1.00 | 1.00 | 0/10 |
| Obfuscated | 1.00 | 0.55 | 0.71 | 0/10 |

Missed on the obfuscated set: MISSING_INTERLOCK (02, 04), HARDCODED_CREDENTIAL
(03), UNSAFE_STATE_TRANSITION (07, `hmi_skip_purge` became `v2`),
UNPROTECTED_CRITICAL_VAR (08). Exactly the name-dependent rules; every
data-flow rule survived.

**How to talk about this honestly.** The 1.00 on the original set is *not* an
achievement: the rules and the dataset were written by the same person at the
same time, so of course they agree. The finding is the **drop** on renaming,
which shows how fragile naming heuristics are. That is the motivation for
Stage 2.

Next: [Stage 2](04-stage2-llm.md)
