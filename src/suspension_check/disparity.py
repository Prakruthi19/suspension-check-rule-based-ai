"""Pattern Check: disparity metrics from a school discipline log.

The pipeline is: read (CSV or XLSX, bounded) -> map headers to the Appendix D
schema -> drop names, hash student IDs with a per-request salt -> validate ->
compute the Appendix E metrics with small-cell suppression.

Privacy rules this module enforces:

* Only mapped columns are read. Name columns and every unmapped column are
  dropped before any value is parsed.
* A student ID is replaced by an HMAC with a random per-call salt the moment it
  is read. The salt is never returned or stored, so hashes cannot be linked
  across uploads. The raw ID is never kept.
* No subgroup with fewer than ``SUPPRESS_BELOW`` students is shown as a count
  or used in a rate or ratio. Subgroup labels that are not in the enrollment
  table and have fewer than ``SUPPRESS_BELOW`` rows are merged into
  "Other or unlisted", so a free-text value cannot be shown as a label.

Requires the ``pattern`` extra for XLSX (``openpyxl``).
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import re
import secrets
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

__all__ = [
    "DIMENSIONS",
    "MAX_BYTES",
    "MAX_ROWS",
    "SUPPRESS_BELOW",
    "PatternError",
    "Table",
    "analyze",
    "propose_mapping",
    "read_table",
]

SUPPRESS_BELOW = 10
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 20_000
MAX_COLUMNS = 60
MAX_XLSX_UNPACKED = 40 * 1024 * 1024  # a 2 MB workbook that unpacks past this is a zip bomb
OTHER = "Other or unlisted"

# Appendix D: standard field -> aliases (compared after normalisation).
ALIASES: dict[str, tuple[str, ...]] = {
    "incident_date": ("incident_date", "date", "incident date", "event date"),
    "action_type": ("action_type", "action", "consequence", "disposition", "action type"),
    "days_assigned": ("days_assigned", "days", "length", "duration", "days assigned"),
    "grade": ("grade", "grade level", "gr"),
    "incident_category": ("incident_category", "infraction", "misconduct", "offense", "behavior"),
    "race_ethnicity": ("race_ethnicity", "race", "ethnicity", "race/ethnicity"),
    "gender": ("gender", "sex"),
    "iep": ("iep", "sped", "special education", "disability"),
    "el": ("el", "ell", "lep", "english learner"),
    "low_income": ("low_income", "frl", "low income", "economically disadvantaged"),
    "interventions_documented": (
        "interventions_documented",
        "interventions",
        "prior interventions",
        "alternatives tried",
    ),
    "student_id": ("student_id", "id", "student id", "student number"),
}
REQUIRED = ("incident_date", "action_type", "days_assigned")
NAME_HEADERS = {"student name", "name", "name (last, first)", "first name", "last name"}

# Subgroup dimensions, in the order they are reported.
DIMENSIONS = ("race_ethnicity", "gender", "iep", "el", "low_income")
_YES_NO_DIMS = {"iep", "el", "low_income"}

SUBJECTIVE = {"defiance", "disrespect", "disruption", "insubordination"}
_OSS = {"oss", "out-of-school suspension", "out of school suspension", "suspension (oss)"}
_YES = {"y", "yes", "true", "1", "x"}
_NO = {"n", "no", "false", "0", ""}
_RACE_CANON = {
    "white": "White",
    "black": "Black",
    "black or african american": "Black",
    "african american": "Black",
    "hispanic": "Hispanic",
    "hispanic or latino": "Hispanic",
    "latino": "Hispanic",
    "asian": "Asian",
    "american indian": "American Indian or Alaska Native",
    "american indian or alaska native": "American Indian or Alaska Native",
    "pacific islander": "Native Hawaiian or Pacific Islander",
    "native hawaiian or pacific islander": "Native Hawaiian or Pacific Islander",
    "two or more races": "Two or More Races",
    "multiracial": "Two or More Races",
}


class PatternError(ValueError):
    """A file Pattern Check cannot analyse. The message is safe to show: it
    names columns and row numbers, never cell values."""


def _norm(header: str) -> str:
    return re.sub(r"\s+", " ", str(header).strip().lower())


# --- reading ------------------------------------------------------------------


@dataclass
class Table:
    headers: list[str]
    rows: list[list[object]]


def read_table(raw: bytes, filename: str = "") -> Table:
    """Read CSV or XLSX into memory, within the size, row and column limits."""
    if len(raw) > MAX_BYTES:
        raise PatternError(f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    if raw[:2] == b"PK" or filename.lower().endswith((".xlsx", ".xlsm")):
        headers, rows = _read_xlsx(raw)
    else:
        headers, rows = _read_csv(raw)
    if not headers or not any(h.strip() for h in headers):
        raise PatternError("The file has no header row.")
    if len(headers) > MAX_COLUMNS:
        raise PatternError(f"The file has more than {MAX_COLUMNS} columns.")
    if len(rows) > MAX_ROWS:
        raise PatternError(f"The file has more than {MAX_ROWS:,} rows.")
    return Table(headers=[str(h).strip() for h in headers], rows=rows)


def _read_csv(raw: bytes) -> tuple[list[str], list[list[object]]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    headers = next(reader, [])
    rows: list[list[object]] = []
    for row in reader:
        if len(rows) > MAX_ROWS:
            break
        if any(c.strip() for c in row):
            rows.append(list(row))
    return headers, rows


def _read_xlsx(raw: bytes) -> tuple[list[str], list[list[object]]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - depends on the install
        raise PatternError("XLSX support needs the 'pattern' extra (openpyxl).") from exc
    import zipfile

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            unpacked = sum(i.file_size for i in z.infolist())
    except zipfile.BadZipFile as exc:
        raise PatternError("The file is not a readable XLSX workbook.") from exc
    if unpacked > MAX_XLSX_UNPACKED:
        raise PatternError("The workbook is too large once unpacked.")
    try:
        # read_only streams rows; data_only reads cached values, never formulas.
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:  # zipfile/openpyxl raise many types for bad files
        raise PatternError("The file is not a readable XLSX workbook.") from exc
    try:
        ws = wb.worksheets[0]
        it = ws.iter_rows(values_only=True)
        first = next(it, None)
        headers = ["" if v is None else str(v) for v in (first or ())]
        rows: list[list[object]] = []
        for row in it:
            if len(rows) > MAX_ROWS:
                break
            if any(v not in (None, "") for v in row):
                rows.append(list(row))
        return headers, rows
    finally:
        wb.close()


# --- mapping ------------------------------------------------------------------

_ALIAS_INDEX = {alias: std for std, aliases in ALIASES.items() for alias in aliases}


def propose_mapping(headers: list[str]) -> dict[str, str | None]:
    """Header -> standard field, ``"name"`` for a name column, or None (ignored)."""
    out: dict[str, str | None] = {}
    taken: set[str] = set()
    for h in headers:
        n = _norm(h)
        if n in NAME_HEADERS or ("name" in n and n not in _ALIAS_INDEX):
            out[h] = "name"
            continue
        std = _ALIAS_INDEX.get(n)
        if std and std not in taken:
            out[h] = std
            taken.add(std)
        else:
            out[h] = None
    return out


def _check_mapping(headers: list[str], mapping: dict[str, str | None]) -> dict[str, int]:
    """Validate a (possibly user-corrected) mapping; return field -> column index."""
    unknown = [h for h in mapping if h not in headers]
    if unknown:
        raise PatternError(f"The mapping names columns that are not in the file: {unknown}.")
    index: dict[str, int] = {}
    for i, h in enumerate(headers):
        std = mapping.get(h)
        if std in (None, "name"):
            continue
        if std not in ALIASES:
            raise PatternError(f"'{std}' is not a Pattern Check field.")
        if std in index:
            raise PatternError(f"Two columns are mapped to '{std}'.")
        index[std] = i
    missing = [f for f in REQUIRED if f not in index]
    if missing:
        raise PatternError(
            "Pattern Check needs a column for each of: "
            + ", ".join(missing)
            + ". Map one of the file's columns to each, or check that this is a discipline log."
        )
    return index


# --- parsing values ------------------------------------------------------------


def _date(v: object) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _number(v: object) -> float | None:
    if isinstance(v, int | float) and not isinstance(v, bool):
        return float(v)
    try:
        return float(str(v).strip())
    except ValueError:
        return None


def _yes_no(v: object) -> bool | None:
    s = str(v if v is not None else "").strip().lower()
    if s in _YES:
        return True
    if s in _NO:
        return None if s == "" else False
    return None


def _label(dim: str, v: object) -> str | None:
    s = re.sub(r"\s+", " ", str(v if v is not None else "").strip())
    if not s:
        return None
    if dim == "race_ethnicity":
        return _RACE_CANON.get(s.lower(), s)
    if dim in _YES_NO_DIMS:
        yn = _yes_no(s)
        return None if yn is None else ("Yes" if yn else "No")
    if dim == "gender":
        return {"m": "Male", "f": "Female", "male": "Male", "female": "Female"}.get(s.lower(), s)
    return s


def _grade_band(v: object) -> str | None:
    s = str(v if v is not None else "").strip().upper()
    if s in ("K", "KG", "PK"):
        return "K to 2"
    n = _number(s)
    if n is None:
        return None
    n = int(n)
    if n <= 2:
        return "K to 2"
    if n <= 5:
        return "3 to 5"
    if n <= 8:
        return "6 to 8"
    if n <= 12:
        return "9 to 12"
    return None


# --- records ---------------------------------------------------------------------


@dataclass
class _Incident:
    when: date
    oss: bool
    days: float
    student: str | None  # salted hash, or None
    long_documented: bool | None  # interventions documented, None when not recorded
    subjective: bool | None
    grade_band: str | None
    groups: dict[str, str | None] = field(default_factory=dict)


def _records(table: Table, index: dict[str, int]) -> tuple[list[_Incident], list[str]]:
    salt = secrets.token_bytes(16)  # per call; never returned or stored
    bad_rows: list[int] = []
    out: list[_Incident] = []

    def cell(row: list[object], f: str) -> object:
        i = index.get(f)
        return row[i] if i is not None and i < len(row) else None

    for n, row in enumerate(table.rows, start=2):  # row 1 is the header
        when = _date(cell(row, "incident_date"))
        days = _number(cell(row, "days_assigned"))
        action = str(cell(row, "action_type") or "").strip().lower()
        if when is None or days is None or days < 0 or not action:
            bad_rows.append(n)
            continue
        sid = cell(row, "student_id")
        student = None
        if "student_id" in index and str(sid or "").strip():
            student = hmac.new(salt, str(sid).strip().encode(), hashlib.sha256).hexdigest()
        category = cell(row, "incident_category")
        out.append(
            _Incident(
                when=when,
                oss=action in _OSS,
                days=days,
                student=student,
                long_documented=(
                    _yes_no(cell(row, "interventions_documented"))
                    if "interventions_documented" in index
                    else None
                ),
                subjective=(
                    str(category or "").strip().lower() in SUBJECTIVE
                    if "incident_category" in index and str(category or "").strip()
                    else None
                ),
                grade_band=_grade_band(cell(row, "grade")) if "grade" in index else None,
                groups={d: _label(d, cell(row, d)) for d in DIMENSIONS if d in index},
            )
        )
    warnings = []
    if bad_rows:
        share = len(bad_rows) / max(1, len(table.rows))
        shown = ", ".join(str(r) for r in bad_rows[:5]) + (" and more" if len(bad_rows) > 5 else "")
        if share > 0.05:
            raise PatternError(
                f"{len(bad_rows)} of {len(table.rows)} rows have a missing or unreadable date, "
                f"action, or number of days (rows {shown}). Check the column mapping."
            )
        warnings.append(
            f"{len(bad_rows)} rows were skipped because the date, action, or days could not "
            f"be read (rows {shown})."
        )
    return out, warnings


# --- metrics ----------------------------------------------------------------------


def _shown(n: int) -> int | str:
    return n if n >= SUPPRESS_BELOW else "<10"


def _dimension(
    dim: str, oss: list[_Incident], enrollment: dict[str, int] | None, has: set[str]
) -> dict[str, dict]:
    enrollment = {k: int(v) for k, v in (enrollment or {}).items()}
    rows_by: dict[str, list[_Incident]] = defaultdict(list)
    for inc in oss:
        g = inc.groups.get(dim)
        if g is not None:
            rows_by[g].append(inc)
    # Merge small labels the enrollment table does not know about.
    for g in [g for g in rows_by if g not in enrollment and len(rows_by[g]) < SUPPRESS_BELOW]:
        if g != OTHER:
            rows_by[OTHER].extend(rows_by.pop(g))
    groups = list(enrollment) + [g for g in rows_by if g not in enrollment]

    def students(incs: list[_Incident]) -> int:
        if "student_id" in has:
            return len({i.student for i in incs if i.student})
        return len(incs)

    total_incidents = len([i for i in oss if i.groups.get(dim) is not None])
    total_enrolled = sum(enrollment.values())
    stats: dict[str, dict] = {}
    rates: dict[str, float | None] = {}
    count_by: dict[str, int] = {}
    for g in groups:
        incs = rows_by.get(g, [])
        n_students = students(incs)
        count_by[g] = n_students
        enrolled = enrollment.get(g)
        small = enrolled is None or enrolled < SUPPRESS_BELOW or n_students < SUPPRESS_BELOW
        rate = None if small else round(100 * n_students / enrolled, 2)
        rates[g] = rate
        long = [i for i in incs if i.days > 3 and i.long_documented is not None]
        subj = [i for i in incs if i.subjective is not None]
        per_student = Counter(i.student for i in incs if i.student)
        stats[g] = {
            "enrolled": None if enrolled is None else _shown(enrolled),
            "students_suspended": _shown(n_students),
            "students_suspended_per_100": rate,
            "days_lost_per_100": (
                None if small else round(100 * sum(i.days for i in incs) / enrolled, 2)
            ),
            "composition_index": (
                None
                if small or not total_incidents
                else round((len(incs) / total_incidents) / (enrolled / total_enrolled), 3)
            ),
            "documented_intervention_share": (
                round(sum(1 for i in long if i.long_documented) / len(long), 3)
                if "interventions_documented" in has and len(long) >= SUPPRESS_BELOW
                else None
            ),
            "subjective_share": (
                round(sum(1 for i in subj if i.subjective) / len(subj), 3)
                if len(subj) >= SUPPRESS_BELOW
                else None
            ),
            "repeat_share": (
                round(sum(1 for c in per_student.values() if c >= 2) / len(per_student), 3)
                if "student_id" in has and len(per_student) >= SUPPRESS_BELOW
                else None
            ),
        }
    # Risk ratio (Appendix E): against white students when that rate is
    # reportable, otherwise against all other students. Both must clear the bar.
    white = rates.get("White") if dim == "race_ethnicity" else None
    for g, m in stats.items():
        r = rates[g]
        if white is not None and g != "White":
            ref, reference = white, "white"
        else:
            other_students = sum(v for k, v in count_by.items() if k != g)
            other_enrolled = sum(v for k, v in enrollment.items() if k != g)
            ok = other_students >= SUPPRESS_BELOW and other_enrolled >= SUPPRESS_BELOW
            ref = round(100 * other_students / other_enrolled, 2) if ok else None
            reference = "all other students"
        m["risk_ratio"] = round(r / ref, 3) if r is not None and ref else None
        m["risk_ratio_reference"] = reference
    return stats


def _counts(keys: list[str]) -> dict[str, int | str]:
    return {k: _shown(v) for k, v in sorted(Counter(keys).items())}


def analyze(
    raw: bytes,
    filename: str = "",
    enrollment: dict[str, dict[str, int]] | None = None,
    mapping: dict[str, str | None] | None = None,
) -> dict:
    """Run Pattern Check on one file. ``enrollment`` maps a dimension (such as
    ``race_ethnicity``) to subgroup counts. ``mapping`` overrides the proposed
    header mapping (the user's confirmation step)."""
    table = read_table(raw, filename)
    proposed = propose_mapping(table.headers)
    final = {**proposed, **(mapping or {})}
    index = _check_mapping(table.headers, final)
    incidents, warnings = _records(table, index)
    oss = [i for i in incidents if i.oss]
    if not oss:
        raise PatternError(
            "No out-of-school suspensions were found. Check that the action column is mapped "
            "and uses 'OSS' or 'Out-of-school suspension'."
        )
    has = set(index)
    if "student_id" not in has:
        warnings.append(
            "No student ID column, so each suspension is counted as a different student and "
            "repeat suspensions cannot be measured."
        )
    enrollment = enrollment or {}
    by_dim = {
        f"by_{d}": _dimension(d, oss, enrollment.get(d), has)
        for d in DIMENSIONS
        if d in has or d in enrollment
    }
    long = [i for i in oss if i.days > 3 and i.long_documented is not None]
    return {
        "suppression_threshold": SUPPRESS_BELOW,
        "rows_read": len(table.rows),
        "oss_incidents": len(oss),
        "iss_rows_ignored": len(incidents) - len(oss),
        "mapping": final,
        "dropped_columns": [h for h, f in final.items() if f in (None, "name")],
        "fields_found": sorted(has - {"student_id"}),
        "warnings": warnings,
        "documented_intervention_share": (
            round(sum(1 for i in long if i.long_documented) / len(long), 3)
            if "interventions_documented" in has and len(long) >= SUPPRESS_BELOW
            else None
        ),
        **by_dim,
        "monthly": _counts([f"{i.when:%Y-%m}" for i in oss]),
        "grade_bands": _counts([i.grade_band for i in oss if i.grade_band]),
    }
