# This is a Python implementation of the following jsonLogic JS library:
# https://github.com/jwadhams/json-logic-js

import logging
from datetime import date, datetime, timedelta
from functools import reduce

import isodate
from dateutil.relativedelta import relativedelta

from .typing import JSON, Object

logger = logging.getLogger(__name__)


class UndefinedType:
    """
    Sentinel for 'undefined' values.

    Used when `use_var_undefined` is set to True in order to treat None values in a more
    specific way (JS-style).
    """

    def __repr__(self):
        return "undefined"

    def __bool__(self):
        return False


UNDEFINED_VALUE = UndefinedType()


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
    if type(a) is not type(b):
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


def apply_relative_delta(year=0, month=0, day=0, hours=0, minutes=0, seconds=0):
    return relativedelta(
        years=year,
        months=month,
        days=day,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
    )


def less_or_equal(a, b, *args):
    """Implements the '<=' operator with JS-style type coertion."""
    return (less(a, b) or soft_equals(a, b)) and (not args or less_or_equal(b, *args))


def to_numeric(arg):
    """
    Converts a string either to int or to float.
    This is important, because e.g. {"!==": [{"+": "0"}, 0.0]}
    """
    if isinstance(arg, str):
        if "." in arg:
            return float(arg)
        else:
            return int(arg)
    return arg


def sum_dates(*args):
    # Since sum() converts to ints or floats, in the case of
    # dates the normal + operator is needed
    total = args[0]
    for arg in args[1:]:
        total += arg
    return total


def plus(*args):
    """Sum converts either to ints or to floats."""
    if any([isinstance(arg, date) for arg in args]):
        return sum_dates(*args)
    return sum(to_numeric(arg) for arg in args)


def minus(*args):
    """Also, converts either to ints or to floats."""
    if len(args) == 1:
        return -to_numeric(args[0])
    result = to_numeric(args[0]) - to_numeric(args[1])
    if isinstance(result, timedelta):
        return isodate.duration_isoformat(result)
    return result


def merge(*args):
    """Implements the 'merge' operator for merging lists."""
    ret = []
    for arg in args:
        if isinstance(arg, list) or isinstance(arg, tuple):
            ret += list(arg)
        else:
            ret.append(arg)
    return ret


def get_var(data, var_name, not_found=UNDEFINED_VALUE, use_var_undefined=False):
    if not var_name:
        return data

    # Setting UNDEFINED_VALUE as the default value for not_found function argument ensures
    # we can detect when no value was passed, because it's not possible to specify this
    # undefined value in a JSON logic expression. We need to switch back to None, though,
    # if we are opting out of using the undefined value.
    if not use_var_undefined and not_found is UNDEFINED_VALUE:
        not_found = None

    default_not_found = UNDEFINED_VALUE if use_var_undefined else None

    try:
        for key in str(var_name).split("."):
            try:
                data = data[key]
            except TypeError:
                data = data[int(key)]
    except (KeyError, TypeError, ValueError, IndexError):
        return not_found
    else:
        if data is None and not_found is not default_not_found:
            return not_found
        return data


def get_date(value, *args):
    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(value)
    except ValueError:
        date_with_time = datetime.fromisoformat(value)
        return date_with_time.date()


def get_datetime(value, *args):
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


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


def substr(text, start, length):
    if text is None or text is UNDEFINED_VALUE:
        return ""
    return text[start : start + length]


def apply_reduce(data, iterable_path, scoped_logic, initializer):
    """Calculate reduce

    If the data was

    ```python
    data = {"cars": [{"colour": "blue", "price": 2000}, {"colour": "red", "price": 3000}]}
    ```
    and the rule

    ```python
    rule = {"reduce": [{"var": "cars"}, {"+": [{"var": "accumulator"}, {"var": "current.price"}]}, 0]}
    ```

    This function then receives:
    ```python
    iterable = [{"colour": "blue", "price": 2000}, {"colour": "red", "price": 3000}]
    scoped_logic = {"+": [{"var": "accumulator"}, {"var": "current.price"}]}
    initializer = 0
    ```
    """
    iterable = jsonLogic(iterable_path, data)
    if not isinstance(iterable, list):
        return initializer

    return reduce(
        lambda accumulator, current: jsonLogic(
            scoped_logic, {"accumulator": accumulator, "current": current}
        ),
        iterable,
        jsonLogic(initializer, data),
    )


