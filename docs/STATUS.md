# Status and next steps

As of 2026-10-08, about 65 hours in (three weeks at 20 hours, plus a small Week 4 feature). Current release: v0.3.0-alpha.

## Done

- Rule table v1: 26 rules (IL-01 to IL-17, FED-01 to FED-09), each with
  citation, quoted authority, URL, flag, action, severity, and fires / silent
  fixtures. `docs/legal/rules_v1.xlsx`
- Deadline table v1 with the unit of every clock. `docs/legal/deadlines_v1.xlsx`
- Family Check survey draft and Pattern Check schema. `docs/survey_v1.md`, `docs/schema_v1.md`
- Engine: facts, rules, calendar, timeline, report, CLI
- Tests: 316 tests, 97% coverage, Hypothesis property tests, adversarial redaction, letter goldens, no-persistence check
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
- Gate 2 demo script (`docs/gate2_demo.md`) and front-end recommendation (DECISIONS.md)

## Next (in brief order)

1. Gate 2 with Benjamin: run `docs/gate2_demo.md`, confirm React + Vite for v1.
2. Replace the provisional CPS calendar with the official one.
3. Re-verify every quote and subsection letter against ilga.gov and eCFR;
   resolve the ISSRA response-time question.
4. Week 4: FastAPI hardening (CORS lock, deploy), React front end, PDF
   timeline export, accessibility pass, PRIVACY.md, alpha deployment.
5. CPS layer from the current Student Code of Conduct.
6. Week 5: Pattern Check (header mapping, metrics, suppression, LSC brief).

## Open questions for Benjamin

- ISSRA records response: 15 school days (brief) or a different unit in current text?
- Should "sent home without paperwork" be treated as an out-of-school suspension
  for IL-05 to IL-08 thresholds, or only for notice rules (current behaviour)?
- Who at ChiEAC will own the rule table and calendar updates after hand-off?
- Is seven days the right trigger for asking for an expulsion-hearing continuance?
- Redaction removes role words with names ("Dean Ortiz" becomes <PERSON>). OK to over-redact?
