import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .tools import search_knowledge, calculate, get_system_status

logger = logging.getLogger("ra_nexus.agent")
TIMETABLE_FILE = Path(__file__).resolve().parent.parent / "data" / "college_timetable.json"

SUBJECT_NAMES = {
    "MAT": "Mathematics I",
    "MES": "Mechanical Engineering Science",
    "RES": "Renewable Energy Sources",
    "PSC": "Problem Solving Using C",
    "BEC": "Basics of Electronics Engineering",
    "ENVS": "Environmental Science and Engineering",
    "ENG": "Communicative English",
    "ICN": "Indian Constitution",
    "KAN": "Kannada Samskruthi / Kali Kannada",
    "MATL": "Mathematics Lab",
    "PSCL": "Problem Solving Using C Lab",
    "BECL": "Basics of Electronics Engineering Lab",
    "CAM": "Class Advisor Meeting",
}


def load_timetable() -> Dict[str, Any]:
    """Load the user-provided timetable as structured, factual source data."""
    try:
        with TIMETABLE_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Timetable unavailable: %s", exc)
        return {}


def timetable_answer(message: str) -> Optional[str]:
    """Answer timetable questions only from documented timetable records."""
    query = message.lower().strip()
    data = load_timetable()
    if not data:
        return None

    # Day/room queries must be handled before the generic calculator ("what is") intent.
    day_match = re.search(r"\bday\s*([1-5])\b", query)
    day = "Day " + day_match.group(1) if day_match else None
    room_match = re.search(r"\b(a\s*\d{3,4}(?:\s*/\s*a\s*\d{3,4})?)\b", query, re.I)
    room = re.sub(r"\s+", "", room_match.group(1).upper()) if room_match else None

    # Normalize subject code / name mentions.
    aliases = {
        "english": "ENG", "communicative english": "ENG",
        "mathematics lab": "MATL", "maths lab": "MATL",
        "math lab": "MATL", "mathematics": "MAT", "maths": "MAT",
        "mechanical engineering science": "MES",
        "renewable energy sources": "RES", "problem solving using c lab": "PSCL",
        "c programming lab": "PSCL", "problem solving using c": "PSC",
        "electronics engineering lab": "BECL", "electronics lab": "BECL",
        "basics of electronics engineering": "BEC",
        "environmental science": "ENVS", "indian constitution": "ICN",
        "kannada": "KAN", "class advisor meeting": "CAM",
    }
    subject = None
    # Long phrases first, to avoid matching "Problem Solving Using C" before its lab.
    for alias in sorted(aliases, key=len, reverse=True):
        if alias in query:
            subject = aliases[alias]
            break
    if not subject:
        for code in sorted(SUBJECT_NAMES, key=len, reverse=True):
            if re.search(r"\b" + re.escape(code.lower()) + r"\b", query):
                subject = code
                break

    asks_timetable = any(word in query for word in (
        "timetable", "time table", "class", "classes", "room", "where",
        "faculty", "teacher", "subject", "period", "day", "lab",
        "which room", "held", "schedule", "when"
    ))
    if not asks_timetable:
        return None

    if "period" in query or "what time" in query or "at " in query or "next class" in query:
        # Source includes period times, but no exact subject-to-period assignments.
        if subject or day or room:
            return (
                "The timetable source contains the period timings, but the exact "
                "subject-to-period sequence was not included in the provided records. "
                "I can't verify the specific class period without the full period-by-period timetable."
            )

    courses = data.get("courses", [])
    if subject:
        course = next((c for c in courses if c.get("short_code") == subject), None)
        subject_name = SUBJECT_NAMES.get(subject, subject)
        if any(word in query for word in ("faculty", "teacher", "who teaches", "professor")):
            if course and course.get("faculty"):
                return f"{subject_name} ({subject}) faculty: {course['faculty']}."
            return f"The faculty allocation for {subject_name} ({subject}) is not provided in the timetable records."
        if any(word in query for word in ("course code", "subject code", "code for", "code of")):
            if course and course.get("code"):
                return f"{subject_name} ({subject}) course code: {course['code']}."
        if room or day or any(word in query for word in ("where", "which room", "room", "held", "location")):
            entries = data.get("room_day_entries", [])
            matches = [e for e in entries
                       if subject in e.get("subjects", [])
                       and (not day or e.get("day") == day)
                       and (not room or room in re.sub(r"\s+", "", e.get("room", "")).upper())]
            if matches:
                return "\n".join(
                    f"{subject_name} ({subject}) — {entry['day']}, Room {entry['room']}."
                    for entry in matches
                )
            if day:
                return f"The provided timetable records do not establish a room for {subject_name} ({subject}) on {day}."
            return f"The provided timetable records do not establish a room for {subject_name} ({subject}) for that query."
        if course:
            return f"{subject_name} ({subject}) — Faculty: {course.get('faculty', 'Not provided')}. Course code: {course.get('code', 'Not provided')}."
        return f"The timetable identifies {subject_name} ({subject}), but no additional detail matching that question is available."

    entries = data.get("room_day_entries", [])
    if room:
        matches = [e for e in entries
                   if room in re.sub(r"\s+", "", e.get("room", "")).upper()
                   and (not day or e.get("day") == day)]
        if matches:
            return "\n".join(
                f"{entry['day']} — Room {entry['room']}: " +
                ", ".join(f"{code} ({SUBJECT_NAMES.get(code, code)})" for code in entry.get("subjects", [])) + "."
                for entry in matches
            )
        if day:
            return f"The provided timetable records do not list any classes in {room} on {day}."
        return f"I couldn't find a matching room entry for {room} in the provided timetable."

    if day:
        matches = [e for e in entries if e.get("day") == day]
        if matches:
            return "\n".join(
                f"Room {entry['room']}: " +
                ", ".join(f"{code} ({SUBJECT_NAMES.get(code, code)})" for code in entry.get("subjects", [])) + "."
                for entry in matches
            )
        return f"The timetable does not contain a verified entry for {day}."

    if any(word in query for word in ("timetable", "time table", "schedule")):
        return (
            "I have the timetable metadata, course/faculty list, period timings, and room-to-day subject mappings. "
            "The weekday names and exact subject-to-period assignments are not present in the text provided, "
            "so I won't guess them. Ask me about a subject, faculty member, room, or Day 1–Day 5."
        )
    return None


