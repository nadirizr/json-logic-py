# json-logic-py

This parser accepts [JsonLogic](http://jsonlogic.com) rules and executes them in Python.

This is a fork of [json-logic-py](https://github.com/nadirizr/json-logic-py>) by 
[nadir.izr](https://github.com/nadirizr), which is a Python porting of the
GitHub project by [jwadhams](https://github.com/jwadhams>) for JavaScript:
[json-logic-js](https://github.com/jwadhams/json-logic-js>).

The JsonLogic format is designed to allow you to share rules (logic) between front-end and back-end code (regardless of language difference), even to store logic along with a record in a database.  JsonLogic is documented extensively at [JsonLogic.com](http://jsonlogic.com), including examples of every [supported operation](http://jsonlogic.com/operations.html) and a place to [try out rules in your browser](http://jsonlogic.com/play.html).

The same format can also be executed in PHP by the library [json-logic-php](https://github.com/jwadhams/json-logic-php/)

## Examples

### Simple
```python
from json_logic import jsonLogic
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

And in an array of objects, it is also possible to access elements based on their index (index starting from 0):

```python
data = {
    "cars": [
        {"colour": "blue", "price": 2000},
        {"colour": "red", "price": 3000},
    ]
}
rule = {"var": "cars.0.colour"}

jsonLogic(rule, data)
# "blue"
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

It is also possible to specify default values for the vars:

```python
rules = { "var": ["a", 1] }

data = { "b": 2 }

jsonLogic(rules, data)
# 1
```

If the value is present but empty, the default value will be used:

```python
rules = { "var": ["a", 1] }

data = { "a": None, "b": 2 }

jsonLogic(rules, data)
# 1
```

This is slightly different behaviour from javascript, where the default is used only if the variable is `undefined`:

```js
logic = {"var": ["a", 3]};
data = {"a": undefined};
jsonLogic.apply(logic, data);
// 3
data = {"a": null}
jsonLogic.apply(logic, data);
// null
```

### Dates

You can use the `date` operator to include dates in the json logic. The dates are internally converted to `datetime.date`
objects, and then the comparison is performed.

```python
rule = {"<=": [{"date": {"var": "testDate"}}, {"date": "2021-01-01"}]}
data = {"testDate": "2020-01-01"}

jsonLogic(rule, data)
# True
```

The operator `{"today": []}` gets the current date. It is also possible to add/subtract years to a date. This makes use 
of `relativedelta` from `dateutils`.

```python
rule = {"-": [{"date": "2021-01-01"}, {"years": 18}]}

jsonLogic(rule)
# date(2003, 1, 1)
```

### Datetimes

You can use the `datetime` operator to include datetimes in the json logic. The datetimes are internally converted to `datetime.datetime`
objects, and then the comparison is performed.

```python
rule = {
    "<=": [
        {"datetime": {"var": "testDatetime"}},
        {"datetime": "2022-12-01T10:00:00.000+02:00"},
    ]
}
data = {"testDatetime": "2022-11-01T10:00:00.000+02:00"}

jsonLogic(rule, data)
# True
```

### Always and Never
Sometimes the rule you want to process is "Always" or "Never."  If the first parameter passed to `jsonLogic` is a non-object, non-associative-array, it is returned immediately.

```python
#Always
jsonLogic(True, data_will_be_ignored);
# True

#Never
jsonLogic(False, i_wasnt_even_supposed_to_be_here);
# False
```

## Array operations

### Reduce

You can use reduce to combine all the elements in an array into a single value, like adding up a list of numbers. 
Note, that inside the logic being used to reduce, var operations only have access to an object like:

```
{
    "current": # this element of the array,
    "accumulator": # progress so far, or the initial value
}
```

Example to sum a particular element of each item:

```python
data = {
    "cars": [
        {"colour": "blue", "price": 2000},
        {"colour": "red", "price": 3000},
    ]
}

rule = {
    "reduce": [
        {"var": "cars"},
        {"+": [{"var": "accumulator"}, {"var": "current.price"}]},
        0,
    ]
}

jsonLogic(rule, data)
# 5000
```

Example to calculate the length of the `cars` array from the previous example:

```python
rule = {"reduce": [{"var": "cars"}, {"+": [{"var": "accumulator"}, 1]}, 0]}

jsonLogic(rule, data)
# 2
```

## Installation

The best way to install this library is via [PIP](https://pypi.python.org/pypi/):

```bash
pip install json-logic
```

If that doesn't suit you, and you want to manage updates yourself, the entire library is self-contained in `json_logic.py` and you can download it straight into your project as you see fit.

```bash
curl -O https://raw.githubusercontent.com/nadirizr/json-logic-py/master/json_logic.py
```
