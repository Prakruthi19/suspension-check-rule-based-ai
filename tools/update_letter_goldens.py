"""Regenerate letter goldens and the docs/letters/ samples.

Run only after a deliberate template change, and log it in DECISIONS.md:
    python tools/update_letter_goldens.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from suspension_check.facts import Facts
from suspension_check.letters import TITLES, applicable, render_text
from suspension_check.letters.formats import to_html
from suspension_check.rules import evaluate

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 27)
GOLDENS = ROOT / "tests" / "fixtures" / "letters"
DOCS = ROOT / "docs" / "letters"


def main() -> None:
    GOLDENS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    index = [
        "# Letter samples",
        "",
        "Rendered from the synthetic Gate 2 scenarios as of "
        f"{TODAY:%B %d, %Y}. Templates live in `src/suspension_check/letters/templates/`.",
        "",
    ]
    for path in sorted((ROOT / "examples").glob("scenario_*.json")):
        facts = Facts.model_validate(json.loads(path.read_text()))
        flags = evaluate(facts)
        for v in applicable(facts, flags):
            text = render_text(v, facts, flags, TODAY)
            (GOLDENS / f"{path.stem}.{v.value}.txt").write_text(text, encoding="utf-8")
            (GOLDENS / f"{path.stem}.{v.value}.html").write_text(
                to_html(text, TITLES[v]), encoding="utf-8"
            )
            (DOCS / f"{path.stem}.{v.value}.md").write_text(
                f"# {TITLES[v]}\n\nSynthetic scenario: `{path.name}`\n\n```text\n{text}```\n",
                encoding="utf-8",
            )
            index.append(f"- [{TITLES[v]}]({path.stem}.{v.value}.md) ({path.stem})")
    (DOCS / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
