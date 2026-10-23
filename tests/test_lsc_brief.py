from __future__ import annotations

import json
from pathlib import Path

import pytest

from suspension_check.disparity import analyze
from suspension_check.lsc_brief import GENERIC_QUESTIONS, findings, questions, to_html

SYN = Path(__file__).parent.parent / "synthetic"


def _result(name, ext):
    exp = json.loads((SYN / "expected" / f"{name}.json").read_text(encoding="utf-8"))
    raw = (SYN / f"{name}.{ext}").read_bytes()
    return analyze(raw, f"{name}.{ext}", {"race_ethnicity": exp["enrollment"]})


def test_school_a_findings():
    kinds = [f.kind for f in findings(_result("school_a", "csv"))]
    assert kinds == [
        "risk_ratio",
        "documented_intervention_share",
        "subjective_share",
        "repeat_share",
    ]
    head = findings(_result("school_a", "csv"))[0].headline
    assert "2.7 times" in head and "all other students" in head


def test_school_b_compares_with_white_students():
    f = findings(_result("school_b", "xlsx"))[0]
    assert f.kind == "risk_ratio" and "3.2 times" in f.headline and "white students" in f.headline


def test_small_school_has_no_findings_and_three_generic_questions():
    r = _result("school_c_small", "csv")
    assert findings(r) == []
    assert questions(r) == GENERIC_QUESTIONS


@pytest.mark.parametrize(
    ("name", "ext"), [("school_a", "csv"), ("school_b", "xlsx"), ("school_c_small", "csv")]
)
def test_always_exactly_three_distinct_questions(name, ext):
    qs = questions(_result(name, ext))
    assert len(qs) == 3 and len(set(qs)) == 3


def test_brief_html_is_one_escaped_page():
    html = to_html(_result("school_a", "csv"), "<script>alert(1)</script> LSC")
    assert "<script>alert" not in html and "&lt;script&gt;" in html
    assert html.count('<ol class="q">') == 1
    assert "suppressed" in html  # the white group is too small to report
    assert "not legal advice" in html


def test_composition_finding_when_no_risk_ratio():
    r = {
        "oss_incidents": 30,
        "suppression_threshold": 10,
        "documented_intervention_share": None,
        "by_race_ethnicity": {
            "Black": {
                "risk_ratio": None,
                "composition_index": 1.8,
                "subjective_share": None,
                "repeat_share": None,
                "students_suspended": 20,
                "students_suspended_per_100": None,
                "risk_ratio_reference": "white",
            },
        },
    }
    assert [f.kind for f in findings(r)] == ["composition_index"]
    assert "1.8 times their share" in findings(r)[0].headline


def test_yes_no_groups_read_naturally():
    r = {
        "oss_incidents": 30,
        "suppression_threshold": 10,
        "documented_intervention_share": None,
        "by_iep": {
            "Yes": {
                "risk_ratio": 2.5,
                "composition_index": None,
                "subjective_share": None,
                "repeat_share": None,
                "students_suspended": 20,
                "students_suspended_per_100": 20.0,
                "risk_ratio_reference": "all other students",
            },
            "No": {
                "risk_ratio": None,
                "composition_index": None,
                "subjective_share": None,
                "repeat_share": 0.3,
                "students_suspended": 20,
                "students_suspended_per_100": None,
                "risk_ratio_reference": "all other students",
            },
        },
    }
    heads = [f.headline for f in findings(r)]
    assert heads[0].startswith("Students with an IEP were suspended")
    assert "students without an IEP" in heads[1]
