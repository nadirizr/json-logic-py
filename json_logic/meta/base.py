from dataclasses import dataclass, field
from typing import Union

from .. import operations
from ..typing import JSON, Primitive

OperationArgument = Union[Primitive, "Operation"]

NormalizedExpression = dict[str, list[JSON]]

OPERATION_MAP = {}


@dataclass(repr=False)
class Operation:
    operator: str
    """
    The operator of the operation.

    This should be a supported operation in :attr:`json_logic.operations`.
    """
    arguments: list[OperationArgument] = field(default_factory=list)
    """
    List of arguments for the operation.

    Note that an argument can itself be an operation, or it may be a literal expression
    (taking the form of a JSON primitive).

    Evaluation happens depth-first in case an argument is an operation itself.
    """
    _check_registered: bool = field(init=False, default=True)

    def __post_init__(self):
        if self._check_registered and self.operator not in operations:
            raise ValueError(
                f"Operator '{self.operator}' is unknown (unregistered in "
                "'json_logic.operations')."
            )

    def __repr__(self):
        bits = [self.op_repr]

        last_index = len(self.arguments) - 1
        for index, child in enumerate(self.arguments):
            first_prefix = "  ├─" if index != last_index else "  └─"
            separator = "  │ " if index != last_index else "    "
            child_tree = repr(child).splitlines()
            child_bits = [f"{first_prefix} {child_tree[0]}"] + [
                f"{separator} {line}" for line in child_tree[1:]
            ]
            bits.append("\n".join(child_bits))
        return "\n".join(bits)

    @property
    def op_repr(self) -> str:
        clsname = self.__class__.__qualname__
        return f"{clsname}({self.operator})"

    @classmethod
    def for_operator(cls, operator: str, *args, **kwargs):
        operator_cls = OPERATION_MAP.get(operator, cls)
        return operator_cls(operator, *args, **kwargs)


def register(operation: str):
    def decorator(cls: type[Operation]):
        OPERATION_MAP[operation] = cls
        return cls

    return decorator


def unregister(operation: str):
    if operation not in OPERATION_MAP:
        return

    del OPERATION_MAP[operation]
