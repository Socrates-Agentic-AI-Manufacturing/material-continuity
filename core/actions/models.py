"""Typed command and result models for controlled mock enterprise actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from core.compat import StrEnum

from core.approval import ApprovalGateDecision, ApprovalValidationRequest
from core.case_state import ActionReceipt, RecoveryCase


class ActionAdapterInputError(ValueError):
    """Raised when an action command is structurally invalid."""


class ActionExecutionStatus(StrEnum):
    CREATED = "CREATED"
    BLOCKED = "BLOCKED"


class ActionBlockReason(StrEnum):
    APPROVAL_BLOCKED = "APPROVAL_BLOCKED"
    CANDIDATE_NOT_FOUND = "CANDIDATE_NOT_FOUND"
    CANDIDATE_HARD_REJECTED = "CANDIDATE_HARD_REJECTED"
    QUALIFICATION_PLAN_NOT_FOUND = "QUALIFICATION_PLAN_NOT_FOUND"
    REQUIREMENT_NOT_IN_PLAN = "REQUIREMENT_NOT_IN_PLAN"


@dataclass(frozen=True, slots=True)
class CreateQualificationTaskCommand:
    candidate_id: str
    requirement_id: str
    task_name: str
    approval: ApprovalValidationRequest


@dataclass(frozen=True, slots=True)
class QualificationTaskRecord:
    qms_task_id: str
    candidate_id: str
    requirement_id: str
    task_name: str
    status: ActionExecutionStatus
    created_at: datetime
    production_release_authorized: bool


@dataclass(frozen=True, slots=True)
class QualificationTaskCreationResult:
    status: ActionExecutionStatus
    case: RecoveryCase
    approval_decision: ApprovalGateDecision
    qms_task_id: str | None
    task: QualificationTaskRecord | None
    action_receipt: ActionReceipt | None
    block_reasons: tuple[ActionBlockReason, ...]
    production_release_authorized: bool

    @property
    def created(self) -> bool:
        return self.status is ActionExecutionStatus.CREATED
