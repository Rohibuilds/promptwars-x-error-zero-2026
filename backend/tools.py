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

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg
}


def _calculate_node(node):

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value

        raise ValueError("Invalid number")

    if isinstance(node, ast.BinOp):
        operation = _ALLOWED_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Operator not allowed")

        left = _calculate_node(node.left)
        right = _calculate_node(node.right)

        return operation(left, right)

    if isinstance(node, ast.UnaryOp):
        operation = _ALLOWED_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Operator not allowed")

        return operation(_calculate_node(node.operand))

    raise ValueError("Invalid expression")


def calculate(expression):

    try:
        tree = ast.parse(
            expression,
            mode="eval"
        )

        result = _calculate_node(tree.body)

        return {
            "success": True,
            "result": result
        }

    except Exception:

        return {
            "success": False,
            "result": None
        }


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
