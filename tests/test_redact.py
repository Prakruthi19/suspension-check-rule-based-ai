"""Adversarial redaction fixtures. Synthetic names, numbers and addresses only."""

from __future__ import annotations

import pytest

pytest.importorskip("presidio_analyzer")

from suspension_check.redact import MAX_TEXT_CHARS, redact

from .conftest import FIXTURES, load_json

ADVERSARIAL = load_json(FIXTURES / "redact" / "adversarial.json")
KEEP = load_json(FIXTURES / "redact" / "keep.json")


@pytest.mark.parametrize("case", ADVERSARIAL, ids=lambda c: c["id"])
def test_secrets_never_survive(case):
    out = redact(case["text"])
    for secret in case["secrets"]:
        assert secret not in out.text, f"{secret!r} survived: {out.text}"
    assert out.changed


@pytest.mark.parametrize("case", KEEP, ids=lambda c: c["id"])
def test_useful_facts_are_kept(case):
    out = redact(case["text"])
    for keep in case["keep"]:
        assert keep in out.text, f"{keep!r} was removed: {out.text}"


def test_placeholders_are_typed():
    out = redact("Call Marcus Johnson at (773) 555-0142.")
    assert "<PERSON>" in out.text and "<PHONE>" in out.text
    assert out.entities == ("PERSON", "PHONE_NUMBER")


def test_input_is_bounded():
    assert len(redact("a" * (MAX_TEXT_CHARS + 500)).text) == MAX_TEXT_CHARS


def test_empty_text():
    out = redact("")
    assert out.text == "" and not out.changed
