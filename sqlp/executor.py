from __future__ import annotations

import re
from typing import Optional

import duckdb

from .ast import Script, RawSQL, IfStmt, Stmt


class Executor:
    def __init__(self, engine: str = "duckdb") -> None:
        if engine != "duckdb":
            raise NotImplementedError("Only duckdb engine is supported for runtime execution in MVP.")
        self.engine = engine

    def _ensure_conn(self, conn: Optional[duckdb.DuckDBPyConnection]) -> duckdb.DuckDBPyConnection:
        return conn or duckdb.connect(database=":memory:")

    def execute(self, script: Script, conn: Optional[duckdb.DuckDBPyConnection] = None) -> duckdb.DuckDBPyConnection:
        conn = self._ensure_conn(conn)
        self._exec_stmts(script.stmts, conn)
        return conn

    def _exec_stmts(self, stmts: list[Stmt], conn: duckdb.DuckDBPyConnection) -> None:
        for s in stmts:
            if isinstance(s, RawSQL):
                self._exec_raw(s, conn)
            elif isinstance(s, IfStmt):
                self._exec_if(s, conn)
            else:
                raise TypeError(f"Unknown statement type: {type(s)}")

    def _exec_raw(self, raw: RawSQL, conn: duckdb.DuckDBPyConnection) -> None:
        sql = raw.sql
        conn.execute(sql)

    def _exec_if(self, node: IfStmt, conn: duckdb.DuckDBPyConnection) -> None:
        cond = node.condition_sql.strip()
        # Determine if cond is a SELECT/WITH; otherwise wrap as SELECT (expr)
        if re.match(r"(?is)^(SELECT|WITH)\b", cond):
            q = cond
        else:
            q = f"SELECT ({cond})"

        res = conn.execute(q).fetchone()
        val = res[0] if res is not None else None
        truthy = self._truthy(val)
        if truthy:
            self._exec_stmts(node.then_block, conn)
        else:
            if node.else_block is not None:
                self._exec_stmts(node.else_block, conn)

    @staticmethod
    def _truthy(val) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0 and val is not False
        return bool(val)

