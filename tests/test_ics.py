from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from suspension_check.ics import REMINDER_DAYS, _fold, to_ics, upcoming
from suspension_check.ingest import ingest
from suspension_check.timeline import build_timeline

from .conftest import EXAMPLES, FIXTURES

TODAY = date(2026, 9, 27)
SCENARIOS = [
    "scenario_a_two_day_no_notice",
    "scenario_b_iep_cumulative_twelve",
    "scenario_c_expulsion_hearing",
]


def _timeline(name, cps):
    facts = ingest((EXAMPLES / f"{name}.json").read_text(encoding="utf-8")).facts
    return facts, build_timeline(facts, cps)


def _events(ics: str) -> list[dict[str, str]]:
    """Unfold (RFC 5545 3.1) and parse VEVENTs into dicts. Enough to check our own output."""
    unfolded = ics.replace("\r\n ", "")
    events, cur, depth = [], None, 0
    for line in unfolded.split("\r\n"):
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            events.append(cur)
            cur = None
        elif line == "BEGIN:VALARM":
            depth += 1
        elif line == "END:VALARM":
            depth -= 1
        elif cur is not None and depth == 0 and line:
            key, _, value = line.partition(":")
            cur[key] = value
    return events


@pytest.mark.parametrize("name", SCENARIOS)
def test_golden(name, cps):
    _, tl = _timeline(name, cps)
    golden = (FIXTURES / "ics" / f"{name}.ics").read_bytes().decode("utf-8")
    assert to_ics(tl, TODAY) == golden


@pytest.mark.parametrize("name", SCENARIOS)
def test_one_event_per_upcoming_deadline(name, cps):
    _, tl = _timeline(name, cps)
    events = _events(to_ics(tl, TODAY))
    expected = upcoming(tl, TODAY)
    assert len(events) == len(expected)
    for ev, o in zip(events, expected, strict=True):
        assert ev["DTSTART;VALUE=DATE"] == f"{o.due:%Y%m%d}"
        assert ev["UID"] == f"{o.id}-{o.due:%Y%m%d}@suspension-check"


def test_passed_deadlines_are_left_out(cps):
    _, tl = _timeline("scenario_b_iep_cumulative_twelve", cps)
    late = date(2026, 10, 3)
    starts = {e["DTSTART;VALUE=DATE"] for e in _events(to_ics(tl, late))}
    assert starts and all(s >= "20261003" for s in starts)
    assert _events(to_ics(tl, date(2027, 12, 31))) == []


def test_reminder_and_structure(cps):
    _, tl = _timeline("scenario_b_iep_cumulative_twelve", cps)
    ics = to_ics(tl, TODAY)
    assert ics.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n")
    assert ics.endswith("END:VCALENDAR\r\n")
    assert ics.count("BEGIN:VEVENT") == ics.count(f"TRIGGER:-P{REMINDER_DAYS}D")
    assert "\n" not in ics.replace("\r\n", "")


def test_no_student_facts_in_the_file(cps):
    facts, tl = _timeline("scenario_c_expulsion_hearing", cps)
    ics = to_ics(tl, TODAY).replace("\r\n ", "")
    if facts.incident_description:
        assert facts.incident_description not in ics
    assert "<PERSON>" not in ics


@given(st.text(min_size=0, max_size=300))
def test_fold_keeps_text_and_line_limit(text):
    line = "SUMMARY:" + text.replace("\r", "").replace("\n", "")
    parts = _fold(line)
    assert "".join(p[1:] if i else p for i, p in enumerate(parts)) == line
    assert all(len(p.encode("utf-8")) <= 75 for p in parts)
