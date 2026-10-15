"""Semantics-preserving identifier renaming for robustness testing.

Every declared variable is renamed to a neutral name (v1, v2, ...), keeping
types, locations and logic identical. A detector that really understands the
code should score the same on both variants; one that keys on names won't.
"""
from __future__ import annotations

import re

from .st_parser import parse


def obfuscate(source: str) -> str:
    names: list[str] = []
    for pou in parse(source):
        for decl in pou.vars.values():
            if decl.name.upper() not in (n.upper() for n in names):
                names.append(decl.name)
    # Longest first so that e.g. 'flow_a' never clobbers part of 'flow_ab'.
    mapping = {n.upper(): f"v{i}" for i, n in enumerate(names, 1)}
    if not mapping:
        return source
    pattern = re.compile(
        r"(?<![\w.#%])(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True))
        + r")(?!\w)", re.I)
    return pattern.sub(lambda m: mapping[m.group(1).upper()], source)
