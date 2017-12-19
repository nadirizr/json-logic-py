"""JonLogic tests."""

from __future__ import unicode_literals

import json
import logging
import datetime
import unittest
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen
from json_logic import \
    jsonLogic, \
    is_logic, \
    uses_data, \
    rule_like, \
    operations, \
    add_operation, \
    rm_operation
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


def shared_test(function, url):
    """Class UnitTest class decorator for shared tests."""

    def create_test(cls, count, arg1, arg2, expected):
        def test(self):
            self.assertEqual(function(arg1, arg2), expected)
        test.__doc__ = "{},  {}  =>  {}".format(arg1, arg2, expected)
        setattr(cls, "test_{}".format(count), test)

    def class_decorator(cls):
        shared_tests = json.loads(urlopen(url).read().decode('utf-8'))
        count = 0
        for entry in shared_tests:
            if isinstance(entry, list):
                count += 1
                create_test(cls, count, *entry)
        return cls

    return class_decorator


@shared_test(jsonLogic, 'http://jsonlogic.com/tests.json')
class SharedJsonLogicTests(unittest.TestCase):
    """Shared JsonLogic tests."""


@shared_test(rule_like, 'http://jsonlogic.com/rule_like.json')
class SharedRuleLikeTests(unittest.TestCase):
    """Shared 'rule_like' tests."""


