#!/usr/bin/env python3
"""CLI utility for Stage 5B Isolated Timetable Staging and Audit.

Usage:
  python scripts/stage_timetable.py run [--force]
  python scripts/stage_timetable.py status
  python scripts/stage_timetable.py validate
"""

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.timetable_staging import (
    TimetableStager,
    get_staging_status,
    resolve_workbook_path,
    validate_staged_dataset,
)


def main():
    parser = argparse.ArgumentParser(description="RA NEXUS Stage 5B Timetable Staging Pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run full isolated staging of the official workbook")
    run_parser.add_argument("--force", action="store_true", help="Force re-staging if provenance differs")

    subparsers.add_parser("status", help="Check read-only staging status")
    subparsers.add_parser("validate", help="Validate current staged dataset against the source workbook")

    args = parser.parse_args()
    stager = TimetableStager()

    if args.command == "run":
        res = stager.stage_workbook(force=args.force)
        print("\n" + "=" * 70)
        print("STAGE 5B EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Status:             {res['status']}")
        print(f"Idempotent Run:     {res['idempotent']}")
        print(f"Source SHA-256:     {res.get('source_sha256')}")
        print(f"Total Sections:     {res.get('section_count')}")
        print(f"Total Staged:       {res.get('record_count')}")
        print(f"Staging File:       {res.get('staging_file')}")
        if res.get("report_json_file"):
            print(f"Report JSON:        {res.get('report_json_file')}")
            print(f"Report Markdown:    {res.get('report_md_file')}")
        print("=" * 70)

    elif args.command == "status":
        status_data = get_staging_status()
        print("\n" + "=" * 70)
        print("STAGE 5B STAGING STATUS")
        print("=" * 70)
        print(json.dumps(status_data, indent=2))
        print("=" * 70)

    elif args.command == "validate":
        existing = stager.load_existing_staging()
        if not existing:
            print("Error: No staged dataset found. Run 'python scripts/stage_timetable.py run' first.")
            sys.exit(1)
        wb_path = resolve_workbook_path()
        val_res = validate_staged_dataset(existing, wb_path)
        print("\n" + "=" * 70)
        print("STAGE 5B DATASET VALIDATION")
        print("=" * 70)
        print(f"Is Valid: {val_res['is_valid']}")
        print(f"Checks Passed ({len(val_res['checks_passed'])}):")
        for chk in val_res['checks_passed']:
            print(f"  [x] {chk}")
        if val_res['warnings']:
            print(f"Warnings ({len(val_res['warnings'])}):")
            for w in val_res['warnings']:
                print(f"  [!] {w}")
        if val_res['errors']:
            print(f"Errors ({len(val_res['errors'])}):")
            for e in val_res['errors']:
                print(f"  [ERROR] {e}")
            sys.exit(1)
        print("=" * 70)


if __name__ == "__main__":
    main()
