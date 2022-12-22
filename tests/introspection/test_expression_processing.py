from textwrap import dedent

import pytest

from json_logic.meta import JSONLogicExpression, Operation, Var


@pytest.mark.parametrize(
    "expr",
    (None, "foo", 42, 0.05, True, False),
)
def test_expression_parser_primitives(expr):
    expression = JSONLogicExpression.from_expression(expr)

    assert expression.expression == expr
    assert expression.as_tree() == expr


def test_expression_parser_simple_operation():
    expression = JSONLogicExpression.from_expression({"var": ["foo"]})

    assert expression.expression == {"var": ["foo"]}
    assert expression.as_tree() == Var("var", ["foo"])


def test_expression_parser_simple_operation_syntactic_sugar():
    expression = JSONLogicExpression.from_expression({"var": "foo"})

    assert expression.expression == {"var": ["foo"]}
    assert expression.as_tree() == Var("var", ["foo"])


def test_complex_expression_into_tree_with_representation():
    complex_reduce = {
        ">": [
            {"reduce": [{"var": "kinderen"}, {"+": [{"var": "accumulator"}, 1]}, 0]},
            1,
        ]
    }
    expression = JSONLogicExpression.from_expression(complex_reduce)
    tree = expression.as_tree()

    expected_repr = dedent(
        """
        Operation(>)
          ├─ Operation(reduce)
          │    ├─ $kinderen
          │    ├─ Operation(+)
          │    │    ├─ $accumulator
          │    │    └─ 1
          │    └─ 0
          └─ 1
        """
    ).strip()
    assert repr(tree) == expected_repr


def test_complex_expression_into_tree_with_representation2():
    complex_and = {
        "and": [
            {"==": [{"var": "heeftUEenVanDezeUitkeringen.i"}, True]},
            {
                "or": [
                    {"==": [{"var": "heeftUEenVanDezeUitkeringen.a"}, True]},
                    {"==": [{"var": "heeftUEenVanDezeUitkeringen.b"}, True]},
                    {"==": [{"var": "heeftUEenVanDezeUitkeringen.c"}, True]},
                    {"==": [{"var": "heeftUEenVanDezeUitkeringen.d"}, True]},
                    {"==": [{"var": "heeftUEenVanDezeUitkeringen.e"}, True]},
                    {"==": [{"var": "heeftUEenVanDezeUitkeringen.f"}, True]},
                    {"==": [{"var": "heeftUEenVanDezeUitkeringen.g"}, True]},
                    {"==": [{"var": "heeftUEenVanDezeUitkeringen.h"}, True]},
                ]
            },
        ]
    }
    expression = JSONLogicExpression.from_expression(complex_and)
    tree = expression.as_tree()

    expected_repr = dedent(
        """
        Operation(and)
          ├─ Operation(==)
          │    ├─ $heeftUEenVanDezeUitkeringen.i
          │    └─ True
          └─ Operation(or)
               ├─ Operation(==)
               │    ├─ $heeftUEenVanDezeUitkeringen.a
               │    └─ True
               ├─ Operation(==)
               │    ├─ $heeftUEenVanDezeUitkeringen.b
               │    └─ True
               ├─ Operation(==)
               │    ├─ $heeftUEenVanDezeUitkeringen.c
               │    └─ True
               ├─ Operation(==)
               │    ├─ $heeftUEenVanDezeUitkeringen.d
               │    └─ True
               ├─ Operation(==)
               │    ├─ $heeftUEenVanDezeUitkeringen.e
               │    └─ True
               ├─ Operation(==)
               │    ├─ $heeftUEenVanDezeUitkeringen.f
               │    └─ True
               ├─ Operation(==)
               │    ├─ $heeftUEenVanDezeUitkeringen.g
               │    └─ True
               └─ Operation(==)
                    ├─ $heeftUEenVanDezeUitkeringen.h
                    └─ True

        """
    ).strip()
    assert repr(tree) == expected_repr


def test_if_elif():
    expr = {
        "if": [
            {"<": [{"var": "temp"}, 0]},
            "freezing",
            {"<": [{"var": "temp"}, 100]},
            "liquid",
            "gas",
        ]
    }
    expression = JSONLogicExpression.from_expression(expr)
    tree = expression.as_tree()

    expected_repr = dedent(
        """
        Conditional
          If
          ├─ Operation(<)
          │    ├─ $temp
          │    └─ 0
          └─ Then
               └─ 'freezing'
          Elif
          ├─ Operation(<)
          │    ├─ $temp
          │    └─ 100
          └─ Then
               └─ 'liquid'
          Else
          └─ 'gas'
        """
    ).strip()
    assert repr(tree) == expected_repr
