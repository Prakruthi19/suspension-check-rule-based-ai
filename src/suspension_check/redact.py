"""Redaction on ingest.

Runs before validation, rules, templating, and logging on every free-text
field. Names, phone numbers, emails, street addresses, and student ID patterns
are replaced with typed placeholders such as ``<PERSON>``.

Presidio (with the small English spaCy model) finds names; everything else is
an explicit regex recognizer so its behaviour is testable and needs no network.
Presidio's built-in email and URL recognizers are removed because they call
out to the public suffix list on first use.

Requires the ``redact`` extra: ``pip install "suspension-check-rule-based-ai[redact]"``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

__all__ = ["MAX_TEXT_CHARS", "Redaction", "redact"]

MAX_TEXT_CHARS = 1000

# Typed placeholders, one per entity the tool removes.
PLACEHOLDERS = {
    "PERSON": "<PERSON>",
    "PHONE_NUMBER": "<PHONE>",
    "EMAIL_ADDRESS": "<EMAIL>",
    "STREET_ADDRESS": "<ADDRESS>",
    "STUDENT_ID": "<STUDENT_ID>",
    "US_SSN": "<SSN>",
}

_PHONE = r"(?<!\w)(?:\+?1[\s.\-]?)?(?:\(\s*\d{3}\s*\)|\d{3})[\s.\-]*\d{3}[\s.\-]*\d{4}(?!\w)"
_EMAIL = r"\b[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+\b"
_STREET = (
    r"\b\d{1,6}\s+(?:[NSEW]\.?\s+)?(?:[A-Z][a-z]+\.?\s+){1,3}"
    r"(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Ct|Court|Pl|Place|Ln|Lane|Pkwy|Parkway|Way|Ter|Terrace)\b\.?"
    r"(?:\s*(?:Apt|Unit|#)\s*\w+)?"
)
# Student IDs: a run of 6 to 10 digits, near words like "ID", "student", "#".
_STUDENT_ID = r"\b\d{6,10}\b"
_STUDENT_ID_CONTEXT = ["id", "student", "number", "no", "cps", "#"]
_SSN = r"\b\d{3}-\d{2}-\d{4}\b"
# Bare ID-shaped numbers with an explicit cue are always removed, even if
# Presidio's context scoring misses the cue.
_CUED_ID = re.compile(
    r"(?i)(?:student\s*(?:id|number|no\.?|#)|\bid\s*(?:number|no\.?|#)?|#)\s*[:#]?\s*(\d{5,10})\b"
)

# Names after a cue word ("Student: Jamal Carter", "Mr. Patel", "call Marcus
# Johnson"). The small spaCy model misses short or sentence-initial names; a cue
# is strong evidence even when the model is unsure.
_CUED_NAME = re.compile(
    r"(?:\b(?:[Ss]tudent|[Pp]arent|[Gg]uardian|[Tt]eacher|[Pp]rincipal|[Dd]ean|[Cc]all|[Cc]ontact|[Nn]amed|[Ss]on|[Dd]aughter|[Cc]hild)\b\s*:?\s+"
    r"|\b(?:Mr|Ms|Mrs|Miss|Dr)\.?\s+)"
    r"(?!(?:ID|Grade|Number|Assistant|Principal|Dean|Teacher|Counselor)\b)([A-Z][a-z]+(?:[-'][A-Z][a-z]+)?(?:\s+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?)?)"
)
_NAME_TOKEN = re.compile(r"[A-Z][a-z]{2,}(?:[-'][A-Z][a-z]+)?")
# Capitalized words that are never names in this context.
_NOT_NAMES = {
    "The",
    "This",
    "That",
    "Student",
    "Parent",
    "Grade",
    "Notice",
    "Suspension",
    "School",
    "Principal",
    "Assistant",
    "Dean",
    "Contact",
    "Call",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "Email",
    "Phone",
    "Referral",
    "Room",
    "Ave",
    "Street",
    "Blvd",
    "Road",
}

# A score threshold low enough to catch weak phone and ID matches.
_THRESHOLD = 0.35


@dataclass(frozen=True)
class Redaction:
    text: str
    entities: tuple[str, ...]  # entity types that were removed, in order of appearance

    @property
    def changed(self) -> bool:
        return bool(self.entities)


@lru_cache(maxsize=1)
def _engines():
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    nlp = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
    ).create_engine()
    registry = RecognizerRegistry(supported_languages=["en"])
    registry.load_predefined_recognizers(nlp_engine=nlp, languages=["en"])
    for name in ("EmailRecognizer", "UrlRecognizer", "PhoneRecognizer"):
        registry.remove_recognizer(name)

    def pattern(entity: str, regex: str, score: float, context: list[str] | None = None):
        return PatternRecognizer(
            supported_entity=entity,
            patterns=[Pattern(name=entity.lower(), regex=regex, score=score)],
            context=context,
        )

    registry.add_recognizer(pattern("PHONE_NUMBER", _PHONE, 0.7))
    registry.add_recognizer(pattern("EMAIL_ADDRESS", _EMAIL, 0.9))
    registry.add_recognizer(pattern("STREET_ADDRESS", _STREET, 0.7))
    registry.add_recognizer(pattern("STUDENT_ID", _STUDENT_ID, 0.3, _STUDENT_ID_CONTEXT))
    # Presidio's SSN recognizer rejects well-known test numbers; ours does not.
    registry.add_recognizer(pattern("US_SSN", _SSN, 0.8))
    analyzer = AnalyzerEngine(nlp_engine=nlp, registry=registry, supported_languages=["en"])
    return analyzer, AnonymizerEngine()


def redact(text: str) -> Redaction:
    """Replace identifying text with typed placeholders.

    Text longer than ``MAX_TEXT_CHARS`` is truncated first: the free-text field
    is "a sentence or two", and a bounded input bounds the work per request.
    """
    from presidio_anonymizer.entities import OperatorConfig

    text = text[:MAX_TEXT_CHARS]
    analyzer, anonymizer = _engines()
    results = [
        r
        for r in analyzer.analyze(text=text, language="en", entities=list(PLACEHOLDERS))
        if r.score >= _THRESHOLD
    ]
    from presidio_analyzer import RecognizerResult

    for m in _CUED_ID.finditer(text):
        results.append(RecognizerResult("STUDENT_ID", m.start(1), m.end(1), 1.0))
    for m in _CUED_NAME.finditer(text):
        results.append(RecognizerResult("PERSON", m.start(1), m.end(1), 0.9))
    results += _propagate_names(text, results)
    operators = {e: OperatorConfig("replace", {"new_value": p}) for e, p in PLACEHOLDERS.items()}
    out = anonymizer.anonymize(text=text, analyzer_results=_resolve(results), operators=operators)
    entities = tuple(i.entity_type for i in sorted(out.items, key=lambda i: i.start))
    return Redaction(text=out.text, entities=entities)


def _propagate_names(text, results):
    """Once a name is found anywhere, remove every other use of its parts.

    "Jamal Carter" found once means "Jamal" and "Carter" are names everywhere
    in this text, including where the model missed them.
    """
    from presidio_analyzer import RecognizerResult

    tokens = {
        t
        for r in results
        if r.entity_type == "PERSON"
        for t in _NAME_TOKEN.findall(text[r.start : r.end])
        if t not in _NOT_NAMES
    }
    extra = []
    for t in tokens:
        for m in re.finditer(rf"\b{re.escape(t)}\b", text):
            extra.append(RecognizerResult("PERSON", m.start(), m.end(), 0.85))
    return extra


def _resolve(results):
    """Merge overlapping spans, keeping the widest (then highest-scoring) one."""
    ordered = sorted(results, key=lambda r: (r.start, -(r.end - r.start), -r.score))
    merged = []
    for r in ordered:
        if merged and r.start < merged[-1].end:
            last = merged[-1]
            if r.end > last.end:
                last.end = r.end
            continue
        merged.append(r)
    return merged
