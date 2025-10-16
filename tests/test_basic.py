import duckdb
import re

from sqlp import parse_script, Executor, Compiler


def run_and_fetch(conn: duckdb.DuckDBPyConnection, q: str):
    return conn.execute(q).fetchall()


def test_if_then_true_executes_then_branch():
    text = """
    IF 1=1 THEN
      CREATE TABLE t (i INTEGER);
      INSERT INTO t VALUES (1);
    ELSE
      CREATE TABLE t (i INTEGER);
      INSERT INTO t VALUES (2);
    END IF;
    """
    script = parse_script(text)
    conn = Executor().execute(script)
    rows = run_and_fetch(conn, "SELECT * FROM t")
    assert rows == [(1,)]


def test_if_then_false_executes_else_branch():
    text = """
    IF 1=0 THEN
      CREATE TABLE t (i INTEGER);
      INSERT INTO t VALUES (1);
    ELSE
      CREATE TABLE t (i INTEGER);
      INSERT INTO t VALUES (2);
    END IF;
    """
    script = parse_script(text)
    conn = Executor().execute(script)
    rows = run_and_fetch(conn, "SELECT * FROM t")
    assert rows == [(2,)]


def test_plain_sql_passthrough_in_transpile():
    text = """
    CREATE TABLE x (i INTEGER);
    INSERT INTO x VALUES (42);
    """.strip()
    script = parse_script(text)
    out = Compiler(target="postgres").transpile(script)
    # Output should be the same text with semicolons preserved and joining by newlines
    assert out.strip() == text

