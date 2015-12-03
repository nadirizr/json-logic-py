# json-logic-py

This parser accepts [JsonLogic](http://jsonlogic.com) rules and executes them in Python.
This is a Python porting of the excellend GitHub project by [jwadhams](https://github.com/jwadhams) for JavaScript: [json-logic-js](https://github.com/jwadhams/json-logic-js).
All credit goes to him, this is simply an implementation of the same logic in Python (small differences below).

The JsonLogic format is designed to allow you to share rules (logic) between front-end and back-end code (regardless of language difference), even to store logic along with a record in a database.  JsonLogic is documented extensively at [JsonLogic.com](http://jsonlogic.com), including examples of every [supported operation](http://jsonlogic.com/operations.html) and a place to [try out rules in your browser](http://jsonlogic.com/play.html).

The same format can also be executed in PHP by the library [json-logic-php](https://github.com/jwadhams/json-logic-php/)

## Examples

### Simple
```python
jsonLogic( { "==" : [1, 1] } )
# True
```

This is a simple test, equivalent to `1 == 1`.  A few things about the format:

  1. The operator is always in the "key" position. There is only one key per JsonLogic rule.
  1. The values are typically an array.
  1. Each value can be a string, number, boolean, array (non-associative), or null

### Compound
Here we're beginning to nest rules. 

```python
jsonLogic(
  {"and" : [
    { ">" : [3,1] },
    { "<" : [1,3] }
  ] }
)
# True
```
  
In an infix language (like Python) this could be written as:

```python
( (3 > 1) and (1 < 3) )
```
    
### Data-Driven

Obviously these rules aren't very interesting if they can only take static literal data. Typically `jsonLogic` will be called with a rule object and a data object. You can use the `var` operator to get attributes of the data object:

```python
jsonLogic(
  { "var" : ["a"] }, # Rule
  { a : 1, b : 2 }   # Data
)
# 1
```

If you like, we support [syntactic sugar](https://en.wikipedia.org/wiki/Syntactic_sugar) on unary operators to skip the array around values:

```python
jsonLogic(
  { "var" : "a" },
  { a : 1, b : 2 }
)
# 1
```

You can also use the `var` operator to access an array by numeric index:

```python
jsonLogic(
  {"var" : 1 },
  [ "apple", "banana", "carrot" ]
)
# "banana"
```

Here's a complex rule that mixes literals and data. The pie isn't ready to eat unless it's cooler than 110 degrees, *and* filled with apples.

```python
rules = { "and" : [
  {"<" : [ { "var" : "temp" }, 110 ]},
  {"==" : [ { "var" : "pie.filling" }, "apple" ] }
] }

data = { "temp" : 100, "pie" : { "filling" : "apple" } }

jsonLogic(rules, data)
# True
```

### Always and Never
Sometimes the rule you want to process is "Always" or "Never."  If the first parameter passed to `jsonLogic` is a non-object, non-associative-array, it is returned immediately.

```python
#Always
jsonLogic(True, data_will_be_ignored);
# True

#Never
jsonLogic(false, i_wasnt_even_supposed_to_be_here);
# False
```

## Installation

The best way to install this library is via [PIP](https://pypi.python.org/pypi/):

```bash
pip install json-logic-py
```

If that doesn't suit you, and you want to manage updates yourself, the entire library is self-contained in `json_logic.py` and you can download it straight into your project as you see fit.

```bash
curl -O https://raw.githubusercontent.com/nadirizr/json-logic-py/master/json_logic.py
```

## Differences from the original [JavaScript version](https://github.com/jwadhams/json-logic-js)

The only difference is in the straightforward '==' and '===' comparison operators, since they have different expected behavior in Python than in JavaScript.

In JS:
* '==' - Performs type coercion and compares.
* '===' - Does not perform type coercion.

In Python:
* '==' - Does not perform type coercion, compares using Pyton's __eq__ operator.
* '===' - Does not perform type coercion, compares using Python's 'is' operator.
