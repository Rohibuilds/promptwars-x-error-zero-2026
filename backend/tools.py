import ast
import json
import operator
from pathlib import Path


DATA_FILE = Path(__file__).parent.parent / "data" / "knowledge.json"


def search_knowledge(query):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            knowledge = json.load(file)
    except FileNotFoundError:
        return []

    query_words = query.lower().split()

    results = []

    for item in knowledge:
        text = json.dumps(item).lower()

        score = sum(
            1
            for word in query_words
            if word in text
        )

        if score > 0:
            results.append((score, item))

    results.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [item for _, item in results[:5]]


# Safe calculator

import math

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}

_MAX_EXPRESSION_LENGTH = 100
_MAX_AST_NODES = 40
_MAX_ABS_NUMBER = 1e100


def _calculate_node(node):
    if isinstance(node, ast.Constant):
        value = node.value

        if type(value) not in (int, float):
            raise ValueError("Only numeric constants are allowed")

        if abs(value) > _MAX_ABS_NUMBER:
            raise ValueError("Number is too large")

        return value

    if isinstance(node, ast.BinOp):
        operation = _ALLOWED_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Operator not allowed")

        left = _calculate_node(node.left)
        right = _calculate_node(node.right)

        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponent is too large")

        if isinstance(node.op, (ast.Mult, ast.Pow)) and (
            abs(left) > 1e10 or abs(right) > 1e10
        ):
            raise ValueError("Calculation is too large")

        result = operation(left, right)

        if not math.isfinite(result) or abs(result) > _MAX_ABS_NUMBER:
            raise ValueError("Result is outside the allowed range")

        return result

    if isinstance(node, ast.UnaryOp):
        operation = _ALLOWED_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Operator not allowed")

        result = operation(_calculate_node(node.operand))

        if not math.isfinite(result) or abs(result) > _MAX_ABS_NUMBER:
            raise ValueError("Result is outside the allowed range")

        return result

    raise ValueError("Invalid expression")


def calculate(expression):
    try:
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError("Expression is empty")

        if len(expression) > _MAX_EXPRESSION_LENGTH:
            raise ValueError("Expression is too long")

        tree = ast.parse(expression, mode="eval")

        if sum(1 for _ in ast.walk(tree)) > _MAX_AST_NODES:
            raise ValueError("Expression is too complex")

        result = _calculate_node(tree.body)

        return {"success": True, "result": result}

    except (ValueError, TypeError, SyntaxError, ArithmeticError, OverflowError):
        return {"success": False, "result": None}


def get_system_status():
    return {
        "name": "RA NEXUS",
        "version": "0.1.0",
        "status": "online",
        "tools": [
            "knowledge_search",
            "calculator",
            "system_status"
        ]
    }
