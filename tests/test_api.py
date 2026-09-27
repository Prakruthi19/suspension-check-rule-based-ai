from __future__ import annotations

import json
import logging

from app.api import main
from app.api.main import app
from fastapi.testclient import TestClient

from .conftest import EXAMPLES, load_json

client = TestClient(app)


def _post(body, **kw):
    return client.post(
        "/api/check?as_of=2026-09-27",
        content=json.dumps(body),
        headers={"content-type": "application/json"},
        **kw,
    )


def test_check_returns_flags_timeline_and_letter():
    r = _post(load_json(EXAMPLES / "scenario_b_iep_cumulative_twelve.json"))
    assert r.status_code == 200
    body = r.json()
    assert "FED-02" in {f["rule_id"] for f in body["flags"]}
    assert any(o["id"] == "mdr" and o["due"] == "2026-10-06" for o in body["timeline"])
    assert body["letter"].startswith("September 27, 2026")
    assert body["disclaimer"]


def test_security_headers():
    r = client.get("/api/health")
    for h in (
        "strict-transport-security",
        "content-security-policy",
        "x-content-type-options",
        "referrer-policy",
    ):
        assert h in r.headers
    assert r.headers["cache-control"] == "no-store"


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "Suspension Check" in r.text


def test_validation_error_does_not_echo_values():
    secret = "Jordan Example 555-0100"
    r = _post({"incident_date": secret})
    assert r.status_code == 422
    assert secret not in r.text


def test_body_limit():
    r = client.post(
        "/api/check",
        content=b"x" * (main.MAX_BODY_BYTES + 1),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 413


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT", 2)
    main._hits.clear()
    body = load_json(EXAMPLES / "scenario_a_two_day_no_notice.json")
    assert _post(body).status_code == 200
    assert _post(body).status_code == 200
    assert _post(body).status_code == 429
    main._hits.clear()


def test_logs_never_contain_request_body(caplog):
    main._hits.clear()
    body = load_json(EXAMPLES / "scenario_a_two_day_no_notice.json")
    with caplog.at_level(logging.INFO, logger="suspension_check.api"):
        _post(body)
    text = "\n".join(caplog.messages)
    assert "rules=IL-01" in text
    assert "2026-09-21" not in text and "phone_only" not in text
