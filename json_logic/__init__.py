# This is a Python implementation of the following jsonLogic JS library:
# https://github.com/jwadhams/json-logic-js
from __future__ import unicode_literals

import sys
from six.moves import reduce
import logging

logger = logging.getLogger(__name__)

try:
    unicode
except NameError:
    pass
else:
    # Python 2 fallback.
    str = unicode

def if_(data, *args):
    """
    Implements the 'if' operator with support for multiple elseif-s.
    Short Circuit, only process branches that you need to go down.
    Return 'if' or 'else' value as appropriate but None if 'if' condition is false and there is no 'else' value.
    """
    for i in range(0, len(args) - 1, 2):
        if jsonLogic(args[i], data):
            return jsonLogic(args[i + 1], data)
    if len(args) % 2:
        return jsonLogic(args[-1], data)
    else:
        return None


def soft_equals(a, b):
    """Implements the '==' operator, which does type JS-style coertion."""
    if isinstance(a, str) or isinstance(b, str):
        return str(a) == str(b)
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) is bool(b)
    return a == b


def hard_equals(a, b):
    """Implements the '===' operator."""
    if type(a) != type(b):
        return False
    return a == b


def less(a, b, *args):
    """Implements the '<' operator with JS-style type coertion."""
    types = set([type(a), type(b)])
    if float in types or int in types:
        try:
            a, b = float(a), float(b)
        except TypeError:
            # NaN
            return False
    return a < b and (not args or less(b, *args))


def less_or_equal(a, b, *args):
    """Implements the '<=' operator with JS-style type coertion."""
    return (
        less(a, b) or soft_equals(a, b)
    ) and (not args or less_or_equal(b, *args))


def to_numeric(arg):
    """
    Converts a string either to int or to float.
    This is important, because e.g. {"!==": [{"+": "0"}, 0.0]}
    """
    if isinstance(arg, str):
        if '.' in arg:
            return float(arg)
        else:
            return int(arg)
    return arg


def plus(*args):
    """Sum converts either to ints or to floats."""
    return sum(to_numeric(arg) for arg in args)


def minus(*args):
    """Also, converts either to ints or to floats."""
    if len(args) == 1:
        return -to_numeric(args[0])
    return to_numeric(args[0]) - to_numeric(args[1])


def merge(*args):
    """Implements the 'merge' operator for merging lists."""
    ret = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            ret += list(arg)
        else:
            ret.append(arg)
    return ret


def get_var(data, var_name=None, not_found=None):
    """Gets variable value from data dictionary."""
    if var_name in ["", None, ()] and not isinstance(data, dict):
        return data
    try:
        for key in str(var_name).split('.'):
            try:
                data = data[key]
            except TypeError:
                data = data[int(key)]
    except (KeyError, TypeError, ValueError):
        return not_found
    else:
        return data


def missing(data, *args):
    """Implements the missing operator for finding missing variables."""
    not_found = object()
    if args and isinstance(args[0], list):
        args = args[0]
    ret = []
    for arg in args:
        if get_var(data, arg, not_found) is not_found:
            ret.append(arg)
    return ret


def missing_some(data, min_required, args):
    """Implements the missing_some operator for finding missing variables."""
    if min_required < 1:
        return []
    found = 0
    not_found = object()
    ret = []
    for arg in args:
        if get_var(data, arg, not_found) is not_found:
            ret.append(arg)
        else:
            found += 1
            if found >= min_required:
                return []
    return ret


def or_(data, *values):
    """
    Short Circuit OR. Stop processing when you get a True value.
    Return last value processed.
    """
    for val in values:
        val = jsonLogic(val, data)
        if val:
            return val
    return val


def and_(data, *values):
    """
    Short Circuit AND. Stop processing when you get a False value.
    Return last value processed.
    """
    for val in values:
        val = jsonLogic(val, data)
        if not val:
            return val
    return val


def filter_(data, values, scoped_logic):
    """
    Filter values based on provided logic.
    """
    scoped_data = jsonLogic(values, data)
    if not isinstance(scoped_data, (list, tuple)):
        return []
    return [val for val in scoped_data if jsonLogic(scoped_logic, val )]


