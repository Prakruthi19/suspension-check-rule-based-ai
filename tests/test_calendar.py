from __future__ import annotations

from datetime import date, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dueproc.calendar import BeyondSchoolYear, SchoolCalendar

CPS = SchoolCalendar.default()
IN_YEAR = st.dates(min_value=CPS.first_day, max_value=CPS.last_day)


def test_known_cps_dates():
    assert not CPS.is_school_day(date(2026, 9, 7))  # Labor Day
    assert not CPS.is_school_day(date(2026, 9, 26))  # Saturday
    assert CPS.is_school_day(date(2026, 9, 28))
    assert not CPS.is_school_day(date(2026, 12, 28))  # winter break
    assert not CPS.is_school_day(date(2026, 7, 1))  # summer
    assert CPS.next_school_day(date(2026, 9, 25)) == date(2026, 9, 28)
    assert CPS.add_school_days(date(2026, 10, 9), 1) == date(2026, 10, 13)  # skips Oct 12
    assert CPS.nth_school_day(date(2026, 9, 23), 7) == date(2026, 10, 1)


def test_winter_break_is_skipped():
    assert CPS.add_school_days(date(2026, 12, 18), 1) == date(2027, 1, 4)


def test_beyond_school_year_raises():
    with pytest.raises(BeyondSchoolYear):
        CPS.add_school_days(date(2027, 6, 1), 30)


def test_negative_days_rejected():
    with pytest.raises(ValueError):
        CPS.add_school_days(date(2026, 9, 1), -1)
    with pytest.raises(ValueError):
        CPS.nth_school_day(date(2026, 9, 1), 0)


def test_before_first_day_counts_from_first_day():
    assert CPS.add_school_days(date(2026, 8, 1), 1) == CPS.first_day


@given(IN_YEAR, st.integers(min_value=0, max_value=60))
def test_result_is_always_a_school_day(start, n):
    try:
        d = CPS.add_school_days(start, n)
    except BeyondSchoolYear:
        return
    assert CPS.is_school_day(d)


@given(IN_YEAR, st.integers(min_value=1, max_value=60))
def test_add_counts_exactly_n_school_days(start, n):
    try:
        d = CPS.add_school_days(start, n)
    except BeyondSchoolYear:
        return
    assert CPS.school_days_between(start, d) == n


@given(IN_YEAR, st.integers(min_value=1, max_value=59))
def test_more_days_is_never_earlier(start, n):
    try:
        later = CPS.add_school_days(start, n + 1)
    except BeyondSchoolYear:
        return
    assert CPS.add_school_days(start, n) < later


@given(IN_YEAR, IN_YEAR, st.integers(min_value=1, max_value=30))
def test_later_start_is_never_earlier(a, b, n):
    a, b = min(a, b), max(a, b)
    try:
        db = CPS.add_school_days(b, n)
    except BeyondSchoolYear:
        return
    assert CPS.add_school_days(a, n) <= db


ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Holiday
DTSTART;VALUE=DATE:20261012
DTEND;VALUE=DATE:20261013
END:VEVENT
BEGIN:VEVENT
SUMMARY:Break
DTSTART;VALUE=DATE:20261125
DTEND;VALUE=DATE:20261128
END:VEVENT
BEGIN:VEVENT
SUMMARY:One day, no end
DTSTART;VALUE=DATE:20261111
END:VEVENT
END:VCALENDAR
"""


def test_ics_import():
    cal = SchoolCalendar.from_ics(
        ICS, name="t", first_day=date(2026, 8, 17), last_day=date(2027, 6, 10)
    )
    assert cal.closures == {
        date(2026, 10, 12),
        date(2026, 11, 11),
        date(2026, 11, 25),
        date(2026, 11, 26),
        date(2026, 11, 27),
    }


def test_json_roundtrip(tmp_path):
    p = tmp_path / "cal.json"
    p.write_text(
        '{"name": "x", "first_day": "2026-09-01", "last_day": "2026-09-30",'
        ' "closures": [{"start": "2026-09-07"}]}'
    )
    cal = SchoolCalendar.from_json(p)
    assert not cal.is_school_day(date(2026, 9, 7))
    assert cal.school_days_between(date(2026, 9, 1), date(2026, 9, 30)) == 20


def test_last_before_first_rejected():
    with pytest.raises(ValueError):
        SchoolCalendar(name="bad", first_day=date(2026, 9, 2), last_day=date(2026, 9, 1))


def test_every_day_of_year_classified():
    d, n = CPS.first_day, 0
    while d <= CPS.last_day:
        n += CPS.is_school_day(d)
        d += timedelta(days=1)
    # The provisional calendar has holidays only (190 days). Once CPS professional
    # development and report-card days are added this should drop to about 176.
    assert 170 <= n <= 195, "a plausible Illinois school year"
