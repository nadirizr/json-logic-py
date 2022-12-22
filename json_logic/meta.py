"""
Meta module for json-logic.

This module implements the tooling to convert between JSON and python datastructures
for json-logic expressions. The Python datastructures provider richer introspection
potential to (statically) analyze JSON logic expressions.
"""

from dataclasses import dataclass, field
from textwrap import indent
from typing import Union, cast

from . import operations
from .typing import JSON, Primitive

OperationArgument = Union[Primitive, "Operation"]

NormalizedExpression = dict[str, list[JSON]]


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
    _check_registered: bool = field(init=False, default=True)

    def __post_init__(self):
        if self._check_registered and self.operator not in operations:
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

    @classmethod
    def for_operator(cls, operator: str, *args, **kwargs):
        operator_cls = OPERATION_MAP.get(operator, cls)
        return operator_cls(operator, *args, **kwargs)


class Var(Operation):
    _check_registered = False

    def __repr__(self):
        return f"${self.arguments[0]}"


def destructure(expression: NormalizedExpression) -> tuple[str, list[JSON]]:
    """
    Decompose a normalized expression into the operator and arguments.
    """
    # TODO: reliable way to read/extract the operator if we add extensions
    # to expressions
    operator = list(expression.keys())[0]
    values = expression[operator]
    return (operator, values)


@dataclass
class JSONLogicExpression:
    expression: NormalizedExpression | Primitive | list[JSON]

    @staticmethod
    def normalize(expression: JSON) -> NormalizedExpression | Primitive | list[JSON]:
        """
        Remove syntactic sugar for unary operators.

        Normalization happens only on the provided expression, not on nested
        expressions inside.
        """
        # we only normalize one level at a time
        if isinstance(expression, (list, Primitive)):
            return cast(Primitive | list, expression)

        assert isinstance(expression, dict)

        operator, values = destructure(cast(dict, expression))
        if not isinstance(values, list):
            values = [values]

        # make sure to keep any additional extension keys
        return cast(NormalizedExpression, {**expression, operator: values})

    @classmethod
    def from_expression(cls, expression: JSON):
        normalized = cls.normalize(expression)
        return cls(normalized)

    def as_tree(self):
        """
        Convert the JSON expression into a tree with Operation nodes.
        """
        if isinstance(self.expression, Primitive):
            return self.expression

        if isinstance(self.expression, list):
            return [self.from_expression(child).as_tree() for child in self.expression]

        assert isinstance(self.expression, dict)
        operator, values = destructure(self.expression)
        arguments = [
            JSONLogicExpression.from_expression(value).as_tree() for value in values
        ]
        return Operation.for_operator(operator, arguments=arguments)


OPERATION_MAP = {
    "var": Var,
}
