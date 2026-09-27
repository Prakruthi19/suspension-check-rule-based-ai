"""Stateless Family Check API (alpha spike).

Nothing is stored: requests are validated in memory, evaluated, and discarded.
Logs carry only a request ID, timing, and the rule IDs that fired.

Run locally:  uvicorn app.api.main:app --reload   then open http://127.0.0.1:8000
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from dueproc import __version__
from dueproc.calendar import SchoolCalendar
from dueproc.facts import Facts
from dueproc.letters import review_request
from dueproc.report import check
from dueproc.rules import evaluate

MAX_BODY_BYTES = 32 * 1024
RATE_LIMIT = int(os.environ.get("DUEPROC_RATE_LIMIT", "30"))  # requests per minute per client
ALLOWED_ORIGINS = [o for o in os.environ.get("DUEPROC_ALLOWED_ORIGINS", "").split(",") if o]
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

log = logging.getLogger("dueproc.api")
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title="Suspension Check API", version=__version__, docs_url=None, redoc_url=None)
if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["POST"],
        allow_headers=["content-type"],
    )

CALENDAR = SchoolCalendar.default()

# In-memory sliding window. Client addresses live here for at most 60 seconds
# and are never written to logs.
_hits: dict[str, deque[float]] = defaultdict(deque)


def _rate_limited(client: str) -> bool:
    now = time.monotonic()
    window = _hits[client]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT:
        return True
    window.append(now)
    return False


SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cache-Control": "no-store",
}


@app.middleware("http")
async def guard(request: Request, call_next):
    rid = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    if request.method == "POST":
        length = request.headers.get("content-length")
        if length is None or int(length) > MAX_BODY_BYTES:
            return JSONResponse({"error": "Request body missing or too large."}, status_code=413)
        client = request.client.host if request.client else "unknown"
        if _rate_limited(client):
            return JSONResponse(
                {"error": "Too many requests. Try again in a minute."}, status_code=429
            )
    request.state.rid = rid
    request.state.rule_ids = []
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    # Allowlist logging: request id, path, status, timing, rule IDs. Never a body.
    log.info(
        "rid=%s path=%s status=%s ms=%.1f rules=%s",
        rid,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
        ",".join(getattr(request.state, "rule_ids", [])),
    )
    return response


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", media_type="text/html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "calendar": CALENDAR.name}


@app.post("/api/check")
async def api_check(request: Request, as_of: date | None = None) -> dict:
    """Evaluate facts. ``as_of`` lets a demo pin "today" (defaults to the real date)."""
    raw = await request.body()
    try:
        facts = Facts.model_validate_json(raw)
    except ValidationError as exc:
        # Report which fields failed, never the submitted values.
        fields = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})
        raise HTTPException(status_code=422, detail={"invalid_fields": fields}) from None
    today = as_of or date.today()
    result = check(facts, CALENDAR, today)
    result["letter"] = review_request(facts, evaluate(facts), today)
    request.state.rule_ids = [f["rule_id"] for f in result["flags"]]
    return result
