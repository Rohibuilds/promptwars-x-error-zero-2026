"""Automated test suite for Sapthagiri NPS University Timetable Engine.

Covers:
- Subject, faculty, and classroom lookups
- Missing information and ambiguous questions
- Strict isolation between sections (preventing cross-section leaks)
- Missing period and weekday data handling
- Calculator and campus-information intent disambiguation
- Invalid timetable records validation
"""

import json
import tempfile
import unittest
from pathlib import Path

from backend.agent import run_agent, is_math_query, is_timetable_query, is_knowledge_query
from backend.timetable_engine import (
    TimetableEngine,
    validate_timetable_entry,
    load_timetable_data,
    clear_timetable_cache
)


class TestTimetableEngine(unittest.TestCase):
    """Test suite for TimetableEngine deterministic lookup and isolation."""

    def setUp(self):
        clear_timetable_cache()
        self.engine = TimetableEngine()

    def tearDown(self):
        clear_timetable_cache()

    def test_production_catalog_contains_1ece02(self):
        """Verify that 1ECE02 is cataloged in the official initial dataset."""
        sections = self.engine.get_registered_section_ids()
        self.assertIn("1ECE02", sections)
        info = self.engine.get_section_info("1ECE02")
        self.assertIsNotNone(info)
        self.assertEqual(info.get("branch"), "ECE")
        self.assertEqual(info.get("verification_status"), "partial_verified")

    def test_missing_section_context_prompts_user(self):
        """Queries without branch or section context must prompt for selection, never guess."""
        res = self.engine.query_schedule("Where is my next class?")
        self.assertEqual(res["status"], "context_required")
        self.assertIn("please specify your branch and section", res["response"].lower())
        self.assertIn("1ECE02", res["response"])

    def test_unregistered_section_rejected_safely(self):
        """Unregistered sections like 1CSE01 must be rejected without leaking 1ECE02 data."""
        res = self.engine.query_schedule("Show timetable for section 1CSE01")
        self.assertEqual(res["status"], "section_not_found")
        self.assertIn("1CSE01", res["response"])
        self.assertIn("not currently available", res["response"])
        self.assertIn("1ECE02", res["response"])

    def test_1ece02_unreleased_schedule_handled_gracefully(self):
        """When 1ECE02 is queried for next class or weekly schedule, engine must explain that periods are unreleased."""
        res = self.engine.query_schedule("What is the timetable for 1ECE02?")
        self.assertEqual(res["status"], "schedule_pending")
        self.assertIn("1ECE02", res["response"])
        self.assertIn("pending official publication", res["response"].lower())

        # Also test temporal question
        temp_res = self.engine.query_schedule("Where is my next class for 1ECE02?")
        self.assertEqual(temp_res["status"], "schedule_pending")
        self.assertIn("official", temp_res["response"].lower())

    def test_section_isolation_with_multi_section_fixture(self):
        """Strict isolation: Section A records must never be returned for Section B."""
        fixture_data = {
            "institution": "Sapthagiri NPS University",
            "sections_catalog": [
                {"section_id": "SEC-A", "branch": "ECE", "branch_name": "ECE Section A"},
                {"section_id": "SEC-B", "branch": "CSE", "branch_name": "CSE Section B"}
            ],
            "entries": [
                {
                    "section": "SEC-A",
                    "branch": "ECE",
                    "subject_code": "EC201",
                    "subject_name": "Analog Circuits",
                    "faculty_name": "Dr. Raman",
                    "classroom": "Room 101",
                    "weekday": "monday",
                    "period": 1,
                    "start_time": "09:00",
                    "end_time": "10:00",
                    "batch": "All"
                },
                {
                    "section": "SEC-B",
                    "branch": "CSE",
                    "subject_code": "CS201",
                    "subject_name": "Data Structures",
                    "faculty_name": "Prof. Rao",
                    "classroom": "Room 202",
                    "weekday": "monday",
                    "period": 1,
                    "start_time": "09:00",
                    "end_time": "10:00",
                    "batch": "All"
                }
            ]
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(fixture_data, f)
            temp_path = f.name

        try:
            fixture_engine = TimetableEngine(data_file=temp_path)

            # Query SEC-A
            res_a = fixture_engine.query_schedule("Show timetable for SEC-A")
            self.assertEqual(res_a["status"], "completed")
            self.assertIn("Analog Circuits", res_a["response"])
            self.assertIn("Dr. Raman", res_a["response"])
            self.assertNotIn("Data Structures", res_a["response"])
            self.assertNotIn("Prof. Rao", res_a["response"])

            # Query SEC-B
            res_b = fixture_engine.query_schedule("Show timetable for SEC-B")
            self.assertEqual(res_b["status"], "completed")
            self.assertIn("Data Structures", res_b["response"])
            self.assertIn("Prof. Rao", res_b["response"])
            self.assertNotIn("Analog Circuits", res_b["response"])
            self.assertNotIn("Dr. Raman", res_b["response"])
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_fixture_subject_faculty_classroom_lookups(self):
        """Verify subject, faculty, and room lookups on verified schedule records."""
        fixture_data = {
            "institution": "Sapthagiri NPS University",
            "sections_catalog": [
                {"section_id": "TEST-SEC", "branch": "ECE", "branch_name": "ECE Test"}
            ],
            "entries": [
                {
                    "section": "TEST-SEC",
                    "branch": "ECE",
                    "subject_code": "EC305",
                    "subject_name": "Signals and Systems",
                    "faculty_name": "Dr. Anita Desai",
                    "classroom": "Auditorium 3",
                    "weekday": "wednesday",
                    "period": 3,
                    "start_time": "11:15",
                    "end_time": "12:15",
                    "batch": "All"
                }
            ]
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(fixture_data, f)
            temp_path = f.name

        try:
            fixture_engine = TimetableEngine(data_file=temp_path)

            # Subject lookup
            sub_res = fixture_engine.lookup_subject("Signals and Systems", section="TEST-SEC")
            self.assertEqual(sub_res["status"], "completed")
            self.assertIn("Dr. Anita Desai", sub_res["response"])
            self.assertIn("Auditorium 3", sub_res["response"])

            # Faculty lookup
            fac_res = fixture_engine.lookup_faculty("Anita Desai", section="TEST-SEC")
            self.assertEqual(fac_res["status"], "completed")
            self.assertIn("Signals and Systems", fac_res["response"])

            # Classroom lookup
            room_res = fixture_engine.lookup_classroom("Auditorium 3", section="TEST-SEC")
            self.assertEqual(room_res["status"], "completed")
            self.assertIn("Signals and Systems", room_res["response"])

            # Non-existent subject in section
            nf_res = fixture_engine.lookup_subject("Quantum Physics", section="TEST-SEC")
            self.assertEqual(nf_res["status"], "not_found")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_missing_period_and_weekday_data_graceful_handling(self):
        """When period and weekday are None, the engine reports Time: Pending rather than crashing."""
        fixture_data = {
            "institution": "Sapthagiri NPS University",
            "sections_catalog": [
                {"section_id": "PARTIAL-SEC", "branch": "ECE", "branch_name": "ECE Partial"}
            ],
            "entries": [
                {
                    "section": "PARTIAL-SEC",
                    "branch": "ECE",
                    "subject_code": "EC101",
                    "subject_name": "Basic Electronics",
                    "faculty_name": "Prof. K. Verma",
                    "classroom": "Room 204",
                    "weekday": None,
                    "period": None,
                    "start_time": None,
                    "end_time": None,
                    "batch": "All"
                }
            ]
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(fixture_data, f)
            temp_path = f.name

        try:
            fixture_engine = TimetableEngine(data_file=temp_path)
            res = fixture_engine.query_schedule("Show timetable for PARTIAL-SEC")
            self.assertEqual(res["status"], "completed")
            self.assertIn("Basic Electronics", res["response"])
            self.assertIn("Time: Pending", res["response"])

            # Temporal query should report timing unavailable
            temp_res = fixture_engine.query_schedule("Where is my next class for PARTIAL-SEC?")
            self.assertEqual(temp_res["status"], "timing_unavailable")
            self.assertIn("verified period times", temp_res["response"].lower())
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_invalid_timetable_records_validation(self):
        """Verify that malformed or invalid records fail validation and are safely skipped."""
        # Non-dict
        ok, reason = validate_timetable_entry("not a dict")  # type: ignore
        self.assertFalse(ok)

        # Missing section
        ok, reason = validate_timetable_entry({"branch": "ECE"})
        self.assertFalse(ok)
        self.assertIn("section", reason.lower())

        # Missing branch
        ok, reason = validate_timetable_entry({"section": "1ECE02"})
        self.assertFalse(ok)
        self.assertIn("branch", reason.lower())

        # Invalid weekday
        ok, reason = validate_timetable_entry({"section": "1ECE02", "branch": "ECE", "weekday": "Funday"})
        self.assertFalse(ok)
        self.assertIn("weekday", reason.lower())

        # Valid entry
        ok, reason = validate_timetable_entry({
            "section": "1ECE02",
            "branch": "ECE",
            "weekday": "monday",
            "period": 1
        })
        self.assertTrue(ok)
        self.assertIsNone(reason)


class TestIntentRoutingDisambiguation(unittest.TestCase):
    """Test suite ensuring natural language questions are not misrouted to the calculator."""

    def test_library_timing_routes_to_knowledge_not_calculator(self):
        """'What is the library timing?' must NOT route to calculator."""
        self.assertFalse(is_math_query("what is the library timing?"))
        self.assertTrue(is_knowledge_query("what is the library timing?"))

        res = run_agent("What is the library timing?")
        self.assertEqual(res["type"], "knowledge")
        self.assertEqual(res["status"], "completed")
        self.assertIn("9:00 AM to 6:00 PM", res["response"])

    def test_lab_location_routes_to_knowledge_not_calculator(self):
        """'What is the computer lab location?' must NOT route to calculator."""
        self.assertFalse(is_math_query("what is the computer lab location?"))
        self.assertTrue(is_knowledge_query("what is the computer lab location?"))

        res = run_agent("What is the computer lab location?")
        self.assertEqual(res["type"], "knowledge")
        self.assertEqual(res["status"], "completed")
        self.assertIn("Block B", res["response"])

    def test_valid_math_queries_route_to_calculator(self):
        """Genuine arithmetic queries must route to calculator correctly."""
        self.assertTrue(is_math_query("calculate 25 plus 17"))
        self.assertTrue(is_math_query("what is 12 times 3?"))
        self.assertTrue(is_math_query("solve 20 divided by 4"))
        self.assertTrue(is_math_query("what is 50 + 25"))

        res1 = run_agent("What is 12 times 3?")
        self.assertEqual(res1["type"], "calculator")
        self.assertIn("36", res1["response"])

        res2 = run_agent("Calculate 25 plus 17")
        self.assertEqual(res2["type"], "calculator")
        self.assertIn("42", res2["response"])

    def test_timetable_intent_routing(self):
        """Timetable queries must route to timetable engine."""
        self.assertTrue(is_timetable_query("where is my next class?"))
        self.assertTrue(is_timetable_query("show my timetable for tomorrow"))
        self.assertTrue(is_timetable_query("what is the schedule for 1ece02?"))

        res = run_agent("Where is my next class?")
        self.assertEqual(res["type"], "timetable")
        self.assertEqual(res["status"], "context_required")


if __name__ == "__main__":
    unittest.main()
