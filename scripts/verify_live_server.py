"""Live server runner and endpoint probe script for RA NEXUS."""

import sys
import time
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app
from fastapi.testclient import TestClient


def main():
    print("[*] Initializing RA NEXUS FastAPI ASGI application test harness...")
    client = TestClient(app)

    endpoints_to_test = [
        ("GET", "/", "Home Web Portal", 200),
        ("GET", "/style.css", "Static Stylesheet", 200),
        ("GET", "/app.js", "Static JavaScript App", 200),
        ("GET", "/health", "Health Diagnostic", 200),
        ("GET", "/docs", "Swagger OpenAPI UI", 200),
        ("GET", "/openapi.json", "OpenAPI JSON Schema", 200),
        ("GET", "/api/campus/facilities", "Campus Facilities Directory", 200),
        ("GET", "/api/timetable/sections", "Timetable Sections Catalog", 200),
        ("GET", "/api/timetable/subjects?section=1ECE02", "Section 1ECE02 Subjects", 200),
        ("GET", "/api/timetable/schedule?section=1ECE02", "Section 1ECE02 Schedule", 200),
        ("GET", "/api/timetable/next-class?section=1ECE02&client_time=2026-10-12T10:15:00", "Next Class Query", 200),
        (
            "POST",
            "/chat",
            "Full Context Chat",
            200,
            {
                "message": "Where is the library located?",
                "student_context": {"branch": "ECE", "section": "1ECE02"},
                "client_time": "2026-10-12T10:15:00"
            }
        ),
        (
            "POST",
            "/chat",
            "Safe Calculator Chat",
            200,
            {"message": "Calculate 75 * 4 + 10"}
        ),
        (
            "POST",
            "/chat",
            "Legacy String Chat",
            200,
            {"message": "What is the electronics laboratory equipment?"}
        ),
        (
            "GET",
            "/api/timetable/subjects?section=NONEXISTENT_SEC",
            "Invalid Section Rejection (404)",
            404
        ),
        (
            "GET",
            "/api/timetable/subjects?section=1ECE02&branch=CSE",
            "Branch Mismatch Rejection (400)",
            400
        ),
    ]

    print("\n" + "=" * 70)
    print("RA NEXUS LIVE SERVER ENDPOINT VALIDATION REPORT")
    print("=" * 70)

    all_passed = True

    for item in endpoints_to_test:
        method = item[0]
        url = item[1]
        desc = item[2]
        expected_code = item[3]
        payload = item[4] if len(item) > 4 else None

        start = time.perf_counter()
        if method == "GET":
            resp = client.get(url)
        else:
            resp = client.post(url, json=payload)
        elapsed_ms = (time.perf_counter() - start) * 1000

        passed = (resp.status_code == expected_code)
        if not passed:
            all_passed = False

        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {method:4} {url:45} -> {resp.status_code} (expected {expected_code}) in {elapsed_ms:5.1f}ms | {desc}")

        # Specific assertion checks
        if url == "/" and passed:
            assert "Sapthagiri NPS University" in resp.text, "Branding missing in HTML"
            assert "RA NEXUS" in resp.text, "Title missing in HTML"
        elif url == "/health" and passed:
            data = resp.json()
            assert data.get("status") == "online", "Server status not online"
            assert data.get("institution") == "Sapthagiri NPS University"
        elif url == "/api/campus/facilities" and passed:
            data = resp.json()
            assert data.get("count", 0) >= 3, "Missing facilities"
        elif url == "/api/timetable/sections" and passed:
            data = resp.json()
            assert any(s["section_id"] == "1ECE02" for s in data.get("sections", [])), "1ECE02 not cataloged"

    print("=" * 70)
    if all_passed:
        print(f"[SUCCESS] All {len(endpoints_to_test)} live server endpoints validated successfully!")
    else:
        print(f"[FAILURE] One or more endpoints failed validation.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
