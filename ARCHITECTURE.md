# Architecture

One core library, thin products on top.

```
src/suspension_check/
  facts.py            Pydantic v2 models for everything the survey collects (strict, frozen)
  rules/__init__.py   registry, @rule decorator, evaluate(), three-valued helpers
  rules/sources.py    every source URL, once
  rules/illinois.py   IL-01..IL-17  (105 ILCS 5/10-22.6, ISSRA)
  rules/idea.py       FED-01..FED-09 (34 CFR 300.530-536, 104.35)
  calendar.py         SchoolCalendar: school-day arithmetic, JSON and .ics loading
  data/               bundled CPS 2026-2027 calendar (provisional)
  timeline.py         two table-driven state machines and the Obligation dataclass
  ingest.py           the only front door: parse, redact free text, then validate
  redact.py           Presidio + custom recognizers; typed placeholders (<PERSON>, <PHONE>...)
  letters/            four Jinja2 text templates; formats.py renders HTML and DOCX in memory
  report.py           check(): rules + timeline + disclaimer + resource card as plain data
  cli.py              suspension-check check / letter / redact / rules
app/api/main.py       stateless FastAPI service (POST /api/check, POST /api/letter)
app/web/index.html    Family Check page (no build step)
synthetic/            Faker-based discipline log generator, three logs, expected metrics
tools/                export_rule_table.py (registry -> docs/legal/*.xlsx, *.md)
```

## The rule contract

- A rule is a pure function `Facts -> bool | None` plus metadata: `id`, `layer`
  (federal, illinois, cps), `citation`, `url`, `quote`, `flag`, `action`,
  `severity` (information, ask, assert), `pack`, and `reviewed`.
- Rules register themselves with `@rule`; there is no hand-maintained list.
  Built-in packs load on first use; external packs register through the
  `suspension_check.rule_packs` entry-point group, which is how the IEP Placement
  Checklist pack will load in Week 7 without touching the core.
- `None` means "cannot decide on these facts". The evaluator emits the flag as
  an Ask with `uncertain=True`. Combine optional facts with `all3` / `any3`
  (Kleene logic) and `is_no` for Yes / No / Not sure answers.
- **Rules never compute dates.** Dates belong to the timeline.
- Every rule needs `tests/fixtures/rules/<ID>_fires.json` and `<ID>_silent.json`.
  An optional `<ID>_uncertain.json` pins the Not-sure behaviour.
- `reviewed` stays `False` until the Gate 3 legal review; the UI shows a
  "pending legal review" label on every unreviewed flag.

## The calendar model

A school day is a weekday within `[first_day, last_day]` that is not a
closure. `add_school_days(start, n)` returns the n-th school day after `start`;
`nth_school_day(start, n)` counts `start` as day 1 (used for "the last day of a
5-day suspension"). A clock that runs past `last_day` raises
`BeyondSchoolYear`; the timeline turns that into an obligation with no date
and a note, never a date in July.

## The timeline

Main track: `Incident -> NoticeIssued -> Removal -> ReviewRequested -> DecisionIssued -> Closed`.
IDEA track: `NotTracked -> CumulativeDaysTracked -> ChangeOfPlacement -> MDRDue -> MDRHeld -> Manifestation | NotManifestation -> ExpeditedHearingRequested`.

Facts are replayed as events through two table-driven machines; an event that
is not legal from the current state raises `InvalidTransition`. Each
transition emits `Obligation`s with a clock start, length, unit (school days,
calendar days, same day, immediately), authority, and due date.

Property tests (Hypothesis) hold that no school-day deadline lands on a
non-school day, that lengthening a removal never moves a deadline earlier, and
that no random legal event sequence reaches a state outside the table.
