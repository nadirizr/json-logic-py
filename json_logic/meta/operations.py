from .base import Operation, register


@register("var")
class Var(Operation):
    _check_registered = False

    def __repr__(self):
        return f"${self.arguments[0]}"


@register("if")
class If(Operation):
    def __repr__(self):
        if (num_args := len(self.arguments)) <= 2:  # simple if arg0 then arg1 else arg2
            return super().__repr__()

        bits = ["Conditional"]
        # loop over groups of two which map to 'if x1 then x2'
        for i in range(0, num_args - 1, 2):
            condition, outcome = self.arguments[i : i + 2]
            condition_tree = repr(condition).splitlines()
            outcome_tree = repr(outcome).splitlines()

            bits += [
                "  If" if i == 0 else "  Elif",
                f"  ├─ {condition_tree[0]}",
                *[f"  │  {line}" for line in condition_tree[1:]],
                "  └─ Then",
                f"       └─ {outcome_tree[0]}",
                *[f"          {line}" for line in outcome_tree[1:]],
            ]

        if num_args % 2 == 1:
            else_tree = repr(self.arguments[-1]).splitlines()
            bits += [
                "  Else",
                f"  └─ {else_tree[0]}",
                *[f"     {line}" for line in else_tree[1:]],
            ]

        return "\n".join(bits)


@register("missing")
class Missing(Operation):
    _check_registered = False


@register("missing_some")
class MissingSome(Operation):
    _check_registered = False
