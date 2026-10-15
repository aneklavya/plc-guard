import pytest

from plcguard.rules import check
from plcguard.taxonomy import VulnType as V


def program(decls: str, body: str) -> str:
    return f"PROGRAM P\n  VAR\n{decls}\n  END_VAR\n{body}\nEND_PROGRAM\n"


def types(src: str) -> set:
    return {f.vuln_type for f in check(src)}


CASES = [
    # (vulnerability, vulnerable program, fixed program)
    (V.INPUT_VALIDATION,
     program("sp AT %MW0 : INT; out AT %QW0 : INT;", "out := sp * 2;"),
     program("sp AT %MW0 : INT; out AT %QW0 : INT;", "out := LIMIT(0, sp, 100) * 2;")),
    (V.INPUT_VALIDATION,
     program("sp AT %MW0 : INT; out AT %QW0 : INT;", "out := sp;"),
     program("sp AT %MW0 : INT; out AT %QW0 : INT;",
             "IF sp >= 0 AND sp <= 100 THEN\n out := sp;\nEND_IF;")),
    (V.MISSING_INTERLOCK,
     program("start AT %IX0.0 : BOOL; pump AT %QX0.0 : BOOL;", "pump := start;"),
     program("start AT %IX0.0 : BOOL; estop AT %IX0.1 : BOOL; pump AT %QX0.0 : BOOL;",
             "pump := start AND NOT estop;")),
    (V.MISSING_INTERLOCK,  # safety reached through an intermediate latch
     program("start AT %IX0.0 : BOOL; motor AT %QX0.0 : BOOL; latch : BOOL;",
             "latch := start;\nmotor := latch;"),
     program("start AT %IX0.0 : BOOL; overload AT %IX0.1 : BOOL; "
             "motor AT %QX0.0 : BOOL; latch : BOOL;",
             "latch := start AND NOT overload;\nmotor := latch;")),
    (V.HARDCODED_CREDENTIAL,
     program("pin AT %MW1 : INT; ok : BOOL;", "IF pin = 1234 THEN\n ok := TRUE;\nEND_IF;"),
     program("key_sw AT %IX0.0 : BOOL; ok : BOOL;", "ok := key_sw;")),
    (V.LOGIC_BOMB,
     program("run AT %IX0.0 : BOOL; valve AT %QX0.0 : BOOL; n : DINT;",
             "valve := run;\nn := n + 1;\nIF n > 50000 THEN\n valve := FALSE;\nEND_IF;"),
     program("run AT %IX0.0 : BOOL; valve AT %QX0.0 : BOOL; lamp AT %QX0.1 : BOOL; n : DINT;",
             "valve := run;\nn := n + 1;\nlamp := n > 50000;")),
    (V.OOB_INDEX,
     program("i AT %MW0 : INT; arr : ARRAY[0..3] OF INT; x : INT;", "x := arr[i];"),
     program("i AT %MW0 : INT; arr : ARRAY[0..3] OF INT; x : INT;",
             "IF i >= 0 AND i <= 3 THEN\n x := arr[i];\nEND_IF;")),
    (V.DIV_BY_ZERO,
     program("a : INT; b : INT; c : INT;", "c := a / b;"),
     program("a : INT; b : INT; c : INT;", "IF b <> 0 THEN\n c := a / b;\nEND_IF;")),
    (V.UNSAFE_STATE_TRANSITION,
     program("cmd AT %MW0 : INT; s : INT; x : INT;",
             "CASE s OF\n 0:\n x := 1;\nEND_CASE;\ns := cmd;"),
     program("cmd AT %IX0.0 : BOOL; s : INT; x : INT;",
             "CASE s OF\n 0:\n x := 1;\nEND_CASE;\nIF cmd AND s = 0 THEN\n s := 1;\nEND_IF;")),
    (V.UNPROTECTED_CRITICAL_VAR,
     program("trip_temp AT %MW5 : INT; t AT %IW0 : INT; a AT %QX0.0 : BOOL;",
             "a := t > trip_temp;"),
     program("t AT %IW0 : INT; a AT %QX0.0 : BOOL;",
             "a := t > 90;")),
]


@pytest.mark.parametrize("vuln, bad, good", CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_rule_flags_vulnerable_and_accepts_fix(vuln, bad, good):
    assert vuln in types(bad)
    assert vuln not in types(good)


def test_findings_point_at_the_right_line():
    src = program("sp AT %MW0 : INT; out AT %QW0 : INT; ok : INT;", "ok := 1;\nout := sp;")
    (f,) = check(src)
    assert src.splitlines()[f.line - 1].strip() == "out := sp;"


def test_loop_variable_is_not_an_oob_index():
    src = program("arr : ARRAY[0..3] OF INT;",
                  "FOR i := 0 TO 3 DO\n arr[i] := 0;\nEND_FOR;")
    assert V.OOB_INDEX not in types(src)
