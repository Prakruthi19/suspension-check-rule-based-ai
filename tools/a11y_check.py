"""Run axe-core against the Family Check page for each Gate 2 scenario.

Usage: python tools/a11y_check.py URL PATH_TO_axe.min.js [CHROMIUM_PATH]
Prints axe violations per scenario and how many controls Tab reaches.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main(url: str, axe_path: str, chromium: str | None = None) -> int:
    axe = Path(axe_path).read_text(encoding="utf-8")
    bad = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium) if chromium else p.chromium.launch()
        page = browser.new_page()
        for ex in ("a", "b", "c"):
            page.goto(url)
            page.click(f"button[data-example={ex}]")
            page.click("button[type=submit]")
            page.wait_for_selector("#results-head")
            page.add_script_tag(content=axe)
            found = page.evaluate(
                "async () => (await axe.run(document, {runOnly: ['wcag2a', 'wcag2aa', "
                "'best-practice']})).violations.map(v => [v.id, v.impact, v.nodes.length])"
            )
            bad += len(found)
            print(f"scenario {ex}: {found or 'no violations'}")
        total = page.evaluate(
            "document.querySelectorAll('button, a[href], input, select, textarea').length"
        )
        reached = set()
        for _ in range(total * 3):
            page.keyboard.press("Tab")
            reached.add(page.evaluate("document.activeElement.outerHTML.slice(0, 120)"))
        print(f"keyboard: {len(reached)} distinct controls reached of {total}")
        browser.close()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
