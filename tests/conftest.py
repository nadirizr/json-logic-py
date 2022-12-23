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
