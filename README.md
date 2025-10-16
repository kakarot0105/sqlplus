SQL+
====

SQL+ is a tiny superset of SQL adding a single control-flow construct at the top level:

  IF <condition> THEN
    <statements>
  ELSE
    <statements>
  END IF;

Goals
-----
- Preserve plain SQL: raw statements pass through unchanged.
- Provide a runtime executor to evaluate IF conditions and run only the THEN/ELSE branch using DuckDB (in-memory by default).
- Provide a simple transpiler that emits a best-effort SQL rewrite for downstream engines (Postgres today).

Quickstart
----------

1) Create a virtual environment and install:

  python -m venv .venv
  source .venv/bin/activate
  pip install -e .

2) Run the example:

  sqlp run examples/demo.sqlp

3) Transpile to Postgres SQL (best-effort):

  sqlp transpile --target=postgres examples/demo.sqlp

4) Run tests:

  pytest -q

Streamlit App (Local UI)
------------------------
This repo includes a simple local UI to upload datasets and run SQL or SQL+ queries using DuckDB in-memory.

Run it with:

  streamlit run sqlp/app/app.py

Features:
- Upload CSV / Parquet / JSON.
- Preview uploaded data.
- Auto-register table name from filename.
- SQL editor prefilled with `SELECT * FROM <table> LIMIT 10`.
- Choose engine: DuckDB SQL or SQL+ runtime (DuckDB backend).
- Run query and view results.
- Download results as CSV.

Notes on semantics
------------------
- Conditions: If the condition starts with SELECT or WITH, the executor runs it and interprets the first cell of the first row for truthiness. Otherwise, the executor wraps the condition as SELECT (<expr>) to evaluate.
- Truthiness: booleans use their value; numbers treat 0/0.0 as false; NULL/None is false; anything else uses Python truthiness.
- Transpile: Emitted SQL uses a minimal CTE wrapper plus commented THEN/ELSE blocks. It is intended for inspection or further tooling, not guaranteed to execute the same control flow in Postgres/DuckDB for arbitrary statements (especially DDL). The runtime executor is the authoritative execution path.

Example
-------
See examples/demo.sqlp

Repository Hygiene
------------------
- Code lives under sqlp/ with modules: grammar, parser, ast, executor, compiler, cli.
- Tests are under tests/ using pytest.
- VS Code configs under .vscode/ for running tests and the example.
