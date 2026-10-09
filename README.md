# RA NEXUS

**An Autonomous Campus AI Assistant Prototype**

RA NEXUS is an autonomous AI assistant prototype built by RA Tech for the PromptWars × Error Zero 2026 hackathon. It integrates rule-based intent recognition, campus knowledge retrieval with in-memory caching, an AST-based safe arithmetic evaluator, and a dark-mode web dashboard.

---

## Features

- **Rule-Based Autonomous Agent**: Deterministic intent recognition routing user requests across system diagnostics, campus facilities, arithmetic, and general assistance.
- **In-Memory Cached Knowledge Search**: Fast campus knowledge search cached via `@lru_cache(maxsize=1)` to avoid repeated disk reads.
- **Safe Calculator**: AST-based arithmetic evaluation with strict token and node complexity boundaries, preventing arbitrary code execution.
- **System Diagnostics**: Real-time status inspection reporting engine version, status, and loaded tool capabilities.
- **Hardened Web Security**:
  - Strict Content Security Policy (`default-src 'self'`) with no `'unsafe-inline'` directives.
  - MIME-sniffing protection (`X-Content-Type-Options: nosniff`).
  - Clickjacking protection (`X-Frame-Options: DENY`).
  - Sliding-window rate limiting (60 requests/minute on `/chat`).
  - Configurable CORS with no wildcard credentials.
  - Safe error handling preventing Python tracebacks from leaking to clients.
- **Accessible User Interface**:
  - Dedicated ARIA live region (`#liveAnnouncer`) for screen readers announcing new responses without reading prior history.
  - Keyboard skip-link jumping past navigation directly to main content.
  - Visible focus indicators (`outline: 2px solid var(--green)`).
  - Responsive layout usable down to narrow viewports and at 200% zoom.
- **Automated Test Suite**: 28 automated tests covering routing, AST calculator safety, input validation, rate limiting, CORS, and security headers.

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
        ├─ System Status  ─► get_system_status()
        ├─ Calculator     ─► calculate() (AST-based safe evaluator)
        ├─ Knowledge Base ─► search_knowledge() (Cached @lru_cache)
        └─ Chat Fallback  ─► Structured guidance response
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
Returns operational health status and engine version:
```json
{
  "name": "RA NEXUS",
  "version": "0.1.0",
  "status": "online"
}
```

### `POST /chat`
Accepts a JSON message payload and executes the agent pipeline:

**Request Body:**
```json
{
  "message": "Where is the computer laboratory located?"
}
```

**Response Payload:**
```json
{
  "type": "knowledge",
  "status": "completed",
  "tool": "knowledge_search",
  "results": [
    {
      "title": "Computer Laboratory",
      "location": "Block B, Second Floor",
      "description": "Computer laboratory for programming and software development",
      "equipment": ["Desktop Computers", "Networking Equipment", "Projector"]
    }
  ],
  "response": "Here's what I found:\n\nComputer Laboratory\nLocation: Block B, Second Floor\n..."
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
- `tests/test_agent.py`: Intent routing across all 4 types, expression sanitization, formatting.
- `tests/test_tools.py`: Arithmetic correctness, order of operations, AST limits, modulo, unary operators, division-by-zero rejection, code-injection rejection, knowledge cache hit/miss behavior.
- `tests/test_api.py`: Endpoint availability, Pydantic validation (empty strings, whitespace, missing fields, length limits), CORS origin rejection, strict CSP validation, and rate limiter isolation.

---

## Security & Operational Limitations

1. **Rule-Based Routing**: The agent uses deterministic keyword matching. It does not use an external Large Language Model (LLM) and only processes queries matching its recognized intents or campus records.
2. **In-Memory Rate Limiting**: The sliding-window rate limiter stores timestamps in local process memory (`RATE_LIMIT_RECORDS`). Counters are not shared across multiple worker processes or multi-server clusters. Multi-worker scaling requires backing with an external data store such as Redis.
3. **Static Knowledge Base**: Campus facilities are loaded from `data/knowledge.json`. Modifying records requires editing the file and restarting the application or refreshing the cache.