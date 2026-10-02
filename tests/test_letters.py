"""Golden-file tests: a fixed Facts input must always produce the same letter.

A template change is a deliberate golden update (tools/update_letter_goldens.py)
with a DECISIONS.md entry.
"""

from __future__ import annotations

import io
from datetime import date

import pytest
from docx import Document

from suspension_check.facts import Facts
from suspension_check.letters import TITLES, Variant, applicable, render_text, review_request
from suspension_check.letters.formats import paragraphs, to_docx, to_html
from suspension_check.report import DISCLAIMER
from suspension_check.rules import evaluate

from .conftest import EXAMPLES, FIXTURES, load_json

TODAY = date(2026, 9, 27)
GOLDENS = sorted((FIXTURES / "letters").glob("*.txt"))


def _facts(name: str) -> Facts:
    return Facts.model_validate(load_json(EXAMPLES / f"{name}.json"))


def _parts(golden):
    scenario, variant, _ = golden.name.split(".")
    return scenario, Variant(variant)


@pytest.mark.parametrize("golden", GOLDENS, ids=lambda p: p.stem)
def test_text_matches_golden(golden):
    scenario, variant = _parts(golden)
    f = _facts(scenario)
    assert render_text(variant, f, evaluate(f), TODAY) == golden.read_text(encoding="utf-8")


@pytest.mark.parametrize("golden", GOLDENS, ids=lambda p: p.stem)
def test_html_matches_golden(golden):
    scenario, variant = _parts(golden)
    f = _facts(scenario)
    html = to_html(render_text(variant, f, evaluate(f), TODAY), TITLES[variant])
    assert html == golden.with_suffix(".html").read_text(encoding="utf-8")


@pytest.mark.parametrize("golden", GOLDENS, ids=lambda p: p.stem)
def test_docx_has_the_same_words(golden):
    _, variant = _parts(golden)
    text = golden.read_text(encoding="utf-8")
    doc = Document(io.BytesIO(to_docx(text, TITLES[variant])))
    body = [p.text for p in doc.paragraphs]
    for block in paragraphs(text):
        assert "\n".join(block) in body
    assert DISCLAIMER in body
    assert doc.core_properties.author == ""


def test_every_scenario_and_variant_has_a_golden():
    for path in sorted(EXAMPLES.glob("scenario_*.json")):
        f = Facts.model_validate(load_json(path))
        for v in applicable(f, evaluate(f)):
            assert (FIXTURES / "letters" / f"{path.stem}.{v.value}.txt").exists()


def test_letter_is_stable_across_runs():
    f = _facts("scenario_b_iep_cumulative_twelve")
    assert render_text(Variant.MDR, f, evaluate(f), TODAY) == render_text(
        Variant.MDR, f, evaluate(f), TODAY
    )


def test_applicable_variants():
    a, b, c = (
        _facts(n)
        for n in (
            "scenario_a_two_day_no_notice",
            "scenario_b_iep_cumulative_twelve",
            "scenario_c_expulsion_hearing",
        )
    )
    assert applicable(a, evaluate(a)) == [Variant.REVIEW, Variant.RECORDS]
    assert applicable(b, evaluate(b)) == [Variant.REVIEW, Variant.MDR, Variant.RECORDS]
    assert applicable(c, evaluate(c)) == [Variant.EXPULSION, Variant.RECORDS]


def test_paragraphs_follow_flags():
    f = _facts("scenario_a_two_day_no_notice")
    letter = review_request(f, evaluate(f), TODAY)
    assert "34 CFR 300.530(e)" not in letter  # no IEP, no MDR paragraph
    assert "the reasons for the suspension" in letter
    assert "equivalent academic credit" in letter


def test_504_and_basis_of_knowledge_paragraphs():
    base = load_json(EXAMPLES / "scenario_a_two_day_no_notice.json")
    base["removal"]["school_days"] = 12
    base["student"]["disability"] = {"plan_504": True}
    base["idea"] = {"reevaluation_504_done": "no"}
    f = Facts.model_validate(base)
    assert "34 CFR 104.35" in review_request(f, evaluate(f), TODAY)
    base["student"]["disability"] = {"evaluation_requested_in_writing": True}
    f = Facts.model_validate(base)
    assert "34 CFR 300.534" in review_request(f, evaluate(f), TODAY)
    assert "basis of knowledge" in render_text(Variant.MDR, f, evaluate(f), TODAY)


def test_expulsion_continuance_only_when_hearing_is_close():
    f = _facts("scenario_c_expulsion_hearing")
    near = render_text(Variant.EXPULSION, f, evaluate(f), date(2026, 9, 28))
    far = render_text(Variant.EXPULSION, f, evaluate(f), date(2026, 9, 18))
    assert "continuance" in near and "continuance" not in far


def test_expulsion_without_certified_mail_and_firearm():
    base = load_json(EXAMPLES / "scenario_c_expulsion_hearing.json")
    base["expulsion"]["hearing_request_by_certified_mail"] = "no"
    base["expulsion"]["firearm"] = True
    f = Facts.model_validate(base)
    text = render_text(Variant.EXPULSION, f, evaluate(f), TODAY)
    assert "registered or certified mail" in text and "case-by-case" in text


def test_html_escapes_text():
    html = to_html('<script>alert("x")</script>', "t")
    assert "<script>alert" not in html and "&lt;script&gt;" in html
    assert DISCLAIMER in html
