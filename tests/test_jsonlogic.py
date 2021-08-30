"""
Tests for jsonLogic.
"""
import unittest
from datetime import date, timedelta

from freezegun import freeze_time

from json_logic import jsonLogic


class JSONLogicTest(unittest.TestCase):
    """
    The tests here come from 'Supported operations' page on jsonlogic.com:
    http://jsonlogic.com/operations.html
    """

    def test_var(self):
        """Retrieve data from the provided data object."""
        self.assertEqual(jsonLogic({"var": ["a"]}, {"a": 1, "b": 2}), 1)

        # If you like, we support syntactic sugar to skip the array around
        # single values.
        self.assertEqual(jsonLogic({"var": "a"}, {"a": 1, "b": 2}), 1)

        # You can supply a default, as the second argument, for values that
        # might be missing in the data object.
        self.assertEqual(jsonLogic({"var": ["z", 26]}, {"a": 1, "b": 2}), 26)

        # The key passed to var can use dot-notation to get
        # the property of a property (to any depth you need):
        self.assertEqual(
            jsonLogic(
                {"var": "champ.name"},
                {
                    "champ": {"name": "Fezzig", "height": 223},
                    "challenger": {"name": "Dread Pirate Roberts", "height": 183},
                },
            ),
            "Fezzig",
        )

        # You can also use the var operator to access an array
        # by numeric index:
        self.assertEqual(jsonLogic({"var": 1}, ["apple", "banana", "carrot"]), "banana")

        # Here's a complex rule that mixes literals and data. The pie isn't
        # ready to eat unless it's cooler than 110 degrees, and filled
        # with apples.
        self.assertTrue(
            jsonLogic(
                {
                    "and": [
                        {"<": [{"var": "temp"}, 110]},
                        {"==": [{"var": "pie.filling"}, "apple"]},
                    ]
                },
                {"temp": 100, "pie": {"filling": "apple"}},
            )
        )

    def test_date(self):
        test_date = date(2021, 10, 1)

        self.assertEqual(test_date, jsonLogic({"date": "2021-10-01"}))
        self.assertEqual(
            test_date,
            jsonLogic({"date": {"var": "testDate"}}, {"testDate": "2021-10-01"}),
        )
        self.assertTrue(
            jsonLogic({"<=": [{"date": "2020-01-01"}, {"date": "2021-01-01"}]})
        )

        self.assertEqual(
            timedelta(days=366),
            jsonLogic({"-": [{"date": "2021-01-01"}, {"date": "2020-01-01"}]}),
        )

    def test_today(self):
        test_date = date(2021, 10, 1)

        with freeze_time("2021-10-01"):
            self.assertEqual(test_date, jsonLogic({"today": []}))
            self.assertTrue(jsonLogic({"==": [{"today": []}, {"date": "2021-10-01"}]}))

    def test_relative_delta(self):
        self.assertEqual(
            date(2003, 1, 1),
            jsonLogic({"-": [{"date": "2021-05-05"}, {"rdelta": [18, 4, 4]}]}),
        )
        self.assertEqual(
            date(2003, 1, 1),
            jsonLogic({"-": [{"date": "2021-05-01"}, {"rdelta": [18, 4]}]}),
        )
        self.assertEqual(
            date(2003, 1, 1),
            jsonLogic({"-": [{"date": "2021-01-01"}, {"rdelta": [18]}]}),
        )

        self.assertEqual(
            date(2021, 5, 5),
            jsonLogic({"+": [{"date": "2003-01-01"}, {"rdelta": [18, 4, 4]}]}),
        )
        self.assertEqual(
            date(2021, 5, 5),
            jsonLogic({"+": [{"date": "2003-01-05"}, {"rdelta": [18, 4]}]}),
        )
        self.assertEqual(
            date(2021, 5, 5),
            jsonLogic({"+": [{"date": "2003-05-05"}, {"rdelta": [18]}]}),
        )

    def test_missing(self):
        """
        Takes an array of data keys to search for (same format as var).
        Returns an array of any keys that are missing from the data object,
        or an empty array.
        """
        self.assertEqual(
            jsonLogic({"missing": ["a", "b"]}, {"a": "apple", "c": "carrot"}), ["b"]
        )

        self.assertEqual(
            jsonLogic({"missing": ["a", "b"]}, {"a": "apple", "b": "banana"}), []
        )

        # Note, in JsonLogic, empty arrays are falsy. So you can use missing
        # with if like:
        self.assertEqual(
            jsonLogic(
                {"if": [{"missing": ["a", "b"]}, "Not enough fruit", "OK to proceed"]},
                {"a": "apple", "b": "banana"},
            ),
            "OK to proceed",
        )

    def test_missing_some(self):
        """
        Takes a minimum number of data keys that are required, and an array
        of keys to search for (same format as var or missing). Returns
        an empty array if the minimum is met, or an array of the missing
        keys otherwise.
        """
        self.assertEqual(
            jsonLogic({"missing_some": [1, ["a", "b", "c"]]}, {"a": "apple"}), []
        )

        self.assertEqual(
            jsonLogic({"missing_some": [2, ["a", "b", "c"]]}, {"a": "apple"}),
            ["b", "c"],
        )

        # This is useful if you're using missing to track required fields,
        # but occasionally need to require N of M fields.
        self.assertEqual(
            jsonLogic(
                {
                    "if": [
                        {
                            "merge": [
                                {"missing": ["first_name", "last_name"]},
                                {"missing_some": [1, ["cell_phone", "home_phone"]]},
                            ]
                        },
                        "We require first name, last name, and one phone number.",
                        "OK to proceed",
                    ]
                },
                {"first_name": "Bruce", "last_name": "Wayne"},
            ),
            "We require first name, last name, and one phone number.",
        )

    def test_if(self):
        """
        The if statement typically takes 3 arguments: a condition (if),
        what to do if it's true (then), and what to do if it's false (else).
        """
        self.assertEqual(jsonLogic({"if": [True, "yes", "no"]}), "yes")

        self.assertEqual(jsonLogic({"if": [False, "yes", "no"]}), "no")

        # If can also take more than 3 arguments, and will pair up arguments
        # like if/then elseif/then elseif/then else. Like:
        self.assertEqual(
            jsonLogic(
                {
                    "if": [
                        {"<": [{"var": "temp"}, 0]},
                        "freezing",
                        {"<": [{"var": "temp"}, 100]},
                        "liquid",
                        "gas",
                    ]
                },
                {"temp": 200},
            ),
            "gas",
        )

    def test_equality(self):
        """Tests equality, with type coercion. Requires two arguments."""
        self.assertTrue(jsonLogic({"==": [1, 1]}))
        self.assertTrue(jsonLogic({"==": [1, "1"]}))
        self.assertTrue(jsonLogic({"==": [0, False]}))

    def test_stricy_equality(self):
        """Tests strict equality. Requires two arguments."""
        self.assertTrue(jsonLogic({"===": [1, 1]}))
        self.assertFalse(jsonLogic({"===": [1, "1"]}))

    def test_nonequality(self):
        """Tests not-equal, with type coercion."""
        self.assertTrue(jsonLogic({"!=": [1, 2]}))
        self.assertFalse(jsonLogic({"!=": [1, "1"]}))

    def test_strict_nonequality(self):
        """Tests not-equal, with type coercion."""
        self.assertTrue(jsonLogic({"!==": [1, 2]}))
        self.assertTrue(jsonLogic({"!==": [1, "1"]}))

    def test_not(self):
        """Logical negation ("not"). Takes just one argument."""
        self.assertFalse(jsonLogic({"!": [True]}))
        # Note: unary operators can also take a single, non array argument:
        self.assertFalse(jsonLogic({"!": True}))

    def test_or(self):
        """
        'or' can be used for simple boolean tests, with 1 or more arguments.
        """
        self.assertTrue(jsonLogic({"or": [True, False]}))
        # At a more sophisticated level, or returns the first truthy argument,
        # or the last argument.
        self.assertTrue(jsonLogic({"or": [False, True]}))
        self.assertEqual(jsonLogic({"or": [False, "apple"]}), "apple")
        self.assertEqual(jsonLogic({"or": [False, None, "apple"]}), "apple")

    def test_and(self):
        """
        'and' can be used for simple boolean tests, with 1 or more arguments.
        """
        self.assertTrue(jsonLogic({"and": [True, True]}))
        self.assertFalse(jsonLogic({"and": [True, True, True, False]}))
        # At a more sophisticated level, and returns the first falsy argument,
        # or the last argument.
        self.assertFalse(jsonLogic({"and": [True, "apple", False]}))
        self.assertEqual(jsonLogic({"and": [True, "apple", 3.14]}), 3.14)

    def test_cmp(self):
        """Arithmetic comparison functions."""
        # Greater than:
        self.assertTrue(jsonLogic({">": [2, 1]}))
        # Greater than or equal to:
        self.assertTrue(jsonLogic({">=": [1, 1]}))
        # Less than:
        self.assertTrue(jsonLogic({"<": [1, 2]}))
        # Less than or equal to:
        self.assertTrue(jsonLogic({"<=": [1, 1]}))

    def test_between(self):
        """
        You can use a special case of < and <= to test that one value
        is between two others.
        """
        # Between exclusive:
        self.assertTrue(jsonLogic({"<": [1, 2, 3]}))
        self.assertFalse(jsonLogic({"<": [1, 1, 3]}))
        self.assertFalse(jsonLogic({"<": [1, 4, 3]}))
        # Between inclusive:
        self.assertTrue(jsonLogic({"<=": [1, 2, 3]}))
        self.assertTrue(jsonLogic({"<=": [1, 1, 3]}))
        self.assertFalse(jsonLogic({"<=": [1, 4, 3]}))
        # This is most useful with data:
        self.assertTrue(jsonLogic({"<": [0, {"var": "temp"}, 100]}, {"temp": 37}))

    def test_max_min(self):
        """Return the maximum or minimum from a list of values."""
        self.assertEqual(jsonLogic({"max": [1, 2, 3]}), 3)
        self.assertEqual(jsonLogic({"min": [1, 2, 3]}), 1)

    def test_arithmetic(self):
        """Arithmetic operators."""
        self.assertEqual(jsonLogic({"+": [1, 1]}), 2)
        self.assertEqual(jsonLogic({"*": [2, 3]}), 6)
        self.assertEqual(jsonLogic({"-": [3, 2]}), 1)
        self.assertEqual(jsonLogic({"/": [2, 4]}), 0.5)
        self.assertEqual(jsonLogic({"+": [1, 1]}), 2)
        # Because addition and multiplication are associative,
        # they happily take as many args as you want:
        self.assertEqual(jsonLogic({"+": [1, 1, 1, 1, 1]}), 5)
        self.assertEqual(jsonLogic({"*": [2, 2, 2, 2, 2]}), 32)
        # Passing just one argument to - returns its arithmetic
        # negative (additive inverse).
        self.assertEqual(jsonLogic({"-": [2]}), -2)
        self.assertEqual(jsonLogic({"-": [-2]}), 2)
        # Passing just one argument to + casts it to a number.
        self.assertEqual(jsonLogic({"+": "0"}), 0)

    def test_modulo(self):
        """
        Modulo. Finds the remainder after the first argument
        is divided by the second argument.
        """
        self.assertEqual(jsonLogic({"%": [101, 2]}), 1)

    def test_merge(self):
        """
        Takes one or more arrays, and merges them into one array.
        If arguments aren't arrays, they get cast to arrays.
        """
        self.assertEqual(jsonLogic({"merge": [[1, 2], [3, 4]]}), [1, 2, 3, 4])
        self.assertEqual(jsonLogic({"merge": [1, 2, [3, 4]]}), [1, 2, 3, 4])
        # Merge can be especially useful when defining complex missing rules,
        # like which fields are required in a document. For example, the this
        # vehicle paperwork always requires the car's VIN, but only needs
        # the APR and term if you're financing.
        missing = {
            "missing": {
                "merge": ["vin", {"if": [{"var": "financing"}, ["apr", "term"], []]}]
            }
        }
        self.assertEqual(
            jsonLogic(missing, {"financing": True}), ["vin", "apr", "term"]
        )
        self.assertEqual(jsonLogic(missing, {"financing": False}), ["vin"])

    def test_in(self):
        """
        If the second argument is a string, tests that the first argument
        is a substring:
        """
        self.assertTrue(jsonLogic({"in": ["Spring", "Springfield"]}))

    def test_cat(self):
        """
        Concatenate all the supplied arguments. Note that this is not
        a join or implode operation, there is no "glue" string.
        """
        self.assertEqual(jsonLogic({"cat": ["I love", " pie"]}), "I love pie")
        self.assertEqual(
            jsonLogic(
                {"cat": ["I love ", {"var": "filling"}, " pie"]},
                {"filling": "apple", "temp": 110},
            ),
            "I love apple pie",
        )

    def test_log(self):
        """
        Logs the first value to console, then passes it through unmodified.
        This can be especially helpful when debugging a large rule.
        """
        self.assertEqual(jsonLogic({"log": "apple"}), "apple")
