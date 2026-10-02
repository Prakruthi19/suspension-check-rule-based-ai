from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

pytest.importorskip("presidio_analyzer")

from suspension_check.ingest import ingest

from .conftest import EXAMPLES, load_json

SECRET = "Marcus Johnson pushed my son; call me at (773) 555-0142. Student ID 50123456."


def _raw(**extra):
    data = load_json(EXAMPLES / "scenario_a_two_day_no_notice.json")
    data.update(extra)
    return data


def test_description_is_redacted_before_validation():
    out = ingest(json.dumps(_raw(incident_description=SECRET)))
    d = out.facts.incident_description
    for s in ("Marcus", "Johnson", "555-0142", "50123456"):
        assert s not in d
    assert set(out.redacted_entities) >= {"PERSON", "PHONE_NUMBER", "STUDENT_ID"}


def test_original_text_never_reaches_any_output():
    from suspension_check.letters import Variant, render_text
    from suspension_check.report import check
    from suspension_check.rules import evaluate

    f = ingest(_raw(incident_description=SECRET)).facts
    blob = json.dumps(check(f)) + f.model_dump_json() + render_text(Variant.REVIEW, f, evaluate(f))
    for s in ("Marcus", "555-0142", "50123456"):
        assert s not in blob


def test_no_description_is_fine():
    assert ingest(_raw()).facts.incident_description is None
    assert ingest(_raw(incident_description="   ")).redacted_entities == ()


def test_non_object_rejected():
    with pytest.raises(ValueError):
        ingest("[1, 2]")


def test_wrong_type_still_fails_validation():
    with pytest.raises(ValidationError):
        ingest(_raw(incident_description=42))
