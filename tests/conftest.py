import json
from functools import cache
from typing import Annotated
from urllib.request import urlopen

import pytest

JSON = str | int | float | bool | None | list["JSON"] | dict[str, "JSON"]


@cache
def _load_shared_tests() -> list[Annotated[list[JSON], 3]]:
    response = urlopen("http://jsonlogic.com/tests.json")
    items = json.loads(response.read().decode("utf-8"))
    return [item for item in items if isinstance(item, list)]


@pytest.fixture(scope="session")
def shared_tests() -> list[Annotated[list[JSON], 3]]:
    return _load_shared_tests()


def pytest_generate_tests(metafunc):
    if "shared_test" in metafunc.fixturenames:
        shared_tests = _load_shared_tests()
        metafunc.parametrize("shared_test", shared_tests)


# TODO currently unsupported operators, skip tests
def _handle_unsupported_operators(item, logic: dict):
    unsupported_operators = sum(
        [mark.args[0] for mark in item.iter_markers(name="unsupported_operators")],
        [],
    )
    for operator in unsupported_operators:
        if operator in logic:
            pytest.skip(reason=f"Operator '{operator}' is not supported yet.")


def _handle_unsupported_logic(item, logic: dict):
    unsupported_logic = sum(
        [mark.args[0] for mark in item.iter_markers(name="unsupported_logic")],
        [],
    )
    if logic in unsupported_logic:
        pytest.skip(reason=f"Logic {logic!r} is not supported yet.")


def pytest_runtest_setup(item):
    if "shared_test" not in item.fixturenames:
        return

    logic, _, _ = item.callspec.params["shared_test"]
    if not isinstance(logic, dict):
        return

    _handle_unsupported_operators(item, logic)
    _handle_unsupported_logic(item, logic)
