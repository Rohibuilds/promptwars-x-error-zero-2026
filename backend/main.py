"""FastAPI application entry point for RA NEXUS with security headers, CORS, rate limiting, and compression.

NOTE ON RATE LIMITING ARCHITECTURE:
The RateLimitMiddleware uses an in-memory dictionary (RATE_LIMIT_RECORDS) suitable for
single-process deployments. Rate-limit counters are not synchronized across multiple workers
or distributed server instances; in a scaled multi-worker deployment, an external shared
store such as Redis would be used.
"""

from collections import defaultdict
import logging
import os
from pathlib import Path
import time
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from .agent import run_agent

logger = logging.getLogger("ra_nexus")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="RA NEXUS",
    description="RA Tech Autonomous Campus AI Assistant",
    version="0.1.0"
)

# 1. Performance: GZip Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. Security: HTTP Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces essential HTTP security headers on all outgoing responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Strict CSP: no inline scripts or styles required by the static dashboard
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self'; "
            "script-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)


# 3. Security: In-Memory Rate Limiter Middleware (DDoS protection)
RATE_LIMIT_RECORDS: Dict[str, List[float]] = defaultdict(list)


def reset_rate_limiter() -> None:
    """Resets in-memory rate limiter tracking for test isolation and administrative resets."""
    RATE_LIMIT_RECORDS.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter (60 requests per minute per client IP)."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit API routes, not static assets
        if request.url.path.startswith("/chat"):
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            cutoff = now - self.window_seconds

            # Prune expired timestamps for active client
            active_timestamps = [t for t in RATE_LIMIT_RECORDS.get(client_ip, []) if t > cutoff]
            if active_timestamps:
                RATE_LIMIT_RECORDS[client_ip] = active_timestamps
            else:
                RATE_LIMIT_RECORDS.pop(client_ip, None)

            # Prevent unbounded memory growth by pruning stale IPs if map exceeds threshold
            if len(RATE_LIMIT_RECORDS) > 1000:
                stale_ips = [
                    ip for ip, times in RATE_LIMIT_RECORDS.items()
                    if not times or max(times) <= cutoff
                ]
                for ip in stale_ips:
                    RATE_LIMIT_RECORDS.pop(ip, None)

            if len(RATE_LIMIT_RECORDS.get(client_ip, [])) >= self.max_requests:
                logger.warning("Rate limit exceeded for client %s", client_ip)
                return Response(
                    content='{"detail": "Rate limit exceeded. Please wait a moment."}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json"
                )

            RATE_LIMIT_RECORDS[client_ip].append(now)

        return await call_next(request)


app.add_middleware(RateLimitMiddleware)


# 4. CORS Middleware: Restrict to explicit local development origins (no wildcard with credentials)
DEFAULT_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]
env_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()] or DEFAULT_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)


class ChatRequest(BaseModel):
    """Schema for chat requests with validation and sanitization."""
    message: str = Field(min_length=1, max_length=2000, description="User prompt message")

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """Validates that the input message is not empty or whitespace only."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty")
        return cleaned


@app.get("/health")
def health() -> Dict[str, str]:
    """Health check endpoint to verify backend operational readiness.
    
    Returns:
        Dict[str, str]: Status details and version metadata.
    """
    return {
        "name": "RA NEXUS",
        "version": "0.1.0",
        "status": "online"
    }


@app.post("/chat")
def chat(request: ChatRequest) -> Dict:
    """Dispatches user message to the RA NEXUS autonomous agent.
    
    Args:
        request: Validated ChatRequest body.
        
    Returns:
        Dict: Agent response payload with tool execution status.
        
    Raises:
        HTTPException: 500 status code with safe message on unexpected execution errors.
    """
    try:
        return run_agent(request.message)
    except Exception as exc:
        logger.exception("Unexpected error executing agent for query: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        )


# Mount static assets (must be after explicit API endpoints)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")