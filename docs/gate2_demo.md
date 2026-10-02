# Gate 2 demo script

Synthetic data only. About ten minutes. Run from the repository root after
`uv sync --all-extras`.

## 1. The engine with no web app (3 minutes)

```bash
uv run suspension-check rules                        # 26 rules, all "pending review"
uv run suspension-check check examples/scenario_a_two_day_no_notice.json --today 2026-09-27
uv run suspension-check check examples/scenario_b_iep_cumulative_twelve.json --today 2026-09-27
uv run suspension-check check examples/scenario_c_expulsion_hearing.json --today 2026-09-27
```

Point out: (a) a phone-call-only notice raises IL-01 to IL-04 as Assert;
(b) twelve cumulative days with an IEP puts the MDR deadline (October 6) on the
timeline and raises FED-02/03 as Ask, because a "pattern" is the team's call;
(c) the expulsion hearing date is on the timeline and IL-05 fires on the
missing interventions.

## 2. Redaction (2 minutes)

```bash
uv run suspension-check redact "Student: Jamal Carter, ID 50876543. Call Linda Nguyen at (773) 535-0000."
```

## 3. Letters (2 minutes)

```bash
uv run suspension-check letter examples/scenario_b_iep_cumulative_twelve.json --variant mdr_request --today 2026-09-27
uv run suspension-check letter examples/scenario_c_expulsion_hearing.json --variant expulsion_response --format docx --today 2026-09-27 > expulsion.docx
```

## 4. The web page (3 minutes)

```bash
uv run uvicorn app.api.main:app
```

Open http://127.0.0.1:8000, click "IEP, 7 days, 12 days this year", show the
redacted description, switch between the three letters, and download the Word file.

## Decision to make at Gate 2

Front end for v1: the recommendation is React + Vite (see DECISIONS.md, 2026-10-02).
