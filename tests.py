"""JonLogic tests."""

from __future__ import unicode_literals

import json
import logging
import unittest
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen
from json_logic import jsonLogic, is_logic, operations
from json_logic import \
    _logical_operations, \
    _scoped_operations, \
    _data_operations, \
    _common_operations, \
    _unsupported_operations


# Python 2 fallback
if not hasattr(unittest.TestCase, 'assertRaisesRegex'):
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp


# Fallback for Python versions prior to 3.4
class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs."""

    def __init__(self, *args, **kwargs):
        self.messages = dict(
            debug=[], info=[], warning=[], error=[], critical=[])
        super(MockLoggingHandler, self).__init__(*args, **kwargs)

    def emit(self, record):
        try:
            self.messages[record.levelname.lower()].append(record.getMessage())
        except Exception:
            self.handleError(record)

    def reset(self):
        for logging_level in self.messages.keys():
            self.messages[logging_level] = []


class SharedJsonLogicTests(unittest.TestCase):
    """Shared tests from from http://jsonlogic.com/tests.json."""

    cnt = 0

    @classmethod
    def create_test(cls, logic, data, expected):
        """Add new test to the class."""

        def test(self):
            """Actual test function."""
            self.assertEqual(jsonLogic(logic, data), expected)

        test.__doc__ = "{},  {}  =>  {}".format(logic, data, expected)
        setattr(cls, "test_{}".format(cls.cnt), test)
        cls.cnt += 1


SHARED_TESTS = json.loads(
    urlopen("http://jsonlogic.com/tests.json").read().decode('utf-8'))

for item in SHARED_TESTS:
    if isinstance(item, list):
        SharedJsonLogicTests.create_test(*item)


