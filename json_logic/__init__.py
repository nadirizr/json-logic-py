"""
This is a Python implementation of the JsonLogic JS library:
https://github.com/jwadhams/json-logic-js
"""

# Python 2 fallbacks
from __future__ import division, unicode_literals

from six import text_type, integer_types, advance_iterator
from six.moves import reduce

numeric_types = integer_types + (float,)

import logging
import warnings

__all__ = (
    'jsonLogic',
    'is_logic',
    'uses_data',
    'rule_like',
    'operations',
    'add_operation',
    'rm_operation'
)

# Helper functions and variables

# Sentinel value to indicate an optional argument
# that can take various values including None
_no_argument = object()


def _is_array(arg):
    """Check if argument is an array (an ordered sequence of elements)."""
    return isinstance(arg, (list, tuple))


def _is_dictionary(arg):
    """Check if argument is an dictionary (or 'object' in JS)."""
    return isinstance(arg, dict)


def _is_boolean(arg):
    """Check if argument is a boolean value (True or False)."""
    return isinstance(arg, bool)


def _is_string(arg):
    """Check if argument is a string."""
    return isinstance(arg, text_type)


def _is_numeric(arg):
    """Check if argument is of a numeric type: float, int or long."""
    return type(arg) in numeric_types


def _to_numeric(arg):
    """
    Convert a string or other value  into float, integer or long.
    Convert float value to integer if appropriate.
    """
    if _is_string(arg) and '.' in arg:
        arg = float(arg)
    if isinstance(arg, float):
        return int(arg) if arg.is_integer() else arg
    return int(arg)


def _get_operator(logic):
    """Return operator name from JsonLogic rule."""
    return text_type(advance_iterator(iter(logic.keys())))


def _get_values(logic, operator, normalize=True):
    """Return array of values from JsonLogic rule by operator name."""
    values = logic[operator]
    # Easy syntax for unary operators like {"var": "x"}
    # instead of strict {"var": ["x"]}
    if normalize and not _is_array(values):
        values = [values]
    return values


def _expose_operations():
    """Gather all operation for read-only introspection."""
    global operations
    operations.clear()
    operations.update(_logical_operations)
    operations.update(_scoped_operations)
    operations.update(_data_operations)
    operations.update(_common_operations)
    operations.update(_unsupported_operations)
    operations.update(_custom_operations)
    return operations


def _not_none(fn):
    def wrapped(*args):
        if len(args) > 1 and all([arg is None for arg in args]):
            return False
        return fn(*args)

    return wrapped


# Common operations

def _equal_to(a, b):
    """Check for non-strict equality ('==') with JS-style type coercion."""
    if _is_string(a) or _is_string(b):
        return text_type(a) == text_type(b)
    if _is_boolean(a) or _is_boolean(b):
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


@_not_none
def _less_than(a, b, c=_no_argument):
    """
    Check that A is less then B (A < B) or
    that B is exclusively between A and C (A < B < C).

    N.B.: Comparison and type coercion is performed
    sequentially in pairs: A < B and B < C.
    So {"<": ["11", 2, "3"]} will evaluate to False,
    while {"<": ["11", "2", 3]} will evaluate to True.
    """
    if _is_numeric(a) or _is_numeric(b):
        try:
            a, b = _to_numeric(a), _to_numeric(b)
        except TypeError:
            return False  # NaN
    return a < b and (c is _no_argument or _less_than(b, c))


@_not_none
def _less_than_or_equal_to(a, b, c=_no_argument):
    """
    Check that A is less then or equal to B (A <= B) or
    that B is inclusively between A and C (A <= B <= C).

    N.B.: Comparison and type coercion is performed
    sequentially in pairs: A <= B and B <= C.
    So {"<=": ["11", 2, "3"]} will evaluate to False,
    while {"<=": ["11", "2", 3]} will evaluate to True.
    """
    return \
        (_less_than(a, b) or _equal_to(a, b)) and \
        (c is _no_argument or _less_than_or_equal_to(b, c))


@_not_none
def _greater_than(a, b):
    """Check that A is greater then B (A > B)."""
    return _less_than(b, a)


@_not_none
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
    return "".join(text_type(arg) for arg in args)


