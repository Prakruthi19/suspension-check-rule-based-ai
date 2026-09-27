# Status and next steps

As of 2026-09-27, after about 40 hours of work (two weeks at 20 hours).

## Done

- Rule table v1: 26 rules (IL-01 to IL-17, FED-01 to FED-09), each with
  citation, quoted authority, URL, flag, action, severity, and fires / silent
  fixtures. `docs/legal/rules_v1.xlsx`
- Deadline table v1 with the unit of every clock. `docs/legal/deadlines_v1.xlsx`
- Family Check survey draft and Pattern Check schema. `docs/survey_v1.md`, `docs/schema_v1.md`
- Engine: facts, rules, calendar, timeline, report, CLI
- Tests: 230 tests, 97% coverage, Hypothesis property tests, no-persistence check
- Three synthetic discipline logs (CSV and XLSX) with expected metrics
- Spikes: review-request letter, stateless API, one-page Family Check UI

## Next (in brief order)

1. Replace the provisional CPS calendar with the official one.
2. Re-verify every quote and subsection letter against ilga.gov and eCFR;
   resolve the ISSRA response-time question.
3. Week 3: `suspension_check.redact` (Presidio + student-ID recognizer), then turn the
   incident-description field back on; DOCX and printable HTML letters; MDR,
   records, and expulsion letter variants; front-end decision at Gate 2.
4. CPS layer from the current Student Code of Conduct.
5. Week 4 onward: deploy alpha, accessibility pass, Pattern Check.

## Open questions for Benjamin

- ISSRA records response: 15 school days (brief) or a different unit in current text?
- Should "sent home without paperwork" be treated as an out-of-school suspension
  for IL-05 to IL-08 thresholds, or only for notice rules (current behaviour)?
- Who at ChiEAC will own the rule table and calendar updates after hand-off?
