# RA NEXUS Architecture

This document describes the architectural design, component interactions, security boundaries, and operational constraints of the RA NEXUS autonomous campus AI assistant prototype.

---

## 1. System Overview

RA NEXUS is built as a lightweight, single-origin or decoupled API web application. It combines a client-side vanilla JavaScript dashboard with a Python FastAPI backend providing rule-based agent routing, AST-safe calculations, and in-memory cached campus knowledge search.

```
+-------------------------------------------------------------------------+
|                               FRONTEND                                  |
|   index.html (Semantic HTML5, ARIA Landmarks, 5 Academic Workspaces)    |
|   style.css  (University Navy/Slate Design System, WCAG AAA, Mobile)    |
|   app.js     (Student Context, Timetable Engine, Directory, Chat State) |
+-------------------------------------------------------------------------+
                                    |
            HTTP POST /chat, GET /health, /api/timetable/*, /api/campus/*
                                    v
+-------------------------------------------------------------------------+
|                            FASTAPI BACKEND                              |
|                                                                         |
|   [1] CORSMiddleware (Configurable ALLOWED_ORIGINS, No Wildcard + Creds)|
|   [2] RateLimitMiddleware (Sliding-window 60 req/min, Memory-bounded)   |
|   [3] SecurityHeadersMiddleware (Strict CSP, nosniff, DENY, Referrer)   |
|   [4] GZipMiddleware (Threshold: 1000 bytes)                            |
|                                                                         |
|                           Endpoint Router                               |
|                     GET /health | POST /chat                            |
|                     GET /api/timetable/sections                         |
|                     GET /api/timetable/subjects                         |
|                     GET /api/timetable/schedule                         |
|                     GET /api/timetable/next-class                       |
|                     GET /api/campus/facilities                          |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                         AGENT & TOOL PIPELINE                           |
|                                                                         |
|   backend.agent.run_agent(message, student_context)                     |
|      |--> 1. System Status Intent   --> get_system_status()             |
|      |--> 2. Calculator Intent      --> calculate(expr) via AST         |
|      |--> 3. Timetable Intent       --> query_timetable(msg, ctx)       |
|      |--> 4. Knowledge Base Intent  --> search_knowledge(query)         |
|      |--> 5. Fallback Chat Intent   --> Default structured response     |
|                                                                         |
|   backend.timetable_engine.TimetableEngine                              |
|      |--> In-Memory Cached via @lru_cache(maxsize=1)                    |
|      |--> Strict Section Isolation (data/timetable.json)                |
|      |--> Verified partial dataset: ECE section 1ECE02                  |
|                                                                         |
|   backend.timetable_importer.TimetableImporter                          |
|      |--> Staging & Extraction Integrity Validation                      |
|      |--> Collision Detection (Period, Room, Faculty Overlaps)          |
|      |--> Automated Backups (data/backups/) & Permission Gate           |
|                                                                         |
|   backend.tools.load_knowledge_base()                                   |
|      |--> In-Memory Cached via @lru_cache(maxsize=1)                    |
|      |--> Loaded once from data/knowledge.json                          |
+-------------------------------------------------------------------------+
```

---

## 2. Frontend / Backend Communication

- **Single-Origin Deployment**: When running in production, FastAPI serves the frontend assets directly via `StaticFiles(directory="frontend", html=True)`. The frontend client communicates using relative URLs (`/chat`), eliminating cross-origin overhead.
- **Decoupled Local Development**: When running the frontend through a separate development server (e.g., Python `http.server` on port 5500), requests are sent to `http://127.0.0.1:8000/chat`.
- **CORS Handling**: Cross-Origin requests are managed through `CORSMiddleware`. Allowed origins are configured via the `ALLOWED_ORIGINS` environment variable (defaulting to ports 5500 and 8000). Wildcard origins (`*`) are prohibited when credentials are enabled.

---

## 3. Middleware Pipeline

FastAPI uses Starlette's ASGI middleware stack, executed in inside-out wrapping order:

1. **CORSMiddleware** (Outermost):
   Intercepts cross-origin preflight `OPTIONS` requests and enforces origin whitelisting before any route logic or rate limiting is reached.
2. **RateLimitMiddleware**:
   Applies a sliding-window algorithm tracking per-client IP timestamps on `/chat`. Over-limit requests immediately receive `429 Too Many Requests`.
3. **SecurityHeadersMiddleware**:
   Appends HTTP defense-in-depth headers to every outgoing response:
   - `Content-Security-Policy`: Restricts resource execution to `'self'` for scripts, styles, connections, and defaults. Avoids `'unsafe-inline'`.
   - `X-Content-Type-Options: nosniff`: Prevents MIME-confusion attacks.
   - `X-Frame-Options: DENY`: Prevents clickjacking and framing.
   - `X-XSS-Protection: 1; mode=block`: Legacy filter activation.
   - `Referrer-Policy: strict-origin-when-cross-origin`: Minimizes referrer leakage.
4. **GZipMiddleware** (Innermost):
   Compresses response bodies exceeding 1,000 bytes when the client presents `Accept-Encoding: gzip`.

---

## 4. Agent Routing & Tool Architecture

The autonomous agent (`backend/agent.py`) operates via deterministic, rule-based intent recognition with strict disambiguation:

1. **System Status (`get_system_status`)**:
   Matches operational queries (`"system status"`, `"are you online"`, `"available tools"`, etc.) and returns system metadata and loaded tool registries.
