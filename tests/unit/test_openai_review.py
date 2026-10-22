"""Bounded read-only model tool selection over canonical deterministic facts."""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import unittest

from agents.recovery_supervisor import FixtureRecoverySupervisorTools, RecoverySupervisorRequest, run_recovery_workflow
from agents.recovery_supervisor.openai_review import MAX_CALLS, run_openai_review
from core.case_state import TriggerType
from core.case_state.serialization import canonicalize
from services.llm.openai import ModelError
from tests.openai_fakes import REVIEW, ScriptedClient, function_response


class OpenAIReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.version = run_recovery_workflow(RecoverySupervisorRequest(
            case_id="CASE-001", event_id="EVT-DELAY-001", trigger_type=TriggerType.DELIVERY_DELAY,
            material_id="MAT-BRG-001", source_reference="purchase-order:PO-ORIGINAL-001",
            as_of=datetime(2026, 9, 29, tzinfo=timezone.utc), shortage_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
            created_at=datetime(2026, 10, 22, tzinfo=timezone.utc),
        ), tools=FixtureRecoverySupervisorTools(Path(__file__).resolve().parents[2] / "data" / "fixtures")).case.current

    def test_model_selects_candidate_order_but_facts_remain_unchanged(self):
        client = ScriptedClient()
        before = canonicalize(self.version)
        result = run_openai_review(self.version, client)
        self.assertEqual(before, canonicalize(self.version))
        self.assertEqual(before["candidate_comparisons"], result["facts"]["candidate_comparisons"])
        self.assertEqual("REJECTED_HARD_MISMATCH", result["facts"]["candidate_comparisons"][1]["decision"])
        self.assertTrue(result["advisory_only"])
        self.assertFalse(result["production_release_authorized"])
        self.assertFalse(result["pdf_extraction"])
        self.assertEqual(["CAND-C", "CAND-B", "CAND-A"], [row["target"] for row in result["tool_trace"] if row["tool"] == "getCandidateEvidence"])
        self.assertEqual(800, result["usage"]["input_tokens"])
        self.assertEqual("function_call_output", client.requests[1]["input_items"][-1]["type"])
        self.assertEqual("2026-10-04", __import__('json').loads(client.requests[1]["input_items"][-1]["output"])["shortage_date"])

    def test_only_expected_read_tools_are_exposed_at_each_stage(self):
        client = ScriptedClient()
        run_openai_review(self.version, client)
        names = [{tool["name"] for tool in request["tools"]} for request in client.requests]
        self.assertEqual({"getExposure"}, names[0])
        self.assertEqual({"findRecoveryOptions"}, names[1])
        self.assertEqual({"finishReview"}, names[-1])
        self.assertFalse(any("createQualificationTask" in group or "approve" in group for group in names))

    def test_unknown_write_tool_early_finish_and_branch_bypass_are_rejected(self):
        for name, args in (("createQualificationTask", {}), ("finishReview", REVIEW), ("getCandidateEvidence", {"candidate_id": "CAND-A"})):
            with self.subTest(name=name), self.assertRaisesRegex(ModelError, "LLM_INVALID_TOOL_CALL"):
                run_openai_review(self.version, ScriptedClient([function_response(name, args)]))

    def test_invalid_candidate_or_extra_arguments_are_rejected(self):
        prefix = [function_response("getExposure"), function_response("findRecoveryOptions")]
        for args in ({"candidate_id": "../../private"}, {"candidate_id": "CAND-A", "role": "quality"}, {"candidate_id": []}):
            with self.subTest(args=args), self.assertRaisesRegex(ModelError, "LLM_INVALID_TOOL_CALL"):
                run_openai_review(self.version, ScriptedClient(prefix + [function_response("getCandidateEvidence", args)]))

    def test_malformed_parallel_refused_or_incomplete_output_is_not_accepted(self):
        parallel = function_response("getExposure")
        parallel["output"] *= 2
        malformed = function_response("getExposure")
        malformed["output"][0]["arguments"] = "bad-json"
        for output in (parallel, malformed, {"status": "incomplete", "output": []}, {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}]}):
            with self.subTest(output=output), self.assertRaises(ModelError):
                run_openai_review(self.version, ScriptedClient([output]))

    def test_hard_rejected_candidate_cannot_get_a_qualification_plan(self):
        client = ScriptedClient([
            function_response("getExposure"), function_response("findRecoveryOptions"),
            function_response("getCandidateEvidence", {"candidate_id": "CAND-B"}),
            function_response("getQualificationDependencies", {"candidate_id": "CAND-B"}),
        ])
        with self.assertRaisesRegex(ModelError, "LLM_INVALID_TOOL_CALL"):
            run_openai_review(self.version, client)

    def test_repeated_calls_are_bounded_without_infinite_retry(self):
        client = ScriptedClient([function_response("getExposure"), function_response("findRecoveryOptions")] + [function_response("getCandidateEvidence", {"candidate_id": "CAND-A"})] * MAX_CALLS)
        with self.assertRaisesRegex(ModelError, "LLM_RUN_LIMIT"):
            run_openai_review(self.version, client)
        self.assertEqual(MAX_CALLS, len(client.requests))

    def test_overall_deadline_is_bounded(self):
        times = iter([0, 0, 91])
        client = ScriptedClient()
        with self.assertRaisesRegex(ModelError, "LLM_RUN_LIMIT"):
            run_openai_review(self.version, client, clock=lambda: next(times))
        self.assertEqual(1, len(client.requests))

    def test_final_schema_cannot_set_status_or_invent_candidates(self):
        for changes in ({"production_release_authorized": True}, {"candidate_ids": ["INVENTED"]}, {"next_steps": ["PURCHASE_NOW"]}, {"summary": ""}, {"next_steps": []}):
            client = ScriptedClient()
            args = deepcopy(REVIEW)
            args.update(changes)
            client.responses[-1] = function_response("finishReview", args)
            with self.subTest(changes=changes), self.assertRaises(ModelError):
                run_openai_review(self.version, client)
