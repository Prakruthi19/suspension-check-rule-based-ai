# Family Check survey v1

Plain language, aimed at a sixth-grade reading level. Every question has a
**Not sure** option, which maps to `"unknown"` in the facts model. A rule that
would fire on an unknown answer is shown as **Ask**, never **Assert**.

Questions marked * branch.

| # | Question | Answers | Facts field | Feeds |
|---|---|---|---|---|
| 1 | Which district is your child's school in? | CPS / another Illinois district / not sure | `student.district` | Calendar, CPS layer |
| 2 | What grade is your child in? | PreK-2, 3-5, 6-8, 9-12 | `student.grade_band` | CPS grade-band rules (later) |
| 3* | Does your child have an IEP or a 504 plan? Is the school evaluating them? Did you ever ask in writing for an evaluation, or write to the school about a concern? | Multi-select | `student.disability.*` | FED rules, IDEA track. Any answer shows Q8 and the IDEA part of Q10 |
| 4 | When did the incident happen? | Date | `incident_date` | Timeline |
| 5 | In a sentence or two, what does the school say happened? | Short text | not stored in facts; **hidden until redaction ships (Week 3)** | Letter context |
| 6* | What did the school do? | In-school suspension / out-of-school suspension / expulsion recommended / moved to alternative school / bus suspension / sent home without paperwork / other | `removal.kind` | Expulsion shows Q11 |
| 7 | When was the decision made, when did the removal start, and how many school days is it? | Dates, number | `removal.decision_date`, `removal.start_date`, `removal.school_days` | Timeline, IL-05 to IL-11 |
| 8 | Before this, how many school days had your child been removed this school year, including times you were asked to pick them up early? | Number / not sure; checkbox "I was asked to pick my child up early or keep them home" | `prior.school_days_this_year`, `prior.informal_removals_reported` | FED-01, FED-02, FED-09 |
| 9* | Did you receive anything in writing? | Nothing / phone call only / paper or email notice | `notice.received` | IL-01. Anything but "written" skips Q10 |
| 10 | Does the written notice do each of the following? (Yes / No / Not sure each) | states the reasons; states the specific act; explains why this length; says other interventions were tried; says presence was a safety threat or disruption; tells you about your right to a review; mentions support services; mentions make-up work; (IEP) includes procedural safeguards notice; (IEP) invites you to a manifestation determination meeting; says a policy required the suspension | `notice.*` | IL-02 to IL-10, FED-03 |
| 11 | (Expulsion) Did you get a certified or registered letter asking you to a hearing? When is the hearing? | Yes / No / Not sure; date | `expulsion.*` | IL-12, IL-13, timeline |
| 12 | Have you already asked for a review, records, or a manifestation determination meeting? | Multi-select with dates | `actions.*` | Timeline state, letter variant |
| 13 | Which letter would you like? | Review request / MDR request / records request / expulsion response | (letters, Week 3) | Letter variant |
| 14 | Preferred language | English / Spanish (stretch) | (UI) | Output language |

Open questions for Gate 1:

- Q7 asks for three dates. Usability sessions may show that decision date and start date are usually the same; consider defaulting start = next school day after the decision.
- Q10 is long. Consider showing the IEP-only items only when Q3 is answered.
