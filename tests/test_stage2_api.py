"""Automated tests for Stage 2: REST API Endpoints, Student Context Validation, and Next-Class Safety."""

import json
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app, reset_rate_limiter
from backend.timetable_engine import TimetableEngine, clear_timetable_cache


class TestStage2API(unittest.TestCase):
    """Test suite for new /api/timetable endpoints and student context validation."""

    def setUp(self):
        reset_rate_limiter()
        clear_timetable_cache()
        self.client = TestClient(app)

    def tearDown(self):
        reset_rate_limiter()
        clear_timetable_cache()

    # 1. Tests for GET /api/timetable/sections
    def test_get_sections_all(self):
        """Test retrieving all registered sections."""
        response = self.client.get("/api/timetable/sections")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["institution"], "Sapthagiri NPS University")
        self.assertGreaterEqual(data["count"], 1)
        sec_ids = [s["section_id"] for s in data["sections"]]
        self.assertIn("1ECE02", sec_ids)

    def test_get_sections_filter_branch(self):
        """Test filtering sections by branch."""
        # Existing branch
        res_ece = self.client.get("/api/timetable/sections?branch=ECE")
        self.assertEqual(res_ece.status_code, 200)
        data_ece = res_ece.json()
        self.assertGreaterEqual(data_ece["count"], 1)
        self.assertEqual(data_ece["sections"][0]["branch"], "ECE")

        # Non-existing branch
        res_civ = self.client.get("/api/timetable/sections?branch=CIVIL")
        self.assertEqual(res_civ.status_code, 200)
        data_civ = res_civ.json()
        self.assertEqual(data_civ["count"], 0)
        self.assertEqual(data_civ["sections"], [])

    def test_get_sections_invalid_semester_param(self):
        """Test validation error for invalid semester range."""
        res = self.client.get("/api/timetable/sections?semester=99")
        self.assertEqual(res.status_code, 422)

    # 2. Tests for GET /api/timetable/subjects
    def test_get_subjects_registered_partial_section(self):
        """Test retrieving subjects for 1ECE02 (schedule pending)."""
        res = self.client.get("/api/timetable/subjects?section=1ECE02")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["section"], "1ECE02")
        self.assertEqual(data["status"], "schedule_pending")
        self.assertEqual(data["subjects"], [])
        self.assertIn("pending official publication", data["message"].lower())

    def test_get_subjects_unregistered_section(self):
        """Test 404 for unregistered section."""
        res = self.client.get("/api/timetable/subjects?section=1CSE99")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not registered", res.json()["detail"].lower())

    def test_get_subjects_branch_mismatch(self):
        """Test 400 when requested branch does not match section."""
        res = self.client.get("/api/timetable/subjects?section=1ECE02&branch=CSE")
        self.assertEqual(res.status_code, 400)
        self.assertIn("branch mismatch", res.json()["detail"].lower())

    def test_get_subjects_missing_param(self):
        """Test 422 when required 'section' parameter is omitted."""
        res = self.client.get("/api/timetable/subjects")
        self.assertEqual(res.status_code, 422)

    # 3. Tests for GET /api/timetable/schedule
    def test_get_schedule_registered_partial_section(self):
        """Test schedule endpoint for 1ECE02."""
        res = self.client.get("/api/timetable/schedule?section=1ECE02")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "schedule_pending")
        self.assertEqual(data["entries"], [])

    def test_get_schedule_unregistered_section(self):
        """Test 404 for unregistered section in schedule endpoint."""
        res = self.client.get("/api/timetable/schedule?section=UNKNOWN_SEC")
        self.assertEqual(res.status_code, 404)

    def test_get_schedule_invalid_weekday(self):
        """Test 400 when invalid weekday is provided."""
        res = self.client.get("/api/timetable/schedule?section=1ECE02&weekday=funday")
        self.assertEqual(res.status_code, 400)
        self.assertIn("invalid weekday", res.json()["detail"].lower())

    def test_get_schedule_missing_section(self):
        """Test 422 when required 'section' parameter is missing."""
        res = self.client.get("/api/timetable/schedule")
        self.assertEqual(res.status_code, 422)

    # 4. Tests for GET /api/timetable/next-class
    def test_get_next_class_incomplete_data(self):
        """Test next-class endpoint explains missing information for 1ECE02."""
        res = self.client.get("/api/timetable/next-class?section=1ECE02&client_time=2026-10-12T10:00:00")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["can_determine"])
        self.assertEqual(data["status"], "schedule_pending")
        self.assertIn("verified_period_timings", data["missing_information"])

    def test_get_next_class_missing_client_time(self):
        """Test next-class endpoint with unreleased section reports missing information safely."""
        res = self.client.get("/api/timetable/next-class?section=1ECE02")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["can_determine"])

    def test_get_next_class_unregistered_section(self):
        """Test next-class endpoint with unregistered section returns 404."""
        res = self.client.get("/api/timetable/next-class?section=NOT_A_SECTION")
        self.assertEqual(res.status_code, 404)

    # 5. Tests for Student Context in POST /chat
    def test_chat_with_valid_student_context_object(self):
        """Test POST /chat with StudentContext schema."""
        payload = {
            "message": "What is my timetable?",
            "student_context": {
                "branch": "ECE",
                "academic_year": 1,
                "semester": 2,
                "section": "1ECE02",
                "batch": "Batch A"
            }
        }
        res = self.client.post("/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["type"], "timetable")
        self.assertEqual(data["status"], "schedule_pending")
        self.assertIn("1ECE02", data["response"])

    def test_chat_with_unregistered_section_in_context(self):
        """Test POST /chat rejects unregistered section in student_context."""
        payload = {
            "message": "Show my classes",
            "student_context": {
                "section": "1MECH99"
            }
        }
        res = self.client.post("/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "invalid_context")
        self.assertIn("not registered", data["response"].lower())

    def test_chat_with_branch_mismatch_in_context(self):
        """Test POST /chat detects branch mismatch in student_context."""
        payload = {
            "message": "Show my timetable",
            "student_context": {
                "branch": "CSE",
                "section": "1ECE02"
            }
        }
        res = self.client.post("/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "invalid_context")
        self.assertIn("does not match", data["response"].lower())

    # 6. Backward Compatibility of POST /chat
    def test_chat_backward_compatibility_minimal_payload(self):
        """Test legacy {"message": "..."} payload functions identically."""
        res1 = self.client.post("/chat", json={"message": "system status"})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["type"], "system_status")

        res2 = self.client.post("/chat", json={"message": "Calculate 100 / 2"})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["type"], "calculator")
        self.assertIn("50", res2.json()["response"])

        res3 = self.client.post("/chat", json={"message": "Where is the library?"})
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.json()["type"], "knowledge")


