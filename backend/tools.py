import json
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