"""Typed facts collected by the Family Check survey.

Every answer that a parent might not know is a ``Tri`` ("yes" / "no" / "unknown").
Rules treat "unknown" as unknown, never as "no": a rule that would fire on an
unknown answer is downgraded from Assert to Ask by the evaluator.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Tri = Literal["yes", "no", "unknown"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class District(StrEnum):
    CPS = "cps"
    OTHER_IL = "other_il"
    UNKNOWN = "unknown"


class GradeBand(StrEnum):
    PRE_K_2 = "prek_2"
    GRADES_3_5 = "3_5"
    GRADES_6_8 = "6_8"
    GRADES_9_12 = "9_12"


class RemovalKind(StrEnum):
    ISS = "iss"  # in-school suspension
    OSS = "oss"  # out-of-school suspension
    EXPULSION = "expulsion"  # expulsion recommended
    ALTERNATIVE = "alternative"  # transfer to an alternative school
    BUS = "bus"  # bus suspension
    INFORMAL = "informal"  # sent home without paperwork
    OTHER = "other"


class NoticeReceived(StrEnum):
    NOTHING = "nothing"
    PHONE_ONLY = "phone_only"
    WRITTEN = "written"


class ManifestationResult(StrEnum):
    MANIFESTATION = "manifestation"
    NOT_MANIFESTATION = "not_manifestation"
    NOT_HELD = "not_held"


class DisabilityStatus(_Strict):
    iep: bool = False
    plan_504: bool = False
    being_evaluated: bool = False
    evaluation_requested_in_writing: bool = False
    concern_expressed_in_writing: bool = False

    @property
    def idea_protected(self) -> bool:
        """IEP, or a basis of knowledge under 34 CFR 300.534."""
        return self.iep or self.basis_of_knowledge

    @property
    def basis_of_knowledge(self) -> bool:
        return not self.iep and (
            self.being_evaluated
            or self.evaluation_requested_in_writing
            or self.concern_expressed_in_writing
        )


class Student(_Strict):
    district: District = District.UNKNOWN
    grade_band: GradeBand | None = None
    disability: DisabilityStatus = Field(default_factory=DisabilityStatus)


class Removal(_Strict):
    kind: RemovalKind
    decision_date: date
    start_date: date
    school_days: int = Field(ge=0, le=400)
    special_circumstances: bool = False  # weapons, drugs, serious bodily injury (IAES)

    @property
    def is_exclusion(self) -> bool:
        return self.kind in {
            RemovalKind.OSS,
            RemovalKind.EXPULSION,
            RemovalKind.ALTERNATIVE,
            RemovalKind.INFORMAL,
        }


class Notice(_Strict):
    received: NoticeReceived = NoticeReceived.NOTHING
    states_reasons: Tri = "unknown"
    states_specific_act: Tri = "unknown"
    states_rationale_for_length: Tri = "unknown"
    documents_interventions: Tri = "unknown"
    states_threat_or_disruption: Tri = "unknown"
    states_review_right: Tri = "unknown"
    support_services_determination: Tri = "unknown"
    mentions_makeup_work: Tri = "unknown"
    procedural_safeguards_notice: Tri = "unknown"
    mdr_invitation: Tri = "unknown"
    cites_zero_tolerance: Tri = "unknown"

    @model_validator(mode="after")
    def _no_written_means_no_contents(self) -> Notice:
        # Without a written notice, every "does the notice say..." answer is "no".
        if self.received is not NoticeReceived.WRITTEN:
            for name in type(self).model_fields:
                if name not in {"received", "cites_zero_tolerance"}:
                    object.__setattr__(self, name, "no")
        return self


class PriorRemovals(_Strict):
    school_days_this_year: int | None = Field(default=None, ge=0, le=200)
    informal_removals_reported: bool = False


class Expulsion(_Strict):
    hearing_request_by_certified_mail: Tri = "unknown"
    hearing_date: date | None = None
    decision_issued: bool = False
    decision_states_reasons: Tri = "unknown"
    decision_states_duration_rationale: Tri = "unknown"
    decision_documents_interventions: Tri = "unknown"
    length_calendar_days: int | None = Field(default=None, ge=0)
    firearm: bool = False


class ParentActions(_Strict):
    review_requested_on: date | None = None
    records_requested_on: date | None = None
    mdr_requested_on: date | None = None
    expedited_hearing_requested_on: date | None = None


class IdeaProcess(_Strict):
    mdr_scheduled_on: date | None = None
    mdr_result: ManifestationResult = ManifestationResult.NOT_HELD
    parent_disagrees_with_mdr: bool = False
    reevaluation_504_done: Tri = "unknown"


class Facts(_Strict):
    student: Student = Field(default_factory=Student)
    incident_date: date
    # Free text from the parent. Build Facts through ``suspension_check.ingest``
    # so this is always redacted before validation; never put raw text here.
    incident_description: str | None = Field(default=None, max_length=1000)
    removal: Removal
    notice: Notice = Field(default_factory=Notice)
    prior: PriorRemovals = Field(default_factory=PriorRemovals)
    expulsion: Expulsion | None = None
    actions: ParentActions = Field(default_factory=ParentActions)
    idea: IdeaProcess = Field(default_factory=IdeaProcess)

    @model_validator(mode="after")
    def _dates_in_order(self) -> Facts:
        if self.removal.decision_date < self.incident_date:
            raise ValueError("removal decision_date cannot be before incident_date")
        if self.removal.start_date < self.incident_date:
            raise ValueError("removal start_date cannot be before incident_date")
        return self

    @property
    def cumulative_days(self) -> int | None:
        """School days removed this year including the current removal, if known."""
        if self.prior.school_days_this_year is None:
            return None
        return self.prior.school_days_this_year + self.removal.school_days

    @property
    def is_change_of_placement(self) -> bool | None:
        """34 CFR 300.536: >10 consecutive days, or a series totalling >10 (pattern).

        A pattern is a team judgement; the tool treats >10 cumulative days as
        "possibly a pattern" and returns None (unknown) rather than asserting.
        """
        if (
            self.removal.kind in {RemovalKind.EXPULSION, RemovalKind.ALTERNATIVE}
            or self.removal.school_days > 10
        ):
            return True
        cumulative = self.cumulative_days
        if cumulative is None:
            return None
        if cumulative > 10:
            return None
        return False
