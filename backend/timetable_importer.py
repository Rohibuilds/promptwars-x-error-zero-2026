"""Staging, validation, and conflict-detection pipeline for official university timetables.

Designed for Sapthagiri NPS University to import official timetables provided
as spreadsheets, documents, or OCR extracts with strict validation, collision
detection, and an approval gate before modifying production records.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple

from .timetable_engine import (
    VALID_WEEKDAYS,
    clear_timetable_cache,
    load_timetable_data,
    validate_timetable_entry,
)

logger = logging.getLogger("ra_nexus.importer")

DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_TIMETABLE_FILE = DATA_DIR / "timetable.json"
DEFAULT_STAGING_DIR = DATA_DIR / "staging"
DEFAULT_BACKUP_DIR = DATA_DIR / "backups"


class TimetableImporter:
    """Manages the staging, integrity validation, and approved ingestion of timetable records."""

    def __init__(
        self,
        timetable_file: Optional[Path] = None,
        staging_dir: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
    ):
        self.timetable_file = Path(timetable_file) if timetable_file else DEFAULT_TIMETABLE_FILE
        self.staging_dir = Path(staging_dir) if staging_dir else DEFAULT_STAGING_DIR
        self.backup_dir = Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR

        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def stage_records(
        self,
        source_document: str,
        effective_date: str,
        branch: str,
        semester: Optional[int],
        section: str,
        records: List[Dict[str, Any]],
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Stages extracted timetable records, evaluates data integrity, and quarantines uncertain items.

        Args:
            source_document: Original document name or filename (e.g. 'Official_ECE_Timetable_Sem2_2026.pdf').
            effective_date: Date from which the timetable takes effect (YYYY-MM-DD).
            branch: Academic department code (e.g. 'ECE', 'CSE').
            semester: Academic semester number (1-8) or None.
            section: Section ID (e.g. '1ECE02').
            records: List of timetable period dictionaries.
            notes: Optional administrative notes.

        Returns:
            Dict[str, Any]: Staging report including stage_id, valid count, and quarantined count.
        """
        normalized_branch = str(branch).strip().upper()
        normalized_section = str(section).strip().upper()
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        stage_id = f"stage_{timestamp_str}_{normalized_branch}_{normalized_section}"

        staged_verified: List[Dict[str, Any]] = []
        quarantined: List[Dict[str, Any]] = []

        # Tracking for internal collision detection within this batch
        period_slots: Dict[Tuple[str, int, str], Dict[str, Any]] = {}  # (weekday, period, batch) -> record
        room_slots: Dict[Tuple[str, int, str], Dict[str, Any]] = {}    # (weekday, period, classroom) -> record
        faculty_slots: Dict[Tuple[str, int, str], Dict[str, Any]] = {} # (weekday, period, faculty) -> record

        for idx, raw in enumerate(records):
            quarantine_reasons: List[str] = []

            # 1. Normalize fields
            entry_id = raw.get("id") or f"{normalized_section}-{timestamp_str}-{idx+1:03d}"
            weekday_val = raw.get("weekday")
            weekday = str(weekday_val).strip().lower() if weekday_val else None

            period_val = raw.get("period")
            period = None
            if period_val is not None:
                try:
                    period = int(period_val)
                except (ValueError, TypeError):
                    quarantine_reasons.append(f"Invalid non-integer period value: {period_val}")

            start_time = str(raw.get("start_time")).strip() if raw.get("start_time") else None
            end_time = str(raw.get("end_time")).strip() if raw.get("end_time") else None
            subject_code = str(raw.get("subject_code")).strip() if raw.get("subject_code") else None
            subject_name = str(raw.get("subject_name")).strip() if raw.get("subject_name") else None
            faculty_name = str(raw.get("faculty_name")).strip() if raw.get("faculty_name") else None
            classroom = str(raw.get("classroom")).strip() if raw.get("classroom") else None
            batch = str(raw.get("batch")).strip() if raw.get("batch") else "All"

            confidence = float(raw.get("confidence", 1.0))
            if confidence < 0.90:
                quarantine_reasons.append(f"Low OCR/extraction confidence ({confidence:.2f} < 0.90)")

            normalized_entry = {
                "id": entry_id,
                "academic_year": raw.get("academic_year"),
                "branch": normalized_branch,
                "semester": semester,
                "section": normalized_section,
                "subject_code": subject_code,
                "subject_name": subject_name,
                "faculty_name": faculty_name,
                "weekday": weekday,
                "period": period,
                "start_time": start_time,
                "end_time": end_time,
                "classroom": classroom,
                "batch": batch,
                "effective_date": effective_date,
                "source_metadata": {
                    "source_document": source_document,
                    "effective_date": effective_date,
                    "staged_at": datetime.now().isoformat(),
                    "extraction_confidence": confidence,
                    "notes": notes or raw.get("notes")
                }
            }

            # 2. Schema validation
            is_valid, err_reason = validate_timetable_entry(normalized_entry)
            if not is_valid:
                quarantine_reasons.append(f"Schema validation failure: {err_reason}")

            # 3. Collision / Conflict detection
            if weekday and period:
                # A. Section period collision
                slot_key = (weekday, period, batch)
                if slot_key in period_slots:
                    prev = period_slots[slot_key]
                    quarantine_reasons.append(
                        f"Period collision: overlaps with existing entry '{prev.get('subject_name')}' on {weekday} period {period} (batch {batch})"
                    )
                else:
                    period_slots[slot_key] = normalized_entry

                # B. Classroom collision
                if classroom:
                    room_key = (weekday, period, classroom.lower())
                    if room_key in room_slots:
                        prev = room_slots[room_key]
                        quarantine_reasons.append(
                            f"Classroom collision: room '{classroom}' already booked on {weekday} period {period} by '{prev.get('subject_name')}'"
                        )
                    else:
                        room_slots[room_key] = normalized_entry

                # C. Faculty collision
                if faculty_name:
                    fac_key = (weekday, period, faculty_name.lower())
                    if fac_key in faculty_slots:
                        prev = faculty_slots[fac_key]
                        quarantine_reasons.append(
                            f"Faculty collision: faculty '{faculty_name}' already scheduled on {weekday} period {period} for '{prev.get('subject_name')}'"
                        )
                    else:
                        faculty_slots[fac_key] = normalized_entry

            # 4. Routing to Staged vs Quarantine
            if quarantine_reasons:
                normalized_entry["verification_status"] = "quarantined"
                normalized_entry["quarantine_reasons"] = quarantine_reasons
                quarantined.append(normalized_entry)
            else:
                normalized_entry["verification_status"] = "staged_verified"
                staged_verified.append(normalized_entry)

        stage_payload = {
            "stage_id": stage_id,
            "institution": "Sapthagiri NPS University",
            "branch": normalized_branch,
            "semester": semester,
            "section": normalized_section,
            "effective_date": effective_date,
            "source_document": source_document,
            "staged_at": datetime.now().isoformat(),
            "status": "pending_approval",
            "counts": {
                "total_records": len(records),
                "verified_ready": len(staged_verified),
                "quarantined_uncertain": len(quarantined),
            },
            "verified_entries": staged_verified,
            "quarantined_entries": quarantined,
        }

        stage_filepath = self.staging_dir / f"{stage_id}.json"
        with open(stage_filepath, "w", encoding="utf-8") as f:
            json.dump(stage_payload, f, indent=2)

        return {
            "stage_id": stage_id,
            "filepath": str(stage_filepath),
            "branch": normalized_branch,
            "section": normalized_section,
            "total_records": len(records),
            "verified_ready": len(staged_verified),
            "quarantined_uncertain": len(quarantined),
            "has_quarantined": len(quarantined) > 0,
        }

    def inspect_stage(self, stage_id: str) -> Dict[str, Any]:
        """Loads and returns details of a staged import batch."""
        filepath = self.staging_dir / f"{stage_id}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Staged import batch '{stage_id}' not found.")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_diff(self, stage_id: str) -> Dict[str, Any]:
        """Compares staged verified records against live production records."""
        staged_data = self.inspect_stage(stage_id)
        section = staged_data["section"]
        verified_staged = staged_data["verified_entries"]

        live_data = load_timetable_data(str(self.timetable_file))
        existing_catalog = live_data.get("sections_catalog", [])
        existing_entries = live_data.get("entries", [])

        is_new_section = not any(s.get("section_id") == section for s in existing_catalog)
        existing_section_entries = [e for e in existing_entries if e.get("section") == section]

        return {
            "stage_id": stage_id,
            "section": section,
            "branch": staged_data["branch"],
            "is_new_section": is_new_section,
            "existing_entries_count": len(existing_section_entries),
            "staged_verified_count": len(verified_staged),
            "staged_quarantined_count": len(staged_data.get("quarantined_entries", [])),
            "will_replace_existing": len(existing_section_entries) > 0,
        }

    def apply_stage(self, stage_id: str, confirm: bool = False) -> Dict[str, Any]:
        """Merges verified staged records into production after explicit confirmation and automated backup.

        Args:
            stage_id: Batch ID to merge.
            confirm: Must be explicitly True to prevent accidental overwrites.

        Returns:
            Dict[str, Any]: Merge completion summary and backup file location.
        """
        if not confirm:
            raise PermissionError(
                "Explicit confirmation (confirm=True) is required to apply staged timetables to production."
            )

        staged_data = self.inspect_stage(stage_id)
        section = staged_data["section"]
        branch = staged_data["branch"]
        semester = staged_data.get("semester")
        effective_date = staged_data.get("effective_date")
        source_document = staged_data.get("source_document")
        verified_entries = staged_data.get("verified_entries", [])

        if not verified_entries:
            raise ValueError("No verified records to apply. All staged records were quarantined.")

        # 1. Create timestamped automated backup of live dataset
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"timetable_backup_{timestamp_str}.json"
        if self.timetable_file.exists():
            shutil.copy2(self.timetable_file, backup_file)
        else:
            live_empty = {
                "institution": "Sapthagiri NPS University",
                "version": "1.0.0",
                "sections_catalog": [],
                "entries": []
            }
            with open(self.timetable_file, "w", encoding="utf-8") as f:
                json.dump(live_empty, f, indent=2)

        # 2. Load live data
        with open(self.timetable_file, "r", encoding="utf-8") as f:
            live = json.load(f)

        # 3. Update section catalog
        catalog = live.get("sections_catalog", [])
        section_item = next((s for s in catalog if s.get("section_id") == section), None)
        if not section_item:
            section_item = {
                "section_id": section,
                "branch": branch,
                "branch_name": branch,
                "semester": semester,
                "effective_date": effective_date,
                "source_document": source_document,
                "verification_status": "verified",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
            }
            catalog.append(section_item)
        else:
            section_item["verification_status"] = "verified"
            section_item["effective_date"] = effective_date
            section_item["source_document"] = source_document
            section_item["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        live["sections_catalog"] = catalog

        # 4. Replace section entries with newly verified entries
        entries = live.get("entries", [])
        entries = [e for e in entries if e.get("section") != section]
        for e in verified_entries:
            # Change status from staged_verified to verified in production
            entry_copy = dict(e)
            entry_copy["verification_status"] = "verified"
            entries.append(entry_copy)

        live["entries"] = entries
        live["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        # 5. Atomic write back to production
        temp_target = self.timetable_file.with_suffix(".tmp")
        with open(temp_target, "w", encoding="utf-8") as f:
            json.dump(live, f, indent=2)
        temp_target.replace(self.timetable_file)

        # 6. Mark stage as applied
        staged_data["status"] = "applied"
        staged_data["applied_at"] = datetime.now().isoformat()
        stage_file = self.staging_dir / f"{stage_id}.json"
        with open(stage_file, "w", encoding="utf-8") as f:
            json.dump(staged_data, f, indent=2)

        # 7. Clear in-memory caches
        clear_timetable_cache()

        return {
            "status": "success",
            "stage_id": stage_id,
            "section": section,
            "records_applied": len(verified_entries),
            "quarantined_retained": len(staged_data.get("quarantined_entries", [])),
            "backup_file": str(backup_file),
            "production_file": str(self.timetable_file),
        }
