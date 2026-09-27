"""Illinois layer: 105 ILCS 5/10-22.6 as amended by PA 99-0456 (SB 100), and ISSRA.

Quotes are transcribed from the ilga.gov text during Week 1. Every rule ships
with ``reviewed=False`` until the Gate 3 legal review signs it off.
"""

from __future__ import annotations

from dueproc.facts import Facts, NoticeReceived, RemovalKind
from dueproc.rules import Layer, Severity, any3, is_no, rule
from dueproc.rules.sources import SOURCES

IL = Layer.ILLINOIS
URL = SOURCES["ILCS_10_22_6"]

# Removals the statute treats as a suspension for notice purposes. An informal
# removal (sent home, no paperwork) is a suspension the school did not record.
SUSPENSIONS = {RemovalKind.OSS, RemovalKind.ISS, RemovalKind.BUS, RemovalKind.INFORMAL}
EXCLUSIONS_OUT_OF_SCHOOL = {RemovalKind.OSS, RemovalKind.BUS, RemovalKind.INFORMAL}


def _is_suspension(f: Facts) -> bool:
    return f.removal.kind in SUSPENSIONS


def _long_oss(f: Facts, over: int) -> bool:
    return f.removal.kind is RemovalKind.OSS and f.removal.school_days > over


@rule(
    id="IL-01",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b)",
    url=URL,
    quote=(
        "Any suspension shall be reported immediately to the parents or guardian of a "
        "student along with a full statement of the reasons for such suspension and a "
        "notice of their right to a review."
    ),
    flag=(
        "The school must tell you about a suspension right away, in writing, with a full "
        "statement of the reasons. You did not get that."
    ),
    action="Ask in writing for the written notice and the complete written suspension decision.",
    severity=Severity.ASSERT,
)
def notice_with_reasons(f: Facts) -> bool | None:
    if not _is_suspension(f):
        return False
    return any3(f.notice.received is not NoticeReceived.WRITTEN, is_no(f.notice.states_reasons))


@rule(
    id="IL-02",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b)",
    url=URL,
    quote=(
        "...along with a full statement of the reasons for such suspension and a notice "
        "of their right to a review."
    ),
    flag=(
        "You have the right to a review of the suspension, where you can appear and "
        "discuss it. The notice should have told you so."
    ),
    action="Request a review of the suspension in writing.",
    severity=Severity.ASSERT,
)
def notice_of_review_right(f: Facts) -> bool | None:
    return _is_suspension(f) and is_no(f.notice.states_review_right)


@rule(
    id="IL-03",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b)",
    url=URL,
    quote=(
        "The written suspension decision shall detail the specific act of gross "
        "disobedience or misconduct resulting in the decision to suspend."
    ),
    flag="The written decision must say exactly what your child is accused of doing.",
    action="Ask for a written decision that states the specific act.",
    severity=Severity.ASSERT,
)
def decision_states_specific_act(f: Facts) -> bool | None:
    return _is_suspension(f) and is_no(f.notice.states_specific_act)


@rule(
    id="IL-04",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b)",
    url=URL,
    quote="The written suspension decision shall also provide a rationale as to the specific duration of the suspension.",
    flag="The written decision must explain why the suspension is this long.",
    action="Ask for the rationale for the length of the suspension in writing.",
    severity=Severity.ASSERT,
)
def decision_states_duration_rationale(f: Facts) -> bool | None:
    return _is_suspension(f) and is_no(f.notice.states_rationale_for_length)


@rule(
    id="IL-05",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b-20)",
    url=URL,
    quote=(
        "...may be used only if other appropriate and available behavioral and "
        "disciplinary interventions have been exhausted..."
    ),
    flag=(
        "A suspension longer than three school days, an expulsion, or a move to an "
        "alternative school requires the school to have tried other interventions first "
        "and to say so in the written decision. Yours does not."
    ),
    action=(
        "Ask in writing for the written decision to state which interventions were "
        "attempted, or why none were appropriate and available."
    ),
    severity=Severity.ASSERT,
)
def long_suspension_requires_exhausted_interventions(f: Facts) -> bool | None:
    in_scope = _long_oss(f, 3) or f.removal.kind in {RemovalKind.ALTERNATIVE, RemovalKind.EXPULSION}
    return in_scope and is_no(f.notice.documents_interventions)


