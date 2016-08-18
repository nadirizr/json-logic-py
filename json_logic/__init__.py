# This is a Python implementation of the following jsonLogic JS library:
# https://github.com/jwadhams/json-logic-js

import sys
from six.moves import reduce


def if_(*args):
    assert len(args) >= 2
    for i in range(0, len(args) - 1, 2):
        if args[i]:
            return args[i + 1]
    if len(args) % 2:
        return args[-1]
    else:
        return None

def soft_equals(a, b):
    if isinstance(a, str) or isinstance(b, str):
        return str(a) == str(b)
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) is bool(b)
    return a == b


def merge(*args):
    ret = []
    for arg in args:
        if isinstance(arg, list) or isinstance(arg, tuple):
            ret += list(arg)
        else:
            ret.append(arg)
    return ret


def get_var(data, var_name, not_found=None):
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
    not_found = object()
    ret = []
    for arg in args:
        if get_var(data, arg, not_found) is not_found:
            ret.append(arg)
    return ret


def missing_some(data, min_required, args):
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


operations = {
    "==": soft_equals,
    "===" : (lambda a, b: a is b),
    "!="  : (lambda a, b: not soft_equals(a, b)),
    "!==" : (lambda a, b: a is not b),
    ">"   : (lambda a, b: a > b),
    ">="  : (lambda a, b: a >= b),
    "<"   : (lambda a, b, c=None:
        a < b if c is None else (a < b < c)
      ),
    "<="  : (lambda a, b, c=None:
        a <= b if c is None else (a <= b <= c)
      ),
    "!"   : (lambda a: not a),
    "%"   : (lambda a, b: a % b),
    "and" : (lambda *args:
        reduce(lambda total, arg: total and arg, args, True)
      ),
    "or"  : (lambda *args:
        reduce(lambda total, arg: total or arg, args, False)
      ),
    "?:"  : (lambda a, b, c: b if a else c),
    "if": if_,
    "log" : (lambda a: a if sys.stdout.write(str(a)) else a),
    "in"  : (lambda a, b:
        a in b if "__contains__" in dir(b) else False
      ),
    "cat" : (lambda *args:
        "".join(args)
      ),
    "+" : (lambda *args:
        reduce(lambda total, arg: total + float(arg), args, 0.0)
      ),
    "*" : (lambda *args:
        reduce(lambda total, arg: total * float(arg), args, 1.0)
      ),
    "-" : (lambda a, b=None: -a if b is None else a - b),
    "/" : (lambda a, b=None: a if b is None else float(a) / float(b)),
    "min": min,
    "max": max,
    "merge": merge,
    "count": (lambda *args: sum(1 if a else 0 for a in args)),
}


def jsonLogic(tests, data=None):
  # You've recursed to a primitive, stop!
  if tests is None or type(tests) != dict:
    return tests

  data = data or {}

  op = list(tests.keys())[0]
  values = tests[op]

  # Easy syntax for unary operators, like {"var": "x"} instead of strict
  # {"var": ["x"]}
  if type(values) not in [list, tuple]:
    values = jsonLogic(values, data)
    # Let's do recursion first. If it's still not a list after processing,
    # then it means it's unary syntax sugar.
    if type(values) not in [list, tuple]:
      values = [values]
  else:
    # Recursion!
    values = [jsonLogic(val, data) for val in values]

  if op == 'var':
    return get_var(data, *values)
  if op == 'missing':
    return missing(data, *values)
  if op == 'missing_some':
    return missing_some(data, *values)

  if op not in operations:
    raise ValueError("Unrecognized operation %s" % op)

  return operations[op](*values)
