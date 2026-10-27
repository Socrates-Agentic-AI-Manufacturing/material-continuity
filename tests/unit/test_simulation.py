from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date, datetime, timezone

from core.exposure import AffectedOrder, ExposureResult
from core.simulation import (
    ScenarioInput,
    ScenarioRankingGroup,
    ScenarioState,
    ScenarioType,
    SimulationInputError,
    simulate_recovery,
)


SHORTAGE_AT = datetime(2026, 10, 4, tzinfo=timezone.utc)


class RecoverySimulationTests(unittest.TestCase):
    def test_timely_full_coverage_is_feasible(self) -> None:
        result = self.simulate(self.scenario(quantity=200, ready_at=SHORTAGE_AT))
        scenario = result.scenarios[0]

        self.assertEqual(ScenarioState.FEASIBLE, scenario.state)
        self.assertEqual(200, scenario.protected_quantity)
        self.assertEqual(0, scenario.remaining_exposed_quantity)
        self.assertFalse(scenario.authorized_for_execution)

    def test_late_recovery_leaves_earlier_order_exposed(self) -> None:
        late = datetime(2026, 10, 5, tzinfo=timezone.utc)
        result = self.simulate(self.scenario(quantity=200, ready_at=late))
        scenario = result.scenarios[0]

        self.assertEqual(ScenarioState.PARTIAL, scenario.state)
        self.assertEqual(100, scenario.protected_quantity)
        self.assertEqual(100, scenario.remaining_exposed_quantity)
        self.assertEqual(24, scenario.delay_after_shortage_hours)

    def test_same_day_readiness_is_available_before_demand(self) -> None:
        result = self.simulate(self.scenario(quantity=100, ready_at=SHORTAGE_AT))
        scenario = result.scenarios[0]

        self.assertEqual(100, scenario.order_impacts[0].protected_quantity)
        self.assertEqual(0, scenario.order_impacts[0].remaining_unserved_quantity)

    def test_insufficient_quantity_is_partial(self) -> None:
        result = self.simulate(self.scenario(quantity=50, ready_at=SHORTAGE_AT))
        scenario = result.scenarios[0]

        self.assertEqual(ScenarioState.PARTIAL, scenario.state)
        self.assertEqual(150, scenario.remaining_exposed_quantity)

    def test_unknown_completion_remains_unresolved(self) -> None:
        scenario = self.scenario(quantity=200, ready_at=None)
        result = self.simulate(scenario)

        self.assertEqual(ScenarioState.UNRESOLVED, result.scenarios[0].state)
        self.assertEqual(200, result.scenarios[0].remaining_exposed_quantity)
        self.assertEqual(
            ("Recovery ready time is unknown.",),
            result.scenarios[0].unresolved_conditions,
        )

    def test_ready_before_qualification_completion_fails_closed(self) -> None:
        scenario = replace(
            self.scenario(quantity=200, ready_at=SHORTAGE_AT),
            qualification_complete=datetime(2026, 10, 5, tzinfo=timezone.utc),
        )

        with self.assertRaisesRegex(SimulationInputError, "cannot be ready before"):
            self.simulate(scenario)

    def test_duplicate_scenario_ids_fail_closed(self) -> None:
        scenario = self.scenario(quantity=200, ready_at=SHORTAGE_AT)

        with self.assertRaisesRegex(SimulationInputError, "duplicate scenario ID"):
            simulate_recovery(
                exposure=self.exposure(),
                shortage_at=SHORTAGE_AT,
                scenarios=(scenario, scenario),
            )

    def test_ranking_prefers_fewer_exposed_orders_then_time_and_cost(self) -> None:
        partial = replace(
            self.scenario(quantity=100, ready_at=SHORTAGE_AT),
            scenario_id="SCN-PARTIAL",
            incremental_cost_cents=100,
        )
        costly = replace(
            self.scenario(quantity=200, ready_at=SHORTAGE_AT),
            scenario_id="SCN-COSTLY",
            incremental_cost_cents=5000,
        )
        cheaper = replace(
            self.scenario(quantity=200, ready_at=SHORTAGE_AT),
            scenario_id="SCN-CHEAPER",
            incremental_cost_cents=2000,
        )

        result = simulate_recovery(
            exposure=self.exposure(),
            shortage_at=SHORTAGE_AT,
            scenarios=(partial, costly, cheaper),
        )
        by_id = {item.scenario_id: item for item in result.scenarios}

        self.assertEqual(1, by_id["SCN-CHEAPER"].rank)
        self.assertEqual(2, by_id["SCN-COSTLY"].rank)
        self.assertEqual(3, by_id["SCN-PARTIAL"].rank)
        self.assertEqual(ScenarioRankingGroup.FEASIBLE, by_id["SCN-CHEAPER"].ranking_group)
        self.assertEqual(ScenarioRankingGroup.CONDITIONAL, by_id["SCN-PARTIAL"].ranking_group)
        self.assertIn("exposed orders remain", by_id["SCN-CHEAPER"].rank_reason)

    def simulate(self, scenario: ScenarioInput):
        return simulate_recovery(
            exposure=self.exposure(),
            shortage_at=SHORTAGE_AT,
            scenarios=(scenario,),
        )

    @staticmethod
    def exposure() -> ExposureResult:
        affected = tuple(
            AffectedOrder(
                order_id=f"MO-{day}",
                product_id="ASSEMBLY-A",
                scheduled_date=date(2026, 10, day),
                due_date=date(2026, 10, day),
                required_material_quantity=100,
                unserved_quantity=100,
            )
            for day in (4, 5)
        )
        return ExposureResult(
            material_id="MAT-1",
            as_of="2026-09-29T00:00:00+00:00",
            current_usable_stock=0,
            shortage_date=date(2026, 10, 4),
            affected_orders=affected,
            projection=(),
        )

    @staticmethod
    def scenario(quantity: int, ready_at: datetime | None) -> ScenarioInput:
        return ScenarioInput(
            scenario_id="SCN-1",
            scenario_type=ScenarioType.ORIGINAL_EXPEDITE,
            name="Test scenario",
            ready_at=ready_at,
            available_quantity=quantity,
            incremental_cost_cents=1000,
            qualification_complete=None,
            unresolved_conditions=(),
            source_references=("fixture:SCN-1",),
        )


if __name__ == "__main__":
    unittest.main()
