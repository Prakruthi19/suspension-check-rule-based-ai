"""Synthetic discipline logs with known disparities and known messy headers.

SYNTHETIC DATA ONLY. Every name and ID is produced by Faker from a fixed seed.
No real student record is ever placed in this repository.

Each log is built from an explicit plan (how many students in each subgroup
are suspended, how many times, for how long) so that the expected metrics in
``expected/*.json`` can be checked by hand from the plan alone. Pattern Check
(Week 5) must reproduce those numbers exactly.

Run: python synthetic/generate.py
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from faker import Faker
from openpyxl import Workbook

HERE = Path(__file__).resolve().parent
SUBJECTIVE = {"Defiance", "Disrespect", "Disruption", "Insubordination"}
OBJECTIVE = {"Fighting", "Theft", "Vandalism", "Weapon possession", "Drug possession"}
SUPPRESS_BELOW = 10


@dataclass(frozen=True)
class GroupPlan:
    group: str
    enrolled: int
    suspended_once: int
    suspended_twice: int
    days_each: int  # school days per OSS
    subjective_share: float  # share of incidents coded subjective
    documented_interventions: float  # share of >3-day OSS with interventions documented


@dataclass(frozen=True)
class LogPlan:
    name: str
    headers: dict[str, str]  # standard field -> messy header used in the file
    groups: list[GroupPlan]
    fmt: str = "csv"
    seed: int = 0


# Log A: one elementary/middle school, clean-ish aliases, large Black-white disparity.
LOG_A = LogPlan(
    name="school_a",
    seed=101,
    headers={
        "student_name": "Student Name",
        "student_id": "Student ID",
        "incident_date": "Incident Date",
        "action_type": "Consequence",
        "days_assigned": "Days",
        "grade": "Gr",
        "incident_category": "Infraction",
        "race_ethnicity": "Race/Ethnicity",
        "interventions_documented": "Alternatives Tried",
    },
    groups=[
        GroupPlan("Black", 240, 30, 10, 5, 0.70, 0.30),
        GroupPlan("Hispanic", 200, 12, 3, 3, 0.50, 0.50),
        GroupPlan("White", 120, 4, 1, 2, 0.30, 1.00),
        GroupPlan("Asian", 30, 1, 0, 2, 0.00, 1.00),
        GroupPlan("Two or More Races", 10, 1, 0, 1, 0.00, 1.00),
    ],
)

# Log B: a high school exported as XLSX with different aliases and IEP / EL / FRL fields.
LOG_B = LogPlan(
    name="school_b",
    seed=202,
    fmt="xlsx",
    headers={
        "student_name": "Name (Last, First)",
        "student_id": "Student Number",
        "incident_date": "Event Date",
        "action_type": "Disposition",
        "days_assigned": "Duration",
        "grade": "Grade Level",
        "incident_category": "Misconduct",
        "race_ethnicity": "Race",
        "gender": "Sex",
        "iep": "SpEd",
        "el": "ELL",
        "low_income": "FRL",
    },
    groups=[
        GroupPlan("Black", 400, 45, 15, 4, 0.60, 0.40),
        GroupPlan("Hispanic", 500, 30, 5, 3, 0.45, 0.60),
        GroupPlan("White", 300, 12, 2, 3, 0.25, 0.90),
        GroupPlan("Asian", 60, 2, 0, 2, 0.00, 1.00),
    ],
)

# Log C: a small school where most subgroups fall under the suppression threshold.
LOG_C = LogPlan(
    name="school_c_small",
    seed=303,
    headers={
        "student_id": "ID",
        "incident_date": "Date",
        "action_type": "Action",
        "days_assigned": "Length",
        "race_ethnicity": "Ethnicity",
        "incident_category": "Behavior",
    },
    groups=[
        GroupPlan("Black", 45, 6, 2, 2, 0.50, 0.50),
        GroupPlan("Hispanic", 30, 3, 0, 2, 0.50, 0.50),
        GroupPlan("White", 8, 1, 0, 1, 0.00, 1.00),
    ],
)


def _rows(plan: LogPlan) -> tuple[list[dict], dict[str, dict]]:
    rng = random.Random(plan.seed)
    fake = Faker()
    fake.seed_instance(plan.seed)
    start = date(2025, 9, 2)
    rows: list[dict] = []
    for g in plan.groups:
        n_students = g.suspended_once + g.suspended_twice
        incidents = g.suspended_once + 2 * g.suspended_twice
        n_subjective = round(incidents * g.subjective_share)
        categories = [rng.choice(sorted(SUBJECTIVE)) for _ in range(n_subjective)] + [
            rng.choice(sorted(OBJECTIVE)) for _ in range(incidents - n_subjective)
        ]
        rng.shuffle(categories)
        long_oss = incidents if g.days_each > 3 else 0
        n_documented = round(long_oss * g.documented_interventions)
        documented = [True] * n_documented + [False] * (long_oss - n_documented)
        k = 0
        for s in range(n_students):
            sid = f"{rng.randint(10_000_000, 99_999_999)}"
            name = f"{fake.last_name()}, {fake.first_name()}"
            grade = rng.randint(6, 12) if plan.name == "school_b" else rng.randint(3, 8)
            times = 2 if s < g.suspended_twice else 1
            for _ in range(times):
                when = start + timedelta(days=rng.randint(0, 250))
                rows.append(
                    {
                        "student_name": name,
                        "student_id": sid,
                        "incident_date": when.strftime("%m/%d/%Y") if k % 3 else when.isoformat(),
                        "action_type": "OSS",
                        "days_assigned": str(g.days_each),
                        "grade": str(grade),
                        "incident_category": categories[k],
                        "race_ethnicity": g.group,
                        "gender": rng.choice(["M", "F"]),
                        "iep": rng.choice(["Y", "N", "N", "N"]),
                        "el": rng.choice(["Y", "N", "N"]),
                        "low_income": rng.choice(["Y", "Y", "N"]),
                        "interventions_documented": (
                            ("Yes" if documented[k] else "No") if long_oss else ""
                        ),
                    }
                )
                k += 1
        # a few in-school suspensions, which OSS metrics must ignore
        for _ in range(3):
            rows.append(
                {
                    **rows[-1],
                    "student_id": f"{rng.randint(10_000_000, 99_999_999)}",
                    "student_name": f"{fake.last_name()}, {fake.first_name()}",
                    "action_type": "ISS",
                    "days_assigned": "1",
                    "interventions_documented": "",
                }
            )
    rng.shuffle(rows)
    enrollment = {g.group: g.enrolled for g in plan.groups}
    return rows, {"enrollment": enrollment}


def expected_metrics(plan: LogPlan) -> dict:
    """Metrics derived from the plan alone (Appendix E), independent of the rows."""
    total_enrolled = sum(g.enrolled for g in plan.groups)
    total_incidents = sum(g.suspended_once + 2 * g.suspended_twice for g in plan.groups)
    by_group: dict[str, dict] = {}
    rates: dict[str, float | None] = {}
    for g in plan.groups:
        students = g.suspended_once + g.suspended_twice
        incidents = g.suspended_once + 2 * g.suspended_twice
        days = incidents * g.days_each
        small = g.enrolled < SUPPRESS_BELOW or students < SUPPRESS_BELOW
        rate = None if small else round(100 * students / g.enrolled, 2)
        rates[g.group] = rate
        long_oss = incidents if g.days_each > 3 else 0
        subj = round(incidents * g.subjective_share)
        by_group[g.group] = {
            "enrolled": g.enrolled if g.enrolled >= SUPPRESS_BELOW else "<10",
            "students_suspended": students if students >= SUPPRESS_BELOW else "<10",
            "students_suspended_per_100": rate,
            "days_lost_per_100": None if small else round(100 * days / g.enrolled, 2),
            "composition_index": (
                None
                if small
                else round((incidents / total_incidents) / (g.enrolled / total_enrolled), 3)
            ),
            "documented_intervention_share": (
                round(round(long_oss * g.documented_interventions) / long_oss, 3)
                if long_oss >= SUPPRESS_BELOW
                else None
            ),
            "subjective_share": round(subj / incidents, 3) if incidents >= SUPPRESS_BELOW else None,
            "repeat_share": (
                round(g.suspended_twice / students, 3) if students >= SUPPRESS_BELOW else None
            ),
        }
    # Risk ratio: against white students, or against all other students when the
    # white rate is suppressed. Both rates must clear the threshold.
    white = rates.get("White")
    students_by = {g.group: g.suspended_once + g.suspended_twice for g in plan.groups}
    enrolled_by = {g.group: g.enrolled for g in plan.groups}
    for grp, m in by_group.items():
        r = rates[grp]
        if white is not None and grp != "White":
            ref, reference = white, "white"
        else:
            other_students = sum(v for k, v in students_by.items() if k != grp)
            other_enrolled = sum(v for k, v in enrolled_by.items() if k != grp)
            ok = other_students >= SUPPRESS_BELOW and other_enrolled >= SUPPRESS_BELOW
            ref = round(100 * other_students / other_enrolled, 2) if ok else None
            reference = "all other students"
        m["risk_ratio"] = round(r / ref, 3) if r is not None and ref else None
        m["risk_ratio_reference"] = reference
    return {
        "log": plan.name,
        "synthetic": True,
        "suppression_threshold": SUPPRESS_BELOW,
        "oss_incidents": total_incidents,
        "iss_rows_ignored": 3 * len(plan.groups),
        "by_race_ethnicity": by_group,
    }


def write(plan: LogPlan) -> Path:
    rows, extra = _rows(plan)
    std_fields = list(plan.headers)
    header = [plan.headers[f] for f in std_fields]
    out = HERE / f"{plan.name}.{plan.fmt}"
    if plan.fmt == "csv":
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            for r in rows:
                w.writerow([r[f] for f in std_fields])
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Discipline Log"
        ws.append(header)
        for r in rows:
            ws.append([r[f] for f in std_fields])
        wb.save(out)
    exp_dir = HERE / "expected"
    exp_dir.mkdir(exist_ok=True)
    expected = expected_metrics(plan) | extra
    (exp_dir / f"{plan.name}.json").write_text(
        json.dumps(expected, indent=2) + "\n", encoding="utf-8"
    )
    return out


if __name__ == "__main__":
    for p in (LOG_A, LOG_B, LOG_C):
        print("wrote", write(p).relative_to(HERE.parent))
