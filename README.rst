json-logic-py
=============

This parser accepts `JsonLogic <http://jsonlogic.com>`__ rules and
executes them in Python.

This is a Python porting of the excellent GitHub project by
`jwadhams <https://github.com/jwadhams>`__ for JavaScript:
`json-logic-js <https://github.com/jwadhams/json-logic-js>`__.

All credit goes to him, this is simply an implementation of the same
logic in Python (small differences below).

The JsonLogic format is designed to allow you to share rules (logic)
between front-end and back-end code (regardless of language difference),
even to store logic along with a record in a database. JsonLogic is
documented extensively at `JsonLogic.com <http://jsonlogic.com>`__,
including examples of every `supported
operation <http://jsonlogic.com/operations.html>`__ and a place to `try
out rules in your browser <http://jsonlogic.com/play.html>`__.

The same format can also be executed in PHP by the library
`json-logic-php <https://github.com/jwadhams/json-logic-php/>`__

Examples
--------

Simple
~~~~~~

.. code:: python

    from json_logic import jsonLogic
    jsonLogic( { "==" : [1, 1] } )
    # True

This is a simple test, equivalent to ``1 == 1``. A few things about the
format:

1. The operator is always in the "key" position. There is only one key
   per JsonLogic rule.
2. The values are typically an array.
3. Each value can be a string, number, boolean, array (non-associative),
   or null

Compound
~~~~~~~~

Here we're beginning to nest rules.

.. code:: python

    jsonLogic(
      {"and" : [
        { ">" : [3,1] },
        { "<" : [1,3] }
      ] }
    )
    # True

In an infix language (like Python) this could be written as:

.. code:: python

    ( (3 > 1) and (1 < 3) )

Data-Driven
~~~~~~~~~~~

Obviously these rules aren't very interesting if they can only take
static literal data. Typically ``jsonLogic`` will be called with a rule
object and a data object. You can use the ``var`` operator to get
attributes of the data object:

.. code:: python

    jsonLogic(
      { "var" : ["a"] },       # Rule
      { "a" : 1, "b" : 2 }     # Data
    )
    # 1

If you like, we support `syntactic
sugar <https://en.wikipedia.org/wiki/Syntactic_sugar>`__ on unary
operators to skip the array around values:

.. code:: python

    jsonLogic(
      { "var" : "a" },
      { "a" : 1, "b" : 2 }
    )
    # 1

You can also use the ``var`` operator to access an array by numeric
index:

.. code:: python

    jsonLogic(
      {"var" : 1 },
      [ "apple", "banana", "carrot" ]
    )
    # "banana"

Here's a complex rule that mixes literals and data. The pie isn't ready
to eat unless it's cooler than 110 degrees, *and* filled with apples.

.. code:: python

    rules = { "and" : [
      {"<" : [ { "var" : "temp" }, 110 ]},
      {"==" : [ { "var" : "pie.filling" }, "apple" ] }
    ] }

    data = { "temp" : 100, "pie" : { "filling" : "apple" } }

    jsonLogic(rules, data)
    # True

Always and Never
~~~~~~~~~~~~~~~~

Sometimes the rule you want to process is "Always" or "Never." If the
first parameter passed to ``jsonLogic`` is a non-object,
non-associative-array, it is returned immediately.

.. code:: python

    #Always
    jsonLogic(True, data_will_be_ignored)
    # True

    #Never
    jsonLogic(False, i_wasnt_even_supposed_to_be_here)
    # False

Supported Operations
--------------------

Comparison Operators
~~~~~~~~~~~~~~~~~~~~

- ``==`` - Soft equality (with type coercion)
- ``===`` - Hard equality (strict type check)
- ``!=`` - Soft inequality
- ``!==`` - Hard inequality
- ``>`` - Greater than
- ``>=`` - Greater than or equal
- ``<`` - Less than
- ``<=`` - Less than or equal

Boolean Operators
~~~~~~~~~~~~~~~~~

.. code:: python

    # Logical AND
    jsonLogic({"and": [True, True, True]})
    # True

    # Logical OR  
    jsonLogic({"or": [False, False, True]})
    # True

    # Negation
    jsonLogic({"!": True})
    # False

    # Double negation (convert to boolean)
    jsonLogic({"!!": "yes"})
    # True

Conditional Operators
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    # Ternary operator
    jsonLogic({"?:": [True, "yes", "no"]})
    # "yes"

    # If-else with multiple conditions
    jsonLogic({"if": [
        {"<": [{"var": "temp"}, 0]}, "freezing",
        {"<": [{"var": "temp"}, 20]}, "cold",
        "warm"
    ]}, {"temp": 15})
    # "cold"

Arithmetic Operators
~~~~~~~~~~~~~~~~~~~~

.. code:: python

    # Addition
    jsonLogic({"+": [1, 2, 3]})
    # 6

    # Subtraction
    jsonLogic({"-": [5, 2]})
    # 3

    # Unary minus
    jsonLogic({"-": [5]})
    # -5

    # Multiplication
    jsonLogic({"*": [2, 3, 4]})
    # 24

    # Division
    jsonLogic({"/": [10, 2]})
    # 5.0

    # Modulo
    jsonLogic({"%": [7, 3]})
    # 1

    # Min and Max
    jsonLogic({"min": [1, 5, 3]})
    # 1

    jsonLogic({"max": [1, 5, 3]})
    # 5

String Operations
~~~~~~~~~~~~~~~~~

.. code:: python

    # Concatenation
    jsonLogic({"cat": ["Hello", " ", "World"]})
    # "Hello World"

    # Substring
    jsonLogic({"substr": ["jsonlogic", 0, 4]})
    # "json"

    jsonLogic({"substr": ["jsonlogic", 4]})
    # "logic"

    # Negative length (from end)
    jsonLogic({"substr": ["jsonlogic", 0, -5]})
    # "json"

Array Operations
~~~~~~~~~~~~~~~~

.. code:: python

    # Merge arrays
    jsonLogic({"merge": [[1, 2], [3, 4]]})
    # [1, 2, 3, 4]

    # Check if value is in array
    jsonLogic({"in": ["banana", ["apple", "banana", "carrot"]]})
    # True

    # Count truthy values
    jsonLogic({"count": [True, False, True, True]})
    # 3

Array Iteration Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~

**map** - Apply a rule to each element in an array:

.. code:: python

    jsonLogic(
        {"map": [
            {"var": "integers"},
            {"*": [{"var": ""}, 2]}
        ]},
        {"integers": [1, 2, 3, 4, 5]}
    )
    # [2, 4, 6, 8, 10]

**filter** - Return only elements that pass a test:

.. code:: python

    jsonLogic(
        {"filter": [
            {"var": "integers"},
            {">": [{"var": ""}, 2]}
        ]},
        {"integers": [1, 2, 3, 4, 5]}
    )
    # [3, 4, 5]

**reduce** - Reduce an array to a single value:

.. code:: python

    jsonLogic(
        {"reduce": [
            {"var": "integers"},
            {"+": [{"var": "current"}, {"var": "accumulator"}]},
            0
        ]},
        {"integers": [1, 2, 3, 4, 5]}
    )
    # 15

**all** - Returns true if all elements pass the test:

.. code:: python

    jsonLogic(
        {"all": [
            {"var": "integers"},
            {">": [{"var": ""}, 0]}
        ]},
        {"integers": [1, 2, 3]}
    )
    # True

**some** - Returns true if any element passes the test:

.. code:: python

    jsonLogic(
        {"some": [
            {"var": "integers"},
            {"<": [{"var": ""}, 0]}
        ]},
        {"integers": [1, 2, -1]}
    )
    # True

**none** - Returns true if no elements pass the test:

.. code:: python

    jsonLogic(
        {"none": [
            {"var": "integers"},
            {"<": [{"var": ""}, 0]}
        ]},
        {"integers": [1, 2, 3]}
    )
    # True

Missing Variables
~~~~~~~~~~~~~~~~~

**missing** - Returns an array of missing variable names:

.. code:: python

    jsonLogic(
        {"missing": ["a", "b", "c"]},
        {"a": 1, "c": 3}
    )
    # ["b"]

**missing_some** - Returns missing variables only if less than a minimum are present:

.. code:: python

    jsonLogic(
        {"missing_some": [2, ["a", "b", "c"]]},
        {"a": 1}
    )
    # ["b", "c"]

    jsonLogic(
        {"missing_some": [2, ["a", "b", "c"]]},
        {"a": 1, "b": 2}
    )
    # []

Logging
~~~~~~~

.. code:: python

    # Log a value (uses Python logging module)
    jsonLogic({"log": "Hello World"})
    # Logs "Hello World" and returns "Hello World"

Custom Operations
-----------------

You can add your own custom operations using ``add_operation``:

.. code:: python

    from json_logic import jsonLogic, add_operation

    # Add a custom operation
    add_operation("times", lambda a, b: a * b)

    jsonLogic({"times": [3, 4]})
    # 12

    # Add a more complex operation
    add_operation("pow", lambda a, b: a ** b)

    jsonLogic({"pow": [2, 8]})
    # 256

You can also remove operations with ``rm_operation``:

.. code:: python

    from json_logic import rm_operation

    rm_operation("times")

Installation
------------

The best way to install this library is via
`PIP <https://pypi.python.org/pypi/>`__:

.. code:: bash

    pip install json-logic

If that doesn't suit you, and you want to manage updates yourself, the
entire library is self-contained in ``json_logic/__init__.py`` and you can
download it straight into your project as you see fit.

.. code:: bash

    curl -O https://raw.githubusercontent.com/nadirizr/json-logic-py/master/json_logic/__init__.py