class TestNextClassSafetyWithFixture(unittest.TestCase):
    """Test suite for current/next class resolution on a verified complete schedule fixture."""

    def setUp(self):
        self.fixture_data = {
            "institution": "Sapthagiri NPS University",
            "sections_catalog": [
                {"section_id": "TEST-ECE", "branch": "ECE", "branch_name": "ECE Complete Test"}
            ],
            "entries": [
                {
                    "section": "TEST-ECE",
                    "branch": "ECE",
                    "subject_code": "EC201",
                    "subject_name": "Network Analysis",
                    "faculty_name": "Dr. Rao",
                    "classroom": "Room 101",
                    "weekday": "monday",
                    "period": 1,
                    "start_time": "09:00",
                    "end_time": "10:00",
                    "batch": "All"
                },
                {
                    "section": "TEST-ECE",
                    "branch": "ECE",
                    "subject_code": "EC202",
                    "subject_name": "Analog Electronics",
                    "faculty_name": "Prof. Mehra",
                    "classroom": "Room 102",
                    "weekday": "monday",
                    "period": 2,
                    "start_time": "10:15",
                    "end_time": "11:15",
                    "batch": "All"
                },
                {
                    "section": "TEST-ECE",
                    "branch": "ECE",
                    "subject_code": "EC203",
                    "subject_name": "Digital Logic Lab",
                    "faculty_name": "Dr. Anita",
                    "classroom": "Lab A",
                    "weekday": "monday",
                    "period": 3,
                    "start_time": "11:30",
                    "end_time": "13:00",
                    "batch": "Batch 1"
                },
                {
                    "section": "TEST-ECE",
                    "branch": "ECE",
                    "subject_code": "EC204",
                    "subject_name": "Microcontrollers",
                    "faculty_name": "Prof. Kumar",
                    "classroom": "Room 101",
                    "weekday": "tuesday",
                    "period": 1,
                    "start_time": "09:00",
                    "end_time": "10:00",
                    "batch": "All"
                }
            ]
        }
        self.temp_file = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(self.fixture_data, self.temp_file)
        self.temp_file.close()
        self.engine = TimetableEngine(data_file=self.temp_file.name)

    def tearDown(self):
        Path(self.temp_file.name).unlink(missing_ok=True)
        clear_timetable_cache()

    def test_current_class_in_session(self):
        """At Monday 09:30, current class is Network Analysis and next class is Analog Electronics."""
        res = self.engine.get_current_and_next_class(
            section="TEST-ECE",
            client_time_str="2026-10-12T09:30:00"  # 2026-10-12 is Monday
        )
        self.assertTrue(res["can_determine"])
        self.assertEqual(res["status"], "completed")
        self.assertIsNotNone(res["current_class"])
        self.assertEqual(res["current_class"]["subject_name"], "Network Analysis")
        self.assertIsNotNone(res["next_class"])
        self.assertEqual(res["next_class"]["subject_name"], "Analog Electronics")

    def test_between_classes(self):
        """At Monday 10:05 (break between classes), no class is in session, next class is Analog Electronics."""
        res = self.engine.get_current_and_next_class(
            section="TEST-ECE",
            client_time_str="2026-10-12T10:05:00"
        )
        self.assertTrue(res["can_determine"])
        self.assertIsNone(res["current_class"])
        self.assertIsNotNone(res["next_class"])
        self.assertEqual(res["next_class"]["subject_name"], "Analog Electronics")

    def test_batch_isolation_in_next_class(self):
        """Batch filtering: A student in Batch 2 should not get Batch 1 lab."""
        res = self.engine.get_current_and_next_class(
            section="TEST-ECE",
            client_time_str="2026-10-12T11:20:00",
            batch="Batch 2"
        )
        self.assertTrue(res["can_determine"])
        # Next class for Batch 2 should skip Batch 1 lab and find Tuesday's Microcontrollers
        self.assertIsNotNone(res["next_class"])
        self.assertEqual(res["next_class"]["subject_name"], "Microcontrollers")

    def test_after_all_classes_today_rolls_to_next_day(self):
        """At Monday 18:00, all classes today are over; next class is Tuesday 09:00."""
        res = self.engine.get_current_and_next_class(
            section="TEST-ECE",
            client_time_str="2026-10-12T18:00:00"
        )
        self.assertTrue(res["can_determine"])
        self.assertIsNone(res["current_class"])
        self.assertIsNotNone(res["next_class"])
        self.assertEqual(res["next_class"]["subject_name"], "Microcontrollers")
        self.assertEqual(res["next_class"]["weekday"], "tuesday")

    def test_missing_client_time_fails_safely(self):
        """When client_time is None, the engine safely asks for time rather than guessing."""
        res = self.engine.get_current_and_next_class(
            section="TEST-ECE",
            client_time_str=None
        )
        self.assertFalse(res["can_determine"])
        self.assertEqual(res["status"], "time_required")
        self.assertIn("client_time", res["missing_information"])


if __name__ == "__main__":
    unittest.main()
