from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from agents.recovery_supervisor import (
    FixtureRecoverySupervisorTools,
    RecoverySupervisorInputError,
    RecoverySupervisorRequest,
    RecoveryWorkflowStatus,
    SYSTEM_PROMPT,
    SupervisorTool,
    run_recovery_workflow,
)
from core.case_state import TriggerType


FIXTURE_ROOT = Path(__file__).parents[2] / "data" / "fixtures"


class RecoverySupervisorTests(unittest.TestCase):
    def test_canonical_workflow_branches_to_evidence_and_creates_case(self) -> None:
        result = run_recovery_workflow(
            self.request(),
            tools=FixtureRecoverySupervisorTools(FIXTURE_ROOT),
        )

        self.assertEqual(
            RecoveryWorkflowStatus.CANDIDATE_QUALIFICATION_REQUIRED,
            result.summary.status,
        )
        self.assertEqual(("CAND-B",), result.summary.rejected_candidate_ids)
        self.assertEqual(
            ("CAND-A", "CAND-C"), result.summary.conditional_candidate_ids
        )
        self.assertEqual(3, len(result.candidates))
        self.assertEqual(1, len(result.case.current.qualification_graphs))
        self.assertEqual(3, len(result.simulation.scenarios))
        self.assertFalse(result.summary.production_release_authorized)
        self.assertEqual(1, result.case.current.case_version)

    def test_approved_recovery_skips_evidence_specialist(self) -> None:
        tools = ApprovedRecoveryTools(FIXTURE_ROOT)

        result = run_recovery_workflow(self.request(), tools=tools)

        self.assertEqual(
            RecoveryWorkflowStatus.APPROVED_RECOVERY_AVAILABLE,
            result.summary.status,
        )
        self.assertEqual((), result.candidates)
        self.assertFalse(
            any(
                item.tool is SupervisorTool.EVIDENCE_SPECIALIST
                for item in result.tool_trace
            )
        )
        self.assertEqual((), result.case.current.candidate_comparisons)

    def test_no_exposure_stops_before_recovery_discovery(self) -> None:
        tools = NoExposureTools(FIXTURE_ROOT)

        result = run_recovery_workflow(self.request(), tools=tools)

        self.assertEqual(RecoveryWorkflowStatus.NO_EXPOSURE, result.summary.status)
        self.assertIsNone(result.case)
        self.assertIsNone(result.recovery_options)
        self.assertEqual(1, len(result.tool_trace))
        self.assertFalse(result.summary.human_review_required)

    def test_naive_timestamp_fails_closed(self) -> None:
        with self.assertRaisesRegex(RecoverySupervisorInputError, "timezone-aware"):
            run_recovery_workflow(
                replace(self.request(), as_of=datetime(2026, 9, 29)),
                tools=FixtureRecoverySupervisorTools(FIXTURE_ROOT),
            )

    def test_system_prompt_preserves_orchestration_boundaries(self) -> None:
        self.assertIn("approved recovery paths", SYSTEM_PROMPT)
        self.assertIn("Evidence Specialist only", SYSTEM_PROMPT)
        self.assertIn("deterministic tools", SYSTEM_PROMPT)
        self.assertIn("Humans retain", SYSTEM_PROMPT)

    def request(self) -> RecoverySupervisorRequest:
        return RecoverySupervisorRequest(
            case_id="CASE-001",
            event_id="EVT-DELAY-001",
            trigger_type=TriggerType.DELIVERY_DELAY,
            material_id="MAT-BRG-001",
            source_reference="purchase-order:PO-ORIGINAL-001",
            as_of=datetime(2026, 9, 29, tzinfo=timezone.utc),
            shortage_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
            created_at=datetime(2026, 9, 29, 3, tzinfo=timezone.utc),
        )


class ApprovedRecoveryTools(FixtureRecoverySupervisorTools):
    def find_recovery_options(self, **kwargs):
        result = super().find_recovery_options(**kwargs)
        return replace(
            result,
            approved_covered_quantity=result.required_quantity,
            remaining_quantity=0,
            approved_recovery_sufficient=True,
            unqualified_candidates=(),
        )

    def investigate_candidate(self, **kwargs):
        raise AssertionError("Evidence Specialist must not be called")


class NoExposureTools(FixtureRecoverySupervisorTools):
    def get_exposure(self, **kwargs):
        result = super().get_exposure(**kwargs)
        return replace(result, shortage_date=None, affected_orders=())

    def find_recovery_options(self, **kwargs):
        raise AssertionError("Recovery discovery must not be called")


if __name__ == "__main__":
    unittest.main()
