from textwrap import dedent

import pytest

from json_logic.meta import JSONLogicExpression, Operation, Var


def test_representation_simple_operation():
    op1 = Operation("==", [10, "foo"])

    expected = dedent(
        """
        Operation(==)
          ├─ 10
          └─ 'foo'
    """
    ).strip()
    assert repr(op1) == expected


def test_representation_nested_operations():
    op1 = Operation("+", [10, 5])
    op2 = Operation("==", [op1, 15])

    expected = dedent(
        """
        Operation(==)
          ├─ Operation(+)
          │    ├─ 10
          │    └─ 5
          └─ 15
    """
    ).strip()

    assert repr(op2) == expected


def test_representation_var():
    var_foo = Var("var", ["foo"])

    assert repr(var_foo) == "$foo"


def test_unknown_operator():
    with pytest.raises(ValueError):
        Operation("some-wordsalad that is highly unlikely to be an operation")


@pytest.mark.parametrize(
    "expr",
    (None, "foo", 42, 0.05, True, False),
)
def test_expression_parser_primitives(expr):
    expression = JSONLogicExpression.from_expression(expr)

    assert expression.expression == expr


def test_expression_parser_simple_operation():
    expression = JSONLogicExpression.from_expression({"var": ["foo"]})

    assert expression.expression == {"var": ["foo"]}


def test_expression_parser_simple_operation_syntactic_sugar():
    expression = JSONLogicExpression.from_expression({"var": "foo"})

    assert expression.expression == {"var": ["foo"]}


def test_parse_simple_expression_into_tree():
    expression = JSONLogicExpression.from_expression({"var": ["foo"]})

    tree = expression.as_tree()

    expected_tree = Var("var", ["foo"])
    assert tree == expected_tree


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
