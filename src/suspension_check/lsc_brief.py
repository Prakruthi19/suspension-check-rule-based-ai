"""The one-page LSC brief: findings that crossed a threshold, and three
questions to ask the principal at the next Local School Council meeting.

Findings are generated from a Pattern Check result only, so every number in the
brief has already passed suppression. Thresholds are deliberately simple and
listed in ``THRESHOLDS`` so an LSC member can see why a finding was raised.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from suspension_check.disparity import DIMENSIONS, OTHER

__all__ = ["BRIEF_NOTE", "THRESHOLDS", "Finding", "findings", "questions", "to_html"]

THRESHOLDS = {
    "risk_ratio": 2.0,  # a group suspended at twice the reference rate or more
    "documented_intervention_share": 0.5,  # under half of long OSS document interventions
    "subjective_share": 0.5,  # half or more of a group's OSS for subjective categories ...
    "subjective_gap": 0.15,  # ... and 15 points above the lowest reportable group
    "repeat_share": 0.25,  # a quarter or more suspended again
    "composition_index": 1.5,  # 50% over-represented
}

_DIM_NOUN = {
    "race_ethnicity": "{g} students",
    "gender": "{g} students",
    "iep": "students with an IEP",
    "el": "English learners",
    "low_income": "low-income students",
}
_DIM_NOUN_NO = {
    "iep": "students without an IEP",
    "el": "students who are not English learners",
    "low_income": "students who are not low-income",
}

BRIEF_NOTE = (
    "Produced by Suspension Check from the uploaded discipline log, which was not "
    "stored. The numbers are only as accurate as the log. This is general "
    "information, not legal advice. Metric definitions: docs/metrics.md at "
    "github.com/Prakruthi19/suspension-check-rule-based-ai."
)

GENERIC_QUESTIONS = [
    "Will the school share these suspension numbers with the LSC each semester, "
    "broken down by student group?",
    "What alternatives to out-of-school suspension does the school use, and how often?",
    "How are families told about their right to ask for a review of a suspension?",
]


@dataclass(frozen=True)
class Finding:
    kind: str
    headline: str
    question: str


def _who(dim: str, group: str) -> str:
    if dim in _DIM_NOUN_NO and group == "No":
        return _DIM_NOUN_NO[dim]
    return _DIM_NOUN[dim].format(g=group)


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def _reportable(result: dict, dim: str) -> dict[str, dict]:
    return {g: m for g, m in result.get(f"by_{dim}", {}).items() if g != OTHER}


def findings(result: dict) -> list[Finding]:
    """Every finding that crossed a threshold, most important kind first."""
    out: list[Finding] = []

    # 1. Largest risk ratio at or above the threshold.
    best = None
    for dim in DIMENSIONS:
        for g, m in _reportable(result, dim).items():
            rr = m.get("risk_ratio")
            if rr is not None and rr >= THRESHOLDS["risk_ratio"] and (not best or rr > best[2]):
                best = (dim, g, rr, m)
    if best:
        dim, g, rr, m = best
        who = _who(dim, g)
        ref = "white students" if m["risk_ratio_reference"] == "white" else "all other students"
        out.append(
            Finding(
                "risk_ratio",
                f"{who[0].upper() + who[1:]} were suspended out of school at {rr:.1f} times "
                f"the rate of {ref} ({m['students_suspended_per_100']} per 100 students).",
                f"What explains the gap in suspension rates between {who} and {ref}, and what "
                "is the school's plan to close it this year?",
            )
        )

    # 2. Interventions not documented before long suspensions.
    share = result.get("documented_intervention_share")
    if share is not None and share < THRESHOLDS["documented_intervention_share"]:
        out.append(
            Finding(
                "documented_intervention_share",
                f"Only {_pct(share)} of suspensions longer than three school days record that "
                "other interventions were tried first. Illinois law requires the school to "
                "consider them (105 ILCS 5/10-22.6(b-20)).",
                "For suspensions longer than three days, how does the school document which "
                "interventions it tried first?",
            )
        )

    # 3. Subjective categories concentrated in one group.
    for dim in DIMENSIONS:
        shares = {
            g: m["subjective_share"]
            for g, m in _reportable(result, dim).items()
            if m.get("subjective_share") is not None
        }
        if len(shares) < 2:
            continue
        top = max(shares, key=shares.get)
        low = min(shares, key=shares.get)
        if (
            shares[top] >= THRESHOLDS["subjective_share"]
            and shares[top] - shares[low] >= THRESHOLDS["subjective_gap"]
        ):
            out.append(
                Finding(
                    "subjective_share",
                    f"{_pct(shares[top])} of suspensions of {_who(dim, top)} were for "
                    f"subjective reasons such as defiance or disruption, compared with "
                    f"{_pct(shares[low])} for {_who(dim, low)}.",
                    "How does the school define defiance and disruption, and who reviews "
                    "those referrals before a student is suspended?",
                )
            )
            break

    # 4. Repeat suspensions.
    worst = None
    for dim in DIMENSIONS:
        for g, m in _reportable(result, dim).items():
            r = m.get("repeat_share")
            if r is not None and r >= THRESHOLDS["repeat_share"] and (not worst or r > worst[2]):
                worst = (dim, g, r)
    if worst:
        dim, g, r = worst
        out.append(
            Finding(
                "repeat_share",
                f"{_pct(r)} of suspended {_who(dim, g)} were suspended more than once.",
                "What support does a student get on returning from a suspension, so that "
                "it does not happen again?",
            )
        )

    # 5. Over-representation, when no risk ratio finding already covers it.
    if not best:
        for dim in DIMENSIONS:
            for g, m in _reportable(result, dim).items():
                ci = m.get("composition_index")
                if ci is not None and ci >= THRESHOLDS["composition_index"]:
                    out.append(
                        Finding(
                            "composition_index",
                            f"{_who(dim, g)[0].upper() + _who(dim, g)[1:]} received "
                            f"{ci:.1f} times their share of suspensions.",
                            f"Why do {_who(dim, g)} receive a larger share of suspensions "
                            "than their share of enrollment?",
                        )
                    )
                    break
            else:
                continue
            break
    return out


def questions(result: dict) -> list[str]:
    """Exactly three questions: from findings first, then general ones."""
    qs = [f.question for f in findings(result)][:3]
    for q in GENERIC_QUESTIONS:
        if len(qs) == 3:
            break
        if q not in qs:
            qs.append(q)
    return qs


def _table(result: dict) -> str:
    rows = []
    for g, m in _reportable(result, "race_ethnicity").items():
        cells = [
            m["students_suspended"],
            m["students_suspended_per_100"],
            m["risk_ratio"],
            m["composition_index"],
        ]
        tds = "".join(f"<td>{'suppressed' if c is None else escape(str(c))}</td>" for c in cells)
        rows.append(f"<tr><th scope='row'>{escape(g)}</th>{tds}</tr>")
    if not rows:
        return ""
    return (
        "<table><thead><tr><th scope='col'>Group</th><th scope='col'>Students suspended</th>"
        "<th scope='col'>Per 100 students</th><th scope='col'>Risk ratio</th>"
        "<th scope='col'>Composition index</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def to_html(result: dict, title: str = "") -> str:
    """A printable one-page brief. Print or "Save as PDF" from the browser."""
    title = (title or "Suspension patterns at our school").strip()[:100]
    found = findings(result)[:3]
    items = "".join(f"<li>{escape(f.headline)}</li>" for f in found) or (
        "<li>No finding crossed a threshold, or the groups were too small to report.</li>"
    )
    qs = "".join(f"<li>{escape(q)}</li>" for q in questions(result))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
  body {{ font: 11pt/1.45 system-ui, sans-serif; color: #111; background: #fff;
    max-width: 7.5in; margin: 0.5in auto; padding: 0 16px; }}
  h1 {{ font-size: 16pt; margin: 0 0 4px; }}
  h2 {{ font-size: 12pt; margin: 18px 0 6px; }}
  .meta {{ color: #444; margin: 0 0 12px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 10pt; }}
  th, td {{ border: 1px solid #bbb; padding: 4px 6px; text-align: left; }}
  .q li {{ margin-bottom: 6px; font-weight: 600; }}
  .small {{ font-size: 9pt; color: #444; }}
  @page {{ size: letter; margin: 0.5in; }}
</style>
</head>
<body>
<h1>{escape(title)}</h1>
<p class="meta">{result["oss_incidents"]} out-of-school suspensions analysed with
Suspension Check. Groups with fewer than {result["suppression_threshold"]} students
are not reported.</p>
<h2>What the numbers show</h2>
<ul>{items}</ul>
{_table(result)}
<h2>Three questions for the principal</h2>
<ol class="q">{qs}</ol>
<h2>How to read this</h2>
<p class="small">Per 100 students: students with at least one out-of-school
suspension for every 100 enrolled in the group. Risk ratio: a group's rate divided
by white students' rate (or all other students' rate when the white group is too
small); 2.0 means twice as likely. Composition index: share of suspensions divided
by share of enrollment; 1.0 is proportional. "Suppressed" means the group is too
small to report without risking identifying a student.</p>
<p class="small">{escape(BRIEF_NOTE)}</p>
</body>
</html>
"""