class SpecificJsonLogicTest(unittest.TestCase):
    """Specific JsonLogic tests that are not included into the shared list."""

    @classmethod
    def setUpClass(cls):
        super(SpecificJsonLogicTest, cls).setUpClass()
        mock_logger = logging.getLogger('json_logic')
        mock_logger.setLevel(logging.DEBUG)
        cls.mock_logger_handler = MockLoggingHandler()
        mock_logger.addHandler(cls.mock_logger_handler)
        cls.log_messages = cls.mock_logger_handler.messages

    def setUp(self):
        super(SpecificJsonLogicTest, self).setUp()
        self.mock_logger_handler.reset()

    @classmethod
    def tearDownClass(cls):
        mock_logger = logging.getLogger('json_logic')
        mock_logger.removeHandler(cls.mock_logger_handler)
        super(SpecificJsonLogicTest, cls).tearDownClass()

    def test_bad_operator(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized operation"):
            self.assertFalse(jsonLogic({'fubar': []}))

    def test_array_of_logic_entries(self):
        logic = [
            {'+': [1, 2]},
            {'var': 'a'},
            {'if': [{'>': [1, 2]}, 'yes', 'no']},
            "just some data"
        ]
        self.assertSequenceEqual(
            jsonLogic(logic, {'a': "test"}),
            [3, "test", "no", "just some data"])

    def test_single_non_logic_dictionary_can_be_passed_through(self):
        logic = {'test': 1, 'data': 'single'}
        self.assertEqual(jsonLogic(logic), {'test': 1, 'data': 'single'})

    def test_array_of_logic_entries_can_return_non_logic_dictionaries(self):
        logic = [
            {'+': [1, 2]},
            {'test': 1, 'data': 'if'}
        ]
        self.assertSequenceEqual(
            jsonLogic(logic),
            [3, {'test': 1, 'data': 'if'}])

    def test_if_can_return_non_logic_dictionaries(self):
        logic = {'if': [
            {'==': [{'var': 'a'}, 1]},
            {'test': 1, 'data': 'if'},
            {'==': [{'var': 'a'}, 2]},
            {'test': 2, 'data': 'else if'},
            {'test': 3, 'data': 'else'}
        ]}
        self.assertEqual(
            jsonLogic(logic, {'a': 1}), {'test': 1, 'data': 'if'})
        self.assertEqual(
            jsonLogic(logic, {'a': 2}), {'test': 2, 'data': 'else if'})
        self.assertEqual(
            jsonLogic(logic, {'a': 3}), {'test': 3, 'data': 'else'})

    def test_iif_can_return_non_logic_dictionaries(self):
        logic = {'?:': [
            {'==': [{'var': 'a'}, 1]},
            {'test': 1, 'data': 'if'},
            {'test': 2, 'data': 'else'}
        ]}
        self.assertEqual(
            jsonLogic(logic, {'a': 1}), {'test': 1, 'data': 'if'})
        self.assertEqual(
            jsonLogic(logic, {'a': 2}), {'test': 2, 'data': 'else'})

    def test_log_forwards_first_argument_to_logging_module_at_info_level(self):
        # with self.assertLogs('json_logic', logging.INFO) as log:
        jsonLogic({'log': 'apple'})
        jsonLogic({'log': 1})
        jsonLogic({'log': True})
        self.assertEqual(len(self.log_messages['info']), 3)
        self.assertIn('apple', self.log_messages['info'][0])
        self.assertIn('1', self.log_messages['info'][1])
        self.assertIn('True', self.log_messages['info'][2])

    def test_log_returns_unmodified_first_argument(self):
        self.assertEqual(jsonLogic({'log': 'apple'}), 'apple')
        self.assertEqual(jsonLogic({'log': 1}), 1)
        self.assertEqual(jsonLogic({'log': True}), True)

    def test_strict_equality_ignores_numeric_type_differences(self):
        self.assertIs(jsonLogic({'===': [1, 1]}), True)
        self.assertIs(jsonLogic({'===': [1.23, 1.23]}), True)
        self.assertIs(jsonLogic({'===': [1, 1.0]}), True)
        self.assertIs(
            jsonLogic({'===': [10000000000000000000, 10000000000000000000.0]}),
            True)

    def test_arithmetic_operations_convert_data_to_apropriate_numerics(self):
        # Conversion
        self.assertIs(jsonLogic({'+': [1]}), 1)
        self.assertIs(jsonLogic({'+': [1.0]}), 1)
        self.assertIs(jsonLogic({'+': ["1"]}), 1)
        self.assertIs(jsonLogic({'+': ["1.0"]}), 1)
        self.assertEqual(jsonLogic({'+': [1.23]}), 1.23)
        self.assertEqual(jsonLogic({'+': ["1.23"]}), 1.23)
        self.assertEqual(
            jsonLogic({'+': [10000000000000000000]}), 10000000000000000000)
        # Arithmetic operations
        self.assertIs(jsonLogic({'+': [1, 1]}), 2)
        self.assertIs(jsonLogic({'+': [0.25, 0.75]}), 1)
        self.assertEqual(jsonLogic({'+': [1, 0.75]}), 1.75)
        self.assertIs(jsonLogic({'-': [1, 1]}), 0)
        self.assertIs(jsonLogic({'-': [1.75, 0.75]}), 1)
        self.assertEqual(jsonLogic({'-': [1, 0.75]}), 0.25)
        self.assertIs(jsonLogic({'*': [1, 2]}), 2)
        self.assertIs(jsonLogic({'*': [2, 0.5]}), 1)
        self.assertEqual(jsonLogic({'*': [2, 0.75]}), 1.5)
        self.assertIs(jsonLogic({'/': [2, 2]}), 1)
        self.assertEqual(jsonLogic({'/': [2, 4]}), 0.5)
        self.assertIs(jsonLogic({'/': [2, 0.5]}), 4)
        self.assertIs(jsonLogic({'%': [2, 2]}), 0)
        self.assertIs(jsonLogic({'%': [4, 3]}), 1)
        self.assertEqual(jsonLogic({'%': [2, 1.5]}), 0.5)

    def test_is_logic_function(self):
        # Returns True for logic entries
        self.assertTrue(is_logic({'>': [2, 1]}))
        self.assertTrue(is_logic({'+': [1, 2]}))
        # Returns False for non-logic entries
        self.assertFalse(is_logic(5))
        self.assertFalse(is_logic(True))
        self.assertFalse(is_logic([1, 2, 3]))
        self.assertFalse(is_logic({}))
        self.assertFalse(is_logic({'two': 'keys', 'per': 'dictionary'}))
        # Array of logic entries is not considered a logic entry itself
        self.assertFalse(is_logic([{'>': [2, 1]}, {'+': [1, 2]}]))

    def test_operations_value_exposes_all_operations(self):
        exposable_operations = (
            _logical_operations,
            _scoped_operations,
            _data_operations,
            _common_operations,
            _unsupported_operations)
        for exposable_operation_dict in exposable_operations:
            for operation_name, function in exposable_operation_dict.items():
                self.assertIn(
                    operation_name, operations,
                    "Operation %r is not exposed" % operation_name)

    def test_operations_value_exposes_correct_functions(self):
        exposable_operations = (
            _logical_operations,
            _scoped_operations,
            _data_operations,
            _common_operations,
            _unsupported_operations)
        for exposable_operation_dict in exposable_operations:
            for operation_name, function in exposable_operation_dict.items():
                self.assertIs(
                    function, operations[operation_name],
                    "Invalid function exposed for %r" % operation_name)

    def test_operations_value_modifications_do_not_impact_fuctionality(self):
        global operations
        old_operations = operations
        try:
            operations['+'] = lambda *args: "Ha-ha!"
            result = jsonLogic({'+': [1, 2]})
            self.assertNotEqual(result, "Ha-ha!")
            self.assertEqual(result, 3)
        finally:
            operations = old_operations  # Restore exposed operations list


if __name__ == '__main__':
    unittest.main()
