from __future__ import annotations

import re
from typing import List, Tuple

from .ast import Script, RawSQL, IfStmt, Stmt


_WS = re.compile(r"\s+")
_LINE_COMMENT = re.compile(r"\s*--[^\n]*")


def _skip_ws_and_comments(s: str, i: int) -> int:
    n = len(s)
    while i < n:
        m = _WS.match(s, i)
        if m:
            i = m.end()
            continue
        m = _LINE_COMMENT.match(s, i)
        if m:
            i = m.end()
            continue
        break
    return i


def _is_word_boundary(ch: str) -> bool:
    return not (ch.isalnum() or ch == "_")


def _consume_kw(s: str, i: int, kw: str) -> int:
    i = _skip_ws_and_comments(s, i)
    n = len(s)
    k = kw.lower()
    if s[i:i+len(k)].lower() == k and (i+len(k) == n or _is_word_boundary(s[i+len(k)])):
        return i + len(k)
    raise ValueError(f"Expected keyword {kw} at position {i}")


def _starts_with_kw(s: str, i: int, kw: str) -> bool:
    i = _skip_ws_and_comments(s, i)
    return re.match(rf"(?is){re.escape(kw)}\b", s[i:]) is not None


def _read_until_kw(s: str, i: int, kw: str) -> Tuple[str, int]:
    # Read text until a standalone keyword kw is found (not consuming kw)
    # Assumes no nested quotes contain the keyword for MVP simplicity.
    j = i
    pat = re.compile(rf"(?is)\b{kw}\b")
    while True:
        m = pat.search(s, j)
        if not m:
            raise ValueError(f"Expected keyword {kw} after position {i}")
        # Ensure everything from i..m.start() is the slice
        chunk = s[i:m.start()]
        return chunk, m.start()


def _read_until_semicolon(s: str, i: int) -> Tuple[str, int]:
    m = re.search(r";", s[i:])
    if not m:
        # No semicolon; take rest
        return s[i:].rstrip(), len(s)
    end = i + m.start()
    return s[i:end], end + 1


def _parse_statements(s: str, i: int, terminators: Tuple[str, ...] = ()) -> Tuple[List[Stmt], int, str | None]:
    stmts: List[Stmt] = []
    term_hit: str | None = None
    n = len(s)
    while True:
        i0 = i
        j_scan = _skip_ws_and_comments(s, i)
        i = j_scan
        if i >= n:
            break
        # Check for terminators
        for tkw in terminators:
            if _starts_with_kw(s, i, tkw):
                term_hit = tkw
                return stmts, i, term_hit
        # IF statement
        if _starts_with_kw(s, i, "IF"):
            # consume IF
            i = _consume_kw(s, i, "IF")
            # condition until THEN
            cond_text, j = _read_until_kw(s, i, "THEN")
            cond = cond_text.strip()
            # consume THEN
            j2 = _consume_kw(s, j, "THEN")
            # parse THEN block until ELSE or END
            then_block, k, hit = _parse_statements(s, j2, terminators=("ELSE", "END"))
            else_block = None
            if hit == "ELSE":
                # consume ELSE
                k = _consume_kw(s, k, "ELSE")
                else_block, k, hit2 = _parse_statements(s, k, terminators=("END",))
                # next must be END
                hit = hit2
            if hit != "END":
                raise ValueError("Expected END after IF block")
            # consume END IF ;
            k = _consume_kw(s, k, "END")
            k = _consume_kw(s, k, "IF")
            k = _skip_ws_and_comments(s, k)
            if k < len(s) and s[k] == ";":
                k += 1
            stmts.append(IfStmt(condition_sql=cond, then_block=then_block, else_block=else_block))
            i = k
        else:
            # Raw SQL until semicolon
            sql, j = _read_until_semicolon(s, i0)
            if sql.strip():
                stmts.append(RawSQL(sql=sql + ";"))
            i = j
            # If we hit a terminator directly after semicolon, let the loop check it
    return stmts, i, term_hit


def parse_script(text: str) -> Script:
    stmts, pos, term = _parse_statements(text, 0)
    return Script(stmts=stmts)
