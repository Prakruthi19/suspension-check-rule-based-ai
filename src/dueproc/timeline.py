"""Deterministic deadline timeline.

Two finite-state machines run side by side: the main track (Illinois process)
and the IDEA track (students with an IEP or a basis of knowledge). Facts are
replayed as a fixed sequence of events; each transition emits dated
``Obligation`` objects. Every clock carries its unit explicitly; nothing is
assumed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Generic, TypeVar

from dueproc.calendar import BeyondSchoolYear, SchoolCalendar
from dueproc.facts import Facts, ManifestationResult, NoticeReceived, RemovalKind

__all__ = [
    "IdeaState",
    "InvalidTransition",
    "Machine",
    "MainState",
    "Obligation",
    "Timeline",
    "Unit",
    "build_timeline",
]


# --- state machines ------------------------------------------------------------


class MainState(StrEnum):
    INCIDENT = "Incident"
    NOTICE_ISSUED = "NoticeIssued"
    REMOVAL = "Removal"
    REVIEW_REQUESTED = "ReviewRequested"
    DECISION_ISSUED = "DecisionIssued"
    CLOSED = "Closed"


class IdeaState(StrEnum):
    NOT_TRACKED = "NotTracked"
    CUMULATIVE_DAYS_TRACKED = "CumulativeDaysTracked"
    CHANGE_OF_PLACEMENT = "ChangeOfPlacement"
    MDR_DUE = "MDRDue"
    MDR_HELD = "MDRHeld"
    MANIFESTATION = "Manifestation"
    NOT_MANIFESTATION = "NotManifestation"
    EXPEDITED_HEARING_REQUESTED = "ExpeditedHearingRequested"


MAIN_TRANSITIONS: dict[MainState, dict[str, MainState]] = {
    MainState.INCIDENT: {
        "notice_issued": MainState.NOTICE_ISSUED,
        "removal_started": MainState.REMOVAL,
    },
    MainState.NOTICE_ISSUED: {"removal_started": MainState.REMOVAL},
    MainState.REMOVAL: {
        "review_requested": MainState.REVIEW_REQUESTED,
        "decision_issued": MainState.DECISION_ISSUED,
        "closed": MainState.CLOSED,
    },
    MainState.REVIEW_REQUESTED: {"decision_issued": MainState.DECISION_ISSUED},
    MainState.DECISION_ISSUED: {"closed": MainState.CLOSED},
    MainState.CLOSED: {},
}

IDEA_TRANSITIONS: dict[IdeaState, dict[str, IdeaState]] = {
    IdeaState.NOT_TRACKED: {"track": IdeaState.CUMULATIVE_DAYS_TRACKED},
    IdeaState.CUMULATIVE_DAYS_TRACKED: {"change_of_placement": IdeaState.CHANGE_OF_PLACEMENT},
    IdeaState.CHANGE_OF_PLACEMENT: {"mdr_due": IdeaState.MDR_DUE},
    IdeaState.MDR_DUE: {"mdr_held": IdeaState.MDR_HELD},
    IdeaState.MDR_HELD: {
        "manifestation": IdeaState.MANIFESTATION,
        "not_manifestation": IdeaState.NOT_MANIFESTATION,
    },
    IdeaState.MANIFESTATION: {"expedited_hearing": IdeaState.EXPEDITED_HEARING_REQUESTED},
    IdeaState.NOT_MANIFESTATION: {"expedited_hearing": IdeaState.EXPEDITED_HEARING_REQUESTED},
    IdeaState.EXPEDITED_HEARING_REQUESTED: {},
}


class InvalidTransition(RuntimeError):
    pass


S = TypeVar("S", bound=StrEnum)


class Machine(Generic[S]):
    """A tiny table-driven FSM. Unknown events raise; there is no implicit state."""

    def __init__(self, table: dict[S, dict[str, S]], initial: S) -> None:
        self.table = table
        self.state = initial
        self.history: list[S] = [initial]

    def allowed(self) -> list[str]:
        return sorted(self.table[self.state])

    def fire(self, event: str) -> S:
        try:
            nxt = self.table[self.state][event]
        except KeyError:
            raise InvalidTransition(f"{event!r} is not allowed from {self.state}") from None
        self.state = nxt
        self.history.append(nxt)
        return nxt


# --- obligations -----------------------------------------------------------------


class Unit(StrEnum):
    SCHOOL_DAYS = "school days"
    CALENDAR_DAYS = "calendar days"
    SAME_DAY = "same day"
    IMMEDIATELY = "immediately"
    NONE = "no clock"


@dataclass(frozen=True)
class Obligation:
    id: str
    title: str
    track: str  # "main" or "idea"
    clock_start: date | None
    length: int | None
    unit: Unit
    authority: str
    due: date | None
    note: str = ""

    def status(self, today: date) -> str:
        if self.due is None:
            return "info"
        if self.due < today:
            return "passed"
        if self.due == today:
            return "today"
        return "upcoming"

    def as_dict(self, today: date) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "track": self.track,
            "clock_start": self.clock_start.isoformat() if self.clock_start else None,
            "length": self.length,
            "unit": self.unit.value,
            "authority": self.authority,
            "due": self.due.isoformat() if self.due else None,
            "status": self.status(today),
            "note": self.note,
        }


@dataclass
class Timeline:
    obligations: list[Obligation] = field(default_factory=list)
    main: Machine[MainState] = field(
        default_factory=lambda: Machine(MAIN_TRANSITIONS, MainState.INCIDENT)
    )
    idea: Machine[IdeaState] = field(
        default_factory=lambda: Machine(IDEA_TRANSITIONS, IdeaState.NOT_TRACKED)
    )

    def by_id(self, oid: str) -> Obligation | None:
        return next((o for o in self.obligations if o.id == oid), None)

    def sorted(self) -> list[Obligation]:
        far = date.max
        return sorted(self.obligations, key=lambda o: (o.due or far, o.track, o.id))


# --- builder -----------------------------------------------------------------------

RECORDS_RESPONSE_SCHOOL_DAYS = 15  # Appendix B; ISSRA text to be confirmed (DECISIONS.md)
MDR_SCHOOL_DAYS = 10
EXPEDITED_HEARING_SCHOOL_DAYS = 20
EXPEDITED_DECISION_SCHOOL_DAYS = 10
IAES_MAX_SCHOOL_DAYS = 45


def _school_days(
    cal: SchoolCalendar, start: date, n: int, *, counting_start: bool = False
) -> tuple[date | None, str]:
    try:
        due = cal.nth_school_day(start, n) if counting_start else cal.add_school_days(start, n)
    except BeyondSchoolYear:
        return (
            None,
            "This clock runs past the end of the school year; ask the district for the date.",
        )
    return due, ""


def build_timeline(facts: Facts, cal: SchoolCalendar | None = None) -> Timeline:
    cal = cal or SchoolCalendar.default()
    t = Timeline()
    r = facts.removal
    emit = t.obligations.append

    # Main track -----------------------------------------------------------------
    if facts.notice.received is NoticeReceived.WRITTEN:
        t.main.fire("notice_issued")
    due, note = _school_days(cal, r.decision_date, 1)
    emit(
        Obligation(
            id="notice",
            title="Written notice with reasons and your right to a review",
            track="main",
            clock_start=r.decision_date,
            length=None,
            unit=Unit.IMMEDIATELY,
            authority="105 ILCS 5/10-22.6(b)",
            due=due,
            note=note
            or "The law says immediately; the tool flags it if not received by the next school day.",
        )
    )

    t.main.fire("removal_started")
    if r.kind in {RemovalKind.OSS, RemovalKind.ISS, RemovalKind.BUS} and r.school_days > 0:
        last, note = _school_days(cal, r.start_date, r.school_days, counting_start=True)
        emit(
            Obligation(
                id="last_day",
                title=f"Last day of the {r.school_days}-school-day suspension",
                track="main",
                clock_start=r.start_date,
                length=r.school_days,
                unit=Unit.SCHOOL_DAYS,
                authority="105 ILCS 5/10-22.6(b)",
                due=last,
                note=note,
            )
        )
        if last is not None:
            back, note = _school_days(cal, last, 1)
            emit(
                Obligation(
                    id="return",
                    title="Expected return to school; make-up work for equivalent credit",
                    track="main",
                    clock_start=last,
                    length=1,
                    unit=Unit.SCHOOL_DAYS,
                    authority="105 ILCS 5/10-22.6(b-30)",
                    due=back,
                    note=note,
                )
            )

    if r.kind is RemovalKind.EXPULSION and facts.expulsion is not None:
        e = facts.expulsion
        if e.hearing_date is not None:
            emit(
                Obligation(
                    id="expulsion_hearing",
                    title="Expulsion hearing",
                    track="main",
                    clock_start=None,
                    length=None,
                    unit=Unit.NONE,
                    authority="105 ILCS 5/10-22.6(a)",
                    due=e.hearing_date,
                    note="Bring the notice, any records you received, and a support person.",
                )
            )
        if e.length_calendar_days:
            emit(
                Obligation(
                    id="expulsion_max",
                    title="Latest possible end of the expulsion (2 calendar years)",
                    track="main",
                    clock_start=r.start_date,
                    length=2,
                    unit=Unit.CALENDAR_DAYS,
                    authority="105 ILCS 5/10-22.6(a)",
                    due=_add_years(r.start_date, 2),
                )
            )

    if facts.actions.review_requested_on is not None:
        t.main.fire("review_requested")

    if facts.actions.records_requested_on is not None:
        due, note = _school_days(
            cal, facts.actions.records_requested_on, RECORDS_RESPONSE_SCHOOL_DAYS
        )
        emit(
            Obligation(
                id="records",
                title="School must give you access to the records you requested",
                track="main",
                clock_start=facts.actions.records_requested_on,
                length=RECORDS_RESPONSE_SCHOOL_DAYS,
                unit=Unit.SCHOOL_DAYS,
                authority="105 ILCS 10/5 (ISSRA)",
                due=due,
                note=note or "Length pending confirmation against the current ISSRA text.",
            )
        )

    # IDEA track -------------------------------------------------------------------
    disability = facts.student.disability
    if disability.idea_protected:
        t.idea.fire("track")
        prior = facts.prior.school_days_this_year
        if prior is not None and prior < 10 <= prior + r.school_days:
            tenth, note = _school_days(cal, r.start_date, 10 - prior, counting_start=True)
            emit(
                Obligation(
                    id="tenth_day",
                    title="10th cumulative school day removed this year; services must continue after it",
                    track="idea",
                    clock_start=r.start_date,
                    length=10 - prior,
                    unit=Unit.SCHOOL_DAYS,
                    authority="34 CFR 300.530(d)",
                    due=tenth,
                    note=note,
                )
            )

        cop = facts.is_change_of_placement
        if cop is not False:
            t.idea.fire("change_of_placement")
            maybe = "" if cop else "Possible change of placement (pattern of removals). "
            emit(
                Obligation(
                    id="safeguards_notice",
                    title="Same-day notice of the decision and the procedural safeguards notice",
                    track="idea",
                    clock_start=r.decision_date,
                    length=0,
                    unit=Unit.SAME_DAY,
                    authority="34 CFR 300.530(h)",
                    due=r.decision_date,
                    note=maybe.strip(),
                )
            )
            t.idea.fire("mdr_due")
            due, note = _school_days(cal, r.decision_date, MDR_SCHOOL_DAYS)
            emit(
                Obligation(
                    id="mdr",
                    title="Manifestation determination review must be held",
                    track="idea",
                    clock_start=r.decision_date,
                    length=MDR_SCHOOL_DAYS,
                    unit=Unit.SCHOOL_DAYS,
                    authority="34 CFR 300.530(e)",
                    due=due,
                    note=(maybe + note).strip(),
                )
            )
            result = facts.idea.mdr_result
            if result is not ManifestationResult.NOT_HELD:
                t.idea.fire("mdr_held")
                t.idea.fire(
                    "manifestation"
                    if result is ManifestationResult.MANIFESTATION
                    else "not_manifestation"
                )
                hearing_req = facts.actions.expedited_hearing_requested_on
                if hearing_req is not None:
                    t.idea.fire("expedited_hearing")
                    hearing, note = _school_days(cal, hearing_req, EXPEDITED_HEARING_SCHOOL_DAYS)
                    emit(
                        Obligation(
                            id="expedited_hearing",
                            title="Expedited due process hearing must occur",
                            track="idea",
                            clock_start=hearing_req,
                            length=EXPEDITED_HEARING_SCHOOL_DAYS,
                            unit=Unit.SCHOOL_DAYS,
                            authority="34 CFR 300.532(c)(2)",
                            due=hearing,
                            note=note
                            or "The hearing officer's decision is due within 10 school days after the hearing.",
                        )
                    )

        if r.special_circumstances:
            end, note = _school_days(cal, r.start_date, IAES_MAX_SCHOOL_DAYS, counting_start=True)
            emit(
                Obligation(
                    id="iaes_max",
                    title="Latest end of the interim alternative educational setting (45 school days)",
                    track="idea",
                    clock_start=r.start_date,
                    length=IAES_MAX_SCHOOL_DAYS,
                    unit=Unit.SCHOOL_DAYS,
                    authority="34 CFR 300.530(g)",
                    due=end,
                    note=note,
                )
            )

    return t


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29
        return d.replace(year=d.year + years, day=28)


def records_due_if_requested(on: date, cal: SchoolCalendar | None = None) -> date | None:
    """When the records would be due if the parent sends the request on ``on``."""
    cal = cal or SchoolCalendar.default()
    due, _ = _school_days(cal, on, RECORDS_RESPONSE_SCHOOL_DAYS)
    return due
