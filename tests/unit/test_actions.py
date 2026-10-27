from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.actions import (
    ActionAdapterInputError,
    ActionBlockReason,
    ActionExecutionStatus,
    CreateQualificationTaskCommand,
    AuthorizeResequencingCommand,
    authorize_resequencing,
    create_qualification_task,
)
from core.approval import (
    ApprovalBlockReason,
    ApprovalValidationRequest,
    ApproverRole,
    AuthenticatedPrincipal,
    ControlledAction,
)
from core.case_state import (
    ApprovalRecord,
    RecoveryCaseUpdate,
    append_approval,
    update_case,
)
from core.case_state.canonical import build_canonical_case


FIXTURE_ROOT = Path(__file__).parents[2] / "data" / "fixtures"
CREATED_AT = datetime(2026, 9, 29, 3, tzinfo=timezone.utc)


class QualificationTaskActionTests(unittest.TestCase):
    def setUp(self) -> None:
        case = build_canonical_case(FIXTURE_ROOT, created_at=CREATED_AT)
        approval = ApprovalRecord(
            approval_id="APR-001",
            case_id=case.case_id,
            case_version=case.current.case_version,
            case_hash=case.current.case_hash,
            approver_id="quality-reviewer-1",
            approver_role=ApproverRole.QUALITY_ENGINEER.value,
            permitted_action=ControlledAction.CREATE_QUALIFICATION_TASK.value,
            approved_at=CREATED_AT + timedelta(minutes=5),
            expires_at=CREATED_AT + timedelta(hours=8),
        )
        self.case = append_approval(case, approval, updated_at=approval.approved_at)
        self.approval = approval

    def test_authorized_command_creates_mock_qms_task_and_receipt(self) -> None:
        result = create_qualification_task(self.case, self.command())

        self.assertTrue(result.created)
        self.assertEqual(ActionExecutionStatus.CREATED, result.status)
        self.assertRegex(result.qms_task_id or "", r"^QMS-QUAL-[A-F0-9]{10}$")
        self.assertEqual(
            "Candidate A lubricant temperature qualification",
            result.task.task_name,
        )
        self.assertEqual("CAND-A", result.task.candidate_id)
        self.assertEqual("REQ-LUBE-TEMP-001", result.task.requirement_id)
        self.assertIsNotNone(result.action_receipt)
        self.assertEqual(1, len(result.case.actions))
        self.assertEqual(self.case.current.case_version, result.case.current.case_version)
        self.assertFalse(result.production_release_authorized)

    def test_mock_identifiers_are_deterministic(self) -> None:
        first = create_qualification_task(self.case, self.command())
        second = create_qualification_task(self.case, self.command())

        self.assertEqual(first.qms_task_id, second.qms_task_id)
        self.assertEqual(
            first.action_receipt.action_id,
            second.action_receipt.action_id,
        )

    def test_duplicate_execution_is_blocked_without_second_receipt(self) -> None:
        first = create_qualification_task(self.case, self.command())
        second = create_qualification_task(first.case, self.command())

        self.assertFalse(second.created)
        self.assertEqual((ActionBlockReason.APPROVAL_BLOCKED,), second.block_reasons)
        self.assertIn(
            ApprovalBlockReason.DUPLICATE_ACTION,
            second.approval_decision.reasons,
        )
        self.assertEqual(1, len(second.case.actions))
        self.assertIsNone(second.task)
        self.assertIsNone(second.action_receipt)

    def test_expired_approval_blocks_action(self) -> None:
        command = self.command(evaluated_at=self.approval.expires_at)

        result = create_qualification_task(self.case, command)

        self.assertFalse(result.created)
        self.assertIn(
            ApprovalBlockReason.APPROVAL_EXPIRED,
            result.approval_decision.reasons,
        )
        self.assertEqual((), result.case.actions)

    def test_stale_case_approval_blocks_action(self) -> None:
        revised_sources = tuple(
            replace(source, version="3")
            if source.source_id == "SRC-CAND-A-DATASHEET"
            else source
            for source in self.case.current.source_versions
        )
        case = update_case(
            self.case,
            update=RecoveryCaseUpdate(source_versions=revised_sources),
            change_reason="Candidate A datasheet revision changed.",
            updated_at=CREATED_AT + timedelta(hours=1),
        ).case
        command = self.command(
            evaluated_at=CREATED_AT + timedelta(hours=1, minutes=1),
            source_versions=case.current.source_versions,
        )

        result = create_qualification_task(case, command)

        self.assertIn(
            ApprovalBlockReason.STALE_CASE_VERSION,
            result.approval_decision.reasons,
        )
        self.assertEqual((), result.case.actions)

    def test_hard_rejected_candidate_cannot_receive_qualification_task(self) -> None:
        command = replace(self.command(), candidate_id="CAND-B")

        result = create_qualification_task(self.case, command)

        self.assertEqual(
            (ActionBlockReason.CANDIDATE_HARD_REJECTED,), result.block_reasons
        )
        self.assertEqual((), result.case.actions)

    def test_requirement_must_exist_in_candidate_qualification_plan(self) -> None:
        command = replace(self.command(), requirement_id="REQ-LOAD-001")

        result = create_qualification_task(self.case, command)

        self.assertEqual(
            (ActionBlockReason.REQUIREMENT_NOT_IN_PLAN,), result.block_reasons
        )

    def test_adapter_rejects_wrong_action_type(self) -> None:
        approval = replace(
            self.command().approval,
            action=ControlledAction.AUTHORIZE_RESEQUENCING,
        )

        with self.assertRaisesRegex(
            ActionAdapterInputError, "CREATE_QUALIFICATION_TASK"
        ):
            create_qualification_task(
                self.case, replace(self.command(), approval=approval)
            )

    def command(
        self,
        *,
        evaluated_at: datetime = CREATED_AT + timedelta(minutes=10),
        source_versions=None,
    ) -> CreateQualificationTaskCommand:
        return CreateQualificationTaskCommand(
            candidate_id="CAND-A",
            requirement_id="REQ-LUBE-TEMP-001",
            task_name="Candidate A lubricant temperature qualification",
            approval=ApprovalValidationRequest(
                approval_id=self.approval.approval_id,
                action=ControlledAction.CREATE_QUALIFICATION_TASK,
                principal=AuthenticatedPrincipal(
                    principal_id=self.approval.approver_id,
                    role=ApproverRole.QUALITY_ENGINEER,
                ),
                evaluated_at=evaluated_at,
                current_source_versions=(
                    self.case.current.source_versions
                    if source_versions is None
                    else source_versions
                ),
                idempotency_key="case-001-create-qualification-cand-a-temp",
            ),
        )


