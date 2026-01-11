# This is a Python implementation of the following jsonLogic JS library:
# https://github.com/jwadhams/json-logic-js

from functools import reduce as python_reduce
import logging

logger = logging.getLogger(__name__)


def if_(*args):
    """Implements the 'if' operator with support for multiple elseif-s."""
    for i in range(0, len(args) - 1, 2):
        if args[i]:
            return args[i + 1]
    if len(args) % 2:
        return args[-1]
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
        if isinstance(arg, list) or isinstance(arg, tuple):
            ret += list(arg)
        else:
            ret.append(arg)
    return ret


def get_var(data, var_name, not_found=None):
    """Gets variable value from data dictionary."""
    # Empty string means return the entire data object
    if var_name == '' or var_name is None:
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


def substr(source, start, length=None):
    """
    Implements the 'substr' operator.
    Get a portion of a string.
    """
    if length is None:
        return source[start:]
    elif length < 0:
        return source[start:length]
    else:
        return source[start:start + length]


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
    "and": lambda *args: python_reduce(lambda total, arg: total and arg, args, True),
    "or": lambda *args: python_reduce(lambda total, arg: total or arg, args, False),
    "?:": lambda a, b, c: b if a else c,
    "if": if_,
    "log": lambda a: logger.info(a) or a,
    "in": lambda a, b: a in b if "__contains__" in dir(b) else False,
    "cat": lambda *args: "".join(str(arg) for arg in args),
    "substr": substr,
    "+": plus,
    "*": lambda *args: python_reduce(lambda total, arg: total * float(arg), args, 1),
    "-": minus,
    "/": lambda a, b=None: a if b is None else float(a) / float(b),
    "min": lambda *args: min(args),
    "max": lambda *args: max(args),
    "merge": merge,
    "count": lambda *args: sum(1 if a else 0 for a in args),
}


def add_operation(name, func):
    """
    Add a custom operation to JsonLogic.
    
    Example:
        add_operation("times", lambda a, b: a * b)
        jsonLogic({"times": [2, 3]})  # Returns 6
    """
    operations[name] = func


def rm_operation(name):
    """
    Remove an operation from JsonLogic.
    """
    del operations[name]


def jsonLogic(tests, data=None):
    """Executes the json-logic with given data."""
    # You've recursed to a primitive, stop!
    if tests is None or not isinstance(tests, dict):
        return tests

    data = data or {}

    operator = list(tests.keys())[0]
    values = tests[operator]

    # Easy syntax for unary operators, like {"var": "x"} instead of strict
    # {"var": ["x"]}
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]

    # Special case for array operations that need scoped evaluation
    # These operations don't pre-evaluate all their arguments
    if operator == 'map':
        scoped_data = jsonLogic(values[0], data)
        scoped_logic = values[1]
        return [jsonLogic(scoped_logic, item) for item in scoped_data]

    if operator == 'filter':
        scoped_data = jsonLogic(values[0], data)
        scoped_logic = values[1]
        return [item for item in scoped_data if jsonLogic(scoped_logic, item)]

    if operator == 'reduce':
        scoped_data = jsonLogic(values[0], data)
        scoped_logic = values[1]
        initial = jsonLogic(values[2], data) if len(values) > 2 else 0
        accumulator = initial
        for item in scoped_data:
            accumulator = jsonLogic(
                scoped_logic,
                {"current": item, "accumulator": accumulator}
            )
        return accumulator

    if operator == 'all':
        scoped_data = jsonLogic(values[0], data)
        scoped_logic = values[1]
        if not scoped_data:
            return False
        for item in scoped_data:
            if not jsonLogic(scoped_logic, item):
                return False
        return True

    if operator == 'some':
        scoped_data = jsonLogic(values[0], data)
        scoped_logic = values[1]
        if not scoped_data:
            return False
        for item in scoped_data:
            if jsonLogic(scoped_logic, item):
                return True
        return False

    if operator == 'none':
        scoped_data = jsonLogic(values[0], data)
        scoped_logic = values[1]
        for item in scoped_data:
            if jsonLogic(scoped_logic, item):
                return False
        return True

    # Recursion!
    values = [jsonLogic(val, data) for val in values]

    if operator == 'var':
        return get_var(data, *values)
    if operator == 'missing':
        return missing(data, *values)
    if operator == 'missing_some':
        return missing_some(data, *values)

    if operator not in operations:
        raise ValueError("Unrecognized operation %s" % operator)

    return operations[operator](*values)
