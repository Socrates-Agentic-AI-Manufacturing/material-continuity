"""Typed inputs and outputs for deterministic recovery simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from core.compat import StrEnum
from typing import Any


class SimulationInputError(ValueError):
    """Raised when recovery-simulation inputs are invalid or inconsistent."""


class ScenarioType(StrEnum):
    SUBSTITUTE_QUALIFICATION = "SUBSTITUTE_QUALIFICATION"
    ORIGINAL_EXPEDITE = "ORIGINAL_EXPEDITE"
    PRODUCTION_RESEQUENCING = "PRODUCTION_RESEQUENCING"


class ScenarioState(StrEnum):
    FEASIBLE = "FEASIBLE"
    PARTIAL = "PARTIAL"
    INFEASIBLE = "INFEASIBLE"
    UNRESOLVED = "UNRESOLVED"
    NO_RECOVERY_REQUIRED = "NO_RECOVERY_REQUIRED"


class ScenarioRankingGroup(StrEnum):
    FEASIBLE = "FEASIBLE"
    CONDITIONAL = "CONDITIONAL"
    NOT_ACTIONABLE = "NOT_ACTIONABLE"


@dataclass(frozen=True, slots=True)
class ScenarioInput:
    scenario_id: str
    scenario_type: ScenarioType
    name: str
    ready_at: datetime | None
    available_quantity: int
    incremental_cost_cents: int
    qualification_complete: datetime | None
    unresolved_conditions: tuple[str, ...]
    source_references: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OrderImpact:
    order_id: str
    scheduled_date: str
    baseline_unserved_quantity: int
    protected_quantity: int
    remaining_unserved_quantity: int


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    scenario_id: str
    scenario_type: ScenarioType
    name: str
    state: ScenarioState
    rank: int
    ranking_group: ScenarioRankingGroup
    rank_reason: str
    ready_at: datetime | None
    qualification_complete: datetime | None
    ready_by_shortage: bool | None
    delay_after_shortage_hours: Decimal | None
    available_quantity: int
    protected_quantity: int
    remaining_exposed_quantity: int
    remaining_exposed_order_count: int
    incremental_cost_cents: int
    unresolved_conditions: tuple[str, ...]
    order_impacts: tuple[OrderImpact, ...]
    authorized_for_execution: bool
    source_references: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecoverySimulationResult:
    material_id: str
    shortage_at: datetime | None
    baseline_exposed_quantity: int
    baseline_exposed_order_count: int
    scenarios: tuple[ScenarioResult, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation without custom encoders."""

        def serialize(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
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