2. **Calculator (`calculate`)**:
   Matches mathematical verbs (`"calculate"`, `"solve"`) or numeric arithmetic queries. Natural language facility queries like `"What is the library timing?"` are explicitly excluded from calculator routing via campus keyword guards. Sanitizes mathematical strings via `extract_expression()` and executes safely through the AST sandbox.
3. **Timetable Engine (`query_timetable`)**:
   Matches class, schedule, period, next class, faculty, and section queries. Enforces strict section isolation: prompts students for their branch and section when unspecified, rejects unregistered sections without leaking other sections' data, and reports when period timings are pending official publication.
   - **Student Context**: Validates branch, academic year, semester, section, and laboratory batch against registered institutional records.
   - **Next-Class Resolver (`get_current_and_next_class`)**: Requires verified period timings and a validated client timestamp. If period or weekday mappings are unverified (such as with initial section 1ECE02 records), explicitly reports missing information rather than guessing.
   - **Read-Only REST Endpoints**:
     - `GET /api/timetable/sections`: Filterable by branch and semester.
     - `GET /api/timetable/subjects`: Returns enrolled subjects, faculty, and room allocations.
     - `GET /api/timetable/schedule`: Filterable by section, weekday, period, and batch.
     - `GET /api/timetable/next-class`: Deterministic real-time schedule resolution.
4. **Knowledge Search (`search_knowledge`)**:
   Matches campus queries (`"where"`, `"location"`, `"lab"`, `"library"`, `"timings"`, etc.). Matches normalized query tokens against searchable text fields in `data/knowledge.json`, ranks by relevance score, and formats verified results.
   - **Campus Directory Endpoint (`GET /api/campus/facilities`)**: Exposes verified laboratories, facilities, and services with source metadata and operating hours for the Campus Directory portal.
5. **Fallback Conversational Intent**:
   Unmatched inputs trigger a structured fallback response detailing RA NEXUS's available capabilities at Sapthagiri NPS University.

---

## 5. Security & Safety Boundaries

### Safe Arithmetic Evaluator (AST Sandbox)
To prevent code execution vulnerabilities (`eval()` / `exec()` are strictly avoided), mathematical evaluation utilizes Python's `ast.parse` in `eval` mode with rigorous safety boundaries:
- **Operator Whitelist**: Only `+`, `-`, `*`, `/`, `**`, `%`, and unary `-` are permitted.
- **Node Type Whitelist**: Only numeric constants (`ast.Constant` with `int` or `float`), binary operators (`ast.BinOp`), and unary operators (`ast.UnaryOp`) are evaluated. Function calls, attribute lookups, and imports raise immediate exceptions.
- **Complexity & Size Limits**:
  - Maximum expression length: 100 characters.
  - Maximum AST nodes: 40 nodes.
  - Maximum numeric magnitude: `1e100`.
  - Exponent cap: `abs(exponent) <= 100` (prevents catastrophic CPU denial-of-service via huge exponents).
  - Multiplication/power operand cap: `1e10`.

### Input Validation & Student Context
Incoming payloads are rigorously validated with Pydantic:
- **`StudentContext` Model**:
  - `branch`: Optional string, 1–32 characters, uppercase normalized.
  - `academic_year`: Optional integer (1–5).
  - `semester`: Optional integer (1–10).
  - `section`: Optional string, 1–32 characters, uppercase normalized.
  - `batch`: Optional string, 1–32 characters.
  - Validated against institutional records via `validate_student_context()`. Branch conflicts return `400 Bad Request`, while unregistered sections prompt for clarification without data leakage.
- **`ChatRequest` Model**:
  - `message`: Required non-empty string, 1–2,000 characters (rejects empty or whitespace-only inputs with `422 Unprocessable Entity`).
  - `student_context`: Optional `StudentContext` instance.
  - `client_time`: Optional ISO-8601 formatted client timestamp (e.g. `2026-10-12T10:15:00`).
  - **Backward Compatibility**: Fully backward compatible with legacy single-property payloads (`{"message": "..."}`).

---

## 6. Performance & Knowledge Caching

- **`@lru_cache(maxsize=1)`**: The knowledge base is parsed once on first access from `data/knowledge.json` and cached in-memory. Successive queries bypass disk I/O entirely.
- **Search Latency**: Keyword queries execute against the in-memory structure in ~2.5 microseconds (sub-millisecond latency).

---

## 7. Architectural Constraints & Known Limitations

1. **Rule-Based Agent Scope & Timetable Coverage**:
   RA NEXUS uses deterministic keyword matching and structured query resolution without paid external AI APIs. Currently, verified initial timetable information is cataloged for ECE section 1ECE02 (provisional registration). Detailed weekday and period class schedules for 1ECE02 and other university sections are pending official release and validation. The system strictly avoids guessing or cross-section data leakage.
2. **In-Memory Rate Limiting**:
   The sliding-window rate limiter stores timestamps in an in-memory Python dictionary (`RATE_LIMIT_RECORDS`). Counters are local to the running Python process. In a distributed deployment with multiple Uvicorn workers or across multiple container instances, an external store such as Redis is required for global rate enforcement.
3. **Static Knowledge Base**:
   Campus knowledge is read from a static local JSON file (`data/knowledge.json`). Adding or modifying facilities requires updating the JSON file and clearing the cache or restarting the process.
