"""Deterministic comparison of recovery timing, coverage, and cost."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from core.exposure.models import AffectedOrder, ExposureResult

from .models import (
    OrderImpact,
    RecoverySimulationResult,
    ScenarioInput,
    ScenarioRankingGroup,
    ScenarioResult,
    ScenarioState,
    SimulationInputError,
)


def simulate_recovery(
    *,
    exposure: ExposureResult,
    shortage_at: datetime | None,
    scenarios: Iterable[ScenarioInput],
) -> RecoverySimulationResult:
    """Compare and rank recovery scenarios without authorizing them."""

    scenario_list = tuple(scenarios)
    _validate_inputs(exposure, shortage_at, scenario_list)
    affected_orders = tuple(
        sorted(
            exposure.affected_orders,
            key=lambda order: (order.scheduled_date, order.due_date, order.order_id),
        )
    )
    baseline_quantity = sum(order.unserved_quantity for order in affected_orders)

    simulated = tuple(
        _simulate_scenario(
            scenario=scenario,
            affected_orders=affected_orders,
            baseline_quantity=baseline_quantity,
            shortage_at=shortage_at,
        )
        for scenario in scenario_list
    )
    results = _rank_scenarios(simulated)
    return RecoverySimulationResult(
        material_id=exposure.material_id,
        shortage_at=shortage_at,
        baseline_exposed_quantity=baseline_quantity,
        baseline_exposed_order_count=len(affected_orders),
        scenarios=results,
    )


def _simulate_scenario(
    *,
    scenario: ScenarioInput,
    affected_orders: tuple[AffectedOrder, ...],
    baseline_quantity: int,
    shortage_at: datetime | None,
) -> ScenarioResult:
    if not affected_orders:
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_type=scenario.scenario_type,
            name=scenario.name,
            state=ScenarioState.NO_RECOVERY_REQUIRED,
            rank=0,
            ranking_group=ScenarioRankingGroup.NOT_ACTIONABLE,
            rank_reason="Ranking pending.",
            ready_at=scenario.ready_at,
            qualification_complete=scenario.qualification_complete,
            ready_by_shortage=True,
            delay_after_shortage_hours=Decimal("0"),
            available_quantity=scenario.available_quantity,
            protected_quantity=0,
            remaining_exposed_quantity=0,
            remaining_exposed_order_count=0,
            incremental_cost_cents=scenario.incremental_cost_cents,
            unresolved_conditions=scenario.unresolved_conditions,
            order_impacts=(),
            authorized_for_execution=False,
            source_references=scenario.source_references,
        )

    unresolved_conditions = scenario.unresolved_conditions
    if scenario.ready_at is None and not unresolved_conditions:
        unresolved_conditions = ("Recovery ready time is unknown.",)
    unresolved = scenario.ready_at is None or bool(unresolved_conditions)
    available = 0 if unresolved else scenario.available_quantity
    impacts: list[OrderImpact] = []
    protected_total = 0
    ready_date = scenario.ready_at.date() if scenario.ready_at is not None else None

    for order in affected_orders:
        protected = 0
        if ready_date is not None and order.scheduled_date >= ready_date and available:
            protected = min(available, order.unserved_quantity)
            available -= protected
        remaining = order.unserved_quantity - protected
        protected_total += protected
        impacts.append(
            OrderImpact(
                order_id=order.order_id,
                scheduled_date=order.scheduled_date.isoformat(),
                baseline_unserved_quantity=order.unserved_quantity,
                protected_quantity=protected,
                remaining_unserved_quantity=remaining,
            )
        )

    remaining_quantity = baseline_quantity - protected_total
    remaining_orders = sum(
        impact.remaining_unserved_quantity > 0 for impact in impacts
    )
    if unresolved:
        state = ScenarioState.UNRESOLVED
    elif remaining_quantity == 0 and scenario.ready_at <= shortage_at:
        state = ScenarioState.FEASIBLE
    elif protected_total > 0:
        state = ScenarioState.PARTIAL
    else:
        state = ScenarioState.INFEASIBLE

    ready_by_shortage = (
        scenario.ready_at <= shortage_at if scenario.ready_at is not None else None
    )
    delay_hours = (
        max(
            Decimal("0"),
            Decimal(str((scenario.ready_at - shortage_at).total_seconds()))
            / Decimal("3600"),
        )
        if scenario.ready_at is not None
        else None
    )
    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        scenario_type=scenario.scenario_type,
        name=scenario.name,
        state=state,
        rank=0,
        ranking_group=ScenarioRankingGroup.NOT_ACTIONABLE,
        rank_reason="Ranking pending.",
        ready_at=scenario.ready_at,
        qualification_complete=scenario.qualification_complete,
        ready_by_shortage=ready_by_shortage,
        delay_after_shortage_hours=delay_hours,
        available_quantity=scenario.available_quantity,
        protected_quantity=protected_total,
        remaining_exposed_quantity=remaining_quantity,
        remaining_exposed_order_count=remaining_orders,
        incremental_cost_cents=scenario.incremental_cost_cents,
        unresolved_conditions=unresolved_conditions,
        order_impacts=tuple(impacts),
        authorized_for_execution=False,
        source_references=scenario.source_references,
    )


def _rank_scenarios(results: tuple[ScenarioResult, ...]) -> tuple[ScenarioResult, ...]:
    """Attach a stable rank using proposal criteria while retaining input order."""

    state_priority = {
        ScenarioState.NO_RECOVERY_REQUIRED: 0,
        ScenarioState.FEASIBLE: 0,
        ScenarioState.PARTIAL: 1,
        ScenarioState.INFEASIBLE: 2,
        ScenarioState.UNRESOLVED: 3,
    }
    ordered = sorted(
        results,
        key=lambda item: (
            state_priority[item.state],
            item.remaining_exposed_order_count,
            item.ready_at is None,
            item.ready_at.isoformat() if item.ready_at else "",
            item.incremental_cost_cents,
            item.scenario_id,
        ),
    )
    ranks = {item.scenario_id: index for index, item in enumerate(ordered, 1)}
    ranked = []
    for item in results:
        group = (
            ScenarioRankingGroup.FEASIBLE
            if item.state in (ScenarioState.FEASIBLE, ScenarioState.NO_RECOVERY_REQUIRED)
            else ScenarioRankingGroup.CONDITIONAL
            if item.state is ScenarioState.PARTIAL
            else ScenarioRankingGroup.NOT_ACTIONABLE
        )
        readiness = (
            "timing unresolved"
            if item.ready_at is None
            else "ready by shortage"
            if item.ready_by_shortage
            else f"ready {item.delay_after_shortage_hours} hours after shortage"
        )
        reason = (
            f"{item.remaining_exposed_order_count} exposed orders remain; "
            f"{readiness}; incremental cost {item.incremental_cost_cents / 100:.2f}."
        )
        ranked.append(replace(
            item,
            rank=ranks[item.scenario_id],
            ranking_group=group,
            rank_reason=reason,
        ))
    return tuple(ranked)


def _validate_inputs(
    exposure: ExposureResult,
    shortage_at: datetime | None,
    scenarios: tuple[ScenarioInput, ...],
) -> None:
    if not scenarios:
        raise SimulationInputError("at least one recovery scenario is required")
    duplicates = [
        scenario_id
        for scenario_id, count in Counter(
            scenario.scenario_id for scenario in scenarios
        ).items()
        if count > 1
    ]
    if duplicates:
        raise SimulationInputError(f"duplicate scenario ID: {sorted(duplicates)[0]}")

    if exposure.shortage_date is None and exposure.affected_orders:
        raise SimulationInputError(
            "exposure cannot contain affected orders without a shortage date"
        )
    if exposure.shortage_date is not None and not exposure.affected_orders:
        raise SimulationInputError(
            "exposure cannot contain a shortage date without affected orders"
        )

    if exposure.shortage_date is None:
        if shortage_at is not None:
            raise SimulationInputError(
                "shortage_at must be omitted when exposure has no shortage"
            )
    else:
        if shortage_at is None:
            raise SimulationInputError(
                "shortage_at is required when exposure has a shortage"
            )
        if shortage_at.tzinfo is None or shortage_at.utcoffset() is None:
            raise SimulationInputError("shortage_at must be timezone-aware")
        if shortage_at.date() != exposure.shortage_date:
            raise SimulationInputError(
                "shortage_at date must match the exposure shortage date"
            )

    for scenario in scenarios:
        if not scenario.scenario_id:
            raise SimulationInputError("scenario_id is required")
        if scenario.available_quantity < 0:
            raise SimulationInputError("scenario available quantity cannot be negative")
        if scenario.incremental_cost_cents < 0:
            raise SimulationInputError("scenario incremental cost cannot be negative")
        for value, field_name in (
            (scenario.ready_at, "ready_at"),
            (scenario.qualification_complete, "qualification_complete"),
        ):
            if value is not None and (
                value.tzinfo is None or value.utcoffset() is None
            ):
                raise SimulationInputError(
                    f"scenario {scenario.scenario_id} {field_name} must be timezone-aware"
                )
        if (
            scenario.ready_at is not None
            and scenario.qualification_complete is not None
            and scenario.ready_at < scenario.qualification_complete
        ):
            raise SimulationInputError(
                f"scenario {scenario.scenario_id} cannot be ready before qualification completes"
            )
