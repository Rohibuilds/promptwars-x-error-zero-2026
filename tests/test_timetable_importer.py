"""Unit tests for the TimetableImporter staging, quarantine, and merge pipeline."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from backend.timetable_importer import TimetableImporter


class TestTimetableImporter(unittest.TestCase):
    """Verifies that official timetable staging, validation, quarantine, and backup mechanisms function reliably."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.live_file = Path(self.temp_dir) / "live_timetable.json"
        self.staging_dir = Path(self.temp_dir) / "staging"
        self.backup_dir = Path(self.temp_dir) / "backups"

        initial_live = {
            "institution": "Sapthagiri NPS University",
            "version": "1.0.0",
            "sections_catalog": [
                {
                    "section_id": "1ECE02",
                    "branch": "ECE",
                    "verification_status": "partial_verified"
                }
            ],
            "entries": [
                {
                    "id": "1ECE02-PROV-001",
                    "section": "1ECE02",
                    "branch": "ECE",
                    "subject_name": None,
                    "weekday": None,
                    "period": None,
                    "verification_status": "partial_verified"
                }
            ]
        }
        with open(self.live_file, "w", encoding="utf-8") as f:
            json.dump(initial_live, f)

        self.importer = TimetableImporter(
            timetable_file=self.live_file,
            staging_dir=self.staging_dir,
            backup_dir=self.backup_dir
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_stage_clean_records(self):
        """Clean, valid records should be staged with status staged_verified."""
        records = [
            {
                "weekday": "monday",
                "period": 1,
                "start_time": "09:00",
                "end_time": "09:55",
                "subject_code": "22EC201",
                "subject_name": "Digital Circuit Design",
                "faculty_name": "Dr. Ramesh K",
                "classroom": "LH-201",
                "batch": "All",
                "confidence": 1.0
            },
            {
                "weekday": "monday",
                "period": 2,
                "start_time": "09:55",
                "end_time": "10:50",
                "subject_code": "22EC202",
                "subject_name": "Signals and Systems",
                "faculty_name": "Prof. Ananya M",
                "classroom": "LH-201",
                "batch": "All",
                "confidence": 0.98
            }
        ]

        res = self.importer.stage_records(
            source_document="ECE_Timetable_Official.pdf",
            effective_date="2026-02-01",
            branch="ECE",
            semester=2,
            section="1ECE02",
            records=records
        )

        self.assertEqual(res["total_records"], 2)
        self.assertEqual(res["verified_ready"], 2)
        self.assertEqual(res["quarantined_uncertain"], 0)
        self.assertFalse(res["has_quarantined"])

        staged_details = self.importer.inspect_stage(res["stage_id"])
        self.assertEqual(staged_details["status"], "pending_approval")
        self.assertEqual(len(staged_details["verified_entries"]), 2)

    def test_quarantine_low_confidence_records(self):
        """Records with extraction confidence below 0.90 must be quarantined."""
        records = [
            {
                "weekday": "monday",
                "period": 1,
                "start_time": "09:00",
                "end_time": "09:55",
                "subject_code": "22EC201",
                "subject_name": "Digital Circuit Design",
                "faculty_name": "Dr. Ramesh K",
                "classroom": "LH-201",
                "batch": "All",
                "confidence": 0.72  # Below 0.90 threshold
            }
        ]

        res = self.importer.stage_records(
            source_document="Scanned_Image_OCR.png",
            effective_date="2026-02-01",
            branch="ECE",
            semester=2,
            section="1ECE02",
            records=records
        )

        self.assertEqual(res["verified_ready"], 0)
        self.assertEqual(res["quarantined_uncertain"], 1)
        self.assertTrue(res["has_quarantined"])

        staged = self.importer.inspect_stage(res["stage_id"])
        quarantined_entry = staged["quarantined_entries"][0]
        self.assertEqual(quarantined_entry["verification_status"], "quarantined")
        self.assertTrue(any("Low OCR" in r for r in quarantined_entry["quarantine_reasons"]))

    def test_quarantine_period_collision(self):
        """Two records occupying the same period/day/batch must trigger collision quarantine."""
        records = [
            {
                "weekday": "tuesday",
                "period": 3,
                "subject_name": "Microcontrollers",
                "classroom": "LH-201",
                "batch": "All"
            },
            {
                "weekday": "tuesday",
                "period": 3,  # Collision on same period and batch
                "subject_name": "Electromagnetics",
                "classroom": "LH-201",
                "batch": "All"
            }
        ]

        res = self.importer.stage_records(
            source_document="Conflict_Test.pdf",
            effective_date="2026-02-01",
            branch="ECE",
            semester=2,
            section="1ECE02",
            records=records
        )

        self.assertEqual(res["verified_ready"], 1)
        self.assertEqual(res["quarantined_uncertain"], 1)
        staged = self.importer.inspect_stage(res["stage_id"])
        self.assertTrue(any("Period collision" in r for r in staged["quarantined_entries"][0]["quarantine_reasons"]))

    def test_quarantine_classroom_collision(self):
        """Two different classes claiming the same classroom at the same time must trigger collision quarantine."""
        records = [
            {
                "weekday": "wednesday",
                "period": 4,
                "subject_name": "Physics",
                "classroom": "Room-301",
                "batch": "Batch A"
            },
            {
                "weekday": "wednesday",
                "period": 4,
                "subject_name": "Chemistry",
                "classroom": "Room-301",  # Same classroom
                "batch": "Batch B"
            }
        ]

        res = self.importer.stage_records(
            source_document="Room_Collision.pdf",
            effective_date="2026-02-01",
            branch="ECE",
            semester=2,
            section="1ECE02",
            records=records
        )

        self.assertEqual(res["verified_ready"], 1)
        self.assertEqual(res["quarantined_uncertain"], 1)
        staged = self.importer.inspect_stage(res["stage_id"])
        self.assertTrue(any("Classroom collision" in r for r in staged["quarantined_entries"][0]["quarantine_reasons"]))

    def test_diff_preview(self):
        """Generating diff must report correct counts and overwrite expectation."""
        records = [
            {
                "weekday": "monday",
                "period": 1,
                "subject_name": "Embedded Systems",
                "classroom": "LH-101",
                "batch": "All"
            }
        ]
        res = self.importer.stage_records(
            source_document="Official.pdf",
            effective_date="2026-02-01",
            branch="ECE",
            semester=2,
            section="1ECE02",
            records=records
        )

        diff = self.importer.generate_diff(res["stage_id"])
        self.assertEqual(diff["section"], "1ECE02")
        self.assertFalse(diff["is_new_section"])
        self.assertEqual(diff["staged_verified_count"], 1)
        self.assertTrue(diff["will_replace_existing"])

    def test_apply_without_confirm_raises_permission_error(self):
        """apply_stage without confirm=True must be rejected."""
        records = [{"weekday": "monday", "period": 1, "subject_name": "Maths"}]
        res = self.importer.stage_records(
            source_document="Doc.pdf",
            effective_date="2026-02-01",
            branch="ECE",
            semester=2,
            section="1ECE02",
            records=records
        )

        with self.assertRaises(PermissionError):
            self.importer.apply_stage(res["stage_id"], confirm=False)

    def test_apply_with_confirm_creates_backup_and_updates_live(self):
        """apply_stage with confirm=True must create automated backup and update live dataset."""
        records = [
            {
                "weekday": "monday",
                "period": 1,
                "start_time": "09:00",
                "end_time": "09:55",
                "subject_name": "VLSI Design",
                "classroom": "LH-102",
                "batch": "All"
            }
        ]
        res = self.importer.stage_records(
            source_document="Verified_VLSI.pdf",
            effective_date="2026-02-01",
            branch="ECE",
            semester=2,
            section="1ECE02",
            records=records
        )

        merge_res = self.importer.apply_stage(res["stage_id"], confirm=True)
        self.assertEqual(merge_res["status"], "success")
        self.assertEqual(merge_res["records_applied"], 1)

        # Check backup was created
        backup_path = Path(merge_res["backup_file"])
        self.assertTrue(backup_path.exists())

        # Check live file was updated
        with open(self.live_file, "r", encoding="utf-8") as f:
            updated_live = json.load(f)

        live_entries = updated_live["entries"]
        self.assertEqual(len(live_entries), 1)
        self.assertEqual(live_entries[0]["subject_name"], "VLSI Design")
        self.assertEqual(live_entries[0]["verification_status"], "verified")


if __name__ == "__main__":
    unittest.main()
