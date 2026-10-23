# Handoff

For whoever at ChiEAC maintains Suspension Check after October 2026. Read
`README.md` first, then `docs/STATUS.md` for what is done and what is next.

## Run it

```bash
uv sync --all-extras
uv run pytest                      # full suite with a 90% coverage gate
uv run uvicorn app.api.main:app    # http://127.0.0.1:8000 and /pattern
```

## Every August: load next year's school calendar

1. Get the official CPS calendar for the new school year (first day, last day,
   every day with no school for students).
2. Copy `src/suspension_check/data/cps_2026_2027.json` to
   `cps_2027_2028.json` and edit the dates. A `.ics` file from CPS can be
   loaded with `SchoolCalendar.from_ics` instead.
3. Point `SchoolCalendar.default()` in `calendar.py` at the new file and change
   the calendar name (drop "PROVISIONAL" once checked against the official one).
4. Run `uv run pytest`. The tests use 2026-27 dates through the `cps` fixture
   in `tests/conftest.py`, which calls `SchoolCalendar.default()`. Keep the
   2026-27 file and point that fixture at it with `SchoolCalendar.from_json`,
   then add one test with a known deadline in the new year.
5. Note the change in `DECISIONS.md`.

## When the law or the CPS Code of Conduct changes: update a rule

1. Rules live in `src/suspension_check/rules/illinois.py` (state) and
   `rules/idea.py` (federal). Each rule has its citation, quoted text, source
   URL, the flag and action text a parent sees, and fixtures that must fire and
   must stay silent.
2. Change the quote and the logic together, then update the fixtures.
3. If the wording a parent reads changed, set `reviewed=False` until an
   attorney or advocate has read it again. Unreviewed rules show "pending legal
   review" on every card.
4. Regenerate the rule table: `uv run python tools/export_rule_table.py`.
5. Letter wording lives in `src/suspension_check/letters/templates/`. After a
   change, run `uv run python tools/update_letter_goldens.py`, read the diff,
   and commit it with a `DECISIONS.md` entry.

## Deploy and rotate

See `docs/deploy.md`. The service is one Docker image with no state, so
"rotating" means building a new image from `main` and replacing the old one.
There are no secrets to rotate. After each deploy, run the checklist at the
end of `docs/deploy.md`.

## Keep CI green

CI runs lint, tests with a 90% coverage gate, the three Gate 2 scenarios, and
`pip-audit`. Most red builds are new advisories in dependencies: run
`uv lock --upgrade-package NAME`, re-run the tests, and push. Presidio pins
`cryptography` below a fixed version; the override in `pyproject.toml` can go
once Presidio lifts the pin (see `DECISIONS.md`, 2026-10-03).

## Privacy rules that must never be cut

From the brief: tests and fixtures, the legal review or pending labels, the
no-persistence guarantee, redaction on ingest, small-cell suppression, and the
disclaimer and resource card. `tests/test_no_persistence.py` fails the build if
code starts writing files or importing a database.

## Where the backlog lives

- `docs/STATUS.md`: next steps in order and open questions for Benjamin.
- `DECISIONS.md`: every decision with its date and reason.
- Not done yet: public deployment, legal review, five usability sessions
  (script in `docs/usability_test_script.md`), the CPS rule layer, React front
  end, Pattern Check charts, Spanish output.

## Contacts

- Project lead at ChiEAC: Benjamin (Gate sign-offs).
- Original developer: Prakruthi Koteshwar (through October 2026).
