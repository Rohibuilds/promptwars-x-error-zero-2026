# RA NEXUS Architecture

This document describes the architectural design, component interactions, security boundaries, and operational constraints of the RA NEXUS autonomous campus AI assistant prototype.

---

## 1. System Overview

RA NEXUS is built as a lightweight, single-origin or decoupled API web application. It combines a client-side vanilla JavaScript dashboard with a Python FastAPI backend providing rule-based agent routing, AST-safe calculations, and in-memory cached campus knowledge search.

```
+-------------------------------------------------------------------------+
|                               FRONTEND                                  |
|   index.html (Semantic HTML5, ARIA Landmarks, Live Region Announcer)    |
|   style.css  (Dark Theme, High-Contrast Focus Rings, Mobile Breakpoints)|
|   app.js     (Event Handling, Async Fetch to /chat, Tab Switching)      |
+-------------------------------------------------------------------------+
                                    |
                         HTTP POST /chat /health
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
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                         AGENT & TOOL PIPELINE                           |
|                                                                         |
|   backend.agent.run_agent(message)                                      |
|      |--> 1. System Status Intent   --> get_system_status()             |
|      |--> 2. Calculator Intent      --> calculate(expr) via AST         |
|      |--> 3. Knowledge Base Intent  --> search_knowledge(query)         |
|      |--> 4. Fallback Chat Intent   --> Default structured response     |
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

The autonomous agent (`backend/agent.py`) operates via deterministic, rule-based intent recognition:

1. **System Status (`get_system_status`)**:
   Matches operational queries (`"system status"`, `"are you online"`, `"available tools"`, etc.) and returns system metadata and loaded tool registries.
2. **Calculator (`calculate`)**:
   Matches mathematical verbs and keywords (`"calculate"`, `"solve"`, `"plus"`, `"times"`, etc.). Sanitizes natural language strings via `extract_expression()` into arithmetic expressions, then executes through the AST evaluator.
3. **Knowledge Search (`search_knowledge`)**:
   Matches campus queries (`"where"`, `"location"`, `"lab"`, `"library"`, `"timings"`, etc.). Matches normalized query tokens against searchable text fields, ranks by relevance score, and formats the top entry.
4. **Fallback Conversational Intent**:
   Unmatched inputs trigger a structured fallback response detailing RA NEXUS's available capabilities.

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

### Input Validation
User requests to `POST /chat` are validated via Pydantic (`ChatRequest`):
- Non-empty, stripped strings required (rejects empty or whitespace-only inputs with `422 Unprocessable Entity`).
- Maximum length: 2,000 characters.

---

## 6. Performance & Knowledge Caching

- **`@lru_cache(maxsize=1)`**: The knowledge base is parsed once on first access from `data/knowledge.json` and cached in-memory. Successive queries bypass disk I/O entirely.
- **Search Latency**: Keyword queries execute against the in-memory structure in ~2.5 microseconds (sub-millisecond latency).

---

## 7. Architectural Constraints & Known Limitations

1. **Rule-Based Agent Scope**:
   RA NEXUS uses deterministic keyword matching. It is not an LLM-based agent and cannot answer general knowledge questions outside its hardcoded rules and knowledge records.
2. **In-Memory Rate Limiting**:
   The sliding-window rate limiter stores timestamps in an in-memory Python dictionary (`RATE_LIMIT_RECORDS`). Counters are local to the running Python process. In a distributed deployment with multiple Uvicorn workers or across multiple container instances, an external store such as Redis is required for global rate enforcement.
3. **Static Knowledge Base**:
   Campus knowledge is read from a static local JSON file (`data/knowledge.json`). Adding or modifying facilities requires updating the JSON file and clearing the cache or restarting the process.
