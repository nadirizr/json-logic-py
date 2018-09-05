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
      { "var" : ["a"] }, # Rule
      { a : 1, b : 2 }   # Data
    )
    # 1

If you like, we support `syntactic
sugar <https://en.wikipedia.org/wiki/Syntactic_sugar>`__ on unary
operators to skip the array around values:

.. code:: python

    jsonLogic(
      { "var" : "a" },
      { a : 1, b : 2 }
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
    jsonLogic(True, data_will_be_ignored);
    # True

    #Never
    jsonLogic(False, i_wasnt_even_supposed_to_be_here);
    # False

Installation
------------

The best way to install this library is via
`PIP <https://pypi.python.org/pypi/>`__:

.. code:: bash

    pip install json-logic-qubit
