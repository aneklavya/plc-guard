"""LLM-based vulnerability detector and the rules+LLM hybrid.

The model sees only the program text, with line numbers. It never sees the
file name (which contains "_vuln" / "_clean") or the dataset labels, and the
prompt has no examples taken from the dataset, so the evaluation is zero-shot.
"""
from __future__ import annotations

import hashlib
import json
import re

from . import rules
from .llm import LLMClient, LLMError
from .taxonomy import CWE, DESCRIPTIONS, Finding, VulnType

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """\
You are a security auditor for industrial control systems. You review PLC \
programs written in IEC 61131-3 Structured Text and report security \
vulnerabilities.

Deployment (OpenPLC, Modbus/TCP on the plant network):
- %IX digital inputs and %IW analog inputs are physical sensors and switches.
- %QX digital outputs drive actuators; %QX1.x bits are HMI command bits.
- %QW analog outputs are actuator setpoints.
- %MW / %MD / %ML are Modbus holding registers: writable by the HMI or by \
anyone on the network, hence untrusted.
- Unlocated variables are internal state.
Variable names may be meaningless, so reason from the data flow and the \
physical role a variable plays, not from its name alone.

Report only these vulnerability classes:
{classes}

Rules:
- Report a vulnerability only if it is present in this code. Correct, \
defensive code (range checks, interlocks, bounds checks, constants for trip \
points) is not a finding. An empty list is a valid answer.
- One finding per distinct problem. "line" is the line number from the \
listing where the problem is most visible.
- Reply with JSON only, no prose, in exactly this shape:
{{"findings": [{{"type": "<CLASS>", "line": <int>, "variable": "<name>", \
"explanation": "<one sentence>"}}]}}
"""


def _classes() -> str:
    return "\n".join(f"- {t}: {DESCRIPTIONS[t]} ({CWE[t]})" for t in VulnType)


def build_prompt(source: str) -> tuple[str, str]:
    lines = source.splitlines()
    width = len(str(len(lines)))
    listing = "\n".join(f"{i:>{width}} | {text}" for i, text in enumerate(lines, 1))
    user = f"Audit this program.\n\n```\n{listing}\n```"
    return SYSTEM_PROMPT.format(classes=_classes()), user


def parse_response(text: str, source_name: str = "llm") -> list[Finding]:
    """Turn the model's reply into Findings; unknown classes are dropped."""
    data = _extract_json(text)
    items = data.get("findings", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise LLMError(f"'findings' is not a list: {text[:200]}")
    findings = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("type", "")).strip().upper().replace(" ", "_")
        try:
            vtype = VulnType(raw)
        except ValueError:
            continue
        try:
            line = int(item.get("line", 0))
        except (TypeError, ValueError):
            line = 0
        findings.append(Finding(vtype, line, str(item.get("explanation", "")).strip(),
                                rule=source_name, variable=str(item.get("variable", "")),
                                source="llm"))
    return findings


def _extract_json(text: str):
    # Reasoning models (e.g. Nemotron) may prefix the answer with <think>...</think>.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost {...} or [...] if the model added prose.
    for open_, close in ("{}", "[]"):
        start, end = text.find(open_), text.rfind(close)
        if 0 <= start < end:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise LLMError(f"response is not JSON: {text[:200]}")


def prompt_fingerprint() -> str:
    """Short hash of the system prompt, logged with every run."""
    return hashlib.sha256(build_prompt("")[0].encode()).hexdigest()[:12]


class LLMDetector:
    def __init__(self, client: LLMClient, sample: int = 0):
        self.client = client
        self.sample = sample

    def __call__(self, source: str) -> list[Finding]:
        system, user = build_prompt(source)
        reply = self.client.complete(system, user, self.sample)
        return sorted(parse_response(reply, f"{self.client.provider}:{self.client.model}"),
                      key=lambda f: (f.line, f.vuln_type))


class HybridDetector:
    """Union of the rule-based checker and the LLM detector."""

    def __init__(self, client: LLMClient, sample: int = 0):
        self.llm = LLMDetector(client, sample)
        self.client = client

    def __call__(self, source: str) -> list[Finding]:
        try:
            found = rules.check(source)
        except Exception:  # still use the LLM if the parser rejects the code
            found = []
        return sorted(found + self.llm(source), key=lambda f: (f.line, f.vuln_type))