def _substring(source, start, length=None):
    """
    Return part of 'source' string specified by 'start' and 'length' arguments.
    Positive 'start': start at a specified position in the string.
    Negative 'start': start at a specified position from the end of the string.
    Zero 'start': start at the first character in the string.
    Positive 'length': max length to be returned from the 'start'.
    Negative 'length': max length to be omitted from the end of the string.
    Zero 'length': return empty string.
    Omitted 'length': return part from the 'start' till the end of the string.
    """
    return source[start:][:length]


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
        if _is_array(arg):
            resulting_array.extend(arg)
        else:
            resulting_array.append(arg)
    return resulting_array


def _method(obj, method, args=[]):
    """
    Call the specified 'method' on an 'obj' object with an array of 'args'
    arguments.

    Example:
    {"method": [{"var": "today"}, "isoformat"]}
    gets datetime.date object from 'today' variable and calls its 'isoformat'
    method returning an ISO-formated date string.
    {"method": ["string value", "split", [" "]]}
    calls split(' ') method on a "string value" string returning an array
    of ["string", "format"].

    Can also be used to get property values instead of calling a method.
    In this case arguments are ignored.

    Example:
    {"method": [{"var": "today"}, "month"]}
    gets datetime.date object from 'today' variable and returns the number of
    the month via 'month' property.
    """
    method = getattr(obj, text_type(method))
    if callable(method):
        return method(*args)
    return method


_common_operations = {
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
    'substr': _substring,
    '+': _add,
    '-': _subtract,
    '*': _multiply,
    '/': _divide,
    '%': _modulo,
    'min': _minimal,
    'max': _maximal,
    'merge': _merge,
    'method': _method
}


# Unsupported operations

def _count(*args):
    """Execute 'count' operation unsupported by core JsonLogic."""
    return sum(1 if a else 0 for a in args)


_unsupported_operations = {
    'count': _count
}

# Custom operation (may be added manually)

_custom_operations = {}


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


def _iif(data, a, b, c):
    """
    Evaluate ternary expression and return corresponding evaluated
    argument based on the following pattern: if (A) then {B} else {C}
    """
    return _if(data, a, b, c)


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


_logical_operations = {
    'if': _if,
    '?:': _iif,
    'and': _and,
    'or': _or,
}


# Scoped operations

def _filter(data, scopedData, scopedLogic):
    """
    Filter 'scopedData' using the specified 'scopedLogic' argument.

    'scopedData' argument can be:
      - a manually specified data array;
      - a JsonLogic rule returning a data array;
      - a JsonLogic 'var' operation returning part of the data object
        containing a data array; like: {"var": "a"};
      - a JsonLogic 'var' operation returning the whole data object
        if it is an array itself; like: {"var": ""}.

    'scopedLogic' is a normal JsonLogic rule that uses a 'scopeData'
    element as its data object.

    'scopedLogic' must evaluate to a truthy value in order for the current
    'scopedData' element to be included into the resulting array, or to
    a falsy value to exclude it.

    Example:
    {"filter": [
        [1, 2, 3, 4, 5],
        {"%": [{"var": ""}, 2]}
    ]}
    calculates to: [1, 3, 5]

    If 'scopedData' argument does not evaluate to an array, an empty array
    is returned.
    """
    scopedData = jsonLogic(scopedData, data)
    if not _is_array(scopedData):
        return []
    return list(filter(
        lambda datum: _truthy(jsonLogic(scopedLogic, datum)),
        scopedData))


def _map(data, scopedData, scopedLogic):
    """
    Apply 'scopedLogic' argument to each 'scopedData' element.

    'scopedData' argument can be:
      - a manually specified data array;
      - a JsonLogic rule returning a data array;
      - a JsonLogic 'var' operation returning part of the data object
        containing a data array; like: {"var": "a"};
      - a JsonLogic 'var' operation returning the whole data object
        if it is an array itself; like: {"var": ""}.

    'scopedLogic' is a normal JsonLogic rule that uses a 'scopeData'
    element as its data object.

    Result returned by 'scopedLogic' is included into the resulting array.

    Example:
    {"map": [
        [1, 2, 3, 4, 5],
        {"*": [{"var": ""}, 2]}
    ]}
    calculates to: [2, 4, 6, 8, 10]

    If 'scopedData' argument does not evaluate to an array, an empty array
    is returned.
    """
    scopedData = jsonLogic(scopedData, data)
    if not _is_array(scopedData):
        return []
    return list(map(
        lambda datum: jsonLogic(scopedLogic, datum),
        scopedData))


