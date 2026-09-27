"""Every registered rule must have a fires fixture and a silent fixture."""

from __future__ import annotations

import pytest

from dueproc.facts import Facts
from dueproc.rules import Severity, all3, any3, evaluate, get_rule, is_no, registry, rule

from .conftest import FIXTURES, load_json

RULE_FIXTURES = sorted((FIXTURES / "rules").glob("*.json"))


@pytest.mark.parametrize("rule_obj", registry(), ids=lambda r: r.id)
def test_every_rule_has_fires_and_silent_fixture(rule_obj):
    for kind in ("fires", "silent"):
        assert (FIXTURES / "rules" / f"{rule_obj.id}_{kind}.json").exists(), (
            f"{rule_obj.id} is missing its {kind} fixture"
        )


@pytest.mark.parametrize("path", RULE_FIXTURES, ids=lambda p: p.stem)
def test_rule_fixture(path):
    doc = load_json(path)
    facts = Facts.model_validate(doc["facts"])
    result = get_rule(doc["rule"])(facts)
    expected = {"fires": True, "silent": False, "uncertain": None}[doc["expect"]]
    assert result is expected, doc["description"]


@pytest.mark.parametrize("path", RULE_FIXTURES, ids=lambda p: p.stem)
def test_evaluate_agrees_with_fixture(path):
    doc = load_json(path)
    fired = {f.rule_id: f for f in evaluate(Facts.model_validate(doc["facts"]))}
    if doc["expect"] == "silent":
        assert doc["rule"] not in fired
    else:
        flag = fired[doc["rule"]]
        assert flag.uncertain is (doc["expect"] == "uncertain")


def test_unknown_downgrades_assert_to_ask():
    doc = load_json(FIXTURES / "rules" / "IL-05_uncertain.json")
    flag = next(f for f in evaluate(Facts.model_validate(doc["facts"])) if f.rule_id == "IL-05")
    assert get_rule("IL-05").severity is Severity.ASSERT
    assert flag.severity is Severity.ASK


def test_every_rule_has_citation_quote_and_url():
    for r in registry():
        assert r.citation and r.quote and r.flag and r.action
        assert r.url.startswith("https://")


def test_rule_ids_are_unique_and_duplicate_registration_fails():
    ids = [r.id for r in registry()]
    assert len(ids) == len(set(ids))
    with pytest.raises(ValueError, match="duplicate"):
        rule(
            id="IL-01",
            layer="illinois",
            citation="x",
            url="https://example.org",
            quote="x",
            flag="x",
            action="x",
            severity=Severity.INFO,
        )(lambda f: False)


def test_no_rule_is_marked_reviewed_before_legal_review():
    # Flip this only after the Gate 3 legal review is logged in DECISIONS.md.
    assert not any(r.reviewed for r in registry())


@pytest.mark.parametrize(
    ("values", "all_expected", "any_expected"),
    [
        ((True, True), True, True),
        ((True, None), None, True),
        ((False, None), False, None),
        ((False, False), False, False),
        ((None, None), None, None),
    ],
)
def test_three_valued_logic(values, all_expected, any_expected):
    assert all3(*values) is all_expected
    assert any3(*values) is any_expected


def test_is_no():
    assert is_no("no") is True
    assert is_no("yes") is False
    assert is_no("unknown") is None
