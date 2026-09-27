"""School-day arithmetic.

A school day is a weekday inside the school year that is not a closure. Days
outside the school year are never school days, so a clock that runs past the
last day raises ``BeyondSchoolYear`` instead of silently landing in summer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from importlib import resources
from pathlib import Path

from dateutil.parser import isoparse

__all__ = ["BeyondSchoolYear", "SchoolCalendar"]

_ONE_DAY = timedelta(days=1)


class BeyondSchoolYear(ValueError):
    """A school-day clock ran past the last day of the configured school year."""


@dataclass(frozen=True)
class SchoolCalendar:
    name: str
    first_day: date
    last_day: date
    closures: frozenset[date] = field(default_factory=frozenset)
    status: str = ""

    def __post_init__(self) -> None:
        if self.last_day < self.first_day:
            raise ValueError("last_day is before first_day")

    # --- queries ---------------------------------------------------------------

    def in_year(self, d: date) -> bool:
        return self.first_day <= d <= self.last_day

    def is_school_day(self, d: date) -> bool:
        return self.in_year(d) and d.weekday() < 5 and d not in self.closures

    def school_days_between(self, start: date, end: date) -> int:
        """School days in the half-open interval (start, end]."""
        if end <= start:
            return 0
        n, d = 0, start
        while d < end:
            d += _ONE_DAY
            n += self.is_school_day(d)
        return n

    # --- arithmetic ------------------------------------------------------------

    def next_school_day(self, d: date) -> date:
        """The first school day strictly after ``d``."""
        return self.add_school_days(d, 1)

    def on_or_after(self, d: date) -> date:
        """``d`` if it is a school day, otherwise the next one."""
        return d if self.is_school_day(d) else self.next_school_day(d)

    def add_school_days(self, start: date, n: int) -> date:
        """The ``n``-th school day after ``start`` (``start`` itself is not counted).

        ``n == 0`` returns ``start`` if it is a school day, else the next one.
        """
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0:
            return self.on_or_after(start)
        d, remaining = max(start, self.first_day - _ONE_DAY), n
        while remaining:
            d += _ONE_DAY
            if d > self.last_day:
                raise BeyondSchoolYear(
                    f"{n} school days after {start} falls after the last day of "
                    f"{self.name} ({self.last_day})"
                )
            if self.is_school_day(d):
                remaining -= 1
        return d

    def nth_school_day(self, start: date, n: int) -> date:
        """The ``n``-th school day counting ``start`` as day 1 if it is a school day.

        Used for "the last day of a 5-day suspension that starts on ``start``".
        """
        if n < 1:
            raise ValueError("n must be at least 1")
        first = self.on_or_after(start)
        return first if n == 1 else self.add_school_days(first, n - 1)

    # --- loading ---------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> SchoolCalendar:
        closures: set[date] = set()
        for c in data.get("closures", []):
            start = isoparse(c["start"]).date()
            end = isoparse(c.get("end", c["start"])).date()
            d = start
            while d <= end:
                closures.add(d)
                d += _ONE_DAY
        return cls(
            name=data["name"],
            first_day=isoparse(data["first_day"]).date(),
            last_day=isoparse(data["last_day"]).date(),
            closures=frozenset(closures),
            status=data.get("status", ""),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> SchoolCalendar:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_ics(cls, text: str, *, name: str, first_day: date, last_day: date) -> SchoolCalendar:
        """Load all-day VEVENTs as closures. DTEND is exclusive, per RFC 5545."""
        closures: set[date] = set()
        start = end = None
        for raw in text.splitlines():
            line = raw.strip()
            key, _, value = line.partition(":")
            prop = key.split(";", 1)[0].upper()
            if prop == "BEGIN" and value.upper() == "VEVENT":
                start = end = None
            elif prop == "DTSTART":
                start = _ics_date(value)
            elif prop == "DTEND":
                end = _ics_date(value)
            elif prop == "END" and value.upper() == "VEVENT" and start is not None:
                stop = end if end is not None and end > start else start + _ONE_DAY
                d = start
                while d < stop:
                    closures.add(d)
                    d += _ONE_DAY
        return cls(name=name, first_day=first_day, last_day=last_day, closures=frozenset(closures))

    @classmethod
    def default(cls) -> SchoolCalendar:
        """The bundled CPS 2026-2027 calendar (provisional until verified)."""
        text = (
            resources.files("suspension_check.data")
            .joinpath("cps_2026_2027.json")
            .read_text("utf-8")
        )
        return cls.from_dict(json.loads(text))


def _ics_date(value: str) -> date:
    return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
