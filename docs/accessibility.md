# Accessibility pass

Target from the brief: Lighthouse accessibility at or above 90, and every
interactive element reachable by keyboard.

## Results (Family Check page, checked 2026-10-23)

| Check | Tool | Result |
|---|---|---|
| Lighthouse accessibility, empty form | Lighthouse 12, headless Chromium | 100 |
| WCAG 2 A / AA and best-practice rules, results for each Gate 2 scenario | axe-core 4.10 | 0 violations (a, b, c) |
| Keyboard reach | Tab through the results page | Every visible control reached (47 of 48 on the last scenario; the controls not reached are IEP-only questions that are hidden when there is no IEP) |
| Mobile width (375 px) | Playwright | No horizontal scroll |

## What the page already does

- Every input has a visible `<label>`; Yes / No / Not sure groups are
  `<fieldset>` with a `<legend>`.
- Results move focus to the "What we found" heading, so a screen reader
  announces the result instead of staying on the submit button.
- Severity is never shown by colour alone: each flag card says "Assert",
  "Ask", or "Know this" in words.
- Letter tabs are buttons with `aria-pressed`.
- System fonts at 16 px or larger, no motion, no time limits.

## Re-running

```bash
uv run uvicorn app.api.main:app --port 8000 &
npm i --prefix /tmp/a11y axe-core lighthouse
uv run --with playwright python tools/a11y_check.py http://127.0.0.1:8000/ /tmp/a11y/node_modules/axe-core/axe.min.js
npx --prefix /tmp/a11y lighthouse http://127.0.0.1:8000/ --only-categories=accessibility
```

## Still to do with people

A screen reader walkthrough (NVDA or VoiceOver) by someone who uses one daily
belongs in the Week 6 usability sessions.
