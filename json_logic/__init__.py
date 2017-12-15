"""
This is a Python implementation of the JsonLogic JS library:
https://github.com/jwadhams/json-logic-js
"""


# Python 2 fallbacks
from __future__ import division, unicode_literals
try:
    str = unicode
except NameError:
    pass
from six.moves import reduce
from six import integer_types
numeric_types = integer_types + (float,)

import logging
import warnings


# Helper functions and variables

# Sentinel value to indicate an optional argument
# that can take various values including None
_no_argument = object()


def _is_numeric(arg):
    """Check if argument is of a numeric type: float, int or long."""
    return type(arg) in numeric_types


def _to_numeric(arg):
    """
    Convert a string or other value  into float, integer or long.
    Convert float value to integer if appropriate.
    """
    if isinstance(arg, str) and '.' in arg:
        arg = float(arg)
    if isinstance(arg, float):
        return int(arg) if arg.is_integer() else arg
    return int(arg)


# Common operations

def _equal_to(a, b):
    """Test for non-strict equality ('==') with JS-style type coercion."""
    if isinstance(a, str) or isinstance(b, str):
        return str(a) == str(b)
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) is bool(b)
    return a == b


def _strict_equal_to(a, b):
    """
    Check for strict equality ('===') including type equality.
    N.B.: Core JsonLogic does not differentiate between different numeric
    types and considers them strictly equal to each other.
    E.g.: {"===": [1, 1.0]}
    """
    if type(a) is type(b):
        return a == b
    if _is_numeric(a) and _is_numeric(b):
        return _to_numeric(a) == _to_numeric(b)
    return False


def _not_equal_to(a, b):
    """Check for non-strict inequality ('==') with JS-style type coercion."""
    return not _equal_to(a, b)


def _not_strict_equal_to(a, b):
    """Check for strict inequality ('!==') including type inequality."""
    return not _strict_equal_to(a, b)


def _less_than(a, b, c=_no_argument):
    """
    Check that A is less then B (A < B) or
    that B is exclusively between A and C (A < B < C).
    """
    types = set([type(a), type(b)])
    if float in types or int in types:
        try:
            a, b = float(a), float(b)
        except TypeError:
            return False  # NaN
    return a < b and (c is _no_argument or _less_than(b, c))


def _less_than_or_equal_to(a, b, c=_no_argument):
    """
    Check that A is less then or equal to B (A <= B) or
    that B is inclusively between A and C (A <= B <= C).
    """
    return \
        (_less_than(a, b) or _equal_to(a, b)) and \
        (c is _no_argument or _less_than_or_equal_to(b, c))


def _greater_than(a, b):
    """Check that A is greater then B (A > B)."""
    return _less_than(b, a)


def _greater_than_or_equal_to(a, b):
    """Check that A is greater then or equal to B (A >= B)."""
    return _less_than_or_equal_to(b, a)


def _truthy(a):
    """Check that argument evaluates to True according to core JsonLogic."""
    return bool(a)


def _falsy(a):
    """Check that argument evaluates to False according to core JsonLogic."""
    return not _truthy(a)


def _log(a):
    """Log data to 'logging' module at INFO level."""
    logging.getLogger(__name__).info(a)
    return a


def _in(a, b):
    """Check that A is in B according to core JsonLogic."""
    if hasattr(b, '__contains__'):
        return a in b
    return False


def _concatenate(*args):
    """Concatenate string elements into a single string."""
    return "".join(str(arg) for arg in args)


def _add(*args):
    """Sum up all arguments converting them to either integers or floats."""
    result = sum(_to_numeric(arg) for arg in args)
    return _to_numeric(result)


def _subtract(a, b=_no_argument):
    """
    Subtract B from A converting them to either integers or floats.
    If only A is provided - return its arithmetic negative.
    """
    if b is _no_argument:
        result = -_to_numeric(a)
    else:
        result = _to_numeric(a) - _to_numeric(b)
    return _to_numeric(result)


def _multiply(*args):
    """Multiply all arguments converting them to either integers or floats."""
    result = reduce(lambda total, arg: total * _to_numeric(arg), args, 1)
    return _to_numeric(result)


