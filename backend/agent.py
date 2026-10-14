"""Autonomous Agent Router for RA NEXUS at Sapthagiri NPS University.

Routes user queries to system diagnostics, safe arithmetic calculation,
campus knowledge search, and deterministic timetable engine with section isolation.
"""

import logging
import re
from typing import Any, Dict, Optional
from .tools import search_knowledge, calculate, get_system_status, query_timetable

logger = logging.getLogger("ra_nexus.agent")


def is_math_query(message_lower: str) -> bool:
    """Accurately determines if a message is intended for the arithmetic calculator.

    Prevents natural campus queries like 'What is the library timing?' from being
    misrouted to the arithmetic engine.
    """
    campus_words = [
        "library", "lab", "laboratory", "timing", "timings", "location", "located",
        "classroom", "equipment", "timetable", "schedule", "class", "classes",
        "period", "periods", "faculty", "professor", "teacher", "section", "subject"
    ]
    if any(w in message_lower for w in campus_words):
        return False

    # Explicit mathematical commands
    explicit_commands = ["calculate", "solve", "evaluate"]
    if any(cmd in message_lower for cmd in explicit_commands):
        return True

    # Numeric expressions containing numbers and math operator keywords or symbols
    has_digits = bool(re.search(r"\d", message_lower))
    arithmetic_operators = ["+", "-", "*", "/", "%", "**", "plus", "minus", "times", "divided by"]
    has_operator = any(op in message_lower for op in arithmetic_operators)

    return has_digits and has_operator


def is_timetable_query(message_lower: str) -> bool:
    """Determines if a query is asking for class schedules, timetables, or faculty assignments."""
    timetable_keywords = [
        "timetable", "schedule", "period", "periods", "next class", "current class",
        "my class", "next lecture", "lecture", "lectures", "section", "1ece02",
        "subject", "subjects", "faculty", "professor", "teacher", "tomorrow"
    ]
    return any(kw in message_lower for kw in timetable_keywords)


def is_knowledge_query(message_lower: str) -> bool:
    """Determines if a query is asking about campus facilities, laboratories, or library info."""
    knowledge_keywords = [
        "where", "location", "located", "lab", "laboratory", "library",
        "equipment", "campus", "timing", "timings", "facilities"
    ]
    return any(kw in message_lower for kw in knowledge_keywords)


def run_agent(
    message: str,
    student_context: Optional[Dict[str, Any]] = None,
    client_time: Optional[str] = None
) -> Dict[str, Any]:
    """Processes a user input message, determines intent, executes tools, and formulates response.
    
    Args:
        message: Natural language query provided by user.
        student_context: Optional dictionary with student metadata (branch, section, etc.).
        client_time: Optional ISO timestamp from client for temporal queries.
        
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

    if any(keyword in message_lower for keyword in status_keywords):
        status = get_system_status()
        return {
            "type": "system_status",
            "status": "completed",
            "tool": "system_status",
            "response": (
                f"{status['name']} for {status.get('institution', 'Campus')} is {status['status']}\n"
                f"Version: {status['version']}\n"
                "Available tools: " + ", ".join(status["tools"])
            )
        }

    # 2. Safe calculator intent (with strict mathematical disambiguation)
    if is_math_query(message_lower):
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

    # 3. Timetable & Schedule intent (evaluated before general knowledge for class queries)
    if is_timetable_query(message_lower):
        return query_timetable(message, student_context, client_time=client_time)

    # 4. Campus knowledge intent (facilities, laboratories, library)
    if is_knowledge_query(message_lower):
        results = search_knowledge(message)
        if not results:
            return {
                "type": "knowledge",
                "status": "completed",
                "response": (
                    "I couldn't find relevant information in the university knowledge base."
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

    # 5. General conversation fallback
    return {
        "type": "chat",
        "status": "completed",
        "response": (
            "I'm RA NEXUS, digital assistant for Sapthagiri NPS University. "
            "I can answer questions about campus facilities, timetables, and perform calculations. "
            "Please specify your branch and section (e.g., ECE section 1ECE02) for timetable schedules."
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
        "what's": "",
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

    if "verification_status" in item:
        output += f"Status: {item['verification_status'].capitalize()}\n"

    return output
