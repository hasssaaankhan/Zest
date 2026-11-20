"""The shapes a Zest program can take once it has been read."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


class Node:
    pass


# ---- values ---------------------------------------------------------------

@dataclass
class Literal(Node):
    value: Any
    line: int = 0
    col: int = 0


@dataclass
class Text(Node):
    parts: List[Any]  # plain strings and expression nodes, in order
    line: int = 0
    col: int = 0


@dataclass
class Name(Node):
    name: str
    line: int = 0
    col: int = 0


@dataclass
class ListLit(Node):
    items: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class MapLit(Node):
    pairs: List[Tuple[Node, Node]]
    line: int = 0
    col: int = 0


# ---- expressions ----------------------------------------------------------

@dataclass
class Unary(Node):
    op: str
    operand: Node
    line: int = 0
    col: int = 0


@dataclass
class Binary(Node):
    op: str
    left: Node
    right: Node
    line: int = 0
    col: int = 0


@dataclass
class Compare(Node):
    op: str
    left: Node
    right: Node
    line: int = 0
    col: int = 0


@dataclass
class Logic(Node):
    op: str  # "and" or "or"
    left: Node
    right: Node
    line: int = 0
    col: int = 0


@dataclass
class Call(Node):
    callee: Node
    args: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class Index(Node):
    target: Node
    index: Node
    line: int = 0
    col: int = 0


@dataclass
class Field(Node):
    target: Node
    name: str
    line: int = 0
    col: int = 0


# ---- statements -----------------------------------------------------------

@dataclass
class Assign(Node):
    target: Node  # Name, Index or Field
    op: str       # "=", "+=", "-=", "*=", "/="
    value: Node
    line: int = 0
    col: int = 0


@dataclass
class Say(Node):
    args: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class If(Node):
    cond: Node
    then: List[Node]
    orelse: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class While(Node):
    cond: Node
    body: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class Repeat(Node):
    count: Node
    body: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class ForEach(Node):
    var: str
    iterable: Node
    body: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class ForRange(Node):
    var: str
    start: Node
    stop: Node
    step: Optional[Node]
    body: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class Param(Node):
    name: str
    default: Optional[Node] = None
    line: int = 0
    col: int = 0


@dataclass
class Def(Node):
    name: str
    params: List[Param]
    body: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class Give(Node):
    value: Optional[Node]
    line: int = 0
    col: int = 0


@dataclass
class Stop(Node):
    line: int = 0
    col: int = 0


@dataclass
class Skip(Node):
    line: int = 0
    col: int = 0


@dataclass
class Try(Node):
    body: List[Node]
    name: Optional[str]
    handler: List[Node]
    line: int = 0
    col: int = 0


@dataclass
class Fail(Node):
    value: Node
    line: int = 0
    col: int = 0


@dataclass
class Use(Node):
    path: str
    line: int = 0
    col: int = 0


@dataclass
class ExprStmt(Node):
    expr: Node
    line: int = 0
    col: int = 0
