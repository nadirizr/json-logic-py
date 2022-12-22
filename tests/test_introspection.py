from textwrap import dedent

import pytest

from json_logic.meta import Operation


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


def test_unknown_operator():
    with pytest.raises(ValueError):
        Operation("some-wordsalad that is highly unlikely to be an operation")