@rule(
    id="IL-06",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b-20)",
    url=URL,
    quote=(
        "...the student's continuing presence in school would either (i) pose a threat "
        "to the safety of other students, staff, or members of the school community or "
        "(ii) substantially disrupt, impede, or interfere with the operation of the school."
    ),
    flag=(
        "For a suspension over three days or an expulsion, the school must find that your "
        "child's presence was a safety threat or would substantially disrupt the school."
    ),
    action="Ask the school to state in writing which finding it made and on what facts.",
    severity=Severity.ASK,
)
def long_suspension_requires_threat_finding(f: Facts) -> bool | None:
    in_scope = _long_oss(f, 3) or f.removal.kind in {RemovalKind.ALTERNATIVE, RemovalKind.EXPULSION}
    return in_scope and is_no(f.notice.states_threat_or_disruption)


@rule(
    id="IL-07",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b-15)",
    url=URL,
    quote=(
        "Out-of-school suspensions of 3 days or less may be used only if the student's "
        "continuing presence in school would pose a threat to school safety or a "
        "disruption to other students' learning opportunities."
    ),
    flag=(
        "Short out-of-school suspensions are allowed only if your child's presence was "
        "a safety threat or a disruption to other students' learning."
    ),
    action="Ask the school to state that finding in writing.",
    severity=Severity.ASK,
)
def short_suspension_requires_threat_finding(f: Facts) -> bool | None:
    in_scope = f.removal.kind is RemovalKind.OSS and f.removal.school_days <= 3
    return in_scope and is_no(f.notice.states_threat_or_disruption)


@rule(
    id="IL-08",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b-25)",
    url=URL,
    quote=(
        "Students who are suspended out-of-school for longer than 4 school days shall "
        "be provided appropriate and available support services during the period of "
        "their suspension."
    ),
    flag=(
        "For a suspension over four school days, the decision must say whether support "
        "services will be provided, or why none are available."
    ),
    action="Ask for the support services determination and the services themselves.",
    severity=Severity.ASSERT,
)
def support_services_determination(f: Facts) -> bool | None:
    return _long_oss(f, 4) and is_no(f.notice.support_services_determination)


@rule(
    id="IL-09",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b-30)",
    url=URL,
    quote=(
        "...ensure that suspended students are provided the opportunity to make up work "
        "for equivalent academic credit."
    ),
    flag="Your child has the right to make up missed work for full credit.",
    action="Ask in writing for all missed work and the chance to make it up for equivalent credit.",
    severity=Severity.ASK,
)
def makeup_work(f: Facts) -> bool | None:
    return f.removal.kind in EXCLUSIONS_OUT_OF_SCHOOL and is_no(f.notice.mentions_makeup_work)


@rule(
    id="IL-10",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b-10)",
    url=URL,
    quote=(
        "...school boards may not institute zero-tolerance policies by which school "
        "administrators are required to suspend or expel students for particular behaviors."
    ),
    flag=(
        "Illinois bans zero-tolerance policies. The school cannot exclude your child "
        "just because a policy says it must."
    ),
    action="Ask for the individualized findings behind the decision.",
    severity=Severity.ASSERT,
)
def zero_tolerance_prohibited(f: Facts) -> bool:
    # Only fires on a clear "yes": an unknown here is not worth an Ask on its own.
    return f.notice.cites_zero_tolerance == "yes"


@rule(
    id="IL-11",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b)",
    url=URL,
    quote="...suspend or authorize the suspension of pupils ... for a period not to exceed 10 school days.",
    flag=(
        "A single suspension cannot be longer than 10 school days. Anything longer is an "
        "expulsion and needs the expulsion process."
    ),
    action="Ask the school to either shorten the suspension or follow the expulsion process.",
    severity=Severity.INFO,
)
def suspension_over_ten_days(f: Facts) -> bool:
    return f.removal.kind in {RemovalKind.OSS, RemovalKind.ISS} and f.removal.school_days > 10


