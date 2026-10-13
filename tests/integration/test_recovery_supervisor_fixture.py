from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from agents.recovery_supervisor import (
    FixtureRecoverySupervisorTools,
    RecoverySupervisorRequest,
    RecoveryWorkflowStatus,
    SupervisorTool,
    run_recovery_workflow,
)
from core.case_state import TriggerType


class CanonicalRecoverySupervisorTests(unittest.TestCase):
    def test_local_workflow_builds_versioned_review_case_and_summary(self) -> None:
        fixture_root = Path(__file__).parents[2] / "data" / "fixtures"
        result = run_recovery_workflow(
            RecoverySupervisorRequest(
                case_id="CASE-001",
                event_id="EVT-DELAY-001",
                trigger_type=TriggerType.DELIVERY_DELAY,
                material_id="MAT-BRG-001",
                source_reference="purchase-order:PO-ORIGINAL-001",
                as_of=datetime(2026, 9, 29, tzinfo=timezone.utc),
                shortage_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
                created_at=datetime(2026, 9, 29, 3, tzinfo=timezone.utc),
            ),
            tools=FixtureRecoverySupervisorTools(fixture_root),
        )

        self.assertEqual(
            RecoveryWorkflowStatus.CANDIDATE_QUALIFICATION_REQUIRED,
            result.summary.status,
        )
        self.assertEqual(700, result.summary.exposed_quantity)
        self.assertEqual(7, result.summary.exposed_order_count)
        self.assertEqual(3, len(result.summary.scenarios))
        self.assertEqual(3, len(result.case.current.candidate_comparisons))
        self.assertFalse(result.summary.production_release_authorized)
        self.assertEqual(
            SupervisorTool.CREATE_CASE,
            result.tool_trace[-1].tool,
        )


if __name__ == "__main__":
    unittest.main()