class ResequencingActionTests(unittest.TestCase):
    def setUp(self) -> None:
        case = build_canonical_case(FIXTURE_ROOT, created_at=CREATED_AT)
        approval = ApprovalRecord(
            approval_id="APR-RESEQ-001",
            case_id=case.case_id,
            case_version=case.current.case_version,
            case_hash=case.current.case_hash,
            approver_id="planner-1",
            approver_role=ApproverRole.PRODUCTION_PLANNER.value,
            permitted_action=ControlledAction.AUTHORIZE_RESEQUENCING.value,
            approved_at=CREATED_AT + timedelta(minutes=5),
            expires_at=CREATED_AT + timedelta(hours=8),
        )
        self.case = append_approval(case, approval, updated_at=approval.approved_at)
        self.approval = approval

    def command(self, scenario_id="SCN-PRODUCTION-RESEQUENCING"):
        return AuthorizeResequencingCommand(
            scenario_id=scenario_id,
            approval=ApprovalValidationRequest(
                approval_id=self.approval.approval_id,
                action=ControlledAction.AUTHORIZE_RESEQUENCING,
                principal=AuthenticatedPrincipal(
                    principal_id=self.approval.approver_id,
                    role=ApproverRole.PRODUCTION_PLANNER,
                ),
                evaluated_at=CREATED_AT + timedelta(minutes=10),
                current_source_versions=self.case.current.source_versions,
                idempotency_key="case-001-resequencing-v1",
            ),
        )

    def test_planner_authorization_creates_mock_receipt_without_release(self):
        result = authorize_resequencing(self.case, self.command())

        self.assertTrue(result.created)
        self.assertRegex(result.authorization.authorization_id, r"^MES-RESEQ-[A-F0-9]{10}$")
        self.assertEqual("SCN-PRODUCTION-RESEQUENCING", result.authorization.scenario_id)
        self.assertEqual(ControlledAction.AUTHORIZE_RESEQUENCING.value, result.action_receipt.action_type)
        self.assertFalse(result.production_release_authorized)
        self.assertEqual(1, len(result.case.actions))

    def test_duplicate_resequencing_authorization_is_blocked(self):
        first = authorize_resequencing(self.case, self.command())
        second = authorize_resequencing(first.case, self.command())

        self.assertFalse(second.created)
        self.assertIn(ApprovalBlockReason.DUPLICATE_ACTION, second.approval_decision.reasons)
        self.assertEqual(1, len(second.case.actions))

    def test_non_resequencing_scenario_is_rejected(self):
        result = authorize_resequencing(self.case, self.command("SCN-ORIGINAL-EXPEDITE"))

        self.assertFalse(result.created)
        self.assertEqual((ActionBlockReason.WRONG_SCENARIO_TYPE,), result.block_reasons)


if __name__ == "__main__":
    unittest.main()
