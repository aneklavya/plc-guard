"""Stage 3: LLM repair with a verify-and-retry loop.

For each vulnerable program the LLM proposes a complete fixed program. The
candidate is accepted only if it
  1. compiles with MatIEC (OpenPLC's compiler),
  2. keeps the I/O map: the same located variables at the same addresses
     (a repair must not rewire the plant),
  3. no longer shows the targeted vulnerability types when re-scanned by the
     LLM detector (an independent call with the detection prompt).
Otherwise the failures are fed back and the model tries again, up to
`max_attempts` times. The rules re-scan is recorded as a second opinion but
is not part of acceptance, because the rules miss most held-out bugs.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from . import compile_check, rules
from .llm import LLMClient
from .llm_detector import LLMDetector
from .st_parser import parse
from .taxonomy import CWE, DESCRIPTIONS, Finding, VulnType

REPAIR_PROMPT_VERSION = "r1"

SYSTEM_PROMPT = """\
You are a PLC security engineer. You fix security vulnerabilities in IEC \
61131-3 Structured Text programs that run on OpenPLC.

Deployment: %IX/%IW are physical inputs, %QX/%QW physical outputs, %QX1.x \
are HMI command bits, and %MW/%MD/%ML are Modbus holding registers that \
anyone on the network can write (untrusted).

How to fix:
- Fix every listed vulnerability with the smallest change that makes the \
program safe: add range checks (LIMIT or IF), add the missing interlock \
conditions using signals the program already has, make safety parameters \
VAR CONSTANT, guard divisions, bound array indices, remove hidden \
triggers and hard-coded credentials, and make state changes follow the \
required sequence.
- Keep everything else unchanged: the program name, every located \
variable with its exact AT address and type, and the normal behaviour.
- The result must compile with the MatIEC compiler: located (AT %...) \
variables go in their own VAR ... END_VAR block, separate from other \
variables; constants in VAR CONSTANT; do not use reserved words (e.g. \
STEP, ACTION) as names.

Reply with the complete fixed program in a single ```st code block, \
followed by one short line per vulnerability saying what you changed.
"""


@dataclass
class Attempt:
    code: str
    compile_ok: bool
    compile_errors: list[str]
    io_preserved: bool
    io_problems: list[str]
    llm_remaining: list[str]          # targeted types the LLM re-scan still reports
    rules_remaining: list[str]        # targeted types the rules still report
    diff_lines: int

    @property
    def accepted(self) -> bool:
        return self.compile_ok and self.io_preserved and not self.llm_remaining


@dataclass
class RepairResult:
    attempts: list[Attempt] = field(default_factory=list)
    error: str | None = None

    @property
    def fixed(self) -> bool:
        return bool(self.attempts) and self.attempts[-1].accepted

    @property
    def final_code(self) -> str | None:
        return self.attempts[-1].code if self.attempts else None


def _numbered(source: str) -> str:
    lines = source.splitlines()
    width = len(str(len(lines)))
    return "\n".join(f"{i:>{width}} | {t}" for i, t in enumerate(lines, 1))


def build_prompt(source: str, targets: list[Finding]) -> str:
    items = "\n".join(f"- {f.vuln_type} ({CWE[f.vuln_type]}) at line {f.line}: "
                      f"{f.message or DESCRIPTIONS[f.vuln_type]}" for f in targets)
    return (f"Fix these vulnerabilities:\n{items}\n\nProgram (line numbers are for "
            f"reference only, do not include them):\n```\n{_numbered(source)}\n```")


def feedback_prompt(attempt: Attempt) -> str:
    problems = []
    if not attempt.compile_ok:
        problems.append("It does not compile with MatIEC:\n"
                        + "\n".join(f"  {e}" for e in attempt.compile_errors[:8]))
    if not attempt.io_preserved:
        problems.append("It changes the I/O map:\n"
                        + "\n".join(f"  {p}" for p in attempt.io_problems))
    if attempt.llm_remaining:
        problems.append("An independent review still finds: "
                        + ", ".join(attempt.llm_remaining))
    return ("Your fix was rejected.\n" + "\n".join(problems)
            + "\n\nReturn the complete corrected program again in a single ```st block.")


def extract_code(reply: str) -> str:
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL)
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", reply, flags=re.DOTALL)
    for block in blocks:
        if re.search(r"\bEND_(PROGRAM|FUNCTION_BLOCK|FUNCTION)\b", block):
            return block.strip() + "\n"
    m = re.search(r"\b(PROGRAM|FUNCTION_BLOCK|FUNCTION)\b.*?\bEND_\1\b", reply, re.DOTALL)
    return (m.group(0) + "\n") if m else (blocks[0] if blocks else reply)


def io_map(source: str) -> dict[str, str]:
    """Located variables: NAME -> address, for every POU."""
    return {d.name.upper(): d.location.upper()
            for pou in parse(source) for d in pou.vars.values() if d.location}


def io_problems(original: str, candidate: str) -> list[str]:
    before = io_map(original)
    try:
        after = io_map(candidate)
    except Exception as exc:
        return [f"could not parse the program: {exc}"]
    problems = [f"{n} AT {a} was removed or renamed" for n, a in before.items() if n not in after]
    problems += [f"{n} moved from {a} to {after[n]}" for n, a in before.items()
                 if n in after and after[n] != a]
    problems += [f"new located variable {n} AT {a}" for n, a in after.items() if n not in before]
    return problems


