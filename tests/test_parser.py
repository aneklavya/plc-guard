import pytest

from plcguard.st_parser import STParseError, compared, identifiers, parse, tokenize

SRC = """\
PROGRAM Demo
  VAR
    a, b AT %MW0 : INT := 5;  (* two names, one decl *)
    arr  : ARRAY[0..3] OF INT := [1, 2, 3, 4];
  END_VAR
  VAR CONSTANT
    lim : INT := 10;
  END_VAR
  // line comment
  IF a > 0 THEN
    b := arr[a];
  ELSIF a = 0 THEN
    b := 1;
  ELSE
    b := 2;
  END_IF;
  CASE b OF
    1, 2:
      a := T#5s;
    ELSE
      a := 0;
  END_CASE;
  FOR i := 0 TO 3 DO
    arr[i] := 0;
  END_FOR;
END_PROGRAM
"""


def test_tokenize_skips_comments_and_tracks_lines():
    toks = tokenize("(* multi\nline *)\nx := 16#FF; // c\ny := T#1h30m;")
    assert [t.text for t in toks] == ["x", ":=", "16#FF", ";", "y", ":=", "T#1h30m", ";"]
    assert toks[0].line == 3 and toks[4].line == 4


def test_var_blocks():
    pou = parse(SRC)[0]
    assert pou.name == "Demo"
    assert pou.vars["B"].location == "%MW0"
    assert pou.vars["A"].type_name == "INT"
    assert pou.vars["LIM"].constant
    assert pou.vars["ARR"].type_name.startswith("ARRAY")


def test_if_contexts():
    pou = parse(SRC)[0]
    by_line = {a.line: a for a in pou.assignments}
    assert [c.kind for c in by_line[11].contexts] == ["IF"]
    elsif = by_line[13].contexts[-1]
    assert elsif.kind == "ELSIF"
    # an ELSIF arm depends on every earlier condition too
    assert compared("A", elsif.cond)
    assert by_line[15].contexts[-1].kind == "ELSE"


def test_case_and_for():
    pou = parse(SRC)[0]
    assert pou.case_selectors == {"B"}
    assert "I" in pou.loop_vars
    case_arms = [a.contexts[-1] for a in pou.assignments if a.contexts
                 and a.contexts[-1].kind == "CASE"]
    assert [[t.text for t in c.own] for c in case_arms] == [["1", ",", "2"], []]


def test_identifiers_skip_members_calls_and_params():
    toks = tokenize("ton1(IN := x AND t.Q, PT := LIMIT(0, y, 5))")
    assert [t.text for t in identifiers(toks)] == ["x", "t", "y"]


def test_missing_end_if_is_an_error():
    with pytest.raises(STParseError):
        parse("PROGRAM P\n IF x THEN\n y := 1;\nEND_PROGRAM\n")
