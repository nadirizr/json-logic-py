"""
Meta module for json-logic.

This module implements the tooling to convert between JSON and python datastructures
for json-logic expressions. The Python datastructures provider richer introspection
potential to (statically) analyze JSON logic expressions.
"""

from dataclasses import dataclass, field
from typing import Union, cast

from . import operations
from .typing import JSON, Primitive

OperationArgument = Union[Primitive, "Operation"]

NormalizedExpression = dict[str, list[JSON]]


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
        bits = [self.op_repr]

        last_index = len(self.arguments) - 1
        for index, child in enumerate(self.arguments):
            first_prefix = "  ├─" if index != last_index else "  └─"
            separator = "  │ " if index != last_index else "    "
            child_tree = repr(child).splitlines()
            child_bits = [f"{first_prefix} {child_tree[0]}"] + [
                f"{separator} {line}" for line in child_tree[1:]
            ]
            bits.append("\n".join(child_bits))
        return "\n".join(bits)

    @property
    def op_repr(self) -> str:
        clsname = self.__class__.__qualname__
        return f"{clsname}({self.operator})"

    @classmethod
    def for_operator(cls, operator: str, *args, **kwargs):
        operator_cls = OPERATION_MAP.get(operator, cls)
        return operator_cls(operator, *args, **kwargs)


class Var(Operation):
    _check_registered = False

    def __repr__(self):
        return f"${self.arguments[0]}"


class If(Operation):
    def __repr__(self):
        if (num_args := len(self.arguments)) <= 2:  # simple if arg0 then arg1 else arg2
            return super().__repr__()

        bits = ["Conditional"]
        # loop over groups of two which map to 'if x1 then x2'
        for i in range(0, num_args - 1, 2):
            condition, outcome = self.arguments[i : i + 2]
            condition_tree = repr(condition).splitlines()
            outcome_tree = repr(outcome).splitlines()

            bits += [
                "  If" if i == 0 else "  Elif",
                f"  ├─ {condition_tree[0]}",
                *[f"  │  {line}" for line in condition_tree[1:]],
                "  └─ Then",
                f"       └─ {outcome_tree[0]}",
                *[f"          {line}" for line in outcome_tree[1:]],
            ]

        if num_args % 2 == 1:
            else_tree = repr(self.arguments[-1]).splitlines()
            bits += [
                "  Else",
                f"  └─ {else_tree[0]}",
                *[f"     {line}" for line in else_tree[1:]],
            ]

        return "\n".join(bits)


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
    def from_expression(cls, expression: JSON) -> "JSONLogicExpression":
        normalized = cls.normalize(expression)
        return cls(normalized)

    def as_tree(self) -> Operation | Primitive | list:
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
    "if": If,
}


# TODO: operators
# missing
# missing_some
