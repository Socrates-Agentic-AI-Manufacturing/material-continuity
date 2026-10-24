"""Typed structured-extraction contract for the evidence pipeline boundary."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from core.compat import StrEnum

from core.requirements import CandidateComparisonResult, CandidateEvidence
from core.requirements.models import ScalarValue


class EvidencePipelineInputError(ValueError):
    """Raised when structured extraction output is malformed or ambiguous."""


class ExtractionSupportStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class EvidenceExclusionReason(StrEnum):
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    MISSING_VALUE = "MISSING_VALUE"
    MISSING_PROVENANCE = "MISSING_PROVENANCE"


@dataclass(frozen=True, slots=True)
class EvidenceExtraction:
    extraction_id: str
    candidate_id: str
    property: str
    value: ScalarValue | None
    unit: str | None
    source_document: str
    source_revision: str
    current_source_revision: str
    source_page: str
    source_location: str
    applicability: str
    applicable: bool
    support_status: ExtractionSupportStatus
    extraction_confidence: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ExcludedExtraction:
    extraction: EvidenceExtraction
    reason: EvidenceExclusionReason


@dataclass(frozen=True, slots=True)
class PreparedEvidence:
    evidence: tuple[CandidateEvidence, ...]
    exclusions: tuple[ExcludedExtraction, ...]


@dataclass(frozen=True, slots=True)
class EvidencePipelineResult:
    prepared: PreparedEvidence
    comparison: CandidateComparisonResult
