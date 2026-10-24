"""Typed recovery-case history, versions, approvals, and action receipts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from core.compat import StrEnum
from typing import Any

from core.exposure.models import ExposureResult
from core.qualification.models import QualificationGraphResult
from core.recovery_options.models import RecoverySearchResult
from core.requirements.models import CandidateComparisonResult
from core.simulation.models import RecoverySimulationResult


class RecoveryCaseInputError(ValueError):
    """Raised when a recovery-case mutation is invalid or ambiguous."""


class CaseStatus(StrEnum):
    UNDER_REVIEW = "UNDER_REVIEW"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    ACTIONED = "ACTIONED"
    CLOSED = "CLOSED"


class TriggerType(StrEnum):
    DELIVERY_DELAY = "DELIVERY_DELAY"
    QUALITY_HOLD = "QUALITY_HOLD"
    STOCK_EXCEPTION = "STOCK_EXCEPTION"
    COMPONENT_QUARANTINE = "COMPONENT_QUARANTINE"


class SourceType(StrEnum):
    STOCK = "STOCK"
    PRODUCTION_PLAN = "PRODUCTION_PLAN"
    SUPPLIER = "SUPPLIER"
    DOCUMENT = "DOCUMENT"
    QMS = "QMS"
    RESOURCE_CALENDAR = "RESOURCE_CALENDAR"


@dataclass(frozen=True, slots=True)
class CaseTrigger:
    event_id: str
    trigger_type: TriggerType
    material_id: str
    detected_at: datetime
    source_reference: str


@dataclass(frozen=True, slots=True)
class SourceVersion:
    source_id: str
    source_type: SourceType
    version: str
    observed_at: datetime
    content_hash: str | None = None


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    approval_id: str
    case_id: str
    case_version: int
    case_hash: str
    approver_id: str
    approver_role: str
    permitted_action: str
    approved_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ActionReceipt:
    action_id: str
    case_id: str
    case_version: int
    case_hash: str
    action_type: str
    external_reference: str
    idempotency_key: str
    status: str
    executed_at: datetime


@dataclass(frozen=True, slots=True)
class RecoveryCaseVersion:
    case_id: str
    case_version: int
    case_hash: str
    previous_case_hash: str | None
    status: CaseStatus
    trigger: CaseTrigger
    exposure: ExposureResult
    recovery_options: RecoverySearchResult
    candidate_comparisons: tuple[CandidateComparisonResult, ...]
    qualification_graphs: tuple[QualificationGraphResult, ...]
    simulation: RecoverySimulationResult
    source_versions: tuple[SourceVersion, ...]
    change_reason: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RecoveryCase:
    case_id: str
    versions: tuple[RecoveryCaseVersion, ...]
    approvals: tuple[ApprovalRecord, ...]
    actions: tuple[ActionReceipt, ...]
    created_at: datetime
    updated_at: datetime

    @property
    def current(self) -> RecoveryCaseVersion:
        return self.versions[-1]

    def to_dict(self) -> dict[str, Any]:
        from .serialization import canonicalize

        return canonicalize(self)


@dataclass(frozen=True, slots=True)
class RecoveryCaseUpdate:
    status: CaseStatus | None = None
    exposure: ExposureResult | None = None
    recovery_options: RecoverySearchResult | None = None
    candidate_comparisons: tuple[CandidateComparisonResult, ...] | None = None
    qualification_graphs: tuple[QualificationGraphResult, ...] | None = None
    simulation: RecoverySimulationResult | None = None
    source_versions: tuple[SourceVersion, ...] | None = None


@dataclass(frozen=True, slots=True)
class CaseUpdateResult:
    case: RecoveryCase
    version_changed: bool
    changed_source_ids: tuple[str, ...]
