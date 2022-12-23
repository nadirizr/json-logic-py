"""
Meta module for json-logic.

This module implements the tooling to convert between JSON and python datastructures
for json-logic expressions. The Python datastructures provider richer introspection
potential to (statically) analyze JSON logic expressions.
"""
from .base import Operation, register, unregister
from .expressions import JSONLogicExpression

__all__ = ["Operation", "JSONLogicExpression", "register", "unregister"]
