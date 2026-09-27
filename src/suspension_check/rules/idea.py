"""Federal layer: IDEA discipline rules (34 CFR 300.530-300.536) and Section 504 (34 CFR 104.35).

Rules never compute dates. The manifestation determination deadline and the
other IDEA clocks are obligations emitted by ``suspension_check.timeline``.
"""

from __future__ import annotations

from suspension_check.facts import Facts, ManifestationResult, RemovalKind
from suspension_check.rules import Layer, Severity, all3, is_no, rule
from suspension_check.rules.sources import SOURCES

FED = Layer.FEDERAL


def _over_ten_cumulative(f: Facts) -> bool | None:
    if f.removal.school_days > 10:
        return True
    cumulative = f.cumulative_days
    return None if cumulative is None else cumulative > 10


def _change_of_placement(f: Facts) -> bool | None:
    return f.is_change_of_placement


@rule(
    id="FED-01",
    layer=FED,
    citation="34 CFR 300.530(d)",
    url=SOURCES["CFR_300_530"],
    quote=(
        "A child with a disability who is removed from the child's current placement... "
        "must continue to receive educational services... so as to enable the child to "
        "continue to participate in the general education curriculum... and to progress "
        "toward meeting the goals set out in the child's IEP."
    ),
    flag=(
        "After 10 school days of removal in a school year, the district must keep "
        "providing services so your child can keep working toward IEP goals."
    ),
    action="Ask in writing what services your child will receive during the removal.",
    severity=Severity.INFO,
)
def services_after_ten_days(f: Facts) -> bool | None:
    return all3(f.student.disability.idea_protected, _over_ten_cumulative(f))


@rule(
    id="FED-02",
    layer=FED,
    citation="34 CFR 300.530(e); 300.536",
    url=SOURCES["CFR_300_530"],
    quote=(
        "...within 10 school days of any decision to change the placement of a child with "
        "a disability because of a violation of a code of student conduct, the LEA, the "
        "parent, and relevant members of the child's IEP Team... must review all relevant "
        "information in the student's file..."
    ),
    flag=(
        "This removal may be a change of placement. If it is, a manifestation "
        "determination review is due within 10 school days of the decision."
    ),
    action=(
        "Request a manifestation determination review in writing, and ask for all "
        "relevant records to be shared before the meeting."
    ),
    severity=Severity.ASSERT,
)
def manifestation_determination_due(f: Facts) -> bool | None:
    not_scheduled = (
        f.idea.mdr_scheduled_on is None and f.idea.mdr_result is ManifestationResult.NOT_HELD
    )
    return all3(f.student.disability.idea_protected, _change_of_placement(f), not_scheduled)


@rule(
    id="FED-03",
    layer=FED,
    citation="34 CFR 300.530(h)",
    url=SOURCES["CFR_300_530"],
    quote=(
        "On the date on which the decision is made to make a removal that constitutes a "
        "change of placement... the LEA must notify the parents of that decision, and "
        "provide the parents the procedural safeguards notice described in § 300.504."
    ),
    flag=(
        "On the day it decided on this removal, the district had to tell you and give "
        "you the procedural safeguards notice."
    ),
    action="Ask for the written notice of the decision and the procedural safeguards notice.",
    severity=Severity.ASSERT,
)
def same_day_safeguards_notice(f: Facts) -> bool | None:
    return all3(
        f.student.disability.idea_protected,
        _change_of_placement(f),
        is_no(f.notice.procedural_safeguards_notice),
    )


@rule(
    id="FED-04",
    layer=FED,
    citation="34 CFR 300.530(f)",
    url=SOURCES["CFR_300_530"],
    quote=(
        "...return the child to the placement from which the child was removed, unless "
        "the parent and the LEA agree to a change of placement..."
    ),
    flag=(
        "Because the behavior was found to be a manifestation of the disability, your "
        "child generally returns to their placement, and the team must do or revisit a "
        "functional behavioral assessment and behavior intervention plan."
    ),
    action="Ask for the return date and the date of the FBA / BIP meeting in writing.",
    severity=Severity.INFO,
)
def manifestation_found(f: Facts) -> bool:
    return f.idea.mdr_result is ManifestationResult.MANIFESTATION