def apply_map(data, iterable_path, scoped_logic):
    iterable = jsonLogic(iterable_path, data) or []
    return list(map(lambda item: jsonLogic(scoped_logic, item), iterable))


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
    "and": lambda *args: reduce(lambda total, arg: total and arg, args, True),
    "or": lambda *args: reduce(lambda total, arg: total or arg, args, False),
    "?:": lambda a, b, c: b if a else c,
    "if": if_,
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
    "count": lambda *args: sum(1 if a else 0 for a in args),
    "today": lambda *args: date.today(),
    "date": get_date,
    "datetime": get_datetime,
    "rdelta": apply_relative_delta,
    "duration": isodate.parse_duration,
}

scoped_operations = {
    "reduce": apply_reduce,
    "map": apply_map,
}

ALL_OPERATIONS = (
    {"var", "missing", "missing_some", "substr"}
    .union(operations)
    .union(scoped_operations)
)

# Which values to consider as "empty" for the operands of different operators
empty_operand_values_for_operators = {
    ">": [None, UNDEFINED_VALUE],
    ">=": [None, UNDEFINED_VALUE],
    "<": [None, UNDEFINED_VALUE],
    "<=": [None, UNDEFINED_VALUE],
    "%": [None, UNDEFINED_VALUE],
    "log": [None, UNDEFINED_VALUE],
    "+": [None, UNDEFINED_VALUE],
    "*": [None, UNDEFINED_VALUE],
    "-": [None, UNDEFINED_VALUE],
    "/": [None, UNDEFINED_VALUE],
    "min": [None, UNDEFINED_VALUE],
    "max": [None, UNDEFINED_VALUE],
    "count": [None, UNDEFINED_VALUE],
    "date": [None, "", UNDEFINED_VALUE],
    "datetime": [None, "", UNDEFINED_VALUE],
    "years": [None, UNDEFINED_VALUE],
}


def is_data(tests: Object) -> bool:
    operator_keys = [key for key in tests.keys() if not key.startswith("_")]
    if len(operator_keys) == 1 and operator_keys[0] in ALL_OPERATIONS:
        return False

    return True


def jsonLogic(
    tests: JSON,
    data: JSON = None,
    permissive: bool = False,
    use_var_undefined: bool = False,
):
    """
    Execute the json-logic with given data.

    :param tests: JSON logic expression.
    :param data: The context data.
    :param permissive: If True, invalid JSON logic expressions will be interpreted as
      data, instead of crashing hard.
    :param use_var_undefined: If True, missing variables will return UNDEFINED_VALUE
      instead of None.
    """
    from .meta.expressions import destructure

    if isinstance(tests, list):
        return [
            jsonLogic(item, data, permissive, use_var_undefined=use_var_undefined)
            for item in tests
        ]

    # You've recursed to a primitive, stop!
    if tests is None or not isinstance(tests, dict):
        return tests

    data = data or {}

    if permissive and is_data(tests):
        return tests

    operator, values = destructure(tests)

    # Easy syntax for unary operators, like {"var": "x"} instead of strict
    # {"var": ["x"]}
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]

    if operator in scoped_operations:
        return scoped_operations[operator](data, *values)

    # Recursion!
    values = [
        jsonLogic(val, data, permissive, use_var_undefined=use_var_undefined)
        for val in values
    ]

    match operator:
        case "var":
            return get_var(data, *values, use_var_undefined=use_var_undefined)
        case "missing":
            return missing(data, *values)
        case "missing_some":
            return missing_some(data, *values)
        case "substr":
            return substr(*values)

    if operator not in operations:
        raise ValueError("Unrecognized operation %s" % operator)

    # Some operators raise errors if operands are empty. However, when evaluating without data or with incomplete
    # data, often variables are empty. In this case, the jsonLogic evaluation will return None
    empty_values = empty_operand_values_for_operators.get(operator)
    if empty_values and any([value in empty_values for value in values]):
        return None
    return operations[operator](*values)
