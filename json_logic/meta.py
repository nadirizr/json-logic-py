"""
Meta module for json-logic.

This module implements the tooling to convert between JSON and python datastructures
for json-logic expressions. The Python datastructures provider richer introspection
potential to (statically) analyze JSON logic expressions.
"""

from dataclasses import dataclass, field
from textwrap import indent
from typing import Union

from . import operations
from .typing import Primitive

OperationArgument = Union[Primitive, "Operation"]


def _repr_arg(arg: "OperationArgument", prefix: str) -> str:
    lines = repr(arg).splitlines()
    assert len(lines) >= 1
    result = f"{prefix} {lines[0]}"
    rest = "\n".join(lines[1:])
    if rest:
        rest = indent(rest, "  │  ")
        result = f"{result}\n{rest}"
    return result


@dataclass(repr=False)
class Operation:
    operator: str
    """
    The operator of the operation.

    This should be a supported operation in :attr:`json_logic.operations`.
    """
    arguments: list[OperationArgument] = field(default_factory=list)
    """
    List of arguments for the operation.

    Note that an argument can itself be an operation, or it may be a literal expression
    (taking the form of a JSON primitive).

    Evaluation happens depth-first in case an argument is an operation itself.
    """

    def __post_init__(self):
        if self.operator not in operations:
            raise ValueError(
                f"Operator '{self.operator}' is unknown (unregistered in "
                "'json_logic.operations')."
            )

    def __repr__(self):
        clsname = self.__class__.__qualname__

        prefixed_args = [f"{_repr_arg(arg, '  ├─')}" for arg in self.arguments[:-1]] + [
            f"{_repr_arg(arg, '  └─')}" for arg in self.arguments[-1:]
        ]
        args_repr = "\n".join(prefixed_args)
        op_repr = f"{clsname}({self.operator})"

        if args_repr:
            op_repr = f"{op_repr}\n{args_repr}"
        return op_repr
