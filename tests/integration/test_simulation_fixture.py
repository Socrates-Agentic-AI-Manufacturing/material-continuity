from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from core.exposure import calculate_exposure
from core.exposure.fixtures import load_exposure_fixtures
from core.qualification import build_qualification_graph
from core.qualification.fixtures import load_qualification_fixtures
from core.simulation import ScenarioRankingGroup, ScenarioState, simulate_recovery
from core.simulation.fixtures import load_simulation_fixtures


class CanonicalSimulationFixtureTests(unittest.TestCase):
    def test_compares_three_canonical_recovery_scenarios(self) -> None:
        fixture_root = Path(__file__).parents[2] / "data" / "fixtures"
        material, boms, orders, receipts = load_exposure_fixtures(
            fixture_root, "MAT-BRG-001"
        )
        exposure = calculate_exposure(
            material=material,
            bom_items=boms,
            production_orders=orders,
            receipts=receipts,
            as_of=datetime(2026, 9, 29, tzinfo=timezone.utc),
        )
        tasks, calendars = load_qualification_fixtures(fixture_root)
        qualification = build_qualification_graph(
            candidate_id="CAND-A", tasks=tasks, calendars=calendars
        )
        scenarios = load_simulation_fixtures(fixture_root)

        self.assertEqual(qualification.qualification_complete, scenarios[0].ready_at)
        result = simulate_recovery(
            exposure=exposure,
            shortage_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
            scenarios=scenarios,
        )

        candidate, expedite, resequence = result.scenarios
        self.assertEqual(700, result.baseline_exposed_quantity)
        self.assertEqual(ScenarioState.PARTIAL, candidate.state)
        self.assertEqual(300, candidate.remaining_exposed_quantity)
        self.assertEqual(3, candidate.remaining_exposed_order_count)
        self.assertEqual(ScenarioState.FEASIBLE, expedite.state)
        self.assertEqual(0, expedite.remaining_exposed_quantity)
        self.assertEqual(ScenarioState.PARTIAL, resequence.state)
        self.assertEqual(500, resequence.remaining_exposed_quantity)
        self.assertEqual(1, expedite.rank)
        self.assertEqual(2, candidate.rank)
        self.assertEqual(3, resequence.rank)
        self.assertEqual(ScenarioRankingGroup.FEASIBLE, expedite.ranking_group)
        self.assertEqual(ScenarioRankingGroup.CONDITIONAL, candidate.ranking_group)
        self.assertTrue(
            all(not scenario.authorized_for_execution for scenario in result.scenarios)
        )


if __name__ == "__main__":
    unittest.main()
