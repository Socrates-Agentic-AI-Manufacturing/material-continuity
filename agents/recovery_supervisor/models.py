"""Typed orchestration request, trace, assessment, and summary models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from core.compat import StrEnum

from agents.evidence_specialist import EvidenceSpecialistResult
from core.case_state import RecoveryCase, TriggerType
from core.exposure import ExposureResult
from core.qualification import QualificationGraphResult
from core.recovery_options import RecoverySearchResult
from core.simulation import RecoverySimulationResult, ScenarioState


class RecoverySupervisorInputError(ValueError):
    """Raised when a supervisor request is invalid or internally inconsistent."""


class RecoveryWorkflowStatus(StrEnum):
    NO_EXPOSURE = "NO_EXPOSURE"
    APPROVED_RECOVERY_AVAILABLE = "APPROVED_RECOVERY_AVAILABLE"
    CANDIDATE_QUALIFICATION_REQUIRED = "CANDIDATE_QUALIFICATION_REQUIRED"


class SupervisorTool(StrEnum):
    GET_EXPOSURE = "getExposure"
    FIND_RECOVERY_OPTIONS = "findRecoveryOptions"
    EVIDENCE_SPECIALIST = "EvidenceSpecialist"
    QUALIFICATION_GRAPH = "getQualificationDependencies"
    SIMULATE_RECOVERY = "simulateRecovery"
    CREATE_CASE = "createCase"


@dataclass(frozen=True, slots=True)
class RecoverySupervisorRequest:
    case_id: str
    event_id: str
    trigger_type: TriggerType
    material_id: str
    source_reference: str
    as_of: datetime
    shortage_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SupervisorToolTrace:
    sequence: int
    tool: SupervisorTool
    target: str
    outcome: str


@dataclass(frozen=True, slots=True)
class CandidateAssessment:
    candidate_id: str
    evidence: EvidenceSpecialistResult
    qualification: QualificationGraphResult | None


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    scenario_id: str
    state: ScenarioState
    remaining_exposed_quantity: int
    ready_by_shortage: bool | None


@dataclass(frozen=True, slots=True)
class RecoverySummary:
    status: RecoveryWorkflowStatus
    material_id: str
    shortage_date: date | None
    exposed_quantity: int
    exposed_order_count: int
    approved_recovery_sufficient: bool
    rejected_candidate_ids: tuple[str, ...]
    conditional_candidate_ids: tuple[str, ...]
    scenarios: tuple[ScenarioSummary, ...]
    human_review_required: bool
    production_release_authorized: bool


@dataclass(frozen=True, slots=True)
class RecoverySupervisorResult:
    summary: RecoverySummary
    case: RecoveryCase | None
    exposure: ExposureResult
    recovery_options: RecoverySearchResult | None
    candidates: tuple[CandidateAssessment, ...]
    simulation: RecoverySimulationResult | None
    tool_trace: tuple[SupervisorToolTrace, ...]
