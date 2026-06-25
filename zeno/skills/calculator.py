"""
Zeno Calculator Skill
Safely evaluates simple arithmetic — no eval() of arbitrary code.
"""

import ast
import operator
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("not a number")
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def safe_calculate(expression: str) -> float:
    normalized = expression.replace("x", "*").replace("X", "*")
    tree = ast.parse(normalized, mode="eval")
    return _safe_eval(tree.body)


class CalculatorSkill(BaseSkill):
    intents = ["calculate"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        if not entities.expression:
            return self.say("What would you like me to calculate?")

        try:
            result = safe_calculate(entities.expression)
            if result == int(result):
                result = int(result)
            return self.say(f"{entities.expression.strip()} = {result}")
        except (ValueError, ZeroDivisionError, SyntaxError):
            return self.say("I couldn't work that out — try a simpler expression.")