def map_(data, values, scoped_logic):
    """
    Map values based on provided logic.
    Like multiply each element or do lookup.
    """
    scoped_data = jsonLogic(values, data)
    if not isinstance(scoped_data, (list, tuple)):
        return []
    return [jsonLogic(scoped_logic, val if isinstance(val, dict) else {"":val} ) for val in scoped_data]


def reduce_(data, values, scoped_logic, initial=None):
    """
    Reduce list to a single value based on provided logic.
    """
    scoped_data = jsonLogic(values, data)
    if not isinstance(scoped_data, (list, tuple)) or len(scoped_data) == 0:
        return initial
    return reduce(lambda a, b: jsonLogic(scoped_logic, {"current":b, "accumulator":a}), scoped_data, initial)

def all_(data, values, scoped_logic):
    """
    Short Circuit AND, returns bool. Stop processing when you get a false value.
    Empty list returns False.
    """
    scoped_data = jsonLogic(values, data)
    if not isinstance(scoped_data, (list, tuple)) or not scoped_data:
        return False
    for val in scoped_data:
        val = jsonLogic(scoped_logic, val)
        if not val:
            return False
    return True


def none_(data, values, scoped_logic):
    """
    Short Circuit NOT, return bool. Stop processing when you get a True value.
    Empty list returns True.
    """
    scoped_data = jsonLogic(values, data)
    if not isinstance(scoped_data, (list, tuple)) or not scoped_data:
        return True
    for val in scoped_data:
        val = jsonLogic(scoped_logic, val)
        if val:
            return False
    return True


def some_(data, values, scoped_logic):
    """
    Short Circuit OR, return bool. Stop processing when you get a True value.
    Empty list returns False.
    """
    scoped_data = jsonLogic(values, data)
    if not isinstance(scoped_data, (list, tuple)) or not scoped_data:
        return False
    for val in scoped_data:
        val = jsonLogic(scoped_logic, val)
        if val:
            return True
    return False


operations = {
    "==": soft_equals,
    "===": hard_equals,
    "!=": lambda a, b: not soft_equals(a, b),
    "!==": lambda a, b: not hard_equals(a, b),
    ">": lambda a, b: less(b, a),
    ">=": lambda a, b: less(b, a) or soft_equals(a, b),
    "<": less,
    "<=": less_or_equal,
    "!": lambda a: not a,
    "!!": bool,
    "%": lambda a, b: a % b,
    "log": lambda a: logger.info(a) or a,
    "in": lambda a, b: a in b if "__contains__" in dir(b) else False,
    "cat": lambda *args: "".join(str(arg) for arg in args),
    "+": plus,
    "*": lambda *args: reduce(lambda total, arg: total * float(arg), args, 1),
    "-": minus,
    "/": lambda a, b=None: a if b is None else float(a) / float(b),
    "min": lambda *args: min(args),
    "max": lambda *args: max(args),
    "merge": merge,
    "count": lambda *args: len(args),
    "substr": lambda string, offset=None, length=None: string[offset:][:length],
}

short_circuit_operators = {
    "or": or_,
    "and": and_,
    "if": if_,
    "?:": if_,
    "filter": filter_,
    "map": map_,
    "reduce": reduce_,
    "all": all_,
    "none": none_,
    "some": some_,
}

data_operators = {
    "var": get_var,
    "missing": missing,
    "missing_some": missing_some,
}


def jsonLogic(tests, data={}):
    """Executes the json-logic with given data."""

    if isinstance(tests, (list, tuple)):
        # Recurse Array to process any logic.
        return [jsonLogic(test, data) for test in tests]

    if not isinstance(tests, dict):
        # You've recursed to a primitive, stop!
        return tests

    operator, values = next(iter(tests.items()))

    # Easy syntax for unary operators, like {"var": "x"} instead of strict
    # {"var": ["x"]}
    if not isinstance(values, (list, tuple)):
        values = [values]

    # Short Circuit operations like "and" that should stop after first negative value.
    if operator in short_circuit_operators:
        return short_circuit_operators[operator](data, *values)

    # Recursion!
    values = [jsonLogic(val, data) for val in values]

    # Post recursion operators that use data.
    if operator in data_operators:
        return data_operators[operator](data, *values)

    # Post recursion operators that do NOT use data.
    if operator in operations:
        return operations[operator](*values)

    # Uh oh. We should have found something to do before here.
    # Invalid JsonLogic.
    raise ValueError("Unrecognized operation %s" % operator)