class AdditionalJsonLogicTests(unittest.TestCase):
    """Additional JsonLogic tests not included into the shared list."""

    @classmethod
    def setUpClass(cls):
        super(AdditionalJsonLogicTests, cls).setUpClass()
        mock_logger = logging.getLogger('json_logic')
        mock_logger.setLevel(logging.DEBUG)
        cls.mock_logger_handler = MockLoggingHandler()
        mock_logger.addHandler(cls.mock_logger_handler)
        cls.log_messages = cls.mock_logger_handler.messages

    def setUp(self):
        super(AdditionalJsonLogicTests, self).setUp()
        self.mock_logger_handler.reset()

    @classmethod
    def tearDownClass(cls):
        mock_logger = logging.getLogger('json_logic')
        mock_logger.removeHandler(cls.mock_logger_handler)
        super(AdditionalJsonLogicTests, cls).tearDownClass()

    def test_bad_operator(self):
        self.assertRaisesRegex(
            ValueError, "Unrecognized operation",
            jsonLogic, {'fubar': []})

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

    def test_method_operation_with_method_without_arguments(self):
        todays_date = datetime.date.today()
        logic = {'method': [{'var': 'today'}, 'isoformat']}
        data = {'today': todays_date}
        returned_value = jsonLogic(logic, data)
        self.assertIsInstance(returned_value, str)
        self.assertEqual(returned_value, todays_date.isoformat())

    def test_method_operation_with_method_with_arguments(self):
        logic = {'method': ['string value', 'split', [' ']]}
        returned_value = jsonLogic(logic)
        self.assertIsInstance(returned_value, list)
        self.assertSequenceEqual(returned_value, ['string', 'value'])

    def test_method_operation_with_property(self):
        todays_date = datetime.date.today()
        logic = {'method': [{'var': 'today'}, 'month']}
        data = {'today': todays_date}
        returned_value = jsonLogic(logic, data)
        self.assertIsInstance(returned_value, int)
        self.assertEqual(returned_value, todays_date.month)

    def test_if_operator_does_not_evaluate_depth_first(self):
        # 'if' operation should stop at first truthy condition.
        # Consequents of falsy conditions should not be evaluated.
        conditions = []
        consequents = []

        def push_if(arg):
            conditions.append(arg)
            return arg

        def push_then(arg):
            consequents.append(arg)
            return arg

        def push_else(arg):
            consequents.append(arg)
            return arg

        add_operation('push_if', push_if)
        add_operation('push_then', push_then)
        add_operation('push_else', push_else)

        jsonLogic({'if': [
            {'push_if': [True]},
            {'push_then': ["first"]},
            {'push_if': [False]},
            {'push_then': ["second"]},
            {'push_else': ["third"]}
        ]})
        self.assertSequenceEqual(conditions, [True])
        self.assertSequenceEqual(consequents, ["first"])

        del(conditions[:])
        del(consequents[:])

        jsonLogic({'if': [
            {'push_if': [False]},
            {'push_then': ["first"]},
            {'push_if': [True]},
            {'push_then': ["second"]},
            {'push_else': ["third"]}
        ]})
        self.assertSequenceEqual(conditions, [False, True])
        self.assertSequenceEqual(consequents, ["second"])

        del(conditions[:])
        del(consequents[:])

        jsonLogic({'if': [
            {'push_if': [False]},
            {'push_then': ["first"]},
            {'push_if': [False]},
            {'push_then': ["second"]},
            {'push_else': ["third"]}
        ]})
        self.assertSequenceEqual(conditions, [False, False])
        self.assertSequenceEqual(consequents, ["third"])

    def test_ternary_operator_does_not_evaluate_depth_first(self):
        # False consequent of '?:' operation condition should not run
        consequents = []

        def push_then(arg):
            consequents.append(arg)
            return arg

        def push_else(arg):
            consequents.append(arg)
            return arg

        add_operation('push_then', push_then)
        add_operation('push_else', push_else)

        jsonLogic({'?:': [
            True,
            {'push_then': ["first"]},
            {'push_else': ["second"]}
        ]})
        self.assertSequenceEqual(consequents, ["first"])

        del(consequents[:])

        jsonLogic({'?:': [
            False,
            {'push_then': ["first"]},
            {'push_else': ["second"]}
        ]})
        self.assertSequenceEqual(consequents, ["second"])

    def test_and_operator_does_not_evaluate_depth_first(self):
        # 'and' operator should stop at first falsy value
        evaluated_elements = []

        def push(arg):
            evaluated_elements.append(arg)
            return arg

        add_operation('push', push)

        jsonLogic({'and': [{'push': [False]}, {'push': [False]}]})
        self.assertSequenceEqual(evaluated_elements, [False])

        del(evaluated_elements[:])

        jsonLogic({'and': [{'push': [False]}, {'push': [True]}]})
        self.assertSequenceEqual(evaluated_elements, [False])

        del(evaluated_elements[:])

        jsonLogic({'and': [{'push': [True]}, {'push': [True]}]})
        self.assertSequenceEqual(evaluated_elements, [True, True])

    def test_or_operator_does_not_evaluate_depth_first(self):
        # 'or' operator should stop at first truthy value
        evaluated_elements = []

        def push(arg):
            evaluated_elements.append(arg)
            return arg

        add_operation('push', push)

        jsonLogic({'or': [{'push': [False]}, {'push': [False]}]})
        self.assertSequenceEqual(evaluated_elements, [False, False])

        del(evaluated_elements[:])

        jsonLogic({'or': [{'push': [False]}, {'push': [True]}]})
        self.assertSequenceEqual(evaluated_elements, [False, True])

        del(evaluated_elements[:])

        jsonLogic({'or': [{'push': [True]}, {'push': [False]}]})
        self.assertSequenceEqual(evaluated_elements, [True])

        del(evaluated_elements[:])

        jsonLogic({'or': [{'push': [True]}, {'push': [True]}]})
        self.assertSequenceEqual(evaluated_elements, [True])

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

    def test_uses_data_function_returns_variable_names(self):
        logic = {'+': [{'var': 'a'}, {'var': ['b', 2]}, 3, {'var': ['c']}]}
        variables = uses_data(logic)
        self.assertSequenceEqual(variables, ['a', 'b', 'c'])

    def test_uses_data_function_returns_nested_variable_names(self):
        logic = {'if': [
            {'>': [{'var': 'a'}, {'var': ['b']}]},
            {'var': ['c', 3]},
            {'+': [{'var': 'd'}, 10]}
        ]}
        variables = uses_data(logic)
        self.assertSequenceEqual(variables, ['a', 'b', 'c', 'd'])

    def test_uses_data_function_returns_unique_variable_names(self):
        logic = {'if': [
            {'>': [{'var': 'a'}, {'var': 'b'}]},
            {'var': 'a'},
            {'*': [{'var': 'b'}, 2]}
        ]}
        variables = uses_data(logic)
        self.assertSequenceEqual(variables, ['a', 'b'])

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

    def test_add_operation_with_simple_method(self):
        def add_to_five(*args):
            return sum((5,) + args)
        self.assertRaisesRegex(
            ValueError, "Unrecognized operation",
            jsonLogic, {'add_to_five': [3]})
        add_operation('add_to_five', add_to_five)
        try:
            self.assertEqual(jsonLogic({'add_to_five': 1}), 6)
            self.assertEqual(jsonLogic({'add_to_five': [3]}), 8)
            self.assertEqual(jsonLogic({'add_to_five': [3, 2]}), 10)
        finally:
            rm_operation('add_to_five')

    def test_add_operation_with_packages(self):
        self.assertRaisesRegex(
            ValueError, "Unrecognized operation.*datetime",
            jsonLogic, {'datetime.datetime.now': []})
        add_operation('datetime', datetime)
        try:
            # .now()
            start = datetime.datetime.now()
            returned_value = jsonLogic({'datetime.datetime.now': []})
            self.assertIsInstance(returned_value, datetime.datetime)
            self.assertTrue(start <= returned_value <= datetime.datetime.now())
            # .date()
            returned_value = jsonLogic({'datetime.date': [2018, 1, 1]})
            self.assertIsInstance(returned_value, datetime.date)
            self.assertEqual(returned_value, datetime.date(2018, 1, 1))
        finally:
            rm_operation('datetime')

    def test_add_operation_with_packages_fails_midway(self):
        add_operation('datetime', datetime)
        try:
            self.assertRaisesRegex(
                ValueError, "datetime\.wrong_property(?!\.now)",
                jsonLogic, {'datetime.wrong_property.now': []})
            self.assertRaisesRegex(
                ValueError, "datetime\.datetime.wrong_method",
                jsonLogic, {'datetime.datetime.wrong_method': []})
        finally:
            rm_operation('datetime')

    def test_add_operation_may_override_common_operations(self):
        add_operation('+', lambda *args: "Ha-ha!")
        try:
            self.assertEqual(jsonLogic({'+': [1, 2]}), "Ha-ha!")
        finally:
            rm_operation('+')

    def test_depth_first_rule_still_applies_to_custom_operators(self):
        add_operation('sum_up', lambda *args: sum(args))
        try:
            self.assertEqual(
                jsonLogic({'sum_up': [{'-': [5, 3]}, {'*': [2, 3]}]}),
                8)
        finally:
            rm_operation('sum_up')

    def test_rm_operation_removes_custom_operation(self):
        add_operation('custom', lambda: "Ha-ha!")
        try:
            self.assertEqual(jsonLogic({'custom': []}), "Ha-ha!")
        finally:
            rm_operation('custom')
        self.assertRaisesRegex(
            ValueError, "Unrecognized operation",
            jsonLogic, {'custom': []})

    def test_rm_operation_restores_overridden_operation(self):
        self.assertEqual(jsonLogic({'+': [2, 3]}), 5)
        add_operation('+', lambda *args: "Ha-ha!")
        try:
            self.assertEqual(jsonLogic({'+': [2, 3]}), "Ha-ha!")
        finally:
            rm_operation('+')
            self.assertEqual(jsonLogic({'+': [2, 3]}), 5)
            self.assertNotEqual(jsonLogic({'+': [2, 3]}), "Ha-ha!")

    def test_add_operation_does_not_override_other_operation_types(self):
        test_data = (
            ('if', [True, "yes", "no"], {}, "yes"),
            ('map', [[1, 2, 3], {'*': [{'var': ''}, 2]}], {}, [2, 4, 6]),
            ('var', 'a', {'a': "Ta-da!"}, "Ta-da!"))
        for operation, arguments, data, expected_result in test_data:
            add_operation(operation, lambda *args: "Ha-ha!")
            try:
                result = jsonLogic({operation: arguments}, data)
                self.assertEqual(result, expected_result, operation)
                self.assertNotEqual(result, "Ha-ha!", operation)
            finally:
                rm_operation(operation)

    def test_add_operation_updates_exposed_operations_list(self):
        haha = lambda *args: "Ha-ha!"
        self.assertNotIn('custom', operations)
        add_operation('custom', haha)
        try:
            self.assertIn('custom', operations)
            self.assertIs(operations['custom'], haha)
        finally:
            rm_operation('custom')

    def test_add_operation_overrides_existing_exposed_operations(self):
        haha = lambda *args: "Ha-ha!"
        self.assertIn('+', operations)
        self.assertIsNot(operations['+'], haha)
        add_operation('+', haha)
        try:
            self.assertIn('+', operations)
            self.assertIs(operations['+'], haha)
        finally:
            rm_operation('+')

    def test_rm_operation_updates_exposed_operations_list(self):
        haha = lambda *args: "Ha-ha!"
        add_operation('custom', haha)
        try:
            self.assertIn('custom', operations)
            self.assertIs(operations['custom'], haha)
        finally:
            rm_operation('custom')
        self.assertNotIn('custom', operations)

    def test_rm_operation_restores_overridden_operation_in_exposed_list(self):
        haha = lambda *args: "Ha-ha!"
        add_operation('+', haha)
        try:
            self.assertIn('+', operations)
            self.assertIs(operations['+'], haha)
        finally:
            rm_operation('+')
        self.assertIn('+', operations)
        self.assertIsNot(operations['+'], haha)


if __name__ == '__main__':
    unittest.main()
