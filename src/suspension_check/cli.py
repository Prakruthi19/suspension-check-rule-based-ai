"""Command-line entry points.

``suspension-check check``, ``letter``, ``calendar``, ``redact``, and ``rules``. Output goes to
stdout only; the CLI never writes files (redirect if you want one).
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from suspension_check import __version__
from suspension_check.calendar import SchoolCalendar
from suspension_check.facts import Facts
from suspension_check.ingest import ingest
from suspension_check.letters import TITLES, Variant, render_text
from suspension_check.report import DISCLAIMER, check
from suspension_check.rules import evaluate, registry

_SEV_LABEL = {"assert": "ASSERT", "ask": "ASK", "information": "INFO"}


def _load_facts(path: str) -> Facts:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return ingest(raw).facts


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        facts = _load_facts(args.facts)
    except (ValidationError, ValueError) as exc:
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


def _cmd_letter(args: argparse.Namespace) -> int:
    try:
        facts = _load_facts(args.facts)
    except (ValidationError, ValueError) as exc:
        print(f"Invalid facts file: {exc}", file=sys.stderr)
        return 2
    today = date.fromisoformat(args.today) if args.today else date.today()
    variant = Variant(args.variant)
    text = render_text(variant, facts, evaluate(facts), today)
    if args.format == "txt":
        sys.stdout.write(text)
    elif args.format == "html":
        from suspension_check.letters.formats import to_html

        sys.stdout.write(to_html(text, TITLES[variant]))
    else:
        from suspension_check.letters.formats import to_docx

        if sys.stdout.isatty():
            print("Refusing to print DOCX to a terminal; redirect: > letter.docx", file=sys.stderr)
            return 2
        sys.stdout.buffer.write(to_docx(text, TITLES[variant]))
    return 0


def _cmd_calendar(args: argparse.Namespace) -> int:
    from suspension_check.ics import to_ics
    from suspension_check.timeline import build_timeline

    try:
        facts = _load_facts(args.facts)
    except (ValidationError, ValueError) as exc:
        print(f"Invalid facts file: {exc}", file=sys.stderr)
        return 2
    today = date.fromisoformat(args.today) if args.today else date.today()
    sys.stdout.write(to_ics(build_timeline(facts, SchoolCalendar.default()), today))
    return 0


def _cmd_redact(args: argparse.Namespace) -> int:
    from suspension_check.redact import redact

    text = sys.stdin.read() if args.text == "-" else args.text
    print(redact(text).text)
    return 0


def _cmd_rules(args: argparse.Namespace) -> int:
    for r in registry(args.pack):
        status = "reviewed" if r.reviewed else "pending review"
        print(f"{r.id:<8} {r.severity.value:<12} {r.layer.value:<9} {r.citation:<34} {status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="suspension-check", description="School discipline due-process checks."
    )
    p.add_argument("--version", action="version", version=f"suspension-check {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Evaluate a facts JSON file (use - for stdin).")
    c.add_argument("facts")
    c.add_argument("--calendar", help="School calendar JSON (default: bundled CPS 2026-2027).")
    c.add_argument("--today", help="Evaluate as of this date (YYYY-MM-DD).")
    c.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    c.set_defaults(func=_cmd_check)

    lt = sub.add_parser("letter", help="Render a letter for a facts JSON file to stdout.")
    lt.add_argument("facts")
    lt.add_argument("--variant", choices=[v.value for v in Variant], default=Variant.REVIEW.value)
    lt.add_argument("--format", choices=["txt", "html", "docx"], default="txt")
    lt.add_argument("--today", help="Date the letter (YYYY-MM-DD).")
    lt.set_defaults(func=_cmd_letter)

    ca = sub.add_parser(
        "calendar", help="Print upcoming deadlines as an .ics calendar file to stdout."
    )
    ca.add_argument("facts")
    ca.add_argument("--today", help="Only deadlines on or after this date (YYYY-MM-DD).")
    ca.set_defaults(func=_cmd_calendar)

    rd = sub.add_parser(
        "redact", help="Show what redaction removes from a piece of text (- for stdin)."
    )
    rd.add_argument("text")
    rd.set_defaults(func=_cmd_redact)

    r = sub.add_parser("rules", help="List registered rules.")
    r.add_argument("--pack", default=None)
    r.set_defaults(func=_cmd_rules)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