@rule(
    id="FED-05",
    layer=FED,
    citation="34 CFR 300.530(g); 300.531",
    url=SOURCES["CFR_300_530"],
    quote=(
        "School personnel may remove a student to an interim alternative educational "
        "setting for not more than 45 school days..."
    ),
    flag=(
        "A special-circumstances removal (weapons, drugs, or serious bodily injury) "
        "cannot be longer than 45 school days, and the IEP team decides the setting."
    ),
    action="Ask for the IEP team meeting that decides the interim setting.",
    severity=Severity.INFO,
)
def special_circumstances_iaes(f: Facts) -> bool:
    return f.student.disability.idea_protected and f.removal.special_circumstances


@rule(
    id="FED-06",
    layer=FED,
    citation="34 CFR 300.532",
    url=SOURCES["CFR_300_532"],
    quote=(
        "The parent of a child with a disability who disagrees with any decision "
        "regarding placement under §§ 300.530 and 300.531, or the manifestation "
        "determination under § 300.530(e)... may appeal the decision by requesting a hearing."
    ),
    flag=(
        "If you disagree with the manifestation determination or the placement, you can "
        "ask for an expedited due process hearing."
    ),
    action="Consider contacting Equip for Equality, then request the expedited hearing in writing.",
    severity=Severity.ASK,
)
def expedited_hearing(f: Facts) -> bool:
    return f.idea.parent_disagrees_with_mdr


@rule(
    id="FED-07",
    layer=FED,
    citation="34 CFR 300.534",
    url=SOURCES["CFR_300_534"],
    quote=(
        "A child who has not been determined to be eligible for special education... may "
        "assert any of the protections provided for in this part if the public agency had "
        "knowledge... that the child was a child with a disability before the behavior "
        "that precipitated the disciplinary action occurred."
    ),
    flag=(
        "Your child does not have an IEP yet, but because an evaluation was requested or "
        "concern was raised in writing, the IDEA discipline protections may apply."
    ),
    action="Say so in writing and request an expedited evaluation.",
    severity=Severity.ASK,
)
def basis_of_knowledge(f: Facts) -> bool:
    return f.student.disability.basis_of_knowledge and f.removal.is_exclusion


@rule(
    id="FED-08",
    layer=FED,
    citation="34 CFR 104.35(a)",
    url=SOURCES["CFR_104_35"],
    quote=(
        "A recipient... shall conduct an evaluation... of any person who, because of "
        "handicap, needs or is believed to need special education or related services "
        "before taking any action with respect to... any subsequent significant change "
        "in placement."
    ),
    flag=(
        "For a student with a 504 plan, more than 10 school days of exclusion is a "
        "significant change in placement and needs a reevaluation first."
    ),
    action="Ask for the reevaluation before any further removal.",
    severity=Severity.ASSERT,
)
def section_504_reevaluation(f: Facts) -> bool | None:
    d = f.student.disability
    return all3(
        d.plan_504 and not d.iep,
        f.removal.is_exclusion,
        _over_ten_cumulative(f),
        is_no(f.idea.reevaluation_504_done),
    )


@rule(
    id="FED-09",
    layer=FED,
    citation="34 CFR 300.530; OSEP discipline Q&A (2022)",
    url=SOURCES["OSEP_2022_DISCIPLINE_QA"],
    quote=(
        "...the use of informal removals... may constitute a disciplinary removal... and "
        "count toward the 10-day threshold."
    ),
    flag=(
        "Being sent home early or told to stay home counts toward the 10-day limit, even "
        "if the school did not call it a suspension."
    ),
    action="Write down every informal removal with its date and ask the school to record them.",
    severity=Severity.INFO,
)
def informal_removals_count(f: Facts) -> bool:
    return f.student.disability.idea_protected and (
        f.prior.informal_removals_reported or f.removal.kind is RemovalKind.INFORMAL
    )