def run_agent(message: str) -> Dict[str, Any]:
    """Route questions to verified timetable records, campus knowledge, or safe tools."""
    message_lower = message.lower()

    # Prioritize exact college records before broad phrases such as "what is".
    college_answer = timetable_answer(message)
    if college_answer:
        return {
            "type": "college_timetable",
            "status": "completed",
            "tool": "timetable_search",
            "response": college_answer,
            "source": "User-provided Sapthagiri NPS University ECE timetable"
        }

    status_keywords = [
        "system status", "are you online", "are you running",
        "what version", "your version", "what tools", "available tools"
    ]
    if any(keyword in message_lower for keyword in status_keywords):
        status = get_system_status()
        return {
            "type": "system_status",
            "status": "completed",
            "tool": "system_status",
            "response": (
                f"{status['name']} is {status['status']}\n"
                f"Version: {status['version']}\n"
                "Available tools: " + ", ".join(status["tools"])
            )
        }

    calculation_words = ["calculate", "what is", "solve", "plus", "minus", "times", "divided by"]
    if any(word in message_lower for word in calculation_words):
        expression = extract_expression(message)
        result = calculate(expression)
        if result["success"]:
            return {"type": "calculator", "status": "completed", "tool": "calculator",
                    "response": f"The answer is {result['result']}"}
        return {"type": "calculator", "status": "completed", "tool": "calculator",
                "response": "I couldn't calculate that expression."}

    knowledge_keywords = ["where", "location", "lab", "laboratory", "library", "equipment",
                          "campus", "timing", "timings", "located"]
    if any(keyword in message_lower for keyword in knowledge_keywords):
        results = search_knowledge(message)
        if not results:
            return {"type": "knowledge", "status": "completed",
                    "response": "I couldn't find relevant information in the NEXUS knowledge base."}
        best_result = results[0]
        return {"type": "knowledge", "status": "completed", "tool": "knowledge_search",
                "results": [best_result], "response": format_result(best_result)}

    return {"type": "chat", "status": "completed",
            "response": "I'm RA NEXUS. I can answer verified college timetable questions, search my campus knowledge base, and perform calculations."}


def extract_expression(message: str) -> str:
    expression = message.lower()
    replacements = {
        "calculate": "", "what is": "", "solve": "",
        "plus": "+", "minus": "-", "times": "*", "divided by": "/"
    }
    for word, symbol in replacements.items():
        expression = expression.replace(word, symbol)
    return expression.replace("?", "").strip()


def format_result(item: Dict[str, Any]) -> str:
    output = "Here's what I found:\n\n" + f"{item.get('title', 'Information')}\n"
    if "location" in item:
        output += f"Location: {item['location']}\n"
    if "description" in item:
        output += f"{item['description']}\n"
    if item.get("equipment"):
        output += "Equipment: " + ", ".join(item["equipment"]) + "\n"
    if "timings" in item:
        output += f"Timings: {item['timings']}\n"
    return output
