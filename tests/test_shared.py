import json
import unittest
from urllib.request import urlopen

from json_logic import jsonLogic


class SharedTests(unittest.TestCase):
    """This runs the tests from http://jsonlogic.com/tests.json."""

    cnt = 0

    @classmethod
    def create_test(cls, logic, data, expected):
        """Adds new test to the class."""

        # TODO currently unsupported operators, skip tests
        unsupported_operators = [
            "filter",
            "map",
            "reduce",
            "all",
            "none",
            "some",
            "substr",
        ]
        if isinstance(logic, dict):
            for operator in unsupported_operators:
                if operator in logic:
                    return

        # TODO currently unsupported handling of empty variables, skip tests
        unsupported_logic = [{"var": ""}, {"var": None}, {"var": []}]
        if logic in unsupported_logic:
            return

        def test(self):
            """Actual test function."""
            self.assertEqual(jsonLogic(logic, data), expected)

        test.__doc__ = "{},  {}  =>  {}".format(logic, data, expected)
        setattr(cls, "test_{}".format(cls.cnt), test)
        cls.cnt += 1


SHARED_TESTS = json.loads(
    urlopen("http://jsonlogic.com/tests.json").read().decode("utf-8")
)
for item in SHARED_TESTS:
    if isinstance(item, list):
        SharedTests.create_test(*item)
