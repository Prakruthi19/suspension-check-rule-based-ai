# Status and next steps

As of 2026-10-23, about 136 hours in (20 hours a week since September 14). Current release: v0.4.0-alpha.

## Done

- Rule table v1: 26 rules (IL-01 to IL-17, FED-01 to FED-09), each with
  citation, quoted authority, URL, flag, action, severity, and fires / silent
  fixtures. `docs/legal/rules_v1.xlsx`
- Deadline table v1 with the unit of every clock. `docs/legal/deadlines_v1.xlsx`
- Family Check survey draft and Pattern Check schema. `docs/survey_v1.md`, `docs/schema_v1.md`
- Engine: facts, rules, calendar, timeline, report, CLI
- Tests: 366 tests, 96% coverage, Hypothesis property tests, adversarial redaction, letter goldens, no-persistence check
- Three synthetic discipline logs (CSV and XLSX) with expected metrics
- Week 3: redaction on ingest (`redact.py`, `ingest.py`) with 22 adversarial fixtures
- Week 3: four letters (review request, manifestation determination request,
  records request, expulsion hearing response) as text, printable HTML and DOCX,
  with goldens in `tests/fixtures/letters/` and samples in `docs/letters/`
- Week 3: CLI `letter` and `redact` commands; API `/api/letter` download endpoint;
  web page shows the redacted description and offers every applicable letter
- Week 4: deadline calendar export (`ics.py`). Every upcoming deadline becomes
  an all-day event with a reminder two days before. CLI `calendar`, API
  `/api/calendar`, and an "Add to my calendar" button under the timeline
- Week 4: PRIVACY.md; uvicorn access log off; proxy-aware rate limiting;
  Permissions-Policy; Docker image (non-root, read-only filesystem), `docs/deploy.md`
- Week 4: accessibility pass (Lighthouse 100, axe 0 violations, keyboard reach),
  `docs/accessibility.md`; usability test script with 10 tasks
- Week 5: Pattern Check engine (`disparity.py`): CSV/XLSX within limits, header
  mapping with user correction, names dropped, IDs salted and hashed,
  Appendix E metrics with small-cell suppression. Matches all three synthetic
  logs exactly. `docs/metrics.md` has worked examples
- Week 5: Pattern Check on the CLI (`pattern`), API (`/api/pattern/*`) and web
  page (`/pattern`), and the one-page LSC brief with three questions
- Week 6 (security part): one-page threat model (`docs/threat_model.md`), zip
  bomb guard, pip-audit clean
- HANDOFF.md: calendar each August, rule updates, deploy, CI, backlog
- Gate 2 demo script (`docs/gate2_demo.md`) and front-end recommendation (DECISIONS.md)

## Next (in brief order)

These need people or access this build cannot supply.

1. Gate 2 with Benjamin: run `docs/gate2_demo.md` (now including Pattern Check).
2. Deploy the Docker image to a host with HTTPS and short platform logs; run the
   checklist in `docs/deploy.md`; share the alpha URL privately.
3. Replace the provisional CPS calendar with the official one.
4. Legal review (Week 6): an attorney or advocate arranged by ChiEAC reads every
   rule and letter; log changes in DECISIONS.md; flip `reviewed=True` rule by rule.
5. Usability (Week 6): five sessions with `docs/usability_test_script.md`.
6. Sanity-check Pattern Check against a public ISBE district aggregate.
7. CPS rule layer from the current Student Code of Conduct.
8. Backlog: React front end, Pattern Check charts, Spanish output, server-side PDF.

## Open questions for Benjamin

- ISSRA records response: 15 school days (brief) or a different unit in current text?
- Should "sent home without paperwork" be treated as an out-of-school suspension
  for IL-05 to IL-08 thresholds, or only for notice rules (current behaviour)?
- Who at ChiEAC will own the rule table and calendar updates after hand-off?
- Is seven days the right trigger for asking for an expulsion-hearing continuance?
- Redaction removes role words with names ("Dean Ortiz" becomes <PERSON>). OK to over-redact?
