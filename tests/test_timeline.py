from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from suspension_check.calendar import SchoolCalendar
from suspension_check.facts import Facts
from suspension_check.timeline import (
    IDEA_TRANSITIONS,
    MAIN_TRANSITIONS,
    IdeaState,
    InvalidTransition,
    Machine,
    MainState,
    Unit,
    build_timeline,
)

from .conftest import EXAMPLES, load_json

CPS = SchoolCalendar.default()


def facts(**kw) -> Facts:
    base = {
        "student": {"district": "cps"},
        "incident_date": "2026-09-21",
        "removal": {
            "kind": "oss",
            "decision_date": "2026-09-22",
            "start_date": "2026-09-23",
            "school_days": 7,
        },
        "prior": {"school_days_this_year": 5},
    }
    for k, v in kw.items():
        base[k] = {**base.get(k, {}), **v} if isinstance(v, dict) else v
    return Facts.model_validate(base)


def test_scenario_b_dates():
    t = build_timeline(
        Facts.model_validate(load_json(EXAMPLES / "scenario_b_iep_cumulative_twelve.json")), CPS
    )
    assert t.by_id("last_day").due == date(2026, 10, 1)
    assert t.by_id("return").due == date(2026, 10, 2)
    assert t.by_id("tenth_day").due == date(2026, 9, 29)
    assert t.by_id("mdr").due == date(2026, 10, 6)
    assert t.by_id("safeguards_notice").due == date(2026, 9, 22)
    assert t.idea.state is IdeaState.MDR_DUE


def test_no_idea_track_without_protection():
    t = build_timeline(facts(), CPS)
    assert t.idea.state is IdeaState.NOT_TRACKED
    assert t.by_id("mdr") is None


def test_records_clock_and_review_state():
    t = build_timeline(
        facts(actions={"records_requested_on": "2026-09-23", "review_requested_on": "2026-09-23"}),
        CPS,
    )
    assert t.by_id("records").due == date(2026, 10, 15)  # 15 school days, skipping Oct 12
    assert t.main.state is MainState.REVIEW_REQUESTED


def test_mdr_result_and_expedited_hearing():
    t = build_timeline(
        facts(
            student={"disability": {"iep": True}},
            removal={
                "kind": "oss",
                "decision_date": "2026-09-22",
                "start_date": "2026-09-23",
                "school_days": 11,
            },
            idea={"mdr_result": "not_manifestation", "parent_disagrees_with_mdr": True},
            actions={"expedited_hearing_requested_on": "2026-10-05"},
        ),
        CPS,
    )
    assert t.idea.state is IdeaState.EXPEDITED_HEARING_REQUESTED
    assert t.by_id("expedited_hearing").due == date(2026, 11, 3)


def test_expulsion_obligations():
    t = build_timeline(
        Facts.model_validate(load_json(EXAMPLES / "scenario_c_expulsion_hearing.json")), CPS
    )
    assert t.by_id("expulsion_hearing").due == date(2026, 10, 2)


def test_clock_past_year_end_has_note_not_date():
    t = build_timeline(
        facts(
            student={"disability": {"iep": True}},
            incident_date="2027-06-01",
            removal={
                "kind": "expulsion",
                "decision_date": "2027-06-01",
                "start_date": "2027-06-02",
                "school_days": 10,
            },
        ),
        CPS,
    )
    mdr = t.by_id("mdr")
    assert mdr.due is None and "end of the school year" in mdr.note


def test_machine_rejects_illegal_event():
    m = Machine(MAIN_TRANSITIONS, MainState.INCIDENT)
    with pytest.raises(InvalidTransition):
        m.fire("decision_issued")


# --- property tests --------------------------------------------------------------

removal_kinds = st.sampled_from(["oss", "iss", "bus", "expulsion", "alternative", "informal"])


@st.composite
def random_facts(draw, days=None):
    start = draw(st.dates(min_value=date(2026, 8, 17), max_value=date(2027, 5, 1)))
    return facts(
        student={"disability": {"iep": draw(st.booleans()), "plan_504": draw(st.booleans())}},
        incident_date=start.isoformat(),
        removal={
            "kind": draw(removal_kinds),
            "decision_date": start.isoformat(),
            "start_date": start.isoformat(),
            "school_days": days if days is not None else draw(st.integers(0, 30)),
            "special_circumstances": draw(st.booleans()),
        },
        prior={"school_days_this_year": draw(st.none() | st.integers(0, 20))},
    )


@settings(max_examples=200)
@given(random_facts())
def test_school_day_deadlines_land_on_school_days(f):
    for o in build_timeline(f, CPS).obligations:
        if o.unit is Unit.SCHOOL_DAYS and o.due is not None:
            assert CPS.is_school_day(o.due), o


@settings(max_examples=200)
@given(random_facts(), st.integers(0, 20), st.integers(1, 10))
def test_adding_removal_days_never_moves_a_deadline_earlier(f, days, extra):
    shorter = f.model_copy(update={"removal": f.removal.model_copy(update={"school_days": days})})
    longer = f.model_copy(
        update={"removal": f.removal.model_copy(update={"school_days": days + extra})}
    )
    a, b = build_timeline(shorter, CPS), build_timeline(longer, CPS)
    for o in a.obligations:
        other = b.by_id(o.id)
        if o.due is not None and other is not None and other.due is not None:
            assert other.due >= o.due, o.id


@pytest.mark.parametrize(
    ("table", "initial", "states"),
    [
        (MAIN_TRANSITIONS, MainState.INCIDENT, MainState),
        (IDEA_TRANSITIONS, IdeaState.NOT_TRACKED, IdeaState),
    ],
)
@settings(max_examples=100)
@given(data=st.data())
def test_machine_never_reaches_invalid_state(table, initial, states, data):
    m = Machine(table, initial)
    for _ in range(data.draw(st.integers(0, 12))):
        allowed = m.allowed()
        if not allowed:
            break
        m.fire(data.draw(st.sampled_from(allowed)))
        assert m.state in set(states)
        assert m.state in table
