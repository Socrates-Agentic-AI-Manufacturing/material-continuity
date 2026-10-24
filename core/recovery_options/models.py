"""Typed inputs and outputs for deterministic recovery-option discovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from core.compat import StrEnum
from typing import Any


class RecoveryOptionInputError(ValueError):
    """Raised when recovery-option inputs are ambiguous or invalid."""


class RecoveryCategory(StrEnum):
    NETWORK_STOCK = "NETWORK_STOCK"
    APPROVED_SOURCE = "APPROVED_SOURCE"
    APPROVED_EQUIVALENT = "APPROVED_EQUIVALENT"
    ALTERNATE_BOM = "ALTERNATE_BOM"
    VALID_DEVIATION = "VALID_DEVIATION"
    UNQUALIFIED_CANDIDATE = "UNQUALIFIED_CANDIDATE"
    ORIGINAL_EXPEDITE = "ORIGINAL_EXPEDITE"
    PRODUCTION_RESEQUENCING = "PRODUCTION_RESEQUENCING"


class ApprovalStatus(StrEnum):
    APPROVED = "APPROVED"
    UNQUALIFIED = "UNQUALIFIED"
    NOT_APPROVED = "NOT_APPROVED"
    AVAILABLE = "AVAILABLE"


@dataclass(frozen=True, slots=True)
class RecoverySearchRequest:
    material_id: str
    required_quantity: int
    need_by: date
    as_of: date


@dataclass(frozen=True, slots=True)
class RecoveryOptionRecord:
    option_id: str
    category: RecoveryCategory
    material_id: str
    description: str
    available_quantity: int
    ready_date: date | None
    approval_status: ApprovalStatus
    source_reference: str
    candidate_id: str | None = None
    provider_id: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    unit_cost_cents: int | None = None
    incremental_cost_cents: int | None = None

    def is_valid_on(self, target_date: date) -> bool:
        return (self.valid_from is None or self.valid_from <= target_date) and (
            self.valid_until is None or target_date <= self.valid_until
        )


@dataclass(frozen=True, slots=True)
class OptionFinding:
    option_id: str
    category: RecoveryCategory
    description: str
    available_quantity: int
    coverage_quantity: int
    ready_date: date | None
    arrives_by_need: bool | None
    approval_status: ApprovalStatus
    source_reference: str
    candidate_id: str | None
    provider_id: str | None
    unit_cost_cents: int | None
    incremental_cost_cents: int | None


@dataclass(frozen=True, slots=True)
class SearchStep:
    category: RecoveryCategory
    evaluated_option_ids: tuple[str, ...]
    qualifying_option_ids: tuple[str, ...]
    outcome: str


@dataclass(frozen=True, slots=True)
class RecoverySearchResult:
    material_id: str
    required_quantity: int
    need_by: date
    approved_covered_quantity: int
    remaining_quantity: int
    approved_recovery_sufficient: bool
    approved_options: tuple[OptionFinding, ...]
    unqualified_candidates: tuple[OptionFinding, ...]
    fallbacks: tuple[OptionFinding, ...]
    search_trace: tuple[SearchStep, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation without custom encoders."""

        def serialize(value: Any) -> Any:
            if isinstance(value, date):
                return value.isoformat()
            if isinstance(value, tuple):
                return [serialize(item) for item in value]
            if isinstance(value, list):
                return [serialize(item) for item in value]
            if isinstance(value, dict):
                return {key: serialize(item) for key, item in value.items()}
            return value

        return serialize(asdict(self))
