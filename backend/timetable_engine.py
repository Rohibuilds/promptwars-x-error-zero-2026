"""Deterministic Timetable Engine for Sapthagiri NPS University.

Handles subject, faculty, classroom, and schedule lookups with strict section isolation,
preventing cross-section leaks, rejecting unverified assumptions, validating student context,
and enforcing next-class safety.
"""

from datetime import datetime
from functools import lru_cache
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ra_nexus.timetable")

TIMETABLE_FILE = Path(__file__).parent.parent / "data" / "timetable.json"

VALID_WEEKDAYS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
}

ORDERED_WEEKDAYS = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


def validate_timetable_entry(entry: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validates that a timetable entry conforms to the schema.

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_reason)
    """
    if not isinstance(entry, dict):
        return False, "Entry must be a dictionary"

    section = entry.get("section")
    if not section or not isinstance(section, str) or not section.strip():
        return False, "Missing or invalid 'section' string"

    branch = entry.get("branch")
    if not branch or not isinstance(branch, str) or not branch.strip():
        return False, "Missing or invalid 'branch' string"

    weekday = entry.get("weekday")
    if weekday is not None and str(weekday).lower() not in VALID_WEEKDAYS:
        return False, f"Invalid weekday '{weekday}'"

    period = entry.get("period")
    if period is not None and not isinstance(period, (int, str)):
        return False, f"Invalid period format '{period}'"

    return True, None


@lru_cache(maxsize=1)
def load_timetable_data(filepath: Optional[str] = None) -> Dict[str, Any]:
    """Loads and caches university timetable data.

    Args:
        filepath: Optional path to an alternate JSON file (used for testing).

    Returns:
        Dict[str, Any]: Parsed timetable database structure.
    """
    target = Path(filepath) if filepath else TIMETABLE_FILE
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                logger.error("Timetable data root must be a dictionary, got %s", type(data))
                return {"institution": "Sapthagiri NPS University", "sections_catalog": [], "entries": []}
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read timetable file %s: %s", target, exc)
        return {
            "institution": "Sapthagiri NPS University",
            "sections_catalog": [],
            "entries": [],
            "error": str(exc)
        }


def clear_timetable_cache() -> None:
    """Clears the cached timetable data."""
    load_timetable_data.cache_clear()


class TimetableEngine:
    """Engine for querying Sapthagiri NPS University timetables deterministically."""

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file

    def get_raw_data(self) -> Dict[str, Any]:
        """Returns the loaded timetable dataset."""
        return load_timetable_data(self.data_file)

    def get_sections_catalog(self) -> List[Dict[str, Any]]:
        """Returns the catalog of registered university sections."""
        data = self.get_raw_data()
        return data.get("sections_catalog", [])

    def get_registered_section_ids(self) -> List[str]:
        """Returns a list of registered section IDs in uppercase."""
        return [
            s.get("section_id", "").upper()
            for s in self.get_sections_catalog()
            if s.get("section_id")
        ]

    def get_section_info(self, section_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves catalog metadata for a specific section ID."""
        clean = section_id.strip().upper()
        for s in self.get_sections_catalog():
            if s.get("section_id", "").upper() == clean:
                return s
        return None

    def get_valid_entries(self) -> List[Dict[str, Any]]:
        """Returns all validated schedule entries from the dataset."""
        data = self.get_raw_data()
        raw_entries = data.get("entries", [])
        valid = []
        for entry in raw_entries:
            ok, reason = validate_timetable_entry(entry)
            if ok:
                valid.append(entry)
            else:
                logger.warning("Skipping invalid timetable entry: %s (Reason: %s)", entry, reason)
        return valid

    def validate_student_context(
        self,
        student_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validates student context parameters against the university catalog.

        Enforces:
        - Section must be registered if provided.
        - Branch must match section's registered branch.
        - Batch must be a valid string format.

        Returns:
            Tuple[bool, Optional[str], Optional[Dict[str, Any]]]: (is_valid, error_message, cleaned_context)
        """
        if not student_context:
            return True, None, None

        if not isinstance(student_context, dict):
            return False, "student_context must be a valid dictionary", None

        cleaned: Dict[str, Any] = {}

        # Validate section
        raw_sec = student_context.get("section")
        if raw_sec:
            sec_str = str(raw_sec).strip().upper()
            registered = self.get_registered_section_ids()
            if sec_str not in registered:
                available_str = ", ".join(registered) if registered else "None"
                return (
                    False,
                    f"Section '{sec_str}' is not registered in the university catalog. "
                    f"Currently registered sections: {available_str}.",
                    None
                )
            cleaned["section"] = sec_str

            # Validate branch alignment with section
            sec_info = self.get_section_info(sec_str)
            raw_branch = student_context.get("branch")
            if raw_branch and sec_info:
                branch_str = str(raw_branch).strip().upper()
                sec_branch = sec_info.get("branch", "").upper()
                if sec_branch and branch_str != sec_branch:
                    return (
                        False,
                        f"Branch '{branch_str}' does not match section '{sec_str}' "
                        f"(which belongs to branch '{sec_branch}').",
                        None
                    )
                cleaned["branch"] = branch_str
            elif sec_info and sec_info.get("branch"):
                cleaned["branch"] = sec_info["branch"].upper()

        elif student_context.get("branch"):
            cleaned["branch"] = str(student_context["branch"]).strip().upper()

        # Validate academic year
        raw_year = student_context.get("academic_year")
        if raw_year is not None:
            cleaned["academic_year"] = raw_year

        # Validate semester
        raw_sem = student_context.get("semester")
        if raw_sem is not None:
            try:
                sem_int = int(raw_sem)
                if not (1 <= sem_int <= 8):
                    return False, f"Invalid semester '{raw_sem}'. Semester must be between 1 and 8.", None
                cleaned["semester"] = sem_int
            except (ValueError, TypeError):
                cleaned["semester"] = str(raw_sem).strip()

        # Validate batch
        raw_batch = student_context.get("batch")
        if raw_batch is not None:
            cleaned["batch"] = str(raw_batch).strip()

        return True, None, cleaned

    def extract_section_from_text(self, text: str) -> Optional[str]:
        """Extracts section identifiers such as '1ECE02' from user query text."""
        registered = self.get_registered_section_ids()
        upper_text = text.upper()
        for sec in registered:
            pattern = rf"\b{re.escape(sec)}\b"
            if re.search(pattern, upper_text):
                return sec

        match = re.search(r"\b([1-8][A-Z]{2,4}[0-9]{2})\b", upper_text)
        if match:
            return match.group(1)

        sec_named = re.search(r"\b(?:section|sec)\s+([A-Z0-9_-]+)\b", upper_text, re.IGNORECASE)
        if sec_named:
            return sec_named.group(1).upper()

        return None

    def extract_branch_from_text(self, text: str) -> Optional[str]:
        """Extracts engineering branch from text (e.g., ECE, CSE, Mech)."""
        lower = text.lower()
        branches = {
            "ece": "ECE",
            "electronics": "ECE",
            "cse": "CSE",
            "computer science": "CSE",
            "mech": "MECH",
            "mechanical": "MECH",
            "civil": "CIVIL",
            "eee": "EEE",
            "electrical": "EEE",
            "aiml": "AIML",
            "ai & ml": "AIML",
            "is": "ISE",
            "ise": "ISE"
        }
        for kw, code in branches.items():
            if re.search(rf"\b{re.escape(kw)}\b", lower):
                return code
        return None

    def resolve_student_section(
        self,
        query: str,
        student_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolves section and branch from query text and optional student context."""
        section = None
        branch = None

        if student_context and isinstance(student_context, dict):
            if student_context.get("section"):
                section = str(student_context["section"]).strip().upper()
            if student_context.get("branch"):
                branch = str(student_context["branch"]).strip().upper()

        extracted_sec = self.extract_section_from_text(query)
        if extracted_sec:
            section = extracted_sec

        extracted_branch = self.extract_branch_from_text(query)
        if extracted_branch:
            branch = extracted_branch

        return section, branch

    def handle_unspecified_section(self) -> Dict[str, Any]:
        """Standardized response when a query lacks required section context."""
        registered = self.get_registered_section_ids()
        available_str = ", ".join(registered) if registered else "None currently registered"
        return {
            "type": "timetable",
            "status": "context_required",
            "tool": "timetable_engine",
            "section": None,
            "response": (
                "To look up university timetable details, please specify your branch and section "
                f"(e.g., ECE section 1ECE02).\n\n"
                f"Currently registered sections: {available_str}.\n"
                "Each section follows a distinct schedule, and schedules cannot be shared across sections."
            )
        }

    def handle_unregistered_section(self, section: str) -> Dict[str, Any]:
        """Standardized response when a requested section is not in the official catalog."""
        registered = self.get_registered_section_ids()
        available_str = ", ".join(registered) if registered else "None"
        return {
            "type": "timetable",
            "status": "section_not_found",
            "tool": "timetable_engine",
            "section": section,
            "response": (
                f"Section '{section}' is not currently available in the Sapthagiri NPS University timetable database.\n\n"
                f"Currently verified section data is only available for: {available_str}.\n"
                "Official timetables for other sections and semesters will be published once verified by the university."
            )
        }

    def handle_pending_schedule(self, section: str, info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Standardized response when a section is cataloged but detailed schedules are pending."""
        source_doc = (info.get("source_document") if info else None) or "Department Initial Submission (Provisional)"
        return {
            "type": "timetable",
            "status": "schedule_pending",
            "tool": "timetable_engine",
            "section": section,
            "source_document": source_doc,
            "response": (
                f"Section {section} is registered for {info.get('branch_name', 'Engineering') if info else 'ECE'}.\n\n"
                "However, official period timings, weekday schedule mappings, and classroom allocations "
                "have not yet been released by the university.\n"
                "Status: Detailed timetable pending official publication.\n"
                f"Source: {source_doc}."
            )
        }

    def get_sections(
        self,
        branch: Optional[str] = None,
        semester: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Returns registered sections filtered by branch and semester."""
        catalog = self.get_sections_catalog()
        filtered = []
        for s in catalog:
            if branch and s.get("branch", "").upper() != branch.strip().upper():
                continue
            if semester is not None and s.get("semester") is not None and s.get("semester") != semester:
                continue
            filtered.append(s)
        return filtered

    def get_subjects_for_section(
        self,
        section: str,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Returns distinct subject information for a section."""
        clean_sec = section.strip().upper()
        if clean_sec not in self.get_registered_section_ids():
            return {
                "status": "section_not_found",
                "section": clean_sec,
                "message": f"Section '{clean_sec}' is not registered in the university catalog."
            }

        sec_info = self.get_section_info(clean_sec)
        if branch and sec_info and sec_info.get("branch", "").upper() != branch.strip().upper():
            return {
                "status": "branch_mismatch",
                "section": clean_sec,
                "message": f"Branch mismatch: Section '{clean_sec}' belongs to branch '{sec_info.get('branch')}', not '{branch}'."
            }

        all_valid = self.get_valid_entries()
        sec_entries = [e for e in all_valid if e.get("section", "").strip().upper() == clean_sec]

        subjects_map = {}
        for e in sec_entries:
            code = e.get("subject_code")
            name = e.get("subject_name")
            if code or name:
                key = code or name
                if key not in subjects_map:
                    subjects_map[key] = {
                        "subject_code": code,
                        "subject_name": name,
                        "faculty_name": e.get("faculty_name"),
                        "classroom": e.get("classroom"),
                        "batch": e.get("batch", "All")
                    }

        if not subjects_map:
            return {
                "status": "schedule_pending",
                "section": clean_sec,
                "branch": sec_info.get("branch") if sec_info else None,
                "subjects": [],
                "message": f"Subject details for section {clean_sec} are pending official publication."
            }

        return {
            "status": "completed",
            "section": clean_sec,
            "branch": sec_info.get("branch") if sec_info else None,
            "count": len(subjects_map),
            "subjects": list(subjects_map.values())
        }

    def get_schedule_for_section(
        self,
        section: str,
        branch: Optional[str] = None,
        weekday: Optional[str] = None,
        period: Optional[int] = None,
        batch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Returns schedule entries for a section with optional weekday, period, and batch filters."""
        clean_sec = section.strip().upper()
        if clean_sec not in self.get_registered_section_ids():
            return {
                "status": "section_not_found",
                "section": clean_sec,
                "message": f"Section '{clean_sec}' is not registered in the university catalog."
            }

        sec_info = self.get_section_info(clean_sec)
        if branch and sec_info and sec_info.get("branch", "").upper() != branch.strip().upper():
            return {
                "status": "branch_mismatch",
                "section": clean_sec,
                "message": f"Branch mismatch: Section '{clean_sec}' belongs to branch '{sec_info.get('branch')}', not '{branch}'."
            }

        if weekday and str(weekday).lower() not in VALID_WEEKDAYS:
            return {
                "status": "invalid_weekday",
                "section": clean_sec,
                "message": f"Invalid weekday '{weekday}'. Must be one of Monday through Sunday."
            }

        all_valid = self.get_valid_entries()
        sec_entries = [e for e in all_valid if e.get("section", "").strip().upper() == clean_sec]

        actionable = [e for e in sec_entries if e.get("subject_name") or e.get("subject_code")]
        if not actionable:
            return {
                "status": "schedule_pending",
                "section": clean_sec,
                "entries": [],
                "message": f"Official schedule for section {clean_sec} is pending release by the university."
            }

        filtered = []
        for e in actionable:
            if weekday and e.get("weekday", "").lower() != str(weekday).lower():
                continue
            if period is not None and e.get("period") != period:
                continue
            if batch and e.get("batch") and e["batch"] != "All" and e["batch"].lower() != batch.strip().lower():
                continue
            filtered.append(e)

        return {
            "status": "completed",
            "section": clean_sec,
            "count": len(filtered),
            "entries": filtered
        }

    def get_current_and_next_class(
        self,
        section: str,
        client_time_str: Optional[str] = None,
        timezone_str: Optional[str] = None,
        batch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deterministically resolves the current and next scheduled class.

        Enforces strict safety:
        - If section data is incomplete (e.g. 1ECE02 missing period times), returns schedule_pending.
        - If reliable client_time is missing, returns time_required.
        - Never guesses or extrapolates.
        """
        clean_sec = section.strip().upper()
        if clean_sec not in self.get_registered_section_ids():
            return {
                "status": "section_not_found",
                "can_determine": False,
                "section": clean_sec,
                "message": f"Section '{clean_sec}' is not registered in the university database."
            }

        all_valid = self.get_valid_entries()
        sec_entries = [e for e in all_valid if e.get("section", "").strip().upper() == clean_sec]

        # Safety Check 1: Must have complete verified entries with weekday and times
        timed_entries = [
            e for e in sec_entries
            if e.get("weekday") and e.get("start_time") and e.get("end_time")
        ]

        if not timed_entries:
            return {
                "type": "timetable",
                "status": "schedule_pending",
                "can_determine": False,
                "section": clean_sec,
                "missing_information": [
                    "verified_period_timings",
                    "weekday_class_schedule"
                ],
                "response": (
                    f"Section {clean_sec} has not yet published verified period timings and weekday class schedules. "
                    "Current and next class cannot be inferred from partial data."
                )
            }

        # Safety Check 2: Must have a reliable, parseable client date/time
        if not client_time_str or not client_time_str.strip():
            return {
                "type": "timetable",
                "status": "time_required",
                "can_determine": False,
                "section": clean_sec,
                "missing_information": ["client_time"],
                "response": (
                    "A reliable current date and time (ISO timestamp) is required to determine "
                    f"your current or next class for section {clean_sec}."
                )
            }

        try:
            # Handle ISO timestamp strings
            clean_ts = client_time_str.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
        except Exception as exc:
            logger.warning("Could not parse client_time '%s': %s", client_time_str, exc)
            return {
                "type": "timetable",
                "status": "time_required",
                "can_determine": False,
                "section": clean_sec,
                "missing_information": ["valid_iso_client_time"],
                "response": f"Invalid client time format '{client_time_str}'. Expected ISO 8601 format."
            }

        # Filter by batch if specified
        active_entries = []
        for e in timed_entries:
            if batch and e.get("batch") and e["batch"] != "All":
                if e["batch"].lower() != batch.strip().lower():
                    continue
            active_entries.append(e)

        today_weekday = dt.strftime("%A").lower()
        now_time = dt.strftime("%H:%M")

        today_entries = [e for e in active_entries if e.get("weekday", "").lower() == today_weekday]
        today_entries.sort(key=lambda x: str(x.get("start_time", "")))

        current_class = None
        next_class = None

        for entry in today_entries:
            st = str(entry.get("start_time", ""))
            et = str(entry.get("end_time", ""))
            if st <= now_time <= et:
                current_class = entry
            elif st > now_time and next_class is None:
                next_class = entry

        # If no next class today, look for upcoming days in sequence
        if next_class is None:
            today_idx = ORDERED_WEEKDAYS.index(today_weekday) if today_weekday in ORDERED_WEEKDAYS else 0
            for offset in range(1, 7):
                next_day_idx = (today_idx + offset) % 7
                next_day = ORDERED_WEEKDAYS[next_day_idx]
                day_candidates = [e for e in active_entries if e.get("weekday", "").lower() == next_day]
                if day_candidates:
                    day_candidates.sort(key=lambda x: str(x.get("start_time", "")))
                    next_class = day_candidates[0]
                    break

        lines = [f"Class Schedule Status for Section {clean_sec} ({dt.strftime('%A, %d %B %Y %H:%M')}):"]
        if current_class:
            sub = current_class.get("subject_name") or current_class.get("subject_code")
            room = current_class.get("classroom") or "Room Pending"
            lines.append(f"• CURRENT CLASS: {sub} in {room} ({current_class.get('start_time')} - {current_class.get('end_time')})")
        else:
            lines.append("• CURRENT CLASS: No class currently in session.")

        if next_class:
            sub = next_class.get("subject_name") or next_class.get("subject_code")
            room = next_class.get("classroom") or "Room Pending"
            day_str = f" on {next_class['weekday'].capitalize()}" if next_class.get("weekday") != today_weekday else " today"
            lines.append(f"• NEXT CLASS: {sub} in {room}{day_str} ({next_class.get('start_time')} - {next_class.get('end_time')})")
        else:
            lines.append("• NEXT CLASS: No further upcoming classes found in the weekly schedule.")

        return {
            "type": "timetable",
            "status": "completed",
            "can_determine": True,
            "section": clean_sec,
            "query_time": dt.isoformat(),
            "current_class": current_class,
            "next_class": next_class,
            "response": "\n".join(lines)
        }

    def query_schedule(
        self,
        query: str,
        student_context: Optional[Dict[str, Any]] = None,
        client_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Primary natural language query handler for timetables.

        Args:
            query: User's natural language question.
            student_context: Optional student context dictionary.
            client_time: Optional ISO timestamp from client.
        """
        # Validate student context if provided
        if student_context:
            is_valid, err_msg, cleaned_ctx = self.validate_student_context(student_context)
            if not is_valid:
                return {
                    "type": "timetable",
                    "status": "invalid_context",
                    "tool": "timetable_engine",
                    "response": f"Context clarification required: {err_msg}"
                }
            student_context = cleaned_ctx

        section, branch = self.resolve_student_section(query, student_context)

        # Enforce section isolation
        if not section:
            return self.handle_unspecified_section()

        registered_sections = self.get_registered_section_ids()
        if section not in registered_sections:
            return self.handle_unregistered_section(section)

        section_info = self.get_section_info(section)

        # Retrieve entries strictly matching this section
        all_valid = self.get_valid_entries()
        section_entries = [
            e for e in all_valid
            if e.get("section", "").strip().upper() == section
        ]

        actionable_entries = [
            e for e in section_entries
            if e.get("subject_name") or e.get("subject_code")
        ]

        if not actionable_entries:
            return self.handle_pending_schedule(section, section_info)

        # Check for temporal queries ("next class", "current class", "tomorrow")
        query_lower = query.lower()
        temporal_keywords = ["next class", "next lecture", "current class", "current period", "tomorrow"]
        is_temporal = any(kw in query_lower for kw in temporal_keywords)

        entries_with_time = [
            e for e in actionable_entries
            if e.get("weekday") and (e.get("period") is not None or e.get("start_time"))
        ]

        if is_temporal:
            if not entries_with_time:
                return {
                    "type": "timetable",
                    "status": "timing_unavailable",
                    "tool": "timetable_engine",
                    "section": section,
                    "response": (
                        f"Timetable for section {section} does not have verified period times or weekday slots.\n"
                        "Next class or daily schedule cannot be determined until official time slots are provided."
                    )
                }
            batch_val = student_context.get("batch") if student_context else None
            return self.get_current_and_next_class(section, client_time, batch=batch_val)

        # Filter by weekday if specified
        matched_weekday = None
        for day in VALID_WEEKDAYS:
            if re.search(rf"\b{day}\b", query_lower):
                matched_weekday = day
                break

        if matched_weekday:
            day_entries = [
                e for e in actionable_entries
                if e.get("weekday", "").lower() == matched_weekday
            ]
            if not day_entries:
                return {
                    "type": "timetable",
                    "status": "completed",
                    "tool": "timetable_engine",
                    "section": section,
                    "response": (
                        f"No scheduled classes found for section {section} on {matched_weekday.capitalize()}."
                    )
                }
            return self._format_schedule_entries(section, day_entries, title_prefix=f"{matched_weekday.capitalize()} Schedule")

        # Specific subject, faculty, classroom search
        subject_match = self._find_subject_in_entries(query_lower, actionable_entries)
        if subject_match:
            return self._format_entry_detail(subject_match, section)

        faculty_match = self._find_faculty_in_entries(query_lower, actionable_entries)
        if faculty_match:
            return self._format_entry_detail(faculty_match, section)

        classroom_match = self._find_classroom_in_entries(query_lower, actionable_entries)
        if classroom_match:
            return self._format_entry_detail(classroom_match, section)

        # General schedule
        return self._format_schedule_entries(section, actionable_entries, title_prefix="Class Schedule")

    def lookup_subject(
        self,
        subject_query: str,
        section: Optional[str] = None
    ) -> Dict[str, Any]:
        """Looks up a subject within a section or reports registered availability."""
        if not section:
            return self.handle_unspecified_section()

        if section.upper() not in self.get_registered_section_ids():
            return self.handle_unregistered_section(section.upper())

        all_valid = self.get_valid_entries()
        sec_entries = [
            e for e in all_valid
            if e.get("section", "").strip().upper() == section.upper()
        ]

        match = self._find_subject_in_entries(subject_query.lower(), sec_entries)
        if match:
            return self._format_entry_detail(match, section.upper())

        return {
            "type": "timetable",
            "status": "not_found",
            "tool": "timetable_engine",
            "section": section.upper(),
            "response": (
                f"Subject '{subject_query}' was not found in verified records for section {section.upper()}."
            )
        }

    def lookup_faculty(
        self,
        faculty_query: str,
        section: Optional[str] = None
    ) -> Dict[str, Any]:
        """Looks up a faculty assignment within a section."""
        if not section:
            return self.handle_unspecified_section()

        if section.upper() not in self.get_registered_section_ids():
            return self.handle_unregistered_section(section.upper())

        all_valid = self.get_valid_entries()
        sec_entries = [
            e for e in all_valid
            if e.get("section", "").strip().upper() == section.upper()
        ]

        match = self._find_faculty_in_entries(faculty_query.lower(), sec_entries)
        if match:
            return self._format_entry_detail(match, section.upper())

        return {
            "type": "timetable",
            "status": "not_found",
            "tool": "timetable_engine",
            "section": section.upper(),
            "response": (
                f"Faculty '{faculty_query}' was not found in verified records for section {section.upper()}."
            )
        }

    def lookup_classroom(
        self,
        room_query: str,
        section: Optional[str] = None
    ) -> Dict[str, Any]:
        """Looks up a classroom allocation within a section."""
        if not section:
            return self.handle_unspecified_section()

        if section.upper() not in self.get_registered_section_ids():
            return self.handle_unregistered_section(section.upper())

        all_valid = self.get_valid_entries()
        sec_entries = [
            e for e in all_valid
            if e.get("section", "").strip().upper() == section.upper()
        ]

        match = self._find_classroom_in_entries(room_query.lower(), sec_entries)
        if match:
            return self._format_entry_detail(match, section.upper())

        return {
            "type": "timetable",
            "status": "not_found",
            "tool": "timetable_engine",
            "section": section.upper(),
            "response": (
                f"Classroom '{room_query}' was not found in verified records for section {section.upper()}."
            )
        }

    def _find_subject_in_entries(
        self,
        query: str,
        entries: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        for e in entries:
            code = (e.get("subject_code") or "").lower()
            name = (e.get("subject_name") or "").lower()
            if code and code in query:
                return e
            if name and (name in query or any(w in query for w in name.split() if len(w) > 3)):
                return e
        return None

    def _find_faculty_in_entries(
        self,
        query: str,
        entries: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        for e in entries:
            fac = (e.get("faculty_name") or "").lower()
            if fac and (fac in query or any(w in query for w in fac.split() if len(w) > 3)):
                return e
        return None

    def _find_classroom_in_entries(
        self,
        query: str,
        entries: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        for e in entries:
            room = (e.get("classroom") or "").lower()
            if room and room in query:
                return e
        return None

    def _format_schedule_entries(
        self,
        section: str,
        entries: List[Dict[str, Any]],
        title_prefix: str = "Schedule"
    ) -> Dict[str, Any]:
        lines = [f"{title_prefix} for Section {section}:\n"]
        for idx, e in enumerate(entries, 1):
            sub = e.get("subject_name") or e.get("subject_code") or "Subject Unspecified"
            fac = e.get("faculty_name") or "Faculty: Pending"
            room = e.get("classroom") or "Room: Pending"
            time_str = ""
            if e.get("weekday"):
                time_str += f"{e['weekday'].capitalize()} "
            if e.get("start_time") and e.get("end_time"):
                time_str += f"({e['start_time']} - {e['end_time']}) "
            elif e.get("period") is not None:
                time_str += f"(Period {e['period']}) "
            batch_str = f" [Batch: {e['batch']}]" if e.get("batch") and e["batch"] != "All" else ""
            lines.append(f"{idx}. {sub}{batch_str}\n   {fac} | {room} | {time_str.strip() or 'Time: Pending'}")

        return {
            "type": "timetable",
            "status": "completed",
            "tool": "timetable_engine",
            "section": section,
            "entries_count": len(entries),
            "response": "\n".join(lines)
        }

    def _format_entry_detail(
        self,
        entry: Dict[str, Any],
        section: str
    ) -> Dict[str, Any]:
        sub = entry.get("subject_name") or entry.get("subject_code") or "Class"
        code = f" ({entry['subject_code']})" if entry.get("subject_code") else ""
        lines = [
            f"Course Detail: {sub}{code}",
            f"Section: {section}",
            f"Faculty: {entry.get('faculty_name') or 'Not specified'}",
            f"Classroom / Lab: {entry.get('classroom') or 'Not specified'}"
        ]
        if entry.get("weekday"):
            lines.append(f"Day: {entry['weekday'].capitalize()}")
        if entry.get("period") is not None:
            lines.append(f"Period: {entry['period']}")
        if entry.get("start_time") and entry.get("end_time"):
            lines.append(f"Timing: {entry['start_time']} to {entry['end_time']}")
        if entry.get("batch") and entry["batch"] != "All":
            lines.append(f"Batch: {entry['batch']}")

        return {
            "type": "timetable",
            "status": "completed",
            "tool": "timetable_engine",
            "section": section,
            "result": entry,
            "response": "\n".join(lines)
        }
