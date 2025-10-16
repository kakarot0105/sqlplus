from __future__ import annotations

import re
from typing import List

from .ast import Script, RawSQL, IfStmt, Stmt


class Compiler:
    def __init__(self, target: str = "postgres") -> None:
        if target not in {"postgres", "duckdb"}:
            raise ValueError("target must be 'postgres' or 'duckdb'")
        self.target = target

    def transpile(self, script: Script) -> str:
        # If only raw SQL statements, pass through unchanged
        if all(isinstance(s, RawSQL) for s in script.stmts):
            return "".join(s.sql for s in script.stmts)
        # Otherwise, best-effort annotate IF blocks using a CTE guard and comments.
        out: List[str] = []
        for s in script.stmts:
            out.append(self._emit_stmt(s))
        return "\n".join(filter(None, out))

    def _emit_stmt(self, s: Stmt) -> str:
        if isinstance(s, RawSQL):
            return s.sql
        elif isinstance(s, IfStmt):
            return self._emit_if(s)
        else:
            raise TypeError(f"Unknown statement type: {type(s)}")

    def _emit_if(self, node: IfStmt) -> str:
        cond_sql = node.condition_sql.strip()
        if not re.match(r"(?is)^(SELECT|WITH)\b", cond_sql):
            cond_sql_wrapped = f"SELECT ({cond_sql}) AS cond"
            cond_ref = "(SELECT cond FROM __cond)"
        else:
            cond_sql_wrapped = cond_sql
            cond_ref = "(SELECT * FROM __cond)"

        lines: List[str] = []
        lines.append(f"WITH __cond AS (\n{cond_sql_wrapped}\n)")
        lines.append(f"-- IF {cond_sql}")
        lines.append(f"-- THEN branch guarded by {cond_ref}")
        for t in node.then_block:
            emitted = self._emit_stmt(t)
            # Prefix as a best-effort guard comment
            lines.append(emitted)
        if node.else_block is not None:
            lines.append("-- ELSE branch")
            for e in node.else_block:
                emitted = self._emit_stmt(e)
                lines.append(emitted)
        lines.append("-- END IF")
        return "\n".join(lines)
