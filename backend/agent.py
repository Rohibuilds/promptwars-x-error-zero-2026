from .tools import search_knowledge, calculate, get_system_status


def run_agent(message):
    message_lower = message.lower()

    # System status intent

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
                f"{status['name']} is {status['status']}\\n"
                f"Version: {status['version']}\\n"
                "Available tools: "
                + ", ".join(status["tools"])
            )
        }


    # Calculator intent

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


    # Knowledge intent

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


    # General conversation

    return {
        "type": "chat",
        "status": "completed",
        "response": (
            "I'm RA NEXUS. I can search my knowledge base "
            "and perform calculations."
        )
    }


def extract_expression(message):

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
        expression = expression.replace(
            word,
            symbol
        )

    expression = expression.replace("?", "")


    return expression.strip()


def format_result(item):

    output = "Here's what I found:\n\n"

    output += f"{item.get('title', 'Information')}\n"

    if "location" in item:
        output += f"Location: {item['location']}\n"

    if "description" in item:
        output += f"{item['description']}\n"

    if "equipment" in item:

        output += (
            "Equipment: "
            + ", ".join(item["equipment"])
            + "\n"
        )

    if "timings" in item:
        output += f"Timings: {item['timings']}\n"

    return output
