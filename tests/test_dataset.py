"""Sanity checks on the labeled dataset itself."""
import json
from pathlib import Path

import pytest

from plcguard.evaluate import load_dataset
from plcguard.obfuscate import obfuscate
from plcguard.st_parser import parse
from plcguard.taxonomy import VulnType

DATASET = Path(__file__).resolve().parent.parent / "dataset"
PROGRAMS = load_dataset(DATASET)


def test_every_st_file_is_labeled():
    labeled = {p.file for p in PROGRAMS}
    on_disk = {p.name for p in (DATASET / "programs").glob("*.st")}
    assert labeled == on_disk


def test_labels_are_consistent():
    raw = json.loads((DATASET / "labels.json").read_text(encoding="utf-8"))
    for p in raw["programs"]:
        assert p["vulnerable"] == bool(p["vulns"]), p["file"]
        assert p["file"].endswith("_vuln.st" if p["vulnerable"] else "_clean.st")
        for v in p["vulns"]:
            VulnType(v["type"])  # raises on typos


@pytest.mark.parametrize("prog", PROGRAMS, ids=lambda p: p.file)
def test_program_parses_and_snippets_are_unique(prog):
    assert parse(prog.source)
    for v in prog.vulns:
        assert len(v.lines) == 1, f"snippet {v.snippet!r} must match exactly one line"


@pytest.mark.parametrize("prog", PROGRAMS, ids=lambda p: p.file)
def test_obfuscation_keeps_structure(prog):
    obf = obfuscate(prog.source)
    assert obf.count("\n") == prog.source.count("\n")
    a, b = parse(prog.source)[0], parse(obf)[0]
    assert len(a.assignments) == len(b.assignments)
    assert [d.location for d in a.vars.values()] == [d.location for d in b.vars.values()]
