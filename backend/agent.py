from .tools import search_knowledge


def run_agent(message):
    message_lower = message.lower()

    knowledge_keywords = [
        "where",
        "location",
        "lab",
        "library",
        "equipment",
        "campus",
        "timing",
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
                "response": "I couldn't find relevant information in the NEXUS knowledge base."
            }

        return {
            "type": "knowledge",
            "status": "completed",
            "results": results,
            "response": format_results(results)
        }

    return {
        "type": "chat",
        "status": "completed",
        "response": "I'm RA NEXUS. I can search my knowledge base and help complete tasks."
    }


def format_results(results):
    output = "Here's what I found:\n\n"

    for item in results:
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

        output += "\n"

    return output