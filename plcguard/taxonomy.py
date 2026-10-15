"""Vulnerability taxonomy and the Finding record shared by all detectors."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum


class VulnType(StrEnum):
    INPUT_VALIDATION = "INPUT_VALIDATION"
    MISSING_INTERLOCK = "MISSING_INTERLOCK"
    HARDCODED_CREDENTIAL = "HARDCODED_CREDENTIAL"
    LOGIC_BOMB = "LOGIC_BOMB"
    OOB_INDEX = "OOB_INDEX"
    DIV_BY_ZERO = "DIV_BY_ZERO"
    UNSAFE_STATE_TRANSITION = "UNSAFE_STATE_TRANSITION"
    UNPROTECTED_CRITICAL_VAR = "UNPROTECTED_CRITICAL_VAR"


DESCRIPTIONS: dict[VulnType, str] = {
    VulnType.INPUT_VALIDATION:
        "Value from a network/HMI-writable register reaches an output or "
        "process variable without a range check.",
    VulnType.MISSING_INTERLOCK:
        "Actuator can be energised without checking safety conditions "
        "(e-stop, high/low level, overload, pressure, ...).",
    VulnType.HARDCODED_CREDENTIAL:
        "Password, PIN or magic value hard-coded in logic to grant access "
        "or bypass a mode.",
    VulnType.LOGIC_BOMB:
        "Hidden condition (counter, date, magic constant) that overrides "
        "normal control logic once triggered.",
    VulnType.OOB_INDEX:
        "Array indexed with a value that is not bounds-checked.",
    VulnType.DIV_BY_ZERO:
        "Division or MOD by a variable that may be zero.",
    VulnType.UNSAFE_STATE_TRANSITION:
        "State machine can skip required states or be forced into an "
        "arbitrary state (e.g. HMI writes the state, purge bypass).",
    VulnType.UNPROTECTED_CRITICAL_VAR:
        "Safety-critical parameter (trip point, limit) stored in a "
        "network-writable register instead of a constant.",
}

# Closest CWE for each class, used in reports.
CWE: dict[VulnType, str] = {
    VulnType.INPUT_VALIDATION: "CWE-20",
    VulnType.MISSING_INTERLOCK: "CWE-693",
    VulnType.HARDCODED_CREDENTIAL: "CWE-798",
    VulnType.LOGIC_BOMB: "CWE-511",
    VulnType.OOB_INDEX: "CWE-129",
    VulnType.DIV_BY_ZERO: "CWE-369",
    VulnType.UNSAFE_STATE_TRANSITION: "CWE-1245",
    VulnType.UNPROTECTED_CRITICAL_VAR: "CWE-284",
}


@dataclass(frozen=True)
class Finding:
    vuln_type: VulnType
    line: int
    message: str
    rule: str = ""
    variable: str = ""
    source: str = "rules"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["vuln_type"] = str(self.vuln_type)
        return d