def _divide(a, b):
    """
    Divide A by B converting them to either integers or floats.
    """
    result = _to_numeric(a) / _to_numeric(b)
    return _to_numeric(result)


def _modulo(a, b):
    """
    Get modulo after division of A by B
    (converted to either integers or floats).
    """
    result = _to_numeric(a) % _to_numeric(b)
    return _to_numeric(result)


def _minimal(*args):
    """Get minimal value among provided arguments."""
    return min(_to_numeric(arg) for arg in args) if args else None


def _maximal(*args):
    """Get maximal value among provided arguments."""
    return max(_to_numeric(arg) for arg in args) if args else None


def _merge(*args):
    """Merge several arrays into one."""
    resulting_array = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            resulting_array.extend(arg)
        else:
            resulting_array.append(arg)
    return resulting_array


operations = {
    '==': _equal_to,
    '===': _strict_equal_to,
    '!=': _not_equal_to,
    '!==': _not_strict_equal_to,
    '>': _greater_than,
    '>=': _greater_than_or_equal_to,
    '<': _less_than,
    '<=': _less_than_or_equal_to,
    '!!': _truthy,
    '!': _falsy,
    'log': _log,
    'in': _in,
    'cat': _concatenate,
    '+': _add,
    '-': _subtract,
    '*': _multiply,
    '/': _divide,
    '%': _modulo,
    'min': _minimal,
    'max': _maximal,
    'merge': _merge,
}


# Unsupported operations

def _count(*args):
    """Execute 'count' operation unsupported by core JsonLogic."""
    return sum(1 if a else 0 for a in args)


unsupported_operations = {
    'count': _count
}


# Logical operations

def _if(data, *args):
    """
    Evaluate chainable conditions with multiple 'else if' support and return
    the corresponding evaluated argument based on the following patterns:

    if 0 then 1 else None
    if 0 then 1 else 2
    if 0 then 1 else if 2 then 3 else 4
    if 0 then 1 else if 2 then 3 else if 4 then 5 else 6

    - If no arguments are given then return None.
    - If only one argument is given the evaluate and return it.
    - If two arguments are given then evaluate the first one, if it evaluates
      to True return evaluated second argument, otherwise return None.
    - If three arguments are given then evaluate the first one, if it evaluates
      to True return evaluated second argument, otherwise return evaluated
      third argument.
    - For more then 3 arguments:
        - If the first argument evaluates to True then evaluate and return
          the second argument.
        - If the first argument evaluates to False then jump to the next pair
          (e.g.: from 0,1 to 2,3) and evaluate them.
    """
    for i in range(0, len(args) - 1, 2):
        if _truthy(jsonLogic(args[i], data)):
            return jsonLogic(args[i + 1], data)
    if len(args) % 2:
        return jsonLogic(args[-1], data)
    else:
        return None


def _and(data, *args):
    """
    Evaluate and logically join arguments using the 'and' operator.
    If all arguments evaluate to True return the last (truthy) one (meaning
    that the whole expression evaluates to True).
    Otherwise return first countered falsy argument (meaning that the whole
    expression evaluates to False).
    """
    current = False
    for current in args:
        current = jsonLogic(current, data)
        if _falsy(current):
            return current  # First falsy argument
    return current  # Last argument


def _or(data, *args):
    """
    Evaluate and logically join arguments using the 'or' operator.
    If at least one argument evaluates to True - return it
    (meaning that the whole expression evaluates to True).
    Otherwise return the last (falsy) argument (meaning that the whole
    expression evaluates to False).
    """
    current = False
    for current in args:
        current = jsonLogic(current, data)
        if _truthy(current):
            return current  # First truthy argument
    return current  # Last argument


logical_operations = {
    'if': _if,
    'and': _and,
    'or': _or,
}


# Data operations