class Repairer:
    def __init__(self, client: LLMClient, checker: LLMClient | None = None,
                 max_attempts: int = 3, sample: int = 0):
        self.client = client
        self.detector = LLMDetector(checker or client, sample=sample)
        self.max_attempts = max_attempts
        self.sample = sample

    def verify(self, original: str, code: str, targets: list[Finding]) -> Attempt:
        wanted = {f.vuln_type for f in targets}
        result = compile_check.compile_st(code)
        problems = io_problems(original, code)
        try:
            llm_left = sorted({str(f.vuln_type) for f in self.detector(code)
                               if f.vuln_type in wanted})
        except Exception as exc:  # unparsable review counts as not verified
            llm_left = [f"review failed: {exc}"]
        try:
            rules_left = sorted({str(f.vuln_type) for f in rules.check(code)
                                 if f.vuln_type in wanted})
        except Exception:
            rules_left = ["rules could not parse"]
        diff = sum(1 for ln in difflib.unified_diff(original.splitlines(), code.splitlines(),
                                                    lineterm="", n=0)
                   if ln[:1] in "+-" and not ln.startswith(("+++", "---")))
        return Attempt(code, result.ok, result.errors, not problems, problems,
                       llm_left, rules_left, diff)

    def repair(self, source: str, targets: list[Finding]) -> RepairResult:
        out = RepairResult()
        conversation = build_prompt(source, targets)
        for _ in range(self.max_attempts):
            try:
                reply = self.client.complete(SYSTEM_PROMPT, conversation, self.sample)
            except Exception as exc:
                out.error = f"{type(exc).__name__}: {exc}"
                return out
            attempt = self.verify(source, extract_code(reply), targets)
            out.attempts.append(attempt)
            if attempt.accepted:
                break
            # The whole exchange goes into the next user turn, so each attempt
            # is still one cacheable (system, user) pair.
            conversation += (f"\n\nYour previous answer:\n```st\n{attempt.code}```\n\n"
                             + feedback_prompt(attempt))
        return out


def targets_from_labels(prog) -> list[Finding]:
    """Ground-truth findings for a labeled program (oracle detection)."""
    return [Finding(VulnType(v.type), v.lines[0] if v.lines else 0, v.description,
                    rule="label") for v in prog.vulns]


def evaluate_repairs(programs, repairer: Repairer, workers: int = 1) -> dict:
    """Repair every vulnerable program using its labels as the findings."""
    from concurrent.futures import ThreadPoolExecutor

    vulnerable = [p for p in programs if p.vulnerable]

    def one(prog):
        return prog, repairer.repair(prog.source, targets_from_labels(prog))

    with ThreadPoolExecutor(max(1, workers)) as pool:
        results = list(pool.map(one, vulnerable))

    rows = []
    for prog, res in results:
        last = res.attempts[-1] if res.attempts else None
        rows.append({
            "file": prog.file, "split": prog.split,
            "targets": [str(v.type) for v in prog.vulns],
            "fixed": res.fixed,
            "fixed_first_try": bool(res.attempts) and res.attempts[0].accepted,
            "attempts": len(res.attempts),
            "compiles": bool(last and last.compile_ok),
            "io_preserved": bool(last and last.io_preserved),
            "llm_remaining": last.llm_remaining if last else [],
            "rules_remaining": last.rules_remaining if last else [],
            "diff_lines": last.diff_lines if last else None,
            "error": res.error,
            "code": res.final_code,
            "history": [{"compile_ok": a.compile_ok, "compile_errors": a.compile_errors[:5],
                         "io_problems": a.io_problems, "llm_remaining": a.llm_remaining}
                        for a in res.attempts],
        })
    return {"programs": rows,
            "by_split": {s: _repair_metrics([r for r in rows if s == "all" or r["split"] == s])
                         for s in ("all", "dev", "heldout")}}


def _repair_metrics(rows: list[dict]) -> dict:
    n = len(rows) or 1
    fixed = [r for r in rows if r["fixed"]]
    return {
        "programs": len(rows),
        "fixed": len(fixed),
        "fixed_rate": len(fixed) / n,
        "fixed_first_try_rate": sum(r["fixed_first_try"] for r in rows) / n,
        "compile_rate": sum(r["compiles"] for r in rows) / n,
        "io_preserved_rate": sum(r["io_preserved"] for r in rows) / n,
        "rules_agree_rate": sum(r["fixed"] and not r["rules_remaining"] for r in rows) / n,
        "mean_attempts": sum(r["attempts"] for r in rows) / n,
        "median_diff_lines": sorted(r["diff_lines"] for r in fixed)[len(fixed) // 2] if fixed else None,
    }


def repair_markdown(report: dict, title: str) -> str:
    out = [f"# {title}", "",
           "| Split | Programs | Fixed | Fixed 1st try | Compiles | I/O kept | "
           "Rules agree | Mean attempts | Median lines changed |",
           "|---|---|---|---|---|---|---|---|---|"]
    for split, m in report["by_split"].items():
        if not m["programs"]:
            continue
        out.append(f"| {split} | {m['programs']} | {m['fixed']} ({m['fixed_rate']:.0%}) | "
                   f"{m['fixed_first_try_rate']:.0%} | {m['compile_rate']:.0%} | "
                   f"{m['io_preserved_rate']:.0%} | {m['rules_agree_rate']:.0%} | "
                   f"{m['mean_attempts']:.1f} | {m['median_diff_lines']} |")
    out += ["", "## Per program", "",
            "| File | Targets | Fixed | Attempts | Compiles | I/O kept | Still flagged (LLM / rules) |",
            "|---|---|---|---|---|---|---|"]
    for r in report["programs"]:
        left = f"{', '.join(r['llm_remaining']) or '-'} / {', '.join(r['rules_remaining']) or '-'}"
        out.append(f"| `{r['file']}` | {', '.join(r['targets'])} | {'yes' if r['fixed'] else 'NO'} | "
                   f"{r['attempts']} | {'yes' if r['compiles'] else 'no'} | "
                   f"{'yes' if r['io_preserved'] else 'no'} | {left} |")
    return "\n".join(out) + "\n"
