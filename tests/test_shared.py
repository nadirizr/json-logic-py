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
