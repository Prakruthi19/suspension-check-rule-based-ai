from __future__ import annotations

import pytest
from pydantic import ValidationError

from suspension_check.facts import Facts


def _facts(**overrides):
    base = {
        "incident_date": "2026-09-21",
        "removal": {
            "kind": "oss",
            "decision_date": "2026-09-21",
            "start_date": "2026-09-22",
            "school_days": 2,
        },
    }
    base.update(overrides)
    return Facts.model_validate(base)


def test_phone_only_notice_means_notice_contents_are_no():
    f = _facts(notice={"received": "phone_only", "states_reasons": "yes"})
    assert f.notice.states_reasons == "no"
    assert f.notice.cites_zero_tolerance == "unknown"


def test_decision_before_incident_is_rejected():
    with pytest.raises(ValidationError, match="decision_date"):
        _facts(incident_date="2026-09-25")


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        _facts(student={"favourite_colour": "blue"})


def test_dates_must_be_dates():
    with pytest.raises(ValidationError):
        _facts(incident_date="last tuesday")


def test_cumulative_and_change_of_placement():
    f = _facts(prior={"school_days_this_year": 3})
    assert f.cumulative_days == 5
    assert f.is_change_of_placement is False
    assert _facts(prior={"school_days_this_year": 9}).is_change_of_placement is None
    assert _facts(prior={}).is_change_of_placement is None
    long = _facts(
        removal={
            "kind": "oss",
            "decision_date": "2026-09-21",
            "start_date": "2026-09-22",
            "school_days": 11,
        }
    )
    assert long.is_change_of_placement is True


def test_basis_of_knowledge():
    f = _facts(student={"disability": {"being_evaluated": True}})
    assert f.student.disability.basis_of_knowledge
    assert f.student.disability.idea_protected
    g = _facts(student={"disability": {"iep": True, "being_evaluated": True}})
    assert not g.student.disability.basis_of_knowledge
