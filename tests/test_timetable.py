"""Regression tests for evidence-based college timetable answers."""

import unittest

from backend.agent import run_agent, timetable_answer, load_timetable


class TestCollegeTimetable(unittest.TestCase):
    def test_timetable_data_loads(self):
        data = load_timetable()
        self.assertEqual(data["section"], "1ECE02")
        self.assertEqual(data["academic_year"], "2026-27")
        self.assertTrue(data["room_day_entries"])

    def test_english_day_one_room(self):
        result = run_agent("Where do I have English on Day 1?")
        self.assertEqual(result["type"], "college_timetable")
        self.assertIn("A1203", result["response"])
        self.assertIn("Day 1", result["response"])

    def test_room_a1204_lists_recorded_days(self):
        result = run_agent("Which classes are held in A1204?")
        self.assertIn("Day 1", result["response"])
        self.assertIn("Day 2", result["response"])
        self.assertIn("Day 4", result["response"])
        self.assertIn("Day 5", result["response"])

    def test_subject_and_day_room_lookup(self):
        result = run_agent("Where is BECL on Day 3?")
        self.assertIn("A201/A204", result["response"])

    def test_missing_room_for_subject_day_is_not_guessed(self):
        result = run_agent("Where is English on Day 5?")
        self.assertIn("do not establish a room", result["response"])

    def test_missing_period_mapping_is_disclosed(self):
        result = run_agent("What class do I have at 11:00 AM on Day 1?")
        self.assertIn("exact subject-to-period", result["response"])

    def test_weekday_not_invented(self):
        result = run_agent("What is my Monday timetable?")
        self.assertIn("weekday names", result["response"])

    def test_faculty_lookup(self):
        result = run_agent("Who teaches Mathematics?")
        self.assertIn("Mrs. Dhanalakshmi R", result["response"])

    def test_timetable_answer_precedes_calculator_routing(self):
        result = run_agent("What is the room for English on Day 1?")
        self.assertIn("A1203", result["response"])


if __name__ == "__main__":
    unittest.main()
