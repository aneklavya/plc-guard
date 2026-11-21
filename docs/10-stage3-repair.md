# 10. Stage 3: LLM repair with verification

**Question:** given a vulnerable PLC program and what is wrong with it, can
the LLM produce a fixed program that is actually valid, keeps the plant
wiring, and really removes the vulnerability?

## The loop (`plcguard/repair.py`)

```
vulnerable program + findings
        │
        ▼
  LLM proposes the complete fixed program ◄──── feedback: compiler errors,
        │                                        I/O changes, what is still found
        ▼                                                ▲
  1. compiles with MatIEC? ──────── no ──────────────────┤
  2. same located variables at the same addresses? ─ no ─┤  (at most 3 attempts)
  3. independent LLM re-scan no longer reports           │
     the targeted vulnerability types? ──────── no ──────┘
        │ all yes
        ▼
  accepted fix
```

### Why these three checks

1. **Compiles with MatIEC.** An LLM can write code that *looks* right but is
   not valid IEC 61131-3 (we learned this ourselves: 47 of our 60 programs
   didn't compile at first). The compiler is ground truth for validity, and
   its error messages, with line numbers, are fed back to the model.
2. **I/O map unchanged.** Every `AT %...` variable must keep its name and
   address. A "fix" that renames or moves `pump AT %QX0.0` would rewire the
   plant: the program would drive a different physical output. The check
   uses our own parser to compare located variables before and after.
3. **Independent re-scan.** A *separate* call with the *detection* prompt
   (v1) re-audits the candidate. If it still reports a targeted class, the
   fix is rejected and the model is told what is still found.

The **rules** also re-scan each fix, but only as a recorded second opinion,
because on held-out code they miss most bugs anyway (Stage 4).

### Prompt design

The repair prompt (`REPAIR_PROMPT_VERSION = "r1"`) gives the deployment
model (`%MW` untrusted, etc.), a list of standard fix patterns (LIMIT, add
interlock using existing signals, VAR CONSTANT, guard division, bound the
index, remove the backdoor, enforce the sequence), the constraints (keep
names, addresses, behaviour; MatIEC rules such as separate located VAR
blocks and no reserved words), and asks for the complete program in one
```` ```st ```` block. On retry, the previous answer and the concrete
failures are appended, so each attempt is still a single cacheable request.

### Evaluation setup: oracle findings

`python -m plcguard repair-eval` repairs every vulnerable dataset program
using its **labels** as the findings ("oracle detection"). This measures
repair quality on its own, separately from detection mistakes. Running both
together (detect, then repair) is the `repair` command and is what a user
would do.

Metrics: fixed and verified (all three checks), fixed on the first attempt,
compile rate, I/O preserved, whether the rules also agree, mean attempts,
median number of changed lines (small = minimal, reviewable fix).

## Results

*(filled in from `results/repair_*.md` when the run completes)*

## Limitations

- **The checker is also an LLM**, the same model that wrote the fix. A
  shared blind spot would pass. Mitigations: it is a separate call with a
  different (detection) prompt, and compile + I/O checks are deterministic.
  A stronger design uses a different model as the reviewer.
- **Behaviour preservation is not proven.** We check that the I/O map is
  unchanged and that diffs are small, but not that the fixed program does the
  same thing as before under normal (non-malicious) inputs. Proper checks:
  differential testing in a simulator, or model checking (e.g. translating
  ST to a model checker such as nuXmv). This is the main future work item.
- **Oracle findings** make repair look easier than the end-to-end case,
  where the detector's false positives may cause unnecessary edits.

Next: [Stage 5 demo](11-stage5-openplc-demo.md)
