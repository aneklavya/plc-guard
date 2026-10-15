"""Rule-based static checker for PLC Structured Text.

Conventions (documented in dataset/README.md):
  * %MW / %MD / %ML located variables are Modbus holding registers in
    OpenPLC, i.e. writable by an HMI or anyone on the network -> untrusted.
  * Actuators are BOOL outputs (%QX) whose names look like pumps, valves, ...
  * Safety signals are recognised by name (estop, high_*, overload, trip, ...).

Several rules depend on naming conventions. That is a deliberate,
measurable weakness of rule-based checking that the LLM detector (stage 2)
is compared against.
"""
from __future__ import annotations

import re
from collections import defaultdict

from .st_parser import (LITERAL_KINDS, POU, clamped, compared, identifiers,
                        index_expressions, parse)
from .taxonomy import Finding, VulnType

ACTUATOR = re.compile(r"pump|motor|valve|heater|burner|fuel|compressor|conveyor|"
                      r"mixer|agitator|igniter|drive", re.I)
SAFETY = re.compile(r"high|^hi_|_hi_|low_level|low_lvl|lsl|lsh|estop|e_stop|"
                    r"emergency|over|fault|interlock|trip|guard|door|dry|alarm|"
                    r"permissive|flame", re.I)
CREDENTIAL = re.compile(r"(^|_)(pin|pwd|pass|password|passcode|passwd|code|key|"
                        r"token|secret|auth)(_|\d|$)", re.I)
CRITICAL = re.compile(r"trip|limit|_max|max_|^max|_min|min_|safety|interlock|"
                      r"alarm_sp|alarm_lim|hi_sp|high_sp|lo_sp|low_sp|cutoff|"
                      r"shutdown|relief", re.I)
BYPASS = re.compile(r"skip|bypass|force|override|jump", re.I)
DATE_LITERAL = re.compile(r"^(DT|D|DATE|DATE_AND_TIME|TOD|TIME_OF_DAY)#", re.I)
MAGIC_NUMBER = 10_000


def _location(pou: POU, name: str) -> str:
    decl = pou.vars.get(name)
    return (decl.location or "") if decl else ""


def _tainted(pou: POU, name: str) -> bool:
    decl = pou.vars.get(name)
    return bool(decl and decl.location and decl.location.startswith("%M")
                and decl.type_name != "BOOL")


def _guards(contexts) -> list:
    return [tok for c in contexts for tok in c.cond]


# -- individual rules -----------------------------------------------------------

def check_input_validation(pou: POU):
    for a in pou.assignments:
        for t in identifiers(a.value, include_indices=False):
            n = t.upper
            if not _tainted(pou, n):
                continue
            if compared(n, _guards(a.contexts)) or clamped(n, a.value):
                continue
            yield Finding(VulnType.INPUT_VALIDATION, a.line,
                          f"'{t.text}' ({_location(pou, n)}) is network-writable and "
                          f"flows into '{a.target[0].text}' without a range check",
                          "PLC-IV", t.text)


def check_oob_index(pou: POU):
    for site in pou.sites:
        guards = _guards(site.contexts) + site.tokens
        for idx in index_expressions(site.tokens):
            for t in identifiers(idx):
                n = t.upper
                if n in pou.loop_vars or compared(n, guards):
                    continue
                yield Finding(VulnType.OOB_INDEX, t.line,
                              f"array index '{t.text}' is not bounds-checked",
                              "PLC-OOB", t.text)


def check_div_by_zero(pou: POU):
    for site in pou.sites:
        toks = site.tokens
        guards = _guards(site.contexts) + toks
        for i, t in enumerate(toks[:-1]):
            if t.text != "/" and t.upper != "MOD":
                continue
            d = toks[i + 1]
            after = toks[i + 2].text if i + 2 < len(toks) else ""
            if d.kind != "ident" or after in ("(", "."):
                continue
            if compared(d.upper, guards):
                continue
            yield Finding(VulnType.DIV_BY_ZERO, d.line,
                          f"divisor '{d.text}' is not checked for zero",
                          "PLC-DIV", d.text)


def check_hardcoded_credential(pou: POU):
    for site in pou.sites:
        toks = site.tokens
        for i, t in enumerate(toks):
            if t.kind != "ident" or not CREDENTIAL.search(t.text):
                continue
            right = i + 2 < len(toks) and toks[i + 1].text in ("=", "<>") \
                and toks[i + 2].kind in LITERAL_KINDS
            left = i >= 2 and toks[i - 1].text in ("=", "<>") \
                and toks[i - 2].kind in LITERAL_KINDS
            if right or left:
                yield Finding(VulnType.HARDCODED_CREDENTIAL, t.line,
                              f"'{t.text}' is compared against a hard-coded value",
                              "PLC-CRED", t.text)
    for decl in pou.vars.values():
        if CREDENTIAL.search(decl.name) and len(decl.init) == 1 \
                and decl.init[0].kind == "string" and len(decl.init[0].text) > 2:
            yield Finding(VulnType.HARDCODED_CREDENTIAL, decl.line,
                          f"'{decl.name}' is initialised with a hard-coded secret",
                          "PLC-CRED", decl.name)
    for a in pou.assignments:
        if CREDENTIAL.search(a.target[0].text) and len(a.value) == 1 \
                and a.value[0].kind == "string":
            yield Finding(VulnType.HARDCODED_CREDENTIAL, a.line,
                          f"'{a.target[0].text}' is assigned a hard-coded secret",
                          "PLC-CRED", a.target[0].text)