@rule(
    id="IL-12",
    layer=IL,
    citation="105 ILCS 5/10-22.6(a)",
    url=URL,
    quote=(
        "...the parents or guardian of the pupil must be requested to appear at a meeting "
        "of the board, or with a hearing officer appointed by it... Such request shall be "
        "made by registered or certified mail and shall state the time, place and purpose "
        "of the meeting."
    ),
    flag=(
        "Before an expulsion, the school must ask you by registered or certified mail to "
        "come to a hearing."
    ),
    action="Ask for the hearing notice and confirm the hearing date in writing.",
    severity=Severity.ASSERT,
)
def expulsion_hearing_request(f: Facts) -> bool | None:
    if f.removal.kind is not RemovalKind.EXPULSION:
        return False
    if f.expulsion is None:
        return None
    return is_no(f.expulsion.hearing_request_by_certified_mail)


@rule(
    id="IL-13",
    layer=IL,
    citation="105 ILCS 5/10-22.6(a)",
    url=URL,
    quote=(
        "The written expulsion decision shall detail the specific reasons why removing "
        "the pupil from the learning environment is in the best interest of the school... "
        "[and] provide a rationale as to the specific duration of the expulsion."
    ),
    flag=(
        "An expulsion decision must state the specific reasons, why it is this long, "
        "and which other interventions were considered."
    ),
    action="Request a complete written expulsion decision.",
    severity=Severity.ASSERT,
)
def expulsion_decision_complete(f: Facts) -> bool | None:
    e = f.expulsion
    if f.removal.kind is not RemovalKind.EXPULSION or e is None or not e.decision_issued:
        return False
    return any3(
        is_no(e.decision_states_reasons),
        is_no(e.decision_states_duration_rationale),
        is_no(e.decision_documents_interventions),
    )


@rule(
    id="IL-14",
    layer=IL,
    citation="105 ILCS 5/10-22.6(a)",
    url=URL,
    quote="Expulsion shall take place only ... for a definite period of time not to exceed 2 calendar years.",
    flag="An expulsion cannot be longer than two calendar years.",
    action="Ask the district to correct the length of the expulsion.",
    severity=Severity.INFO,
)
def expulsion_over_two_years(f: Facts) -> bool:
    e = f.expulsion
    return (
        f.removal.kind is RemovalKind.EXPULSION
        and e is not None
        and e.length_calendar_days is not None
        and e.length_calendar_days > 731
    )


@rule(
    id="IL-15",
    layer=IL,
    citation="105 ILCS 10/5 (ISSRA)",
    url=SOURCES["ISSRA_5"],
    quote=(
        "A parent or any person specifically designated as a representative by a parent "
        "shall have the right to inspect and copy all school student permanent and "
        "temporary records of that parent's child."
    ),
    flag=(
        "You can see and copy your child's school records, including the referral and "
        "any record of interventions."
    ),
    action="Request the records in writing. The school has a deadline to respond.",
    severity=Severity.ASK,
)
def records_request(f: Facts) -> bool:
    return f.actions.records_requested_on is None


@rule(
    id="IL-16",
    layer=IL,
    citation="105 ILCS 5/10-22.6(b-35)",
    url=URL,
    quote=(
        "...school boards shall create a policy to facilitate the re-engagement of "
        "students who are suspended out-of-school, expelled, or returning from an "
        "alternative school setting."
    ),
    flag="The district must have a plan to help your child come back after this removal.",
    action="Ask what the re-engagement plan is for your child's return.",
    severity=Severity.INFO,
)
def reengagement(f: Facts) -> bool:
    return f.removal.kind in {RemovalKind.OSS, RemovalKind.EXPULSION, RemovalKind.ALTERNATIVE}


@rule(
    id="IL-17",
    layer=IL,
    citation="105 ILCS 5/10-22.6(d)",
    url=URL,
    quote=(
        "...a student who is determined to have brought ... a firearm to school ... shall "
        "be expelled for a period of not less than one year... The expulsion period may "
        "be modified by the superintendent... on a case-by-case basis."
    ),
    flag=(
        "A firearm expulsion is at least one year, but the superintendent can change it "
        "case by case."
    ),
    action="Ask in writing for a case-by-case review of the length.",
    severity=Severity.ASK,
)
def firearm_case_by_case(f: Facts) -> bool:
    return (
        f.removal.kind is RemovalKind.EXPULSION and f.expulsion is not None and f.expulsion.firearm
    )
