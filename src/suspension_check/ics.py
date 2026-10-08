"""Export the deadline timeline as an iCalendar (.ics) file.

A parent can add every upcoming deadline to their phone's calendar in one tap,
with a reminder two days before each. Only obligations with a due date on or
after ``today`` are exported; passed deadlines would only be noise.

The file carries rule titles, clocks, and citations, never facts about the
student. Output is deterministic for the same facts and ``today`` (DTSTAMP is
``today``, UIDs come from the obligation id and due date), so it can be
golden-tested. Nothing is written to disk.
"""

from __future__ import annotations

from datetime import date, timedelta

from suspension_check.timeline import Obligation, Timeline

__all__ = ["REMINDER_DAYS", "to_ics", "upcoming"]

REMINDER_DAYS = 2
_PRODID = "-//ChiEAC//Suspension Check//EN"
_NOTE = "From Suspension Check. Information, not legal advice. Check every date with the school."


def upcoming(timeline: Timeline, today: date) -> list[Obligation]:
    return [o for o in timeline.sorted() if o.due is not None and o.due >= today]


def _escape(text: str) -> str:
    """RFC 5545 TEXT escaping."""
    return text.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    """Fold to 75 octets per line (RFC 5545 3.1), never splitting a UTF-8 character."""
    out: list[str] = []
    cur, size, limit = "", 0, 75
    for ch in line:
        n = len(ch.encode("utf-8"))
        if size + n > limit:
            out.append(cur)
            cur, size, limit = " ", 1, 75
        cur += ch
        size += n
    out.append(cur)
    return out


def _clock(o: Obligation) -> str:
    if o.length is None:
        return o.unit.value
    unit = o.unit.value[:-1] if o.length == 1 and o.unit.value.endswith("s") else o.unit.value
    return f"{o.length} {unit}"


def to_ics(timeline: Timeline, today: date) -> str:
    stamp = f"{today:%Y%m%d}T000000Z"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{_PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Suspension Check deadlines",
    ]
    for o in upcoming(timeline, today):
        assert o.due is not None
        detail = [f"Clock: {_clock(o)}", f"Law: {o.authority}"]
        if o.note:
            detail.append(o.note)
        detail.append(_NOTE)
        lines += [
            "BEGIN:VEVENT",
            f"UID:{o.id}-{o.due:%Y%m%d}@suspension-check",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{o.due:%Y%m%d}",
            f"DTEND;VALUE=DATE:{o.due + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_escape(o.title)}",
            f"DESCRIPTION:{_escape(chr(10).join(detail))}",
            "TRANSP:TRANSPARENT",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_escape(o.title)}",
            f"TRIGGER:-P{REMINDER_DAYS}D",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "".join(f + "\r\n" for line in lines for f in _fold(line))
