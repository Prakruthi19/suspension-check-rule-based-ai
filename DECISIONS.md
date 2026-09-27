# Decisions

Dated log of scope, legal, and design decisions. Newest last.

## 2026-09-14 · Library name: `dueproc`
Kept the working name from the brief. It is short, available as a package name
pattern, and says what it does. Use it everywhere (repo, PyPI, posts).

## 2026-09-15 · Python 3.11 minimum
CI runs 3.11 and 3.12. 3.11 is what common hosting images ship today; nothing
in the engine needs 3.12 features.

## 2026-09-16 · "Not sure" is a first-class answer
Every notice question is Yes / No / Not sure (`Tri`). Rules return
`True | False | None`; `None` downgrades an Assert to an Ask. A parent who is not
sure must never be handed an accusation. Exception: IL-10 (zero tolerance)
stays silent on "Not sure", because asking about it on every case is noise.

## 2026-09-16 · No written notice means every "does the notice say" answer is No
Enforced in the `Notice` model, so a phone call can never satisfy IL-02 to IL-04.

## 2026-09-17 · Hand-rolled state machine, not `transitions`
Two small tables are easier to read, test, and property-check than a library
with callbacks. One less dependency in the core.

## 2026-09-18 · Change of placement by "pattern" is treated as unknown
34 CFR 300.536 makes a series of removals a change of placement only if it
forms a pattern, which is a team determination. More than 10 consecutive days
(or an expulsion / alternative placement) is a change of placement; more than
10 cumulative days is `None`, so FED-02 and FED-03 fire as Ask, not Assert.

## 2026-09-21 · CPS 2026-2027 calendar is provisional
Bundled calendar has weekday holidays and breaks only. Professional
development and report-card days are missing, so it has about 190 school days
instead of about 176, and some deadlines will land a day or two early. Must be
replaced with the official cps.edu calendar before any alpha users.

## 2026-09-21 · CPS rule layer deferred
The CPS layer needs the current Student Code of Conduct edition and section for
every rule. Not encoded yet rather than encoded from memory. Moves to Week 3.

## 2026-09-22 · ISSRA records clock: open question
Appendix B says 15 school days. Implemented as 15 school days with a visible
"pending confirmation" note until the current 105 ILCS 10/5 text is checked.

## 2026-09-23 · IL-05 and IL-06 also cover expulsions and alternative placements
Subsection (b-20) applies to suspensions over three days, expulsions, and
removals to alternative schools, not only long suspensions.

## 2026-09-24 · Rule table generated from the registry
`tools/export_rule_table.py` writes `docs/legal/rules_v1.xlsx` and `.md` from
the code, so the table under review is always the table that runs.

## 2026-09-25 · Synthetic expected metrics come from the plan, not the rows
Each synthetic log is generated from an explicit per-subgroup plan. Expected
metrics are computed from the plan alone, so Pattern Check (Week 5) is tested
against numbers that can be checked by hand, not against itself.

## 2026-09-26 · Early web spike in plain HTML
Built a one-file Family Check page on a stateless FastAPI endpoint to
demonstrate the engine end to end. It is a spike, not the front-end decision;
React vs Streamlit is still decided at Gate 2. The free-text incident
description is hidden until redaction ships.

## 2026-09-27 · Letter spike: review request only, plain text
One Appendix F letter with golden tests. DOCX, printable HTML, and the other
three variants are Week 3 work.
