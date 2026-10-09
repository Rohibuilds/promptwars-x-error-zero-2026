"""RA NEXUS Tool definitions: knowledge retrieval, safe calculation, and system diagnostics."""

import ast
from functools import lru_cache
import json
import logging
import math
import operator
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("ra_nexus.tools")

DATA_FILE = Path(__file__).parent.parent / "data" / "knowledge.json"


@lru_cache(maxsize=1)
def load_knowledge_base() -> List[Dict[str, Any]]:
    """Loads and caches the campus knowledge base into memory.
    
    Returns:
        List[Dict[str, Any]]: List of campus facilities and equipment entries.
    """
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Knowledge base data file unreadable: %s (%s)", DATA_FILE, exc)
        return []



def search_knowledge(query: str) -> List[Dict[str, Any]]:
    """Searches the in-memory campus knowledge base for matching facilities.
    
    Args:
        query: Natural language query string.
        
    Returns:
        List[Dict[str, Any]]: Top matching knowledge entries ranked by relevance.
    """
    knowledge = load_knowledge_base()
    if not knowledge or not query or not query.strip():
        return []

    query_words = [w.lower() for w in query.split() if len(w) > 1]
    if not query_words:
        query_words = query.lower().split()

    results = []
    for item in knowledge:
        searchable_text = (
            f"{item.get('title', '')} "
            f"{item.get('location', '')} "
            f"{item.get('description', '')} "
            f"{' '.join(item.get('equipment', []))} "
            f"{item.get('timings', '')}"
        ).lower()

        score = sum(1 for word in query_words if word in searchable_text)
        if score > 0:
            results.append((score, item))

    results.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in results[:5]]


# Safe calculator components

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


def _calculate_node(node: ast.AST) -> float:
    """Recursively evaluates an AST node with strict safety limits.
    
    Args:
        node: AST expression node.
        
    Returns:
        float: Evaluated numerical result.
        
    Raises:
        ValueError: If an disallowed operation, invalid constant, or limit violation occurs.
    """
    if isinstance(node, ast.Constant):
        value = node.value
        if type(value) not in (int, float):
            raise ValueError("Only numeric constants are allowed")
        if abs(value) > _MAX_ABS_NUMBER:
            raise ValueError("Number is too large")
        return float(value)

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


def calculate(expression: str) -> Dict[str, Any]:
    """Safely evaluates a basic mathematical expression string.
    
    Args:
        expression: Mathematical string expression (e.g. '25 + 17').
        
    Returns:
        Dict[str, Any]: Dictionary containing success status and result.
    """
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

    except (ValueError, TypeError, SyntaxError, ArithmeticError, OverflowError) as exc:
        logger.debug("Safe calculator rejected expression '%s': %s", expression, exc)
        return {"success": False, "result": None}



def get_system_status() -> Dict[str, Any]:
    """Returns current system health status, version, and loaded capabilities.
    
    Returns:
        Dict[str, Any]: Status metadata dictionary.
    """
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
