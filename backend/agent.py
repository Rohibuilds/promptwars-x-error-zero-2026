import logging
from typing import Any, Dict
from .tools import search_knowledge, calculate, get_system_status

logger = logging.getLogger("ra_nexus.agent")


def run_agent(message: str) -> Dict[str, Any]:
    """Processes a user input message, determines intent, executes tools, and formulates response.
    
    Args:
        message: The natural language string provided by the user.
        
    Returns:
        Dict[str, Any]: Structured response containing intent type, execution status, tool used, and textual output.
    """
    message_lower = message.lower()

    # 1. System status intent
    status_keywords = [
        "system status",
        "are you online",
        "are you running",
        "what version",
        "your version",
        "what tools",
        "available tools"
    ]

    needs_status = any(
        keyword in message_lower
        for keyword in status_keywords
    )

    if needs_status:
        status = get_system_status()
        return {
            "type": "system_status",
            "status": "completed",
            "tool": "system_status",
            "response": (
                f"{status['name']} is {status['status']}\n"
                f"Version: {status['version']}\n"
                "Available tools: "
                + ", ".join(status["tools"])
            )
        }

    # 2. Calculator intent
    calculation_words = [
        "calculate",
        "what is",
        "solve",
        "plus",
        "minus",
        "times",
        "divided by"
    ]

    looks_like_calculation = any(
        word in message_lower
        for word in calculation_words
    )

    if looks_like_calculation:
        expression = extract_expression(message)
        result = calculate(expression)

        if result["success"]:
            return {
                "type": "calculator",
                "status": "completed",
                "tool": "calculator",
                "response": f"The answer is {result['result']}"
            }

        return {
            "type": "calculator",
            "status": "completed",
            "tool": "calculator",
            "response": "I couldn't calculate that expression."
        }

    # 3. Knowledge intent
    knowledge_keywords = [
        "where",
        "location",
        "lab",
        "laboratory",
        "library",
        "equipment",
        "campus",
        "timing",
        "timings",
        "located"
    ]

    needs_knowledge = any(
        keyword in message_lower
        for keyword in knowledge_keywords
    )

    if needs_knowledge:
        results = search_knowledge(message)
        if not results:
            return {
                "type": "knowledge",
                "status": "completed",
                "response": (
                    "I couldn't find relevant information "
                    "in the NEXUS knowledge base."
                )
            }

        best_result = results[0]
        return {
            "type": "knowledge",
            "status": "completed",
            "tool": "knowledge_search",
            "results": [best_result],
            "response": format_result(best_result)
        }

    # 4. General conversation fallback
    return {
        "type": "chat",
        "status": "completed",
        "response": (
            "I'm RA NEXUS. I can search my knowledge base "
            "and perform calculations."
        )
    }


def extract_expression(message: str) -> str:
    """Extracts and normalizes mathematical expressions from natural language.
    
    Args:
        message: Natural language sentence containing an arithmetic problem.
        
    Returns:
        str: Cleaned mathematical expression string with operator symbols.
    """
    expression = message.lower()

    replacements = {
        "calculate": "",
        "what is": "",
        "solve": "",
        "plus": "+",
        "minus": "-",
        "times": "*",
        "divided by": "/"
    }

    for word, symbol in replacements.items():
        expression = expression.replace(word, symbol)

    expression = expression.replace("?", "")
    return expression.strip()


def format_result(item: Dict[str, Any]) -> str:
    """Formats a knowledge record into a clean, human-readable response string.
    
    Args:
        item: Knowledge dictionary containing title, location, description, etc.
        
    Returns:
        str: Formatted markdown-like presentation string.
    """
    output = "Here's what I found:\n\n"
    output += f"{item.get('title', 'Information')}\n"

    if "location" in item:
        output += f"Location: {item['location']}\n"

    if "description" in item:
        output += f"{item['description']}\n"

    if "equipment" in item and item["equipment"]:
        output += "Equipment: " + ", ".join(item["equipment"]) + "\n"

    if "timings" in item:
        output += f"Timings: {item['timings']}\n"

    return output
