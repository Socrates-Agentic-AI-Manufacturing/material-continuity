"""Typed inputs and outputs for deterministic approval validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from core.compat import StrEnum

from core.case_state.models import SourceVersion


class ApprovalGateInputError(ValueError):
    """Raised when an approval validation request is malformed."""


class ApproverRole(StrEnum):
    ENGINEERING_REVIEWER = "ENGINEERING_REVIEWER"
    QUALITY_ENGINEER = "QUALITY_ENGINEER"
    PRODUCTION_PLANNER = "PRODUCTION_PLANNER"


class ControlledAction(StrEnum):
    CREATE_QUALIFICATION_TASK = "CREATE_QUALIFICATION_TASK"
    AUTHORIZE_RESEQUENCING = "AUTHORIZE_RESEQUENCING"


class ApprovalGateStatus(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    BLOCKED = "BLOCKED"


class ApprovalBlockReason(StrEnum):
    APPROVAL_NOT_FOUND = "APPROVAL_NOT_FOUND"
    CASE_REFERENCE_MISMATCH = "CASE_REFERENCE_MISMATCH"
    STALE_CASE_VERSION = "STALE_CASE_VERSION"
    CASE_HASH_MISMATCH = "CASE_HASH_MISMATCH"
    PRINCIPAL_ID_MISMATCH = "PRINCIPAL_ID_MISMATCH"
    PRINCIPAL_ROLE_MISMATCH = "PRINCIPAL_ROLE_MISMATCH"
    ROLE_NOT_PERMITTED = "ROLE_NOT_PERMITTED"
    ACTION_SCOPE_MISMATCH = "ACTION_SCOPE_MISMATCH"
    APPROVAL_NOT_ACTIVE = "APPROVAL_NOT_ACTIVE"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    SOURCE_STATE_CHANGED = "SOURCE_STATE_CHANGED"
    DUPLICATE_ACTION = "DUPLICATE_ACTION"


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    principal_id: str
    role: ApproverRole


@dataclass(frozen=True, slots=True)
class ApprovalValidationRequest:
    approval_id: str
    action: ControlledAction
    principal: AuthenticatedPrincipal
    evaluated_at: datetime
    current_source_versions: tuple[SourceVersion, ...]
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class ApprovalGateDecision:
    status: ApprovalGateStatus
    approval_id: str
    action: ControlledAction
    case_id: str
    case_version: int
    case_hash: str
    evaluated_at: datetime
    reasons: tuple[ApprovalBlockReason, ...]
    changed_source_ids: tuple[str, ...]

    @property
    def authorized(self) -> bool:
        return self.status is ApprovalGateStatus.AUTHORIZED
