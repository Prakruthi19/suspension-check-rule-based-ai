# Pattern Check upload schema v1

One row per incident. Headers are mapped to the standard fields below using the
aliases listed; the user confirms the mapping before analysis. Any column that
looks like a name or student identifier is dropped, or hashed in memory with a
per-request salt for repeat counting and then discarded. Pattern Check itself
is Week 5 work; this schema is what the synthetic logs in `synthetic/` follow.

| Field | Required | Type | Aliases (case-insensitive) |
|---|---|---|---|
| `incident_date` | Yes | Date (ISO or US) | Date, Incident Date, Event Date |
| `action_type` | Yes | ISS, OSS, Expulsion, Alternative placement, Bus, Other | Action, Consequence, Disposition |
| `days_assigned` | Yes | Number (school days) | Days, Length, Duration |
| `grade` | No | K to 12 | Grade Level, Gr |
| `incident_category` | No | Text, mapped to objective / subjective | Infraction, Misconduct, Offense, Behavior |
| `race_ethnicity` | No | ISBE categories | Race, Ethnicity, Race/Ethnicity |
| `gender` | No | Category | Sex |
| `iep` | No | Yes/No | IEP, SpEd, Special Education, Disability |
| `el` | No | Yes/No | EL, ELL, LEP, English Learner |
| `low_income` | No | Yes/No | FRL, Low Income, Economically Disadvantaged |
| `interventions_documented` | No | Yes/No | Interventions, Prior Interventions, Alternatives Tried |
| `student_id` | No | Text; never displayed, hashed then discarded | ID, Student ID, Student Number |
| *(names)* | Never used | Dropped on ingest | Student Name, Name, Name (Last, First), First Name, Last Name |
| enrollment (separate table) | Optional | Subgroup, count | Typed in or pasted from the Illinois Report Card |

Subjective categories: Defiance, Disrespect, Disruption, Insubordination.

Suppression: any subgroup with fewer than 10 students is shown as `<10` and no
rate or ratio is computed from it (Appendix E).

## Synthetic logs

| File | Headers exercised | What it tests |
|---|---|---|
| `synthetic/school_a.csv` | Student Name, Student ID, Consequence, Days, Gr, Infraction, Race/Ethnicity, Alternatives Tried | Large Black-white disparity; white rate suppressed so risk ratios fall back to "all other students" |
| `synthetic/school_b.xlsx` | Name (Last, First), Student Number, Disposition, Duration, Misconduct, Race, Sex, SpEd, ELL, FRL | XLSX ingest; every optional field present; risk ratios against white |
| `synthetic/school_c_small.csv` | ID, Date, Action, Length, Ethnicity, Behavior | Small school: every rate suppressed |

Expected metrics are in `synthetic/expected/*.json`, derived from the
generation plan alone so they can be checked by hand.
