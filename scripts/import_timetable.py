"""Command-line utility for staging, inspecting, diffing, and approving timetable imports.

Usage:
  python scripts/import_timetable.py stage --json <records.json> --branch ECE --section 1ECE02 --source "Official_ECE.pdf" --date 2026-02-01
  python scripts/import_timetable.py inspect --stage-id <stage_id>
  python scripts/import_timetable.py diff --stage-id <stage_id>
  python scripts/import_timetable.py approve --stage-id <stage_id> --confirm
"""

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.timetable_importer import TimetableImporter


def main():
    parser = argparse.ArgumentParser(description="Sapthagiri NPS University Timetable Import Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: stage
    stage_parser = subparsers.add_parser("stage", help="Stage an extracted timetable batch for review")
    stage_parser.add_argument("--json", required=True, help="Path to JSON file containing extracted records")
    stage_parser.add_argument("--branch", required=True, help="Academic branch code (e.g. ECE, CSE)")
    stage_parser.add_argument("--section", required=True, help="Section ID (e.g. 1ECE02)")
    stage_parser.add_argument("--source", required=True, help="Source document name/filename")
    stage_parser.add_argument("--date", required=True, help="Effective date (YYYY-MM-DD)")
    stage_parser.add_argument("--semester", type=int, default=None, help="Academic semester (1-8)")
    stage_parser.add_argument("--notes", default=None, help="Optional administrative notes")

    # Subcommand: inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a staged import batch")
    inspect_parser.add_argument("--stage-id", required=True, help="Stage ID to inspect")

    # Subcommand: diff
    diff_parser = subparsers.add_parser("diff", help="Diff staged batch against live production dataset")
    diff_parser.add_argument("--stage-id", required=True, help="Stage ID to compare")

    # Subcommand: approve
    approve_parser = subparsers.add_parser("approve", help="Apply staged verified records to production")
    approve_parser.add_argument("--stage-id", required=True, help="Stage ID to merge")
    approve_parser.add_argument("--confirm", action="store_true", help="Explicit confirmation flag")

    args = parser.parse_args()
    importer = TimetableImporter()

    if args.command == "stage":
        with open(args.json, "r", encoding="utf-8") as f:
            records = json.load(f)
        if not isinstance(records, list):
            print("Error: Input JSON must contain a list of timetable entry objects.")
            sys.exit(1)

        res = importer.stage_records(
            source_document=args.source,
            effective_date=args.date,
            branch=args.branch,
            semester=args.semester,
            section=args.section,
            records=records,
            notes=args.notes
        )
        print("\n" + "=" * 60)
        print("TIMETABLE BATCH STAGED SUCCESSFULLY")
        print("=" * 60)
        print(f"Stage ID:             {res['stage_id']}")
        print(f"Staged File:          {res['filepath']}")
        print(f"Section:              {res['section']} ({res['branch']})")
        print(f"Total Records:        {res['total_records']}")
        print(f"Verified & Ready:     {res['verified_ready']}")
        print(f"Quarantined / Review: {res['quarantined_uncertain']}")
        if res['has_quarantined']:
            print("\n[!] Attention: Some records were quarantined due to low confidence or collisions.")
            print(f"    Run: python scripts/import_timetable.py inspect --stage-id {res['stage_id']}")

    elif args.command == "inspect":
        data = importer.inspect_stage(args.stage_id)
        print("\n" + "=" * 60)
        print(f"STAGE DETAILS: {args.stage_id}")
        print("=" * 60)
        print(f"Source Document:  {data['source_document']}")
        print(f"Effective Date:   {data['effective_date']}")
        print(f"Status:           {data['status']}")
        print(f"Verified Records: {data['counts']['verified_ready']}")
        print(f"Quarantined:      {data['counts']['quarantined_uncertain']}")

        if data['quarantined_entries']:
            print("\nQUARANTINED ENTRIES REQUIRING REVIEW:")
            for q in data['quarantined_entries']:
                print(f"- Entry ID: {q.get('id')} ({q.get('weekday')} P{q.get('period')})")
                for r in q.get('quarantine_reasons', []):
                    print(f"    * {r}")

    elif args.command == "diff":
        diff = importer.generate_diff(args.stage_id)
        print("\n" + "=" * 60)
        print(f"DIFF PREVIEW: {args.stage_id}")
        print("=" * 60)
        print(f"Target Section:          {diff['section']} ({diff['branch']})")
        print(f"Is New Section:          {diff['is_new_section']}")
        print(f"Existing Live Records:   {diff['existing_entries_count']}")
        print(f"Staged Verified Records: {diff['staged_verified_count']}")
        print(f"Staged Quarantined:      {diff['staged_quarantined_count']}")
        print(f"Will Overwrite Existing: {diff['will_replace_existing']}")

    elif args.command == "approve":
        try:
            res = importer.apply_stage(args.stage_id, confirm=args.confirm)
            print("\n" + "=" * 60)
            print("STAGE MERGED TO PRODUCTION SUCCESSFULLY")
            print("=" * 60)
            print(f"Stage ID:             {res['stage_id']}")
            print(f"Section:              {res['section']}")
            print(f"Records Merged:       {res['records_applied']}")
            print(f"Quarantined Retained: {res['quarantined_retained']}")
            print(f"Automated Backup:     {res['backup_file']}")
            print(f"Production File:      {res['production_file']}")
        except PermissionError as err:
            print(f"\n[ERROR] {err}")
            print("To approve and apply this import, re-run with --confirm.")
            sys.exit(1)


if __name__ == "__main__":
    main()
