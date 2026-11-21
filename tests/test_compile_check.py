"""Every dataset program must compile with MatIEC, OpenPLC's real compiler.

Skipped when iec2c is not installed; CI builds it, so it always runs there.
"""
from pathlib import Path

import pytest

from plcguard import compile_check
from plcguard.evaluate import load_dataset

DATASET = Path(__file__).resolve().parent.parent / "dataset"
pytestmark = pytest.mark.skipif(not compile_check.available(), reason="MatIEC not installed")


def test_every_dataset_program_compiles():
    failures = {}
    for prog in load_dataset(DATASET):
        result = compile_check.compile_st(prog.source)
        if not result.ok:
            failures[prog.file] = result.summary()
    assert not failures, failures


def test_syntax_error_is_reported_with_a_line():
    bad = "PROGRAM P\n  VAR\n    x : INT;\n  END_VAR\n  x := 1\nEND_PROGRAM\n"
    result = compile_check.compile_st(bad)
    assert not result.ok
    assert any(e.startswith("line ") for e in result.errors)