def _reduce(data, scopedData, scopedLogic, initial=None):
    """
    Apply 'scopedLogic' cumulatively to the elements in 'scopedData' argument,
    from left to right, so as to reduce the sequence it to a single value.
    If 'initial' is provided, it is placed before all 'scopedData' elements in
    the calculation, and serves as a default when 'scopedData' array is empty.

    'scopedData' argument can be:
      - a manually specified data array;
      - a JsonLogic rule returning a data array;
      - a JsonLogic 'var' operation returning part of the data object
        containing a data array; like: {"var": "a"};
      - a JsonLogic 'var' operation returning the whole data object
        if it is an array itself; like: {"var": ""}.

    'scopedLogic' is a normal JsonLogic rule that is applied to the following
    data object: {'accumulator': accumulator, 'current': current}; where
    'accumulator' is the result of all previous iterations (of 'initial' if
    none had occurred so far), and 'current' is the value of the current
    'scopedData' element being analyzed.

    The return value of the final application is returned as the result of
    the 'reduce' operation.

    Example:
    {"reduce": [
        [1, 2, 3, 4, 5],
        {"+": [{"var": "accumulator"}, {"var": "current"}]},
        0
    ]}
    calculates as: ((((1+2)+3)+4)+5) = 15

    If 'scopedData' argument does not evaluate to an array, the 'initial'
    value is returned.
    """
    scopedData = jsonLogic(scopedData, data)
    if not _is_array(scopedData):
        return initial
    return reduce(
        lambda accumulator, current: jsonLogic(
            scopedLogic, {'accumulator': accumulator, 'current': current}),
        scopedData, initial)


def _all(data, scopedData, scopedLogic):
    """
    Check if 'scopedLogic' evaluates to a truthy value for all
    'scopedData' elements.

    'scopedData' argument can be:
      - a manually specified data array;
      - a JsonLogic rule returning a data array;
      - a JsonLogic 'var' operation returning part of the data object
        containing a data array; like: {"var": "a"};
      - a JsonLogic 'var' operation returning the whole data object
        if it is an array itself; like: {"var": ""}.

    'scopedLogic' is a normal JsonLogic rule that uses a 'scopeData'
    element as its data object.

    Return True if 'scopedLogic' evaluates to a truthy value for all
    'scopedData' elements. Return False otherwise.

    Example:
    {"all": [
        [1, 2, 3, 4, 5],
        {">=":[{"var":""}, 1]}
    ]}
    evaluates to: True

    If 'scopedData' argument does not evaluate to an array or if the array
    is empty, False is returned.

    N.B.: According to current core JsonLogic evaluation of 'scopedData'
    elements stops upon encountering first falsy value.
    """
    scopedData = jsonLogic(scopedData, data)
    if not _is_array(scopedData):
        return False
    if len(scopedData) == 0:
        return False  # "all" of an empty set is false
    for datum in scopedData:
        if _falsy(jsonLogic(scopedLogic, datum)):
            return False  # First falsy, short circuit
    return True  # All were truthy


def _none(data, scopedData, scopedLogic):
    """
    Check if 'scopedLogic' evaluates to a truthy value for none of
    'scopedData' elements.

    'scopedData' argument can be:
      - a manually specified data array;
      - a JsonLogic rule returning a data array;
      - a JsonLogic 'var' operation returning part of the data object
        containing a data array; like: {"var": "a"};
      - a JsonLogic 'var' operation returning the whole data object
        if it is an array itself; like: {"var": ""}.

    'scopedLogic' is a normal JsonLogic rule that uses a 'scopeData'
    element as its data object.

    Return True if 'scopedLogic' evaluates to a falsy value for all
    'scopedData' elements. Return False otherwise.

    Example:
    {"none": [
        [1, 2, 3, 4, 5],
        {"==":[{"var":""}, 10]}
    ]}
    evaluates to: True

    If 'scopedData' argument does not evaluate to an array or if the array
    is empty, True is returned.

    N.B.: According to current core JsonLogic all 'scopedData' elements are
    evaluated before returning the result. It does not stop at first truthy
    value.
    """
    return len(_filter(data, scopedData, scopedLogic)) == 0


