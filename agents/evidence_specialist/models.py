"""Typed request, retrieval, gap, and result models for the Evidence Specialist."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from core.compat import StrEnum

from core.evidence import EvidenceExtraction, EvidencePipelineResult
from core.requirements import CandidateComparisonResult, ComparisonStatus, Requirement


class EvidenceSpecialistInputError(ValueError):
    """Raised when an Evidence Specialist request or retrieval result is invalid."""


class RetrievalTool(StrEnum):
    CANDIDATE_EVIDENCE = "retrieve_candidate_evidence"
    QUALIFICATION_PROCEDURE = "retrieve_qualification_procedures"


@dataclass(frozen=True, slots=True)
class EvidenceInvestigationRequest:
    candidate_id: str
    requirements: tuple[Requirement, ...]


@dataclass(frozen=True, slots=True)
class QualificationProcedureReference:
    procedure_id: str
    requirement_id: str
    name: str
    source_document: str
    source_revision: str
    source_pages: str
    source_location: str
    duration_hours: Decimal | None
    required_resource: str | None
    applicability: str


@dataclass(frozen=True, slots=True)
class EvidenceGap:
    requirement_id: str
    requirement_name: str
    status: ComparisonStatus
    reason: str
    qualification_procedure_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalTrace:
    tool: RetrievalTool
    query: str
    returned_count: int


@dataclass(frozen=True, slots=True)
class EvidenceSpecialistResult:
    candidate_id: str
    pipeline: EvidencePipelineResult
    comparison: CandidateComparisonResult
    retrieved_extractions: tuple[EvidenceExtraction, ...]
    gaps: tuple[EvidenceGap, ...]
    hard_mismatch_requirement_ids: tuple[str, ...]
    qualification_procedures: tuple[QualificationProcedureReference, ...]
    retrieval_trace: tuple[RetrievalTrace, ...]
