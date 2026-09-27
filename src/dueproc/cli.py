"""Command-line entry points: ``dueproc check`` and ``dueproc rules``."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from dueproc import __version__
from dueproc.calendar import SchoolCalendar
from dueproc.facts import Facts
from dueproc.report import DISCLAIMER, check
from dueproc.rules import registry

_SEV_LABEL = {"assert": "ASSERT", "ask": "ASK", "information": "INFO"}


def _load_facts(path: str) -> Facts:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return Facts.model_validate_json(raw)


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        facts = _load_facts(args.facts)
    except ValidationError as exc:
        print(f"Invalid facts file: {exc}", file=sys.stderr)
        return 2
    cal = SchoolCalendar.from_json(args.calendar) if args.calendar else SchoolCalendar.default()
    today = date.fromisoformat(args.today) if args.today else date.today()
    result = check(facts, cal, today)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Calendar: {cal.name}")
    print(f"State: main={result['state']['main']}  idea={result['state']['idea']}\n")
    print("TIMELINE")
    print(f"  {'Due':<11} {'Status':<9} {'Clock':<16} What")
    for o in result["timeline"]:
        due = o["due"] or "-"
        unit = o["unit"].removesuffix("s") if o["length"] == 1 else o["unit"]
        clock = f"{o['length']} {unit}" if o["length"] else unit
        print(f"  {due:<11} {o['status']:<9} {clock:<16} {o['title']}  [{o['authority']}]")
        if o["note"]:
            print(f"  {'':<38}{o['note']}")
    print(f"\nFLAGS ({len(result['flags'])})")
    for fl in result["flags"]:
        label = _SEV_LABEL[fl["severity"]] + ("?" if fl["uncertain"] else "")
        print(f"  {fl['rule_id']:<7} {label:<7} {fl['citation']}")
        for line in textwrap.wrap(fl["flag"], 76):
            print(f"          {line}")
        for line in textwrap.wrap("Action: " + fl["action"], 76):
            print(f"          {line}")
    print("\n" + textwrap.fill(DISCLAIMER, 80))
    return 0


def _cmd_rules(args: argparse.Namespace) -> int:
    for r in registry(args.pack):
        status = "reviewed" if r.reviewed else "pending review"
        print(f"{r.id:<8} {r.severity.value:<12} {r.layer.value:<9} {r.citation:<34} {status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dueproc", description="School discipline due-process checks.")
    p.add_argument("--version", action="version", version=f"dueproc {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Evaluate a facts JSON file (use - for stdin).")
    c.add_argument("facts")
    c.add_argument("--calendar", help="School calendar JSON (default: bundled CPS 2026-2027).")
    c.add_argument("--today", help="Evaluate as of this date (YYYY-MM-DD).")
    c.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    c.set_defaults(func=_cmd_check)

    r = sub.add_parser("rules", help="List registered rules.")
    r.add_argument("--pack", default=None)
    r.set_defaults(func=_cmd_rules)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