def _some(data, scopedData, scopedLogic):
    """
    Check if 'scopedLogic' evaluates to a truthy value for at least
    one 'scopedData' element.

    'scopedData' argument can be:
      - a manually specified data array;
      - a JsonLogic rule returning a data array;
      - a JsonLogic 'var' operation returning part of the data object
        containing a data array; like: {"var": "a"};
      - a JsonLogic 'var' operation returning the whole data object
        if it is an array itself; like: {"var": ""}.

    'scopedLogic' is a normal JsonLogic rule that uses a 'scopeData'
    element as its data object.

    Return True if 'scopedLogic' evaluates to a truthy value for at least
    one 'scopedData' element. Return False otherwise.

    Example:
    {"some": [
        [1, 2, 3, 4, 5],
        {"==":[{"var":""}, 3]}
    ]}
    evaluates to: True

    If 'scopedData' argument does not evaluate to an array or if the array
    is empty, False is returned.

    N.B.: According to current core JsonLogic all 'scopedData' elements are
    evaluated before returning the result. It does not stop at first truthy
    value.
    """
    return len(_filter(data, scopedData, scopedLogic)) > 0


_scoped_operations = {
    'filter': _filter,
    'map': _map,
    'reduce': _reduce,
    'all': _all,
    'none': _none,
    'some': _some
}


# Data operations

def _var(data, var_name=None, default=None):
    """
    Get variable value from the data object.
    Can also access variable properties (to any depth) via dot-notation:
        "variable.property"
        "variable.property.subproperty"
    The same is true for array elements that can be accessed by index:
        "array_variable.5"
        "variable.array_property.0.subproperty"
    Return the specified default value if variable, its property or element
    is not found. Return None if no default value is specified.
    Return the whole data object if variable name is None or an empty string.
    """
    if var_name is None or var_name == '':
        return data  # Return the whole data object
    try:
        for key in text_type(var_name).split('.'):
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
    var_names = args[0] if args and _is_array(args[0]) else args
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


_data_operations = {
    'var': _var,
    'missing': _missing,
    'missing_some': _missing_some
}


# MAIN LOGIC

def jsonLogic(logic, data=None):
    """
    Evaluate provided JsonLogic using given data (if any).
    If a single JsonLogic rule is provided - return a single resulting value.
    If an array of JsonLogic rule is provided - return an array of each rule's
    resulting values.
    """

    # Is this an array of JsonLogic rules?
    if _is_array(logic):
        return list(map(lambda sublogic: jsonLogic(sublogic, data), logic))

    # You've recursed to a primitive, stop!
    if not is_logic(logic):
        return logic

    # Get operator
    operator = _get_operator(logic)

    # Get values
    values = _get_values(logic, operator)

    # Get data
    data = data or {}

    # Try applying logical operators first as they violate the normal rule of
    # depth-first calculating consequents. Let each manage recursion as needed.
    if operator in _logical_operations:
        return _logical_operations[operator](data, *values)

    # Next up, try applying scoped operations that manage their own data scopes
    # for each constituent operation
    if operator in _scoped_operations:
        return _scoped_operations[operator](data, *values)

    # Recursion!
    values = [jsonLogic(val, data) for val in values]

    # Apply data retrieval operations
    if operator in _data_operations:
        return _data_operations[operator](data, *values)

    # Apply simple custom operations (if any)
    if operator in _custom_operations:
        return _custom_operations[operator](*values)

    # Apply common operations
    if operator in _common_operations:
        return _common_operations[operator](*values)

    # Apply unsupported common operations if any
    if operator in _unsupported_operations:
        warnings.warn(
            ("%r operation is not officially supported by JsonLogic and " +
             "is not guarantied to work in other JsonLogic ports") % operator,
            PendingDeprecationWarning)
        return _unsupported_operations[operator](*values)

    # Apply dot-notated custom operations (if any)
    suboperators = operator.split('.')
    if len(suboperators) > 1 and suboperators[0]:  # Dots in the middle
        current_operation = _custom_operations
        for idx, suboperator in enumerate(suboperators):
            try:
                if _is_dictionary(current_operation):
                    try:
                        current_operation = current_operation[suboperator]
                    except (KeyError, IndexError):
                        current_operation = current_operation[int(suboperator)]
                elif _is_array(current_operation):
                    current_operation = current_operation[int(suboperator)]
                else:
                    current_operation = getattr(current_operation, suboperator)
            except (KeyError, IndexError, AttributeError, ValueError):
                raise ValueError(
                    "Unrecognized operation %r (failed at %r)"
                    % (operator, '.'.join(suboperators[:idx + 1])))
        return current_operation(*values)

    # Report unrecognized operation
    raise ValueError("Unrecognized operation %r" % operator)


