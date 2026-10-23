from __future__ import annotations

import json
import logging

import pytest
from app.api import main
from app.api.main import app
from fastapi.testclient import TestClient

from .conftest import EXAMPLES, load_json

client = TestClient(app)


def _post(body, headers=None, **kw):
    return client.post(
        "/api/check?as_of=2026-09-27",
        content=json.dumps(body),
        headers={"content-type": "application/json", **(headers or {})},
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
        "x-frame-options",
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


SECRET = "Marcus Johnson pushed my son. Call me at (773) 555-0142."


def test_description_redacted_in_response_and_logs(caplog):
    main._hits.clear()
    body = load_json(EXAMPLES / "scenario_a_two_day_no_notice.json")
    body["incident_description"] = SECRET
    with caplog.at_level(logging.INFO, logger="suspension_check.api"):
        r = _post(body)
    assert r.status_code == 200
    data = r.json()
    assert "<PERSON>" in data["description"] and "<PHONE>" in data["description"]
    assert data["redacted"] == ["PERSON", "PHONE_NUMBER"]
    for leaked in ("Marcus", "Johnson", "555-0142"):
        assert leaked not in r.text
        assert leaked not in "\n".join(caplog.messages)


def test_check_lists_applicable_letters():
    main._hits.clear()
    r = _post(load_json(EXAMPLES / "scenario_b_iep_cumulative_twelve.json"))
    assert [x["variant"] for x in r.json()["letters"]] == [
        "review_request",
        "mdr_request",
        "records_request",
    ]


@pytest.mark.parametrize(
    ("fmt", "magic"),
    [("docx", b"PK"), ("html", b"<!doctype html>"), ("txt", b"September 27, 2026")],
)
def test_letter_download(fmt, magic):
    main._hits.clear()
    r = client.post(
        f"/api/letter?variant=mdr_request&format={fmt}&as_of=2026-09-27",
        content=json.dumps(load_json(EXAMPLES / "scenario_b_iep_cumulative_twelve.json")),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200
    assert r.content.startswith(magic)
    assert "attachment" in r.headers["content-disposition"]


def test_letter_rejects_unknown_variant_and_format():
    main._hits.clear()
    body = json.dumps(load_json(EXAMPLES / "scenario_a_two_day_no_notice.json"))
    h = {"content-type": "application/json"}
    assert client.post("/api/letter?variant=nope", content=body, headers=h).status_code == 422
    assert (
        client.post(
            "/api/letter?variant=review_request&format=pdf", content=body, headers=h
        ).status_code
        == 422
    )


def test_non_json_body_is_rejected():
    main._hits.clear()
    r = client.post("/api/check", content=b"not json", headers={"content-type": "application/json"})
    assert r.status_code == 422


def test_calendar_download():
    main._hits.clear()
    r = client.post(
        "/api/calendar?as_of=2026-09-27",
        content=json.dumps(load_json(EXAMPLES / "scenario_b_iep_cumulative_twelve.json")),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert "attachment" in r.headers["content-disposition"]
    assert r.text.startswith("BEGIN:VCALENDAR")
    assert "DTSTART;VALUE=DATE:20261006" in r.text


def test_calendar_rejects_invalid_facts():
    main._hits.clear()
    r = client.post("/api/calendar", content="{}", headers={"content-type": "application/json"})
    assert r.status_code == 422


def test_malformed_content_length_is_rejected_not_a_crash():
    from starlette.testclient import TestClient as TC

    raw = TC(app, raise_server_exceptions=False)
    r = raw.post(
        "/api/check",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": "abc"},
    )
    assert r.status_code in (400, 413)


def test_rate_limit_uses_forwarded_client_only_when_trusted(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT", 1)
    body = load_json(EXAMPLES / "scenario_a_two_day_no_notice.json")
    main._hits.clear()
    monkeypatch.setattr(main, "TRUST_PROXY", True)
    assert _post(body, headers={"x-forwarded-for": "203.0.113.1"}).status_code == 200
    assert _post(body, headers={"x-forwarded-for": "203.0.113.2, 10.0.0.1"}).status_code == 200
    assert _post(body, headers={"x-forwarded-for": "203.0.113.1"}).status_code == 429
    main._hits.clear()
    monkeypatch.setattr(main, "TRUST_PROXY", False)
    assert _post(body, headers={"x-forwarded-for": "203.0.113.9"}).status_code == 200
    assert _post(body, headers={"x-forwarded-for": "203.0.113.8"}).status_code == 429
    main._hits.clear()


def test_permissions_policy_header():
    assert "camera=()" in client.get("/api/health").headers["permissions-policy"]


def test_uvicorn_access_log_is_off():
    # The access log would record client addresses; PRIVACY.md promises it does not.
    assert logging.getLogger("uvicorn.access").disabled


SYN = EXAMPLES.parent / "synthetic"
_OCTET = {"content-type": "application/octet-stream"}


def test_pattern_map_then_analyze_then_brief():
    main._hits.clear()
    raw = (SYN / "school_b.xlsx").read_bytes()
    m = client.post("/api/pattern/map?filename=school_b.xlsx", content=raw, headers=_OCTET)
    assert m.status_code == 200
    body = m.json()
    assert body["mapping"]["Name (Last, First)"] == "name"
    assert body["rows"] == 145
    assert set(body) == {"headers", "mapping", "rows"}  # no cell values come back
    enr = json.dumps({"race_ethnicity": {"Black": 400, "Hispanic": 500, "White": 300, "Asian": 60}})
    r = client.post(
        "/api/pattern",
        params={
            "filename": "school_b.xlsx",
            "enrollment": enr,
            "mapping": json.dumps(body["mapping"]),
        },
        content=raw,
        headers=_OCTET,
    )
    assert r.status_code == 200
    got = r.json()
    assert got["by_race_ethnicity"]["Black"]["risk_ratio"] == 3.212
    assert len(got["questions"]) == 3
    b = client.post(
        "/api/pattern/brief",
        params={"filename": "school_b.xlsx", "enrollment": enr, "title": "Test High"},
        content=raw,
        headers=_OCTET,
    )
    assert b.status_code == 200 and "Test High" in b.text
    main._hits.clear()


def test_pattern_errors_are_422_with_safe_messages():
    main._hits.clear()
    bad = b"Item,Price\nJamal Carter,1\n"
    for path in ("/api/pattern", "/api/pattern/brief"):
        r = client.post(path + "?filename=x.csv", content=bad, headers=_OCTET)
        assert r.status_code == 422 and "Jamal" not in r.text
    assert client.post("/api/pattern/map", content=b"", headers=_OCTET).status_code in (413, 422)
    raw = (SYN / "school_c_small.csv").read_bytes()
    for params in (
        {"enrollment": "not json"},
        {"enrollment": "[1]"},
        {"enrollment": json.dumps({"race_ethnicity": {"Black": "many"}})},
        {"mapping": "{"},
    ):
        r = client.post("/api/pattern", params=params, content=raw, headers=_OCTET)
        assert r.status_code == 422
    main._hits.clear()


def test_pattern_upload_limit_is_larger_but_bounded():
    main._hits.clear()
    from suspension_check import disparity

    big = b"a" * (main.MAX_BODY_BYTES + 10)
    r = client.post("/api/pattern/map?filename=x.csv", content=big, headers=_OCTET)
    assert r.status_code != 413  # a 40 KB log is fine for Pattern Check ...
    too_big = b"a" * (disparity.MAX_BYTES + 1)
    r = client.post("/api/pattern/map", content=too_big, headers=_OCTET)
    assert r.status_code == 413  # ... but not above 2 MB
    main._hits.clear()


def test_pattern_page_and_samples():
    assert client.get("/pattern").status_code == 200
    assert client.get("/api/pattern/sample/school_a").status_code == 200
    assert client.get("/api/pattern/sample/../../etc").status_code == 404
    assert client.get("/api/pattern/sample/nope").status_code == 404
