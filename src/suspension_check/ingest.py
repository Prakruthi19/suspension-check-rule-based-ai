"""The only front door for untrusted input.

Order matters and is the privacy guarantee: parse JSON, redact every free-text
field, and only then validate. Nothing downstream (rules, timeline, letters,
logs) ever sees the original text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from suspension_check.facts import Facts

__all__ = ["FREE_TEXT_FIELDS", "Ingested", "ingest"]

# Dotted paths of every free-text field in the facts model.
FREE_TEXT_FIELDS = ("incident_description",)


@dataclass(frozen=True)
class Ingested:
    facts: Facts
    redacted_entities: tuple[str, ...]  # entity types removed, never the values


def ingest(raw: bytes | str | dict) -> Ingested:
    """Parse, redact, validate. Raises ``ValueError`` / ``pydantic.ValidationError``."""
    data = json.loads(raw) if isinstance(raw, bytes | str) else dict(raw)
    if not isinstance(data, dict):
        raise ValueError("facts must be a JSON object")
    entities: list[str] = []
    for field in FREE_TEXT_FIELDS:
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            from suspension_check.redact import redact  # optional extra; import on use

            r = redact(value)
            data[field] = r.text
            entities.extend(r.entities)
    return Ingested(facts=Facts.model_validate(data), redacted_entities=tuple(entities))
