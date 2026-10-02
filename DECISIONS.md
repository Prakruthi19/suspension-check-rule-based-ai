# Decisions

Dated log of scope, legal, and design decisions. Newest last.

## 2026-09-14 · Library name: `dueproc` (working name)
Started with the brief's working name.

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

## 2026-09-27 · Renamed to `suspension-check-rule-based-ai`
"dueproc" did not say what the project does. Repository and distribution:
`suspension-check-rule-based-ai`; Python package: `suspension_check`; command:
`suspension-check`. "Rule-based AI" is meant in the expert-system sense: every
decision is an explicit, cited, tested rule, and no ML model or LLM is used.

## 2026-09-29 · Redaction: Presidio for names, explicit regex for everything else
Presidio with the small English spaCy model (`en_core_web_sm`) finds names.
Phones, emails, street addresses, student IDs and SSNs use our own regex
recognizers so their behaviour is visible and testable. Two extra passes cover
what the small model misses: names after a cue word ("Student:", "Mr.",
"call", "Dean") and propagation (once "Jamal Carter" is found, every "Jamal"
and "Carter" in the same text goes). Over-redaction is accepted; a removed
role word costs less than a leaked name. Known limit: a lowercase or unusual
name with no cue can still slip through; the adversarial fixtures grow as we
find cases.

## 2026-09-29 · Presidio's email and URL recognizers removed
They fetch the public suffix list from the internet on first use. A privacy
tool should make no outbound calls while handling a family's text.

## 2026-09-30 · spaCy model is installed from a URL, not PyPI
spaCy models are not on PyPI, so `en-core-web-sm` comes from `[tool.uv.sources]`.
Redaction is an optional extra (`[redact]`); the core engine does not need it.
Before the Week 7 PyPI release, decide between documenting a separate model
install step or vendoring a smaller name list.

## 2026-09-30 · Ingest order is enforced in one module
`suspension_check.ingest` is the only front door: parse JSON, redact every
free-text field, then validate. The CLI and API both use it, and a test
asserts the original text never appears in any output (flags, timeline,
letters, API response, logs).

## 2026-09-30 · The incident description does not go into letters
The redacted description is shown back to the parent so they can see what was
removed, but no letter quotes it: placeholders like <PERSON> would read badly
in a letter to the principal, and the letters do not need it.

## 2026-10-01 · Four letter variants from one text template each
Review request, manifestation determination request, records request, and
expulsion hearing response. The plain-text template is the only source of
wording; printable HTML and DOCX are built from it in memory, so the three
formats cannot drift. DOCX author metadata is blank. Each output ends with a
separate "keep this page" section with the disclaimer and resource card.
Goldens: text and HTML exact; DOCX checked paragraph by paragraph.

## 2026-10-01 · Expulsion letter asks for a continuance when the hearing is close
If the hearing is seven calendar days away or less, or the certified-mail
request never arrived (IL-12), the letter asks for a continuance. Seven days is
a judgement call to confirm in the legal review.

## 2026-10-02 · Front-end recommendation for Gate 2: React + Vite, not Streamlit
Streamlit keeps per-user state in a server-side session, which conflicts with
the no-server-sessions rule, and it gives less control over accessibility and
keyboard order. The vanilla-HTML page has proven the API shape, so the React
build in Week 4 is a port, not a redesign. If Week 4 runs short, the vanilla
page stays as the v1 UI (it already meets the privacy rules); Streamlit is not
the fallback. To be confirmed with Benjamin at Gate 2.