def _var(data, var_name=None, default=None):
    """
    Get variable value from the data object.
    Can also access variable properties (to any depth) via dot-notation:
        "variable.property"
        "variable.property.sub_property"
    The same is true for array elements that can be accessed by index:
        "array_variable.5"
        "variable.array_property.0.sub_property"
    Return the specified default value if variable, its property or element
    is not found. Return None if no default value is specified.
    Return the whole data object if variable name is None or an empty string.
    """
    if var_name is None or var_name == '':
        return data  # Return the whole data object
    try:
        for key in str(var_name).split('.'):
            try:
                data = data[key]
            except TypeError:
                data = data[int(key)]
    except (KeyError, TypeError, ValueError):
        return default
    else:
        return data


def _missing(data, *args):
    """
    Check if one or more variables are missing from data object.
    Take either:
      - multiple arguments (one variable name per argument) like:
        {"missing:["variable_1", "variable_2"]}.
      - a single argument that is an array of variable names like:
        {"missing": [["variable_1", "variable_2"]] (this typically happens
        if this operator is applied to the output of another operator
        (like 'if' or 'merge').
    Return an empty array if all variables are present and non-empty.
    Otherwise return a array of all missing variable names.

    N.B.: Per core JsonLogic, if missing variable name is provided several
    times it will also be represented several times in the resulting array.
    """
    missing_array = []
    var_names = \
        args[0] if args and isinstance(args[0], (list, tuple)) \
        else args
    for var_name in var_names:
        if _var(data, var_name) in (None, ""):
            missing_array.append(var_name)
    return missing_array


def _missing_some(data, need_count, args):
    """
    Check if at least some of the variables are missing from data object.
    Take two arguments:
      - minimum number of variables that are required to be present.
      - array of variable names to check for.
    I.e.: "{"missing_some":[1, ["a", "b", "c"]]}" means that at least one of
    the provided "a", "b" and "c" variables must be present in the data object.
    Return an empty array if minimum number of present variables is met.
    Otherwise return an array of all missing variable names.

    N.B.: Per core JsonLogic, if missing variable name is provided several
    times it will also be represented several times in the resulting array.
    In that case all occurrences are counted towards the minimum number of
    variables to be present and may lead to unexpected results.
    """
    missing_array = _missing(data, args)
    if len(args) - len(missing_array) >= need_count:
        return []
    return missing_array


data_operations = {
    'var': _var,
    'missing': _missing,
    'missing_some': _missing_some
}


# MAIN LOGIC

def jsonLogic(logic, data=None):
    """
    Evaluate provided JsonLogic using given data (if any).
    If a single JsonLogic entry is provided - return a single resulting value.
    If an array of JsonLogic entries is provided - return an array of each
    entry's resulting values.
    """

    # Is this an array of JsonLogic entries?
    if isinstance(logic, (list, tuple)):
        return list(map(lambda subset: jsonLogic(subset, data), logic))

    # You've recursed to a primitive, stop!
    if not is_logic(logic):
        return logic

    # Get operator
    operator = next(iter(logic.keys()))

    # Get values
    values = logic[operator]
    # Easy syntax for unary operators like {"var": "x"}
    # instead of strict {"var": ["x"]}
    if not isinstance(values, (list, tuple)):
        values = [values]

    # Get data
    data = data or {}

    # Try applying logical operators first as they violate the normal rule of
    # depth-first calculating consequents. Let each manage recursion as needed.
    if operator in logical_operations:
        return logical_operations[operator](data, *values)

    # Recursion!
    values = [jsonLogic(val, data) for val in values]

    # Apply data retrieval operations
    if operator in data_operations:
        return data_operations[operator](data, *values)

    # Apply common operations
    if operator in operations:
        return operations[operator](*values)

    # Apply unsupported common operations if any
    if operator in unsupported_operations:
        warnings.warn(
            ("%r operation is not officially supported by JsonLogic and " +
             "is not guarantied to work in other JsonLogic ports") % operator,
            PendingDeprecationWarning)
        return unsupported_operations[operator](*values)

    # Report unrecognized operation
    raise ValueError("Unrecognized operation %r" % operator)


def is_logic(logic):
    """
    Determine if specified entry is a logic entry or not.
    A logic entry is a dictionary with exactly one key.
    An array of logic entries is not considered a logic entry itself.
    """
    return isinstance(logic, dict) and len(logic.keys()) == 1
