"""Letters assembled from the flags that fired.

Four variants, each a Jinja2 plain-text template (the single source of the
wording). ``formats`` turns that text into a printable HTML page or a DOCX.
Fill-in fields the survey does not collect stay as [brackets] for the parent.
A change to any template is a deliberate golden update with a DECISIONS.md entry.
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import StrEnum

from jinja2 import Environment, PackageLoader, StrictUndefined

from suspension_check.calendar import SchoolCalendar
from suspension_check.facts import Facts, NoticeReceived, RemovalKind
from suspension_check.rules import Flag
from suspension_check.timeline import build_timeline, records_due_if_requested

__all__ = ["TITLES", "Variant", "applicable", "render_text", "review_request"]


class Variant(StrEnum):
    REVIEW = "review_request"
    MDR = "mdr_request"
    RECORDS = "records_request"
    EXPULSION = "expulsion_response"


TITLES = {
    Variant.REVIEW: "Request for review of the suspension",
    Variant.MDR: "Request for a manifestation determination review",
    Variant.RECORDS: "Request for school records",
    Variant.EXPULSION: "Response to the expulsion hearing",
}

_env = Environment(
    loader=PackageLoader("suspension_check.letters", "templates"),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    autoescape=False,  # plain-text output; the HTML renderer escapes separately
)

_KIND_PHRASE = {
    RemovalKind.OSS: "out-of-school suspension",
    RemovalKind.ISS: "in-school suspension",
    RemovalKind.BUS: "bus suspension",
    RemovalKind.INFORMAL: "removal from school (my child was sent home)",
    RemovalKind.EXPULSION: "recommended expulsion",
    RemovalKind.ALTERNATIVE: "transfer to an alternative school",
    RemovalKind.OTHER: "disciplinary removal",
}
_SUSPENSIONS = {RemovalKind.OSS, RemovalKind.ISS, RemovalKind.BUS, RemovalKind.INFORMAL}


def _join_or(items: list[str]) -> str:
    if len(items) <= 2:
        return " or ".join(items)
    return ", ".join(items[:-1]) + ", or " + items[-1]


_env.filters["join_or"] = _join_or


def _long(d: date | None) -> str | None:
    return None if d is None else f"{d:%B} {d.day}, {d.year}"


def applicable(facts: Facts, flags: list[Flag]) -> list[Variant]:
    """Which letters make sense for these facts, in the order a parent needs them."""
    fired = {f.rule_id for f in flags}
    out: list[Variant] = []
    if facts.removal.kind is RemovalKind.EXPULSION:
        out.append(Variant.EXPULSION)
    elif facts.removal.kind in _SUSPENSIONS:
        out.append(Variant.REVIEW)
    if fired & {"FED-02", "FED-03", "FED-07"}:
        out.append(Variant.MDR)
    out.append(Variant.RECORDS)
    return out


def render_text(
    variant: Variant | str,
    facts: Facts,
    flags: list[Flag],
    today: date | None = None,
    cal: SchoolCalendar | None = None,
) -> str:
    variant = Variant(variant)
    today = today or date.today()
    cal = cal or SchoolCalendar.default()
    fired = {f.rule_id for f in flags}
    r = facts.removal
    timeline = build_timeline(facts, cal)
    mdr = timeline.by_id("mdr")
    e = facts.expulsion
    hearing = e.hearing_date if e else None
    ctx = {
        "today": _long(today),
        "kind": _KIND_PHRASE[r.kind],
        "days": r.school_days,
        "incident_date": _long(facts.incident_date),
        "decision_date": _long(r.decision_date),
        "cumulative": facts.cumulative_days,
        "fired": fired,
        "written_notice": facts.notice.received is NoticeReceived.WRITTEN,
        "notice_defects": bool(fired & {"IL-01", "IL-03", "IL-04", "IL-05"}),
        "missing": [
            text
            for rid, text in (
                ("IL-01", "the reasons for the suspension"),
                ("IL-03", "the specific act of gross disobedience or misconduct"),
                ("IL-04", "the rationale for the length of the suspension"),
                (
                    "IL-05",
                    "whether other appropriate and available interventions were attempted "
                    "before a suspension longer than three days was imposed",
                ),
            )
            if rid in fired
        ],
        "threat_finding": "IL-06" in fired or "IL-07" in fired,
        "idea": facts.student.disability.idea_protected,
        "basis_of_knowledge": "FED-07" in fired,
        "section_504": "FED-08" in fired,
        "records": "IL-15" in fired,
        "support_services": "IL-08" in fired,
        "makeup_work": "IL-09" in fired,
        "safeguards": "FED-03" in fired,
        "services": "FED-01" in fired,
        "informal": "FED-09" in fired,
        "mdr_due": _long(mdr.due) if mdr else None,
        "records_due": _long(records_due_if_requested(today, cal)),
        "hearing_date": _long(hearing),
        "no_certified_mail": "IL-12" in fired,
        "decision_incomplete": "IL-13" in fired,
        "firearm": "IL-17" in fired,
        "support_person": True,
        # Ask for more time if the hearing is a week away or less, or was not properly noticed.
        "continuance": "IL-12" in fired
        or (hearing is not None and hearing - today <= timedelta(days=7)),
    }
    if variant is Variant.REVIEW:
        # The review letter keeps its Week 2 meaning of "idea": MDR paragraph only when flagged.
        ctx["idea"] = bool(fired & {"FED-02", "FED-03"})
    return _env.get_template(f"{variant.value}.txt.j2").render(**ctx)


def review_request(facts: Facts, flags: list[Flag], today: date | None = None) -> str:
    """The suspension review request (Appendix F). Kept for the Week 2 API."""
    return render_text(Variant.REVIEW, facts, flags, today)
