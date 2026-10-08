"""Regenerate tests/fixtures/ics/*.ics. A change here is a deliberate golden update."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from suspension_check.calendar import SchoolCalendar
from suspension_check.ics import to_ics
from suspension_check.ingest import ingest
from suspension_check.timeline import build_timeline

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "fixtures" / "ics"

for path in sorted((ROOT / "examples").glob("scenario_*.json")):
    facts = ingest(path.read_text(encoding="utf-8")).facts
    ics = to_ics(build_timeline(facts, SchoolCalendar.default()), date(2026, 9, 27))
    (OUT / f"{path.stem}.ics").write_bytes(ics.encode("utf-8"))
    print(OUT / f"{path.stem}.ics")
