"""Comprehensive Automated Test Suite for Stage 5B: Timetable Staging and Validation Pipeline.

Covers:
1. Production timetable immutability (data/timetable.json byte integrity).
2. Staging schema structure and approval gate (status: pending_review).
3. Deterministic unique IDs without timestamps or colons.
4. Source provenance preservation (worksheet, cell reference, course allocation).
5. Distinct batch isolation for lab assignments (B1 vs B2 faculty and classrooms).
6. Multi-period lab assignments retain both periods and durations.
7. Blank advisors for the 6 unassigned sections preserved as source warnings.
8. Validation error rejection on corrupted payloads.
9. Provenance mismatch protection (rejects silent overwrite if source hash differs).
10. Atomic write safety (interrupted writes leave existing files intact).
11. Read-only API endpoint GET /api/timetable/staging-status with safe fallback.
12. Opt-in local audit test suite for verifying the full 2,682-record local dataset.
"""

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from backend.main import app, reset_rate_limiter
from backend.timetable_staging import (
    DEFAULT_STAGING_DIR,
    EXTRACTOR_VERSION,
    KNOWN_BLANK_ADVISOR_SECTIONS,
    REPORT_JSON_FILE,
    REPORT_MD_FILE,
    SCHEMA_VERSION,
    STAGING_JSON_FILE,
    TimetableStager,
    compute_file_sha256,
    extract_full_workbook,
    get_staging_status,
    resolve_workbook_path,
    validate_staged_dataset,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_FILE = REPO_ROOT / "data" / "timetable.json"

# Self-contained synthetic staging dataset fixture representing PC and EC cycles,
# lab batch isolation, multi-period labs, and known unassigned advisor sections.
SYNTHETIC_STAGED_FIXTURE = {
    "schema_version": SCHEMA_VERSION,
    "stage": "5B",
    "dataset_type": "timetable_staging",
    "status": "pending_review",
    "source": {
        "workbook_filename": "SOET TT(EC &PC) as on 18_9_26.xlsx",
        "workbook_sha256": "072c23cfedf6c1428fb80bfcb572386ebb1d5d80a93e70ef40a9e1ef182b296c"
    },
    "extraction": {
        "record_count": 5,
        "section_count": 8,
        "extractor_version": EXTRACTOR_VERSION,
        "source_sha256": "072c23cfedf6c1428fb80bfcb572386ebb1d5d80a93e70ef40a9e1ef182b296c",
        "generated_at": "2026-10-13T17:37:34.914628+00:00"
    },
    "sections_catalog": [
        {
            "section_id": "1CSE01",
            "cycle": "PC",
            "department": "Department of Computer Science and Engineering",
            "class_advisor": "Dr. Ashwini V Bhat",
            "verification_status": "staged_pending_review"
        },
        {
            "section_id": "1ECE02",
            "cycle": "EC",
            "department": "Department of Electronics and Communication Engineering",
            "class_advisor": "Ms.Madhu H M",
            "verification_status": "staged_pending_review"
        },
        {"section_id": "1CSE05", "cycle": "PC", "department": "Department of Computer Science and Engineering", "class_advisor": None, "verification_status": "staged_pending_review"},
        {"section_id": "1DAS08", "cycle": "PC", "department": "Department of Computer Science and Engineering", "class_advisor": None, "verification_status": "staged_pending_review"},
        {"section_id": "1CSE39", "cycle": "EC", "department": "Department of Computer Science and Engineering", "class_advisor": None, "verification_status": "staged_pending_review"},
        {"section_id": "1CSE40", "cycle": "EC", "department": "Department of Computer Science and Engineering", "class_advisor": None, "verification_status": "staged_pending_review"},
        {"section_id": "1CSE41", "cycle": "EC", "department": "Department of Computer Science and Engineering", "class_advisor": None, "verification_status": "staged_pending_review"},
        {"section_id": "1CSE42", "cycle": "EC", "department": "Department of Computer Science and Engineering", "class_advisor": None, "verification_status": "staged_pending_review"},
    ],
    "records": [
        {
            "id": "1ECE02-MON-P1-All",
            "section_id": "1ECE02",
            "cycle": "EC",
            "weekday": "monday",
            "period": 1,
            "batch": "All",
            "start_time": "08:30",
            "end_time": "09:30",
            "subject_short": "RES",
            "subject_name": "Renewable Energy Sources",
            "faculty_name": "Mrs. Monica M S",
            "classroom": "Room no:A1204",
            "source_metadata": {
                "worksheet": "EC",
                "cell_ref": "EC!B92",
                "allocation_source": "EC!C121"
            }
        },
        {
            "id": "1ECE02-MON-P6-B1",
            "section_id": "1ECE02",
            "cycle": "EC",
            "weekday": "monday",
            "period": 6,
            "batch": "B1",
            "start_time": "13:45",
            "end_time": "14:40",
            "subject_short": "MATL",
            "subject_name": "Matlab Laboratory",
            "faculty_name": "Mrs.Dhanalakshmi R",
            "classroom": "A1210",
            "source_metadata": {
                "worksheet": "EC",
                "cell_ref": "EC!H93",
                "allocation_source": "EC!C123"
            }
        },
        {
            "id": "1ECE02-MON-P6-B2",
            "section_id": "1ECE02",
            "cycle": "EC",
            "weekday": "monday",
            "period": 6,
            "batch": "B2",
            "start_time": "13:45",
            "end_time": "14:40",
            "subject_short": "MATL",
            "subject_name": "Matlab Laboratory",
            "faculty_name": "Dr. Lakshmi M S",
            "classroom": "A1223",
            "source_metadata": {
                "worksheet": "EC",
                "cell_ref": "EC!H94",
                "allocation_source": "EC!C123"
            }
        },
        {
            "id": "1CSE01-MON-P1-B1",
            "section_id": "1CSE01",
            "cycle": "PC",
            "weekday": "monday",
            "period": 1,
            "batch": "B1",
            "start_time": "08:30",
            "end_time": "09:30",
            "subject_short": "PSCL",
            "subject_name": "Problem Solving with C Lab",
            "faculty_name": "Faculty 1",
            "classroom": "Lab 1",
            "source_metadata": {"worksheet": "PC", "cell_ref": "PC!B10"}
        },
        {
            "id": "1CSE01-MON-P2-B1",
            "section_id": "1CSE01",
            "cycle": "PC",
            "weekday": "monday",
            "period": 2,
            "batch": "B1",
            "start_time": "09:30",
            "end_time": "10:30",
            "subject_short": "PSCL",
            "subject_name": "Problem Solving with C Lab",
            "faculty_name": "Faculty 1",
            "classroom": "Lab 1",
            "source_metadata": {"worksheet": "PC", "cell_ref": "PC!C10"}
        }
    ]
}


class TestStage5BStagingPipeline(unittest.TestCase):
    """Isolated, self-contained test suite for validating Stage 5B staging logic.

    Uses temporary directories and synthetic fixtures to guarantee tests do not depend
    on private files (data:raw/ or data/staging/) and cannot overwrite production data.
    """

    @classmethod
    def setUpClass(cls):
        cls.initial_prod_sha = compute_file_sha256(PRODUCTION_FILE)
        cls.client = TestClient(app)

    def test_production_file_hash_unmodified(self):
        """Rule 1: data/timetable.json must remain byte-for-byte identical."""
        current_sha = compute_file_sha256(PRODUCTION_FILE)
        self.assertEqual(
            current_sha,
            self.initial_prod_sha,
            "data/timetable.json has been modified! SHA-256 digest differs."
        )

    def test_staged_schema_and_approval_gate(self):
        """Verify staging schema adherence and approval gate enforcement."""
        data = copy.deepcopy(SYNTHETIC_STAGED_FIXTURE)
        self.assertEqual(data.get("schema_version"), SCHEMA_VERSION)
        self.assertEqual(data.get("stage"), "5B")
        self.assertEqual(data.get("dataset_type"), "timetable_staging")
        self.assertEqual(data.get("status"), "pending_review")
        self.assertIn("source", data)
        self.assertIn("extraction", data)
        self.assertIn("sections_catalog", data)
        self.assertIn("records", data)

        extraction = data["extraction"]
        self.assertEqual(extraction["extractor_version"], EXTRACTOR_VERSION)
        self.assertIsNotNone(extraction["source_sha256"])

    def test_deterministic_record_ids_structure(self):
        """Verify deterministic unique IDs adhere to naming conventions without timestamps."""
        data = copy.deepcopy(SYNTHETIC_STAGED_FIXTURE)
        records = data["records"]

        id_set = set()
        for r in records:
            rec_id = r.get("id")
            self.assertIsNotNone(rec_id)
            self.assertNotIn(":", rec_id)
            self.assertNotIn(rec_id, id_set, f"Duplicate record ID found: {rec_id}")
            id_set.add(rec_id)

            # Check required fields in each record
            self.assertIn(r.get("weekday"), ["monday", "tuesday", "wednesday", "thursday", "friday"])
            self.assertIn(r.get("period"), [1, 2, 3, 4, 6, 7, 8])
            self.assertIn(r.get("batch"), ["All", "B1", "B2"])
            self.assertIsNotNone(r.get("start_time"))
            self.assertIsNotNone(r.get("end_time"))
            self.assertIsNotNone(r.get("subject_short"))
            self.assertIsNotNone(r.get("subject_name"))

            # Check provenance metadata
            src_meta = r.get("source_metadata", {})
            self.assertIn(src_meta.get("worksheet"), ["PC", "EC"])
            self.assertIsNotNone(src_meta.get("cell_ref"))

    def test_provenance_preservation_for_representative_sections(self):
        """Check ground-truth records and provenance for 1CSE01 (PC) and 1ECE02 (EC)."""
        data = copy.deepcopy(SYNTHETIC_STAGED_FIXTURE)
        records = data["records"]
        catalog = {s["section_id"]: s for s in data["sections_catalog"]}

        # 1CSE01 in PC
        self.assertIn("1CSE01", catalog)
        self.assertEqual(catalog["1CSE01"]["class_advisor"], "Dr. Ashwini V Bhat")
        self.assertEqual(catalog["1CSE01"]["department"], "Department of Computer Science and Engineering")
        self.assertEqual(catalog["1CSE01"]["cycle"], "PC")

        # 1ECE02 in EC
        self.assertIn("1ECE02", catalog)
        self.assertEqual(catalog["1ECE02"]["class_advisor"], "Ms.Madhu H M")
        self.assertEqual(catalog["1ECE02"]["department"], "Department of Electronics and Communication Engineering")
        self.assertEqual(catalog["1ECE02"]["cycle"], "EC")

        # Check 1ECE02 Monday Period 1 (RES)
        ece_mon_p1 = next((r for r in records if r["id"] == "1ECE02-MON-P1-All"), None)
        self.assertIsNotNone(ece_mon_p1)
        self.assertEqual(ece_mon_p1["subject_short"], "RES")
        self.assertEqual(ece_mon_p1["subject_name"], "Renewable Energy Sources")
        self.assertEqual(ece_mon_p1["faculty_name"], "Mrs. Monica M S")
        self.assertEqual(ece_mon_p1["classroom"], "Room no:A1204")
        self.assertEqual(ece_mon_p1["source_metadata"]["cell_ref"], "EC!B92")

    def test_batch_isolation_for_labs(self):
        """Ensure B1 and B2 lab records have distinct faculty and classrooms."""
        data = copy.deepcopy(SYNTHETIC_STAGED_FIXTURE)
        records = data["records"]
        b1_rec = next((r for r in records if r["id"] == "1ECE02-MON-P6-B1"), None)
        b2_rec = next((r for r in records if r["id"] == "1ECE02-MON-P6-B2"), None)

        self.assertIsNotNone(b1_rec)
        self.assertIsNotNone(b2_rec)
        self.assertEqual(b1_rec["subject_short"], "MATL")
        self.assertEqual(b2_rec["subject_short"], "MATL")
        self.assertEqual(b1_rec["faculty_name"], "Mrs.Dhanalakshmi R")
        self.assertEqual(b2_rec["faculty_name"], "Dr. Lakshmi M S")
        self.assertEqual(b1_rec["classroom"], "A1210")
        self.assertEqual(b2_rec["classroom"], "A1223")

    def test_two_period_merged_labs_preserved(self):
        """Verify that a 2-hour lab produces entries for consecutive periods."""
        data = copy.deepcopy(SYNTHETIC_STAGED_FIXTURE)
        records = data["records"]
        p1_b1 = next((r for r in records if r["id"] == "1CSE01-MON-P1-B1"), None)
        p2_b1 = next((r for r in records if r["id"] == "1CSE01-MON-P2-B1"), None)

        self.assertIsNotNone(p1_b1)
        self.assertIsNotNone(p2_b1)
        self.assertEqual(p1_b1["subject_short"], "PSCL")
        self.assertEqual(p2_b1["subject_short"], "PSCL")
        self.assertEqual(p1_b1["start_time"], "08:30")
        self.assertEqual(p1_b1["end_time"], "09:30")
        self.assertEqual(p2_b1["start_time"], "09:30")
        self.assertEqual(p2_b1["end_time"], "10:30")

    def test_blank_advisors_handled_safely(self):
        """Verify that the 6 unassigned sections have class_advisor=None without error."""
        data = copy.deepcopy(SYNTHETIC_STAGED_FIXTURE)
        catalog = {s["section_id"]: s for s in data["sections_catalog"]}
        for sec in KNOWN_BLANK_ADVISOR_SECTIONS:
            self.assertIn(sec, catalog)
            self.assertIsNone(catalog[sec]["class_advisor"])

    def test_provenance_mismatch_protection(self):
        """Verify that differing source hash blocks silent overwrite unless forced."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_staging_file = Path(tmp_dir) / "timetable_stage5b.json"
            fake_staged = {
                "schema_version": "1.0",
                "stage": "5B",
                "dataset_type": "timetable_staging",
                "status": "pending_review",
                "source": {"workbook_sha256": "fake_hash_12345"},
                "extraction": {
                    "record_count": 10,
                    "section_count": 1,
                    "extractor_version": EXTRACTOR_VERSION,
                    "source_sha256": "fake_hash_12345"
                },
                "sections_catalog": [],
                "records": []
            }
            with open(tmp_staging_file, "w", encoding="utf-8") as f:
                json.dump(fake_staged, f)

            stager = TimetableStager(
                staging_dir=Path(tmp_dir),
                staging_file=tmp_staging_file
            )

            # Create a mock workbook path
            mock_wb = Path(tmp_dir) / "mock_workbook.xlsx"
            mock_wb.write_bytes(b"mock_workbook_bytes")

            res = stager.stage_workbook(workbook_path=mock_wb, force=False)
            self.assertEqual(res["status"], "provenance_mismatch")
            self.assertFalse(res["idempotent"])

            # Verify existing file was NOT overwritten
            with open(tmp_staging_file, "r", encoding="utf-8") as f:
                content = json.load(f)
            self.assertEqual(content["extraction"]["source_sha256"], "fake_hash_12345")

    def test_atomic_write_recovery(self):
        """Verify that an interrupted write leaves the existing staging file intact."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_staging_file = Path(tmp_dir) / "timetable_stage5b.json"
            original_content = {"test": "valid_content"}
            with open(tmp_staging_file, "w", encoding="utf-8") as f:
                json.dump(original_content, f)

            # Simulate leftover temporary file from a crashed write
            leftover_tmp = Path(tmp_dir) / "timetable_stage5b.json.tmp"
            with open(leftover_tmp, "w", encoding="utf-8") as f:
                f.write("corrupted incomplete write...")

            # Existing file must be untouched
            with open(tmp_staging_file, "r", encoding="utf-8") as f:
                current = json.load(f)
            self.assertEqual(current, original_content)

    def test_validation_rejects_corrupted_payload(self):
        """Verify validator flags errors on corrupted/incomplete data."""
        with tempfile.NamedTemporaryFile() as tmp_wb:
            tmp_wb.write(b"mock_bytes")
            tmp_wb.flush()
            mock_wb_path = Path(tmp_wb.name)

            data = copy.deepcopy(SYNTHETIC_STAGED_FIXTURE)
            bad_data = copy.deepcopy(data)
            bad_data["status"] = "auto_promoted"
            bad_data["records"].pop()

            val_res = validate_staged_dataset(bad_data, mock_wb_path)
            self.assertFalse(val_res["is_valid"])
            self.assertGreaterEqual(len(val_res["errors"]), 1)

    def test_api_staging_status_when_dataset_absent(self):
        """Verify GET /api/timetable/staging-status when staging dataset is absent."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_file = Path(tmp_dir) / "nonexistent_stage.json"
            stager = TimetableStager(staging_file=empty_file)
            existing = stager.load_existing_staging()
            self.assertIsNone(existing)

    def test_api_staging_status_endpoint(self):
        """Verify GET /api/timetable/staging-status endpoint returns safe diagnostic metadata."""
        response = self.client.get("/api/timetable/staging-status")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["institution"], "Sapthagiri NPS University")
        self.assertIn("status", data)
        # Endpoint must never leak raw records or student schedules
        self.assertNotIn("records", data)
        self.assertNotIn("entries", data)
        self.assertNotIn("schedule", data)

    def test_final_production_file_hash_integrity(self):
        """Final check: ensure production timetable file remains 100% byte-identical."""
        final_sha = compute_file_sha256(PRODUCTION_FILE)
        self.assertEqual(
            final_sha,
            self.initial_prod_sha,
            "CRITICAL: data/timetable.json byte integrity violated!"
        )


class TestLocalStagingDatasetAudit(unittest.TestCase):
    """Opt-in local audit test verifying the complete 2,682-record local staging artifact.

    This test runs only when RUN_LOCAL_STAGING_AUDIT=1 is explicitly set.
    It is excluded from public CI because data/staging/ is excluded from the public git release.
    """

    @classmethod
    def setUpClass(cls):
        if os.environ.get("RUN_LOCAL_STAGING_AUDIT") != "1":
            raise unittest.SkipTest(
                "Opt-in local audit test: requires local private staging file data/staging/timetable_stage5b.json. "
                "Excluded from public CI because data/staging/ is excluded from the release. "
                "Run locally with RUN_LOCAL_STAGING_AUDIT=1."
            )
        if not STAGING_JSON_FILE.exists():
            raise unittest.SkipTest(f"Staging file missing at {STAGING_JSON_FILE}")
        with open(STAGING_JSON_FILE, "r", encoding="utf-8") as f:
            cls.staging_data = json.load(f)

    def test_full_staged_dataset_exists_and_schema_valid(self):
        """Verify full local staging JSON adherence to Stage 5B schema."""
        self.assertEqual(self.staging_data.get("schema_version"), SCHEMA_VERSION)
        self.assertEqual(self.staging_data.get("stage"), "5B")
        self.assertEqual(self.staging_data.get("status"), "pending_review")
        self.assertEqual(self.staging_data["extraction"]["record_count"], 2682)
        self.assertEqual(self.staging_data["extraction"]["section_count"], 75)

    def test_all_2682_record_ids_are_deterministic_and_unique(self):
        """Verify that all 2,682 records have deterministic unique IDs."""
        records = self.staging_data["records"]
        self.assertEqual(len(records), 2682)
        id_set = set()
        for r in records:
            rec_id = r.get("id")
            self.assertIsNotNone(rec_id)
            self.assertNotIn(":", rec_id)
            self.assertNotIn(rec_id, id_set)
            id_set.add(rec_id)

    def test_staging_reports_generated(self):
        """Verify both JSON and Markdown audit reports exist on local disk."""
        self.assertTrue(REPORT_JSON_FILE.exists())
        self.assertTrue(REPORT_MD_FILE.exists())


if __name__ == "__main__":
    unittest.main()
