"""Golden-file tests: a fixed Facts input must always produce the same letter.

A template change is a deliberate golden update with a DECISIONS.md entry.
"""

from __future__ import annotations

from datetime import date

import pytest

from dueproc.facts import Facts
from dueproc.letters import review_request
from dueproc.rules import evaluate

from .conftest import EXAMPLES, FIXTURES, load_json

GOLDENS = sorted((FIXTURES / "letters").glob("*.review_request.txt"))


@pytest.mark.parametrize("golden", GOLDENS, ids=lambda p: p.name.split(".")[0])
def test_review_request_matches_golden(golden):
    name = golden.name.split(".")[0]
    facts = Facts.model_validate(load_json(EXAMPLES / f"{name}.json"))
    letter = review_request(facts, evaluate(facts), date(2026, 9, 27))
    assert letter == golden.read_text(encoding="utf-8")


def test_letter_is_stable_across_runs():
    facts = Facts.model_validate(load_json(EXAMPLES / "scenario_b_iep_cumulative_twelve.json"))
    a = review_request(facts, evaluate(facts), date(2026, 9, 27))
    b = review_request(facts, evaluate(facts), date(2026, 9, 27))
    assert a == b


def test_paragraphs_follow_flags():
    facts = Facts.model_validate(load_json(EXAMPLES / "scenario_a_two_day_no_notice.json"))
    letter = review_request(facts, evaluate(facts), date(2026, 9, 27))
    assert "34 CFR 300.530(e)" not in letter  # no IEP, no MDR paragraph
    assert "the reasons for the suspension" in letter
    assert "equivalent academic credit" in letter


def test_504_and_basis_of_knowledge_paragraphs():
    base = load_json(EXAMPLES / "scenario_a_two_day_no_notice.json")
    base["removal"]["school_days"] = 12
    base["student"]["disability"] = {"plan_504": True}
    base["idea"] = {"reevaluation_504_done": "no"}
    f = Facts.model_validate(base)
    assert "34 CFR 104.35" in review_request(f, evaluate(f), date(2026, 9, 27))
    base["student"]["disability"] = {"evaluation_requested_in_writing": True}
    f = Facts.model_validate(base)
    assert "34 CFR 300.534" in review_request(f, evaluate(f), date(2026, 9, 27))
