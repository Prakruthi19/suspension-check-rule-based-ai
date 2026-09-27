"""Rule registry.

Each rule is a pure function ``Facts -> bool | None`` registered with the
``@rule`` decorator. ``None`` means "the facts needed to decide are unknown";
the evaluator then emits the flag as an Ask instead of an Assert, so a
"Not sure" answer never turns into an accusation.

Rule packs are plain modules. Built-in packs are imported by
``load_builtin_packs()``; third-party packs register through the
``suspension_check.rule_packs`` entry-point group.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.metadata import entry_points

from suspension_check.facts import Facts, Tri

__all__ = [
    "Flag",
    "Layer",
    "Rule",
    "Severity",
    "all3",
    "any3",
    "evaluate",
    "get_rule",
    "is_no",
    "load_builtin_packs",
    "registry",
    "rule",
]


class Severity(StrEnum):
    INFO = "information"
    ASK = "ask"
    ASSERT = "assert"


class Layer(StrEnum):
    FEDERAL = "federal"
    ILLINOIS = "illinois"
    CPS = "cps"


Predicate = Callable[[Facts], bool | None]


@dataclass(frozen=True)
class Rule:
    id: str
    layer: Layer
    citation: str
    url: str
    quote: str
    flag: str
    action: str
    severity: Severity
    predicate: Predicate = field(repr=False, compare=False)
    pack: str = "suspension"
    reviewed: bool = False  # set True only after attorney/advocate review (Gate 3)

    def __call__(self, facts: Facts) -> bool | None:
        return self.predicate(facts)


@dataclass(frozen=True)
class Flag:
    rule_id: str
    severity: Severity
    flag: str
    action: str
    citation: str
    url: str
    quote: str
    layer: Layer
    uncertain: bool  # fired on an unknown fact; downgraded to Ask
    reviewed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "flag": self.flag,
            "action": self.action,
            "citation": self.citation,
            "url": self.url,
            "quote": self.quote,
            "layer": self.layer.value,
            "uncertain": self.uncertain,
            "reviewed": self.reviewed,
        }


_REGISTRY: dict[str, Rule] = {}


def rule(
    *,
    id: str,
    layer: Layer | str,
    citation: str,
    url: str,
    quote: str,
    flag: str,
    action: str,
    severity: Severity,
    pack: str = "suspension",
    reviewed: bool = False,
) -> Callable[[Predicate], Rule]:
    """Register a predicate as a rule. IDs are globally unique."""

    def decorate(fn: Predicate) -> Rule:
        if id in _REGISTRY:
            raise ValueError(f"duplicate rule id {id!r}")
        r = Rule(
            id=id,
            layer=Layer(layer),
            citation=citation,
            url=url,
            quote=quote,
            flag=flag,
            action=action,
            severity=severity,
            predicate=fn,
            pack=pack,
            reviewed=reviewed,
        )
        _REGISTRY[id] = r
        return r

    return decorate


def registry(pack: str | None = None) -> list[Rule]:
    load_builtin_packs()
    rules = _REGISTRY.values()
    if pack is not None:
        rules = [r for r in rules if r.pack == pack]
    return sorted(rules, key=_sort_key)


def get_rule(rule_id: str) -> Rule:
    load_builtin_packs()
    return _REGISTRY[rule_id]


_LAYER_ORDER = {Layer.ILLINOIS: 0, Layer.CPS: 1, Layer.FEDERAL: 2}


def _sort_key(r: Rule) -> tuple[int, str, int]:
    prefix, _, num = r.id.rpartition("-")
    return (_LAYER_ORDER[r.layer], prefix, int(num) if num.isdigit() else 0)


_BUILTIN_PACKS = ("suspension_check.rules.illinois", "suspension_check.rules.idea")
_loaded = False


def load_builtin_packs() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    for mod in _BUILTIN_PACKS:
        importlib.import_module(mod)
    for ep in entry_points(group="suspension_check.rule_packs"):
        ep.load()


_SEVERITY_ORDER = {Severity.ASSERT: 0, Severity.ASK: 1, Severity.INFO: 2}


def evaluate(facts: Facts, rules: Iterable[Rule] | None = None) -> list[Flag]:
    """Run every rule against the facts and return the flags that fired."""
    flags: list[Flag] = []
    for r in rules if rules is not None else registry("suspension"):
        result = r(facts)
        if result is False:
            continue
        uncertain = result is None
        severity = Severity.ASK if uncertain and r.severity is Severity.ASSERT else r.severity
        flags.append(
            Flag(
                rule_id=r.id,
                severity=severity,
                flag=r.flag,
                action=r.action,
                citation=r.citation,
                url=r.url,
                quote=r.quote,
                layer=r.layer,
                uncertain=uncertain,
                reviewed=r.reviewed,
            )
        )
    return sorted(flags, key=lambda f: _SEVERITY_ORDER[f.severity])


# --- three-valued helpers (Kleene logic: False dominates, then None) ---------


def is_no(answer: Tri) -> bool | None:
    """True if the notice is missing the thing; None if the parent is not sure."""
    return {"no": True, "yes": False, "unknown": None}[answer]


def all3(*values: bool | None) -> bool | None:
    if any(v is False for v in values):
        return False
    if any(v is None for v in values):
        return None
    return True


def any3(*values: bool | None) -> bool | None:
    if any(v is True for v in values):
        return True
    if any(v is None for v in values):
        return None
    return False