def _is_magic(tokens) -> bool:
    for t in tokens:
        if t.kind == "typed" and DATE_LITERAL.match(t.text):
            return True
        if t.kind == "number":
            try:
                if float(t.text.replace("_", "")) >= MAGIC_NUMBER:
                    return True
            except ValueError:
                pass
    return False


def check_logic_bomb(pou: POU):
    """A branch gated by a magic constant/date that overrides an output which
    is also driven by the normal logic elsewhere."""
    reported = set()
    for a in pou.assignments:
        if not _location(pou, a.target_name).startswith("%Q"):
            continue
        for ctx in a.contexts:
            if ctx.kind not in ("IF", "ELSIF") or ctx.block_id in reported \
                    or not _is_magic(ctx.own):
                continue
            elsewhere = any(b.target_name == a.target_name and
                            all(c.block_id != ctx.block_id for c in b.contexts)
                            for b in pou.assignments)
            if elsewhere:
                reported.add(ctx.block_id)
                yield Finding(VulnType.LOGIC_BOMB, ctx.line,
                              f"branch gated by a magic constant overrides output "
                              f"'{a.target[0].text}'", "PLC-BOMB", a.target[0].text)


def _dependencies(pou: POU) -> dict[str, set[str]]:
    deps: dict[str, set[str]] = defaultdict(set)
    for a in pou.assignments:
        names = {t.upper for t in identifiers(a.value)}
        for c in a.contexts:
            names |= {t.upper for t in identifiers(c.cond)}
        deps[a.target_name] |= names
    return deps


def _reaches_safety(names: set[str], deps, depth: int = 3) -> bool:
    """Does any name, or anything it is computed from (up to `depth` hops),
    look like a safety signal?"""
    seen: set[str] = set()
    frontier = set(names)
    for _ in range(depth + 1):
        if any(SAFETY.search(n) for n in frontier):
            return True
        seen |= frontier
        frontier = set().union(*(deps.get(n, set()) for n in frontier)) - seen
        if not frontier:
            break
    return False


def check_missing_interlock(pou: POU):
    deps = _dependencies(pou)
    for a in pou.assignments:
        loc = _location(pou, a.target_name)
        if not loc.startswith("%QX") or not ACTUATOR.search(a.target[0].text):
            continue
        if len(a.value) == 1 and a.value[0].upper == "FALSE":
            continue
        names = {t.upper for t in identifiers(a.value)}
        for c in a.contexts:
            names |= {t.upper for t in identifiers(c.cond)}
        if not _reaches_safety(names, deps):
            yield Finding(VulnType.MISSING_INTERLOCK, a.line,
                          f"actuator '{a.target[0].text}' can be energised without "
                          f"any safety condition", "PLC-INTERLOCK", a.target[0].text)


def check_unsafe_state_transition(pou: POU):
    for a in pou.assignments:
        if a.target_name not in pou.case_selectors:
            continue
        for t in identifiers(a.value):
            if _tainted(pou, t.upper):
                yield Finding(VulnType.UNSAFE_STATE_TRANSITION, a.line,
                              f"state '{a.target[0].text}' is written directly from "
                              f"network-writable '{t.text}'", "PLC-STATE", a.target[0].text)
        for c in a.contexts:
            for t in identifiers(c.own):
                if BYPASS.search(t.text):
                    yield Finding(VulnType.UNSAFE_STATE_TRANSITION, a.line,
                                  f"transition of '{a.target[0].text}' can be "
                                  f"triggered by bypass signal '{t.text}'",
                                  "PLC-STATE", a.target[0].text)


def check_unprotected_critical_var(pou: POU):
    for decl in pou.vars.values():
        if decl.location and decl.location.startswith("%M") and not decl.constant \
                and CRITICAL.search(decl.name):
            yield Finding(VulnType.UNPROTECTED_CRITICAL_VAR, decl.line,
                          f"safety parameter '{decl.name}' is stored in "
                          f"network-writable {decl.location}", "PLC-CRITVAR", decl.name)


RULES = [
    check_input_validation,
    check_missing_interlock,
    check_hardcoded_credential,
    check_logic_bomb,
    check_oob_index,
    check_div_by_zero,
    check_unsafe_state_transition,
    check_unprotected_critical_var,
]


def check(source: str) -> list[Finding]:
    """Run every rule over all POUs in `source`. Raises STParseError."""
    findings: dict[tuple, Finding] = {}
    for pou in parse(source):
        for rule in RULES:
            for f in rule(pou):
                findings.setdefault((f.vuln_type, f.line, f.variable.upper()), f)
    return sorted(findings.values(), key=lambda f: (f.line, f.vuln_type))
