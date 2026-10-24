"""Typed requirements, evidence, provenance, and comparison results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from core.compat import StrEnum
from typing import Any

ScalarValue = Decimal | str | bool


class RequirementInputError(ValueError):
    """Raised when requirement-comparison inputs are structurally invalid."""


class ComparisonStatus(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


class ComparisonOperator(StrEnum):
    EQUAL = "="
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    LESS_THAN = "<"


class RequirementCriticality(StrEnum):
    HARD = "HARD"
    CRITICAL = "CRITICAL"
    STANDARD = "STANDARD"


class RequirementKind(StrEnum):
    TECHNICAL = "TECHNICAL"
    RELEASE_GATE = "RELEASE_GATE"


class CandidateDecision(StrEnum):
    REJECTED_HARD_MISMATCH = "REJECTED_HARD_MISMATCH"
    BLOCKED_PENDING_EVIDENCE_OR_RELEASE = "BLOCKED_PENDING_EVIDENCE_OR_RELEASE"
    REQUIREMENTS_MATCH = "REQUIREMENTS_MATCH"


@dataclass(frozen=True, slots=True)
class Requirement:
    requirement_id: str
    product_id: str
    application_id: str
    property: str
    name: str
    operator: ComparisonOperator
    required_value: ScalarValue
    unit: str | None
    criticality: RequirementCriticality
    kind: RequirementKind
    source_document: str
    source_revision: str


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    evidence_id: str
    candidate_id: str
    property: str
    value: ScalarValue
    unit: str | None
    source_document: str
    source_revision: str
    current_source_revision: str
    source_page: str
    source_location: str
    applicability: str
    applicable: bool


@dataclass(frozen=True, slots=True)
class EvidenceProvenance:
    evidence_id: str
    source_document: str
    source_revision: str
    current_source_revision: str
    source_page: str
    source_location: str
    applicability: str


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    candidate_id: str
    requirement_id: str
    requirement_name: str
    status: ComparisonStatus
    required_operator: ComparisonOperator
    required_value: ScalarValue
    required_unit: str | None
    observed_value: ScalarValue | None
    observed_unit: str | None
    normalized_required_value: ScalarValue | None
    normalized_observed_value: ScalarValue | None
    normalized_unit: str | None
    reason: str
    hard_reject: bool
    evidence: tuple[EvidenceProvenance, ...]


@dataclass(frozen=True, slots=True)
class CandidateComparisonResult:
    candidate_id: str
    decision: CandidateDecision
    rows: tuple[ComparisonResult, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation without custom encoders."""

        def serialize(value: Any) -> Any:
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, tuple):
                return [serialize(item) for item in value]
            if isinstance(value, list):
                return [serialize(item) for item in value]
            if isinstance(value, dict):
                return {key: serialize(item) for key, item in value.items()}
            return value

        return serialize(asdict(self))
