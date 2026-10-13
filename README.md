# RA NEXUS

**Brand: RA TECH &bull; Academic Services Portal for Sapthagiri NPS University**

RA NEXUS is an enterprise-grade autonomous academic assistant and timetable portal engineered by **RA TECH** for Sapthagiri NPS University. Built with zero paid external API dependencies, it integrates rule-based intent recognition, deterministic timetable lookup with strict section isolation, in-memory cached campus knowledge retrieval, an AST-based safe arithmetic evaluator, an isolated timetable staging pipeline, and a high-performance web portal.

---

## Features

- **Rule-Based Autonomous Agent**: Deterministic intent recognition routing user requests across system diagnostics, timetable lookups, campus facilities, arithmetic, and general assistance.
- **Deterministic Timetable Engine**: Queries class schedules, subject details, faculty, and classrooms with strict section isolation (currently initialized with verified ECE section 1ECE02 dataset). Never leaks one section's timetable to another section and prompts for missing branch/section context.
- **In-Memory Cached Knowledge Search**: Fast campus knowledge search cached via `@lru_cache(maxsize=1)` to avoid repeated disk reads.
- **Safe Calculator**: AST-based arithmetic evaluation with strict token and node complexity boundaries, preventing arbitrary code execution.
- **System Diagnostics**: Real-time status inspection reporting engine version, university status, and loaded tool capabilities.
- **Hardened Web Security**:
  - Strict Content Security Policy (`default-src 'self'`) with no `'unsafe-inline'` directives.
  - MIME-sniffing protection (`X-Content-Type-Options: nosniff`).
  - Clickjacking protection (`X-Frame-Options: DENY`).
  - Sliding-window rate limiting (60 requests/minute on `/chat`).
  - Configurable CORS with no wildcard credentials.
  - Safe error handling preventing Python tracebacks from leaking to clients.
- **Professional University Portal Interface**:
  - High-trust Sapthagiri NPS University identity and deep navy/slate design system with WCAG AAA compliant contrast.
  - 5 core workspace modules: Home Dashboard, Timetable Center, Campus & Classroom Directory, AI Assistant Chat, and Student Academic Profile.
  - Dedicated ARIA live region (`#liveAnnouncer`) for screen readers announcing new responses without reading prior history.
  - Keyboard skip-link jumping past navigation directly to main content.
  - Visible focus indicators (`outline: 2px solid var(--border-focus)`).
  - Responsive layout for mobile (drawer navigation), tablet, and desktop viewports.
- **Automated Test Suite**: 86 automated unit, integration, and frontend contract tests covering timetable resolution, section and batch isolation, next-class safety, timetable import staging and collision quarantine, REST timetable and facilities endpoints, frontend CSP compliance, DOM contract adherence, AST calculator safety, input validation, rate limiting, CORS, and security headers.

---

## Architecture Overview

```
Frontend (HTML5 / CSS / Vanilla JS)
        │
        ▼ HTTP GET /, GET /health, POST /chat
FastAPI Application (ASGI Middleware Pipeline)
        ├─ CORSMiddleware (Configurable ALLOWED_ORIGINS)
        ├─ RateLimitMiddleware (60 req/min per IP, In-Memory)
        ├─ SecurityHeadersMiddleware (CSP, nosniff, DENY)
        └─ GZipMiddleware (Threshold: 1000 bytes)
        │
        ▼
Autonomous Agent Router (backend.agent.run_agent)
        ├─ System Status    ─► get_system_status()
        ├─ Timetable Engine ─► query_timetable() (backend.timetable_engine)
        ├─ Calculator       ─► calculate() (AST-based safe evaluator)
        ├─ Knowledge Base   ─► search_knowledge() (Cached @lru_cache)
        └─ Chat Fallback    ─► Structured guidance response
```

For a detailed technical breakdown of components, request flow, and security boundaries, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Requirements

- **Python**: 3.9 or higher (tested on Python 3.9.6 and 3.11)
- **External Keys**: **None required**. RA NEXUS runs entirely locally with zero external API dependencies or cloud accounts.

---

## Local Setup & Quickstart

### 1. Clone the Repository

