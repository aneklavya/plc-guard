"""Benchmark a detector against the labeled dataset.

Scoring is per (program, vulnerability type): a type counts as a true positive
if the detector reports it at least once for a program labeled with it.
Localisation is reported separately: did any finding of that type land within
`line_tolerance` lines of the labeled snippet?
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .taxonomy import Finding, VulnType

Detector = Callable[[str], list[Finding]]


@dataclass
class LabeledVuln:
    type: VulnType
    snippet: str
    description: str
    lines: list[int]


@dataclass
class ProgramLabel:
    file: str
    scenario: str
    vulnerable: bool
    source: str
    vulns: list[LabeledVuln] = field(default_factory=list)


def load_dataset(dataset_dir: Path) -> list[ProgramLabel]:
    meta = json.loads((dataset_dir / "labels.json").read_text(encoding="utf-8"))
    programs = []
    for p in meta["programs"]:
        source = (dataset_dir / "programs" / p["file"]).read_text(encoding="utf-8")
        src_lines = source.splitlines()
        vulns = []
        for v in p["vulns"]:
            lines = [i for i, text in enumerate(src_lines, 1) if v["snippet"] in text]
            vulns.append(LabeledVuln(VulnType(v["type"]), v["snippet"],
                                     v.get("description", ""), lines))
        programs.append(ProgramLabel(p["file"], p["scenario"], p["vulnerable"],
                                     source, vulns))
    return programs


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1}


def evaluate(detector: Detector, programs: list[ProgramLabel],
             line_tolerance: int = 1) -> dict:
    tp, fp, fn = Counter(), Counter(), Counter()
    localised = located_total = 0
    per_program = []
    vuln_detected = clean_flagged = errors = 0

    for prog in programs:
        try:
            findings = detector(prog.source)
            error = None
        except Exception as exc:  # parse failures count as "no findings"
            findings, error = [], f"{type(exc).__name__}: {exc}"
            errors += 1
        predicted = {f.vuln_type for f in findings}
        expected = {v.type for v in prog.vulns}

        for t in predicted & expected:
            tp[t] += 1
        for t in predicted - expected:
            fp[t] += 1
        for t in expected - predicted:
            fn[t] += 1

        for v in prog.vulns:
            if v.type not in predicted:
                continue
            located_total += 1
            if any(f.vuln_type == v.type and
                   any(abs(f.line - ln) <= line_tolerance for ln in v.lines)
                   for f in findings):
                localised += 1

        if prog.vulnerable and findings:
            vuln_detected += 1
        if not prog.vulnerable and findings:
            clean_flagged += 1

        per_program.append({
            "file": prog.file,
            "expected": sorted(expected),
            "predicted": sorted(predicted),
            "missed": sorted(expected - predicted),
            "extra": sorted(predicted - expected),
            "findings": [f.to_dict() for f in findings],
            "error": error,
        })

    types = sorted(set(VulnType))
    n_vuln = sum(p.vulnerable for p in programs)
    n_clean = len(programs) - n_vuln
    return {
        "per_type": {str(t): _prf(tp[t], fp[t], fn[t]) for t in types},
        "micro": _prf(sum(tp.values()), sum(fp.values()), sum(fn.values())),
        "file_level": {
            "vulnerable_files": n_vuln,
            "vulnerable_detected": vuln_detected,
            "clean_files": n_clean,
            "clean_flagged": clean_flagged,
        },
        "localisation": {"correct": localised, "of_detected": located_total},
        "parse_errors": errors,
        "programs": per_program,
    }


def to_markdown(report: dict, title: str) -> str:
    m, fl, loc = report["micro"], report["file_level"], report["localisation"]
    out = [f"# {title}", "",
           f"**Micro P / R / F1:** {m['precision']:.2f} / {m['recall']:.2f} / {m['f1']:.2f}  ",
           f"**Vulnerable files detected:** {fl['vulnerable_detected']}/{fl['vulnerable_files']}  ",
           f"**Clean files falsely flagged:** {fl['clean_flagged']}/{fl['clean_files']}  ",
           f"**Correct line (detected types):** {loc['correct']}/{loc['of_detected']}  ",
           f"**Parse errors:** {report['parse_errors']}", "",
           "| Type | TP | FP | FN | Precision | Recall | F1 |",
           "|---|---|---|---|---|---|---|"]
    for t, s in report["per_type"].items():
        out.append(f"| {t} | {s['tp']} | {s['fp']} | {s['fn']} | "
                   f"{s['precision']:.2f} | {s['recall']:.2f} | {s['f1']:.2f} |")
    errors = [p for p in report["programs"] if p["missed"] or p["extra"] or p["error"]]
    if errors:
        out += ["", "## Mistakes", ""]
        for p in errors:
            bits = []
            if p["missed"]:
                bits.append("missed " + ", ".join(p["missed"]))
            if p["extra"]:
                bits.append("false positive " + ", ".join(p["extra"]))
            if p["error"]:
                bits.append(p["error"])
            out.append(f"- `{p['file']}`: " + "; ".join(bits))
    return "\n".join(out) + "\n"
