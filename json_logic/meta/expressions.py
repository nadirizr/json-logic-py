from dataclasses import dataclass
from typing import cast

from ..typing import JSON, Primitive
from .base import Operation

NormalizedExpression = dict[str, list[JSON]]


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
