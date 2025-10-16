from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class RawSQL:
    sql: str  # includes trailing semicolon


@dataclass
class IfStmt:
    condition_sql: str  # raw SQL snippet (no trailing THEN)
    then_block: List[Union["IfStmt", RawSQL]]
    else_block: Optional[List[Union["IfStmt", RawSQL]]] = None


Stmt = Union[IfStmt, RawSQL]


@dataclass
class Script:
    stmts: List[Stmt]

