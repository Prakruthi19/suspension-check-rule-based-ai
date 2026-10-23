# Pattern Check metrics

Definitions follow Appendix E of the brief. Code: `src/suspension_check/disparity.py`.
Every number below comes from the **synthetic** logs in `synthetic/` and is
checked exactly in `tests/test_disparity.py`.

Only out-of-school suspensions (OSS) are counted. Other rows (in-school
suspensions, bus suspensions) are read, counted as "ignored", and left out.

## Suppression comes first

Any subgroup with fewer than **10** students is shown as `<10`, and nothing is
computed from it: no rate, no composition index, no risk ratio. Shares
(subjective categories, documented interventions, repeat suspensions) need a
denominator of at least 10. Monthly and grade-band counts under 10 are shown as
`<10`. A label that is not in the enrollment table and appears fewer than 10
times is merged into "Other or unlisted", so a name typed into a race column
can never appear as a group.

This is a feature, not a limitation: a disparity finding that could identify
one child would do more harm than the finding is worth.

## Worked example: school B (synthetic), Black students

Enrollment (typed in by the user): Black 400, Hispanic 500, White 300, Asian 60.
Total 1,260. The log has 133 OSS incidents.

| Metric | Definition | Black students | White students |
|---|---|---|---|
| Students suspended | Distinct student IDs with at least one OSS | 60 | 14 |
| Suspended per 100 | students / enrollment x 100 | 60 / 400 x 100 = **15.0** | 14 / 300 x 100 = **4.67** |
| Days lost per 100 | OSS days / enrollment x 100 | 75 incidents x 4 days = 300; 300 / 400 x 100 = **75.0** | 48 / 300 x 100 = **16.0** |
| Risk ratio | group rate / reference rate. Reference is white students when their rate is reportable, else all other students | 15.0 / 4.67 = **3.212** (vs white) | 4.67 / 10.10 = **0.462** (vs all others: 97 of 960) |
| Composition index | share of incidents / share of enrollment. 1.0 is proportional | (75 / 133) / (400 / 1260) = **1.776** | **0.505** |
| Subjective share | incidents coded defiance, disrespect, disruption, insubordination / incidents | 45 / 75 = **0.6** | **0.25** |
| Repeat share | students with 2+ OSS / students with 1+ | 15 / 60 = **0.25** | 2 / 14 = **0.143** |

Rates are rounded to 2 decimals and ratios to 3, and a risk ratio is computed
from the rounded rates, exactly as the expected values were hand-derived.

## Worked example: school A (synthetic), when the white group is too small

White students: 120 enrolled, but only 5 were suspended. Five is under 10, so
the white rate is suppressed and every risk ratio falls back to "all other
students". For Black students: 40 of 240 suspended, 16.67 per 100. All other
students: 22 of 360 suspended (Hispanic 15, White 5, Asian 1, Two or More Races
1), 6.11 per 100. Risk ratio: 16.67 / 6.11 = **2.728**. The suppressed groups
still count toward "all other students"; they are only never shown on their own.

## Worked example: school C (synthetic), a small school

Every subgroup has fewer than 10 suspended students, so every rate and ratio is
suppressed. Only one share survives: Black students have 10 incidents, half in
subjective categories (0.5), because that share's denominator is incidents, and
10 meets the threshold.

## Other outputs

| Output | Notes |
|---|---|
| Documented-intervention share | Among OSS longer than 3 school days, the share with interventions documented. Illinois requires the school to consider and document other interventions first (105 ILCS 5/10-22.6(b-20)). Only when the log has that column |
| Monthly trend | OSS incidents per month, cells under 10 shown as `<10` |
| Grade bands | K to 2, 3 to 5, 6 to 8, 9 to 12 |
| Dropped columns | Names and every unmapped column, listed by header only |

## Without enrollment

Rates, risk ratios, and the composition index need enrollment counts. Without
them Pattern Check still reports suppressed counts and the three shares.
Enrollment by subgroup is published on the Illinois Report Card
(illinoisreportcard.com).
