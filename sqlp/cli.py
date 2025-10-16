from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .parser import parse_script
from .executor import Executor
from .compiler import Compiler


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def cmd_run(args: argparse.Namespace) -> int:
    text = _read_text(args.file)
    script = parse_script(text)
    ex = Executor(engine="duckdb")
    conn = ex.execute(script)
    if args.verbose:
        # Print all tables in memory for debugging
        try:
            res = conn.execute("select table_name from information_schema.tables where table_schema = 'main' order by 1").fetchall()
            print("-- Tables:")
            for r in res:
                print(r[0])
        except Exception:
            pass
    return 0


def cmd_transpile(args: argparse.Namespace) -> int:
    text = _read_text(args.file)
    script = parse_script(text)
    comp = Compiler(target=args.target)
    out = comp.transpile(script)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
        if not out.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sqlp", description="SQL+: runtime IF/ELSE and transpiler")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Parse and execute a SQL+ file against DuckDB (in-memory)")
    pr.add_argument("file", help="Path to .sqlp or .sql file")
    pr.add_argument("--verbose", action="store_true", help="Print debug info after execution")
    pr.set_defaults(func=cmd_run)

    pt = sub.add_parser("transpile", help="Transpile SQL+ to target SQL (best-effort)")
    pt.add_argument("file", help="Path to .sqlp or .sql file")
    pt.add_argument("--target", choices=["postgres", "duckdb"], default="postgres")
    pt.add_argument("--output", "-o", help="Write to file instead of stdout")
    pt.set_defaults(func=cmd_transpile)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