def is_logic(logic):
    """
    Determine if specified object is a JsonLogic rule or not.
    A JsonLogic rule is a dictionary with exactly one key.
    An array of JsonLogic rules is not considered a rule itself.
    """
    return _is_dictionary(logic) and len(logic.keys()) == 1


def uses_data(logic):
    """
    Return a unique array of variables used in JsonLogic rule.

    N.B.: It does not cover the case where the argument to 'var'
    is itself a JsonLogic rule.
    """
    variables = set()
    if is_logic(logic):
        operator = _get_operator(logic)
        values = _get_values(logic, operator)
        if operator == "var":
            variables.add(values[0])
        else:
            variables.update(*map(uses_data, values))
    return sorted(variables)


def rule_like(rule, pattern):
    """
    Check if JsonLogic rule matches a certain 'pattern'.
    Pattern follows the same structure as a normal JsonLogic rule
    with the following extensions:
      - '@' element matches anything:
        1 == '@'
        "jsonlogic" == '@'
        [1, 2] == '@'
        {'+': [1, 2]} == '@'
        {'+': [1, 2]} == {'@': [1, 2]}
        {'+': [1, 2]} == {'+': '@'}
        {'+': [1, 2]} == {'+': ['@', '@']}
        {'+': [1, 2]} == {'@': '@'}
      - 'number' element matches any numeric value:
        1 == 'number'
        2.34 == 'number'
        [1, 2] == ['number', 'number']
        {'+': [1, 2]} == {'+': ['number', 'number']}
      - 'string' element matches any string value:
        "name" == 'string'
        {'cat': ["json", "logic"]} = {'cat': ['string', 'string']}
      - 'array' element matches an array of any length:
        [] == 'array'
        [1, 2, 3] = 'array'
        {'+': [1, 2]} == {'+': 'array'}
    Use this method to make sure JsonLogic rule is correctly constructed.
    """
    if pattern == rule:
        return True
    if pattern == '@':
        return True
    if pattern == 'number':
        return _is_numeric(rule)
    if pattern == 'string':
        return _is_string(rule)
    if pattern == "array":
        return _is_array(rule)

    if is_logic(pattern):
        if is_logic(rule):
            # Both pattern and rule are a valid JsonLogic rule, go deeper
            pattern_operator = _get_operator(pattern)
            rule_operator = _get_operator(rule)
            if pattern_operator == '@' or pattern_operator == rule_operator:
                # Operators match, go deeper and try matching values
                return rule_like(
                    _get_values(rule, rule_operator, normalize=False),
                    _get_values(pattern, pattern_operator, normalize=False))
        return False  # All above assumptions failed

    if _is_array(pattern):
        if _is_array(rule):
            # Both pattern and rule are arrays, go deeper
            if len(pattern) == len(rule):
                # Length of pattern and rule arrays are the same,
                # go deeper and try matching each value
                return all(
                    rule_like(rule_elem, pattern_elem)
                    for rule_elem, pattern_elem in zip(rule, pattern))
        return False  # All above assumptions failed

    return False  # Not a match, not a nested rule and not an array


def add_operation(name, code):
    """
    Add a custom common JsonLogic operation.

    Operation code must only take positional arguments that are absolutely
    necessary for its execution. JsonLogic will run it using the array of
    provided values, like: code(*values)

    Example:
    {"my_operation": [1, 2, 3]} will be called as code(1, 2, 3)

    Can also be used to add custom classed or even packages to extend JsonLogic
    functionality.

    Example:
    add_operation("datetime", datetime)

    Methods of such classes or packages can later be called using dot-notation.

    Example:
    {"datetime.datetime.now": []}
    can be used to retrieve current datetime value.
    {"datetime.date": [2018, 1, 1]}
    can be used to retrieve January 1, 2018 date.

    N.B.: Custom operations may be used to override common JsonLogic functions,
    but not logical, scoped or data retrieval ones.
    """
    global _custom_operations
    _custom_operations[text_type(name)] = code
    _expose_operations()


def rm_operation(name):
    """Remove previously added custom common JsonLogic operation."""
    global _custom_operations
    del (_custom_operations[text_type(name)])
    _expose_operations()


# Initially expose operations of read-only introspection
operations = {}
_expose_operations()