```bash
git clone https://github.com/Rohibuilds/promptwars-x-error-zero-2026.git
cd promptwars-x-error-zero-2026
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Application

Run the server from the repository root:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The unified service will be live at:
- **Interactive Web Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **API Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 5. (Optional) Decoupled Frontend Development Setup

If running the frontend independently on a separate web server (e.g. port 5500):

```bash
python3 -m http.server 5500 --directory frontend
```

To configure permitted CORS origins, set the `ALLOWED_ORIGINS` environment variable:

```bash
export ALLOWED_ORIGINS="http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:8000,http://localhost:8000"
uvicorn backend.main:app --reload
```

---

## API Endpoints

### `GET /`
Serves the accessible static dashboard interface.

### `GET /health`
Returns operational health status, university identity, and engine version:
```json
{
  "name": "RA NEXUS",
  "institution": "Sapthagiri NPS University",
  "version": "0.1.0",
  "status": "online"
}
```

### `GET /api/timetable/sections`
Retrieves registered university sections with optional branch and semester filtering:
```http
GET /api/timetable/sections?branch=ECE
```
```json
{
  "institution": "Sapthagiri NPS University",
  "count": 1,
  "sections": [
    {
      "section_id": "1ECE02",
      "branch": "ECE",
      "branch_name": "Electronics and Communication Engineering",
      "academic_year": null,
      "semester": null,
      "verification_status": "partial_verified",
      "source_document": "Department Initial Submission (Provisional)"
    }
  ]
}
```

### `GET /api/timetable/subjects`
Retrieves course subjects, faculty, and room allocations for a registered section:
```http
GET /api/timetable/subjects?section=1ECE02
```
```json
{
  "institution": "Sapthagiri NPS University",
  "section": "1ECE02",
  "status": "schedule_pending",
  "subjects": [],
  "message": "Subject details for section 1ECE02 are pending official publication."
}
```

### `GET /api/timetable/schedule`
Retrieves class schedule entries for a section with optional weekday, period, and batch filters:
```http
GET /api/timetable/schedule?section=1ECE02&weekday=monday
```

### `GET /api/timetable/next-class`
Deterministically queries current and upcoming classes given client timestamp and optional laboratory batch:
```http
GET /api/timetable/next-class?section=1ECE02&client_time=2026-10-12T10:15:00
```
```json
{
  "institution": "Sapthagiri NPS University",
  "type": "timetable",
  "status": "schedule_pending",
  "can_determine": false,
  "section": "1ECE02",
  "missing_information": [
    "verified_period_timings",
    "weekday_class_schedule"
  ],
  "response": "Section 1ECE02 has not yet published verified period timings and weekday class schedules. Current and next class cannot be inferred from partial data."
}
```

### `GET /api/campus/facilities`
Retrieves verified campus facilities, laboratories, and operating hours:
```http
GET /api/campus/facilities
```
```json
{
  "institution": "Sapthagiri NPS University",
  "count": 3,
  "facilities": [
    {
      "id": "FAC-001",
      "category": "laboratory",
      "title": "Electronics Laboratory",
      "location": "Block A, First Floor",
      "equipment": ["Oscilloscope", "Digital Multimeter"],
      "verification_status": "verified"
    }
  ]
}
```

### `GET /api/timetable/staging-status`
Retrieves real-time telemetry from the Stage 5B isolated workbook extractor and staging pipeline:
```http
GET /api/timetable/staging-status
```
```json
{
  "institution": "Sapthagiri NPS University",
  "status": "pending_review",
  "stage": "5B",
  "record_count": 2682,
  "section_count": 75,
  "extractor_version": "1.0.0-stage5b",
  "source_sha256": "072c23cfedf6c1428fb80bfcb572386ebb1d5d80a93e70ef40a9e1ef182b296c",
  "generated_at": "2026-10-13T17:37:34.914628+00:00",
  "approval_gate": "pending_human_review",
  "production_unaffected": true
}
```

### `POST /chat`
Accepts a natural language prompt with optional student profile context:

**Request Body (Full Context):**
```json
{
  "message": "Where is my next class?",
  "student_context": {
    "branch": "ECE",
    "academic_year": 1,
    "semester": 2,
    "section": "1ECE02",
    "batch": "Batch A"
  },
  "client_time": "2026-10-12T10:15:00"
}
```

**Backward Compatible Legacy Request Body:**
```json
{
  "message": "Where is the computer laboratory located?"
}
```

---

## Running the Automated Test Suite

Tests use Python's built-in `unittest` framework and are fully compatible with `pytest`:

### Using `unittest` (Zero Extra Dependencies):
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Using `pytest`:
```bash
pytest -v
```

**Test Coverage Areas:**
- `tests/test_timetable_importer.py`: Official timetable staging, extraction confidence verification, collision detection (period, classroom, faculty overlaps), quarantine routing, dry-run diff preview, automated backups, and permission-gated merge enforcement.
- `tests/test_frontend.py`: Frontend static asset serving, strict CSP compliance (zero inline scripts, styles, or handlers), DOM ID coherence between `app.js` and `index.html`, accessibility landmarks, skip link, live announcer, quick query validity, and directory structure.
- `tests/test_timetable.py`: Deterministic schedule lookups, section isolation, missing context prompts, partial schedule handling, schema validation, and calculator vs campus query disambiguation.
- `tests/test_stage2_api.py`: Stage 2 timetable REST endpoints (`/api/timetable/sections`, `/api/timetable/subjects`, `/api/timetable/schedule`, `/api/timetable/next-class`), student context validation, query parameter filtering, section & batch isolation, backward compatibility, and next-class safety with incomplete data.
- `tests/test_agent.py`: Intent routing across system status, timetable, knowledge, and safe calculation; expression sanitization; formatting.
- `tests/test_tools.py`: Arithmetic correctness, order of operations, AST limits, modulo, unary operators, division-by-zero rejection, code-injection rejection, knowledge cache hit/miss behavior.
- `tests/test_api.py`: Endpoint availability, campus facilities retrieval, student_context payload integration, Pydantic validation (empty strings, whitespace, missing fields, length limits), CORS origin rejection, strict CSP validation, and rate limiter isolation.

---

## Timetable Data Staging & Ingestion Pipeline

To incorporate official university timetables provided as PDFs, spreadsheets, or documents without risking data corruption or silent overwrites, RA NEXUS uses an isolated multi-stage ingestion workflow (`backend/timetable_importer.py` and `scripts/import_timetable.py`):

1. **Staging (`stage`)**:
   - Parses incoming records while preserving the original source document filename (`source_document`), effective date (`effective_date`), and administrative notes.
   - Evaluates schema conformance via `validate_timetable_entry()`.
   - Runs automatic collision checks for section periods, classroom double-bookings, and faculty scheduling overlaps.
   - Flags low-confidence extraction rows (< 0.90) or collisions into a **quarantine batch** (`data/staging/<stage_id>.json`).
2. **Inspection & Review (`inspect`)**:
   - Lists all staged records, quarantined anomalies, and exact review rationales.
   - Quarantined records are never published as verified automatically.
3. **Diff Preview (`diff`)**:
   - Performs a dry-run comparison against the live repository (`data/timetable.json`) to inspect which sections will be added, replaced, or preserved.
4. **Approval-Gated Merge (`approve`)**:
   - Creates a timestamped automated backup in `data/backups/timetable_backup_<timestamp>.json`.
   - Requires the explicit `--confirm` flag to execute.
   - Atomically updates production records and immediately clears in-memory caches.

---

## Security & Operational Limitations

1. **Rule-Based Routing & Partial Timetable Coverage**: The assistant uses deterministic rule-based matching. Currently, verified initial timetable information is only cataloged for ECE section 1ECE02 (provisional registration); full university-wide timetables across all branches and sections will be incorporated as official datasets are released and validated.
2. **In-Memory Rate Limiting**: The sliding-window rate limiter stores timestamps in local process memory (`RATE_LIMIT_RECORDS`). Counters are not shared across multiple worker processes or multi-server clusters. Multi-worker scaling requires backing with an external data store such as Redis.
3. **Static Knowledge Base**: Campus facilities are loaded from `data/knowledge.json`. Modifying records requires editing the file and restarting the application or refreshing the cache.

---

## Public Deployment Preparation Guide

Before transitioning RA NEXUS from a local development environment to an institutional public deployment, adhere to the following architecture and operational safeguards:

### 1. Hosting Architecture & Process Management
- **Reverse Proxy**: Place a hardened reverse proxy (Nginx or Caddy) in front of Uvicorn to handle TLS termination, HTTP/2 or HTTP/3, and slowloris mitigation.
- **Process Supervision**: Run Uvicorn via `systemd` or as a containerized workload (e.g., Docker / Google Cloud Run):
  ```bash
  gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
  ```
- **Distributed Rate Limiting**: If scaling to multiple Uvicorn workers or cluster nodes, replace the in-memory `RATE_LIMIT_RECORDS` dictionary in `backend/main.py` with an external cache such as Redis using sliding-window keys.

### 2. Static Asset & Data Exposure Boundaries
- **Strict File Isolation**: Ensure raw workbooks (e.g. `data:raw/*.xlsx`), isolated staging directories (`data/staging/`), validation reports, and Git metadata are **never** mounted or served through static file handlers.
- **Production CORS Configuration**:
  ```bash
  export ALLOWED_ORIGINS="https://nexus.sapthagiri.edu.in,https://portal.sapthagiri.edu.in"
  ```
  Never use wildcard origins (`*`) with credentials enabled.
- **HTTPS & Security Headers**: Maintain the strict Content Security Policy (`default-src 'self'`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and enforce HSTS (`Strict-Transport-Security: max-age=31536000; includeSubDomains`) at the reverse proxy.

### 3. Stage 5B Staging Isolation Policy
- **Pending Review Gate**: Staged timetable records (`data/staging/timetable_stage5b.json`) must remain isolated from the live student timetable engine until department heads and the academic senate formally review the generated validation reports (`timetable_stage5b_report.md`).
- **Cryptographic Provenance**: Any merge must verify source file hashes and create an automated pre-merge backup in `data/backups/`.