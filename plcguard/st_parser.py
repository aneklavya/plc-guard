"""Lightweight parser for IEC 61131-3 Structured Text.

This is not a full grammar. It understands enough structure for static
security checks -- POUs, VAR blocks (with AT locations), IF/CASE/FOR/WHILE/
REPEAT, assignments and FB calls -- and records, for every expression, the
chain of enclosing conditions ("contexts") it executes under.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field


class STParseError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"line {line}: {message}")
        self.line = line


@dataclass(frozen=True)
class Token:
    kind: str  # ident | number | typed | string | location | op
    text: str
    line: int

    @property
    def upper(self) -> str:
        return self.text.upper()


_TOKEN_RE = re.compile(
    r"""
    (?P<ws>[ \t\r\f]+)
  | (?P<nl>\n)
  | (?P<comment>\(\*.*?\*\)|//[^\n]*|\{[^}]*\})
  | (?P<string>'(?:[^'$]|\$.)*'|"(?:[^"$]|\$.)*")
  | (?P<location>%[IQM][XBWDL]?\d+(?:\.\d+)*)
  | (?P<typed>(?:[A-Za-z_]\w*|\d+)\#[-+\w.:]+)
  | (?P<number>\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][-+]?\d+)?)
  | (?P<ident>[A-Za-z_]\w*)
  | (?P<op>:=|=>|<=|>=|<>|\*\*|\.\.|[-+*/<>=&(),;:\[\].^])
    """,
    re.VERBOSE | re.DOTALL,
)


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    line, pos = 1, 0
    while pos < len(source):
        m = _TOKEN_RE.match(source, pos)
        if not m:
            raise STParseError(f"unexpected character {source[pos]!r}", line)
        kind, text = m.lastgroup, m.group()
        if kind not in ("ws", "nl", "comment"):
            tokens.append(Token(kind, text, line))
        line += text.count("\n")
        pos = m.end()
    return tokens


@dataclass
class VarDecl:
    name: str
    type_tokens: list[Token]
    location: str | None
    init: list[Token]
    section: str
    constant: bool
    line: int

    @property
    def type_name(self) -> str:
        return " ".join(t.text for t in self.type_tokens).upper()


@dataclass(frozen=True)
class Context:
    """One enclosing branch: an IF/ELSIF/ELSE arm, CASE arm, or loop body."""
    kind: str
    cond: tuple[Token, ...]  # every token this branch depends on
    own: tuple[Token, ...]   # tokens of this arm's own condition / label
    block_id: int
    line: int


@dataclass
class Assignment:
    target: list[Token]
    value: list[Token]
    line: int
    contexts: tuple[Context, ...]

    @property
    def target_name(self) -> str:
        return self.target[0].upper


@dataclass
class ExprSite:
    tokens: list[Token]
    line: int
    contexts: tuple[Context, ...]
    role: str  # lhs | rhs | cond | selector | loop | call


@dataclass
class POU:
    kind: str
    name: str
    line: int
    vars: dict[str, VarDecl] = field(default_factory=dict)
    assignments: list[Assignment] = field(default_factory=list)
    sites: list[ExprSite] = field(default_factory=list)
    case_selectors: set[str] = field(default_factory=set)
    loop_vars: set[str] = field(default_factory=set)


_POU_END = {"PROGRAM": "END_PROGRAM", "FUNCTION_BLOCK": "END_FUNCTION_BLOCK",
            "FUNCTION": "END_FUNCTION"}
_SKIP_BLOCKS = {"CONFIGURATION": "END_CONFIGURATION", "TYPE": "END_TYPE"}
_VAR_SECTIONS = {"VAR", "VAR_INPUT", "VAR_OUTPUT", "VAR_IN_OUT", "VAR_GLOBAL",
                 "VAR_EXTERNAL", "VAR_TEMP"}
_VAR_QUALIFIERS = {"CONSTANT", "RETAIN", "NON_RETAIN", "PERSISTENT"}
_OPEN, _CLOSE = {"(", "["}, {")", "]"}


class _Parser:
    def __init__(self, tokens: list[Token]):
        self.toks = tokens
        self.pos = 0
        self.ids = itertools.count(1)
        self.pou: POU | None = None

    # -- token helpers -------------------------------------------------------
    def peek(self) -> Token | None:
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def at(self, *words: str) -> bool:
        t = self.peek()
        return t is not None and t.upper in words

    def _last_line(self) -> int:
        return self.toks[-1].line if self.toks else 1

    def next(self) -> Token:
        t = self.peek()
        if t is None:
            raise STParseError("unexpected end of file", self._last_line())
        self.pos += 1
        return t

    def expect(self, word: str) -> Token:
        t = self.next()
        if t.upper != word:
            raise STParseError(f"expected {word}, found {t.text!r}", t.line)
        return t

    def accept(self, word: str) -> Token | None:
        return self.next() if self.at(word) else None

    def collect(self, stops: set[str]) -> list[Token]:
        """Tokens up to (not including) the first bracket-depth-0 stop word."""
        out: list[Token] = []
        depth = 0
        while True:
            t = self.peek()
            if t is None:
                raise STParseError(f"expected {' or '.join(sorted(stops))}",
                                   self._last_line())
            if depth == 0 and t.upper in stops:
                return out
            if t.text in _OPEN:
                depth += 1
            elif t.text in _CLOSE:
                depth = max(0, depth - 1)
            out.append(self.next())

    def _site(self, tokens: list[Token], ctx: tuple[Context, ...], role: str):
        if tokens:
            self.pou.sites.append(ExprSite(list(tokens), tokens[0].line, ctx, role))

    # -- structure -----------------------------------------------------------
    def parse_file(self) -> list[POU]:
        pous = []
        while (t := self.peek()) is not None:
            if t.upper in _POU_END:
                pous.append(self.parse_pou())
            elif t.upper in _SKIP_BLOCKS:
                end = _SKIP_BLOCKS[t.upper]
                self.next()
                self.collect({end})
                self.next()
                self.accept(";")
            else:
                self.next()
        return pous

    def parse_pou(self) -> POU:
        start = self.next()
        end = _POU_END[start.upper]
        name = self.next()
        if start.upper == "FUNCTION" and self.accept(":"):
            self.next()
        self.pou = POU(start.upper, name.text, start.line)
        while self.peek() is not None and self.peek().upper in _VAR_SECTIONS:
            self.parse_var_block()
        self.parse_statements({end}, ())
        self.expect(end)
        return self.pou

    def parse_var_block(self):
        section = self.next().upper
        constant = False
        while self.at(*_VAR_QUALIFIERS):
            constant |= self.next().upper == "CONSTANT"
        while not self.at("END_VAR"):
            names = [self.next()]
            while self.accept(","):
                names.append(self.next())
            location = None
            if self.accept("AT"):
                location = self.next().text.upper()
            self.expect(":")
            type_tokens = self.collect({":=", ";"})
            init = self.collect({";"}) if self.accept(":=") else []
            self.expect(";")
            for n in names:
                self.pou.vars[n.upper] = VarDecl(n.text, type_tokens, location,
                                                 init, section, constant, n.line)
        self.expect("END_VAR")

    # -- statements ----------------------------------------------------------
    def parse_statements(self, stops: set[str], ctx: tuple[Context, ...],
                         case_mode: bool = False):
        while True:
            t = self.peek()
            if t is None:
                raise STParseError(f"missing {' / '.join(sorted(stops))}",
                                   self._last_line())
            if t.upper in stops or (case_mode and self._at_case_label()):
                return
            self.parse_statement(ctx)

    def parse_statement(self, ctx: tuple[Context, ...]):
        t = self.peek()
        u = t.upper
        if u == ";":
            self.next()
            return
        handler = {"IF": self.parse_if, "CASE": self.parse_case,
                   "FOR": self.parse_for, "WHILE": self.parse_while,
                   "REPEAT": self.parse_repeat}.get(u)
        if handler:
            handler(ctx)
            return
        if u in ("RETURN", "EXIT", "CONTINUE"):
            self.next()
            self.accept(";")
            return
        tokens = self.collect({";"})
        self.expect(";")
        split = next((i for i, tok in enumerate(_depth0(tokens)) if tok and tok.text == ":="), None)
        if split is None:
            self._site(tokens, ctx, "call")
            return
        target, value = tokens[:split], tokens[split + 1:]
        if not target or not value:
            raise STParseError("malformed assignment", t.line)
        self.pou.assignments.append(Assignment(target, value, t.line, ctx))
        self._site(target, ctx, "lhs")
        self._site(value, ctx, "rhs")

    def parse_if(self, ctx):
        start = self.expect("IF")
        cond = self.collect({"THEN"})
        self.expect("THEN")
        self._site(cond, ctx, "cond")
        prior = list(cond)
        arm = Context("IF", tuple(cond), tuple(cond), next(self.ids), start.line)
        self.parse_statements({"ELSIF", "ELSE", "END_IF"}, ctx + (arm,))
        while self.at("ELSIF"):
            t = self.next()
            c = self.collect({"THEN"})
            self.expect("THEN")
            self._site(c, ctx, "cond")
            prior += c
            arm = Context("ELSIF", tuple(prior), tuple(c), next(self.ids), t.line)
            self.parse_statements({"ELSIF", "ELSE", "END_IF"}, ctx + (arm,))
        if self.at("ELSE"):
            t = self.next()
            arm = Context("ELSE", tuple(prior), (), next(self.ids), t.line)
            self.parse_statements({"END_IF"}, ctx + (arm,))
        self.expect("END_IF")
        self.accept(";")

    def parse_case(self, ctx):
        self.expect("CASE")
        sel = self.collect({"OF"})
        self.expect("OF")
        self._site(sel, ctx, "selector")
        self.pou.case_selectors.update(t.upper for t in identifiers(sel))
        while not self.at("END_CASE"):
            if self.at("ELSE"):
                t = self.next()
                labels: list[Token] = []
            else:
                t = self.peek()
                labels = self.collect({":"})
                self.expect(":")
            arm = Context("CASE", tuple(sel + labels), tuple(labels),
                          next(self.ids), t.line)
            self.parse_statements({"ELSE", "END_CASE"}, ctx + (arm,), case_mode=True)
        self.expect("END_CASE")
        self.accept(";")

    def _at_case_label(self) -> bool:
        saw = False
        for t in self.toks[self.pos:]:
            if t.text == ":":
                return saw
            if t.kind in ("number", "typed", "ident") or t.text in (",", "..", "-", "+"):
                saw = True
                continue
            return False
        return False

    def parse_for(self, ctx):
        start = self.expect("FOR")
        var = self.next()
        self.expect(":=")
        bounds = self.collect({"DO"})
        self.expect("DO")
        self.pou.loop_vars.add(var.upper)
        self._site(bounds, ctx, "loop")
        arm = Context("FOR", (var, *bounds), tuple(bounds), next(self.ids), start.line)
        self.parse_statements({"END_FOR"}, ctx + (arm,))
        self.expect("END_FOR")
        self.accept(";")

    def parse_while(self, ctx):
        start = self.expect("WHILE")
        cond = self.collect({"DO"})
        self.expect("DO")
        self._site(cond, ctx, "cond")
        arm = Context("WHILE", tuple(cond), tuple(cond), next(self.ids), start.line)
        self.parse_statements({"END_WHILE"}, ctx + (arm,))
        self.expect("END_WHILE")
        self.accept(";")

    def parse_repeat(self, ctx):
        start = self.expect("REPEAT")
        arm = Context("REPEAT", (), (), next(self.ids), start.line)
        self.parse_statements({"UNTIL"}, ctx + (arm,))
        self.expect("UNTIL")
        cond = self.collect({"END_REPEAT", ";"})
        self.accept(";")
        self._site(cond, ctx, "cond")
        self.expect("END_REPEAT")
        self.accept(";")


def _depth0(tokens: list[Token]):
    """Yield each token if it is at bracket depth 0, else None (keeps indices)."""
    depth = 0
    for t in tokens:
        if t.text in _OPEN:
            depth += 1
            yield None
        elif t.text in _CLOSE:
            depth = max(0, depth - 1)
            yield None
        else:
            yield t if depth == 0 else None


def parse(source: str) -> list[POU]:
    return _Parser(tokenize(source)).parse_file()


# -- expression helpers -------------------------------------------------------

EXPR_KEYWORDS = {"AND", "OR", "XOR", "NOT", "MOD", "TRUE", "FALSE", "AND_THEN",
                 "OR_ELSE", "TO", "BY", "DO", "THEN", "OF"}
COMPARISON_OPS = {"<", ">", "<=", ">=", "=", "<>"}
LITERAL_KINDS = {"number", "typed", "string"}


def identifiers(tokens, *, include_indices: bool = True) -> list[Token]:
    """Variable references in an expression (skips members, calls, param names)."""
    tokens = list(tokens)
    out, depth = [], 0
    for i, t in enumerate(tokens):
        if t.text == "[":
            depth += 1
            continue
        if t.text == "]":
            depth = max(0, depth - 1)
            continue
        if t.kind != "ident" or t.upper in EXPR_KEYWORDS:
            continue
        if depth and not include_indices:
            continue
        if i > 0 and tokens[i - 1].text == ".":
            continue
        nxt = tokens[i + 1].text if i + 1 < len(tokens) else ""
        if nxt in ("(", ":="):
            continue
        out.append(t)
    return out


def index_expressions(tokens) -> list[list[Token]]:
    """Contents of every [...] subscript in an expression."""
    tokens = list(tokens)
    out, stack = [], []
    for i, t in enumerate(tokens):
        if t.text == "[":
            stack.append(i)
        elif t.text == "]" and stack:
            out.append(tokens[stack.pop() + 1:i])
    return out


def compared(name: str, tokens) -> bool:
    """True if variable `name` is an operand of a comparison in `tokens`."""
    tokens = list(tokens)
    for i, t in enumerate(tokens):
        if t.kind != "ident" or t.upper != name or (i and tokens[i - 1].text == "."):
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].text == ")":
            j += 1
        if j < len(tokens) and tokens[j].text in COMPARISON_OPS:
            return True
        k = i - 1
        while k >= 0 and tokens[k].text == "(":
            k -= 1
        if k >= 0 and tokens[k].text in COMPARISON_OPS:
            return True
    return False


def clamped(name: str, tokens) -> bool:
    """True if `name` appears inside a LIMIT(...) call in `tokens`."""
    tokens = list(tokens)
    for i, t in enumerate(tokens):
        if t.upper != "LIMIT" or i + 1 >= len(tokens) or tokens[i + 1].text != "(":
            continue
        depth = 0
        for t2 in tokens[i + 1:]:
            if t2.text == "(":
                depth += 1
            elif t2.text == ")":
                depth -= 1
                if depth == 0:
                    break
            elif t2.kind == "ident" and t2.upper == name:
                return True
    return False
