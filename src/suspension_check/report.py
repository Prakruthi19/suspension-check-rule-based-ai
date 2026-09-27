"""One call that runs rules and timeline together and returns plain data."""

from __future__ import annotations

from datetime import date

from suspension_check.calendar import SchoolCalendar
from suspension_check.facts import Facts
from suspension_check.rules import evaluate
from suspension_check.timeline import build_timeline, records_due_if_requested

DISCLAIMER = (
    "This is general information about Illinois and federal school discipline law, "
    "not legal advice. It does not know everything about your situation. Rule text is "
    "pending review by an attorney or experienced advocate. If you can, talk to one of "
    "the organizations below before a hearing or meeting."
)

# Draft resource card; contact details to be verified before the alpha (Week 4).
RESOURCES: list[dict[str, str]] = [
    {
        "name": "Equip for Equality",
        "for": "Special education and disability rights",
        "url": "https://www.equipforequality.org",
    },
    {
        "name": "Legal Aid Chicago",
        "for": "Free civil legal aid in Cook County, including education",
        "url": "https://www.legalaidchicago.org",
    },
    {
        "name": "Chicago Lawyers' Committee for Civil Rights",
        "for": "Civil rights and education equity",
        "url": "https://www.clccrul.org",
    },
    {
        "name": "Illinois State Board of Education",
        "for": "State complaints and special education dispute resolution",
        "url": "https://www.isbe.net",
    },
    {
        "name": "U.S. Department of Education, Office for Civil Rights",
        "for": "Discrimination complaints, including discipline and Section 504",
        "url": "https://www.ed.gov/about/offices/list/ocr/complaintintro.html",
    },
]


def check(facts: Facts, cal: SchoolCalendar | None = None, today: date | None = None) -> dict:
    cal = cal or SchoolCalendar.default()
    today = today or date.today()
    flags = evaluate(facts)
    timeline = build_timeline(facts, cal)
    return {
        "calendar": {"name": cal.name, "status": cal.status},
        "state": {"main": timeline.main.state.value, "idea": timeline.idea.state.value},
        "timeline": [o.as_dict(today) for o in timeline.sorted()],
        "flags": [f.as_dict() for f in flags],
        "records_due_if_requested_today": (
            None
            if facts.actions.records_requested_on
            else _iso(records_due_if_requested(today, cal))
        ),
        "disclaimer": DISCLAIMER,
        "resources": RESOURCES,
    }


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None
