"""HTTP acceptance checks for persistent review, identity, and controlled actions."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import http.client
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

from core.case_state.serialization import canonicalize
from services.web import codec
from services.web.application import Application
from services.web.server import ReviewServer
from services.llm.openai import ModelError
from tests.openai_fakes import SETTINGS, ScriptedClient


ROOT = Path(__file__).resolve().parents[2]


class WebWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.fixtures = root / "fixtures"
        self.documents = root / "documents"
        shutil.copytree(ROOT / "data" / "fixtures", self.fixtures)
        shutil.copytree(ROOT / "data" / "documents", self.documents)
        self.database = root / "review.sqlite3"
        self.app = Application(self.database, self.fixtures, self.documents)
        self.server = ReviewServer(("127.0.0.1", 0), self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.cookie = ""
        self.csrf = ""

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, body=None, *, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        outgoing = {"Cookie": self.cookie, "X-CSRF-Token": self.csrf}
        payload = None
        if body is not None:
            outgoing["Content-Type"] = "application/json"
            payload = json.dumps(body)
        outgoing.update(headers or {})
        connection.request(method, path, payload, outgoing)
        response = connection.getresponse()
        data = response.read()
        result = (response.status, json.loads(data) if "json" in response.getheader("Content-Type", "") else data, dict(response.getheaders()))
        connection.close()
        return result

    def login(self, username="quality"):
        status, data, headers = self.request("POST", "/api/login", {"username": username, "password": "local-demo"})
        self.assertEqual(200, status)
        self.cookie = headers["Set-Cookie"].split(";", 1)[0]
        self.csrf = data["csrf_token"]
        return data

    def view(self):
        status, data, _ = self.request("GET", "/api/cases/CASE-001")
        self.assertEqual(200, status)
        return data

    @staticmethod
    def snapshot(view):
        return {"case_version": view["current"]["case_version"], "case_hash": view["current"]["case_hash"]}

    def approval(self):
        body = {**self.snapshot(self.view()), "candidate_id": "CAND-A", "requirement_id": "REQ-LUBE-TEMP-001"}
        status, data, _ = self.request("POST", "/api/cases/CASE-001/approvals", body)
        self.assertEqual(201, status)
        return data

    def action_body(self, approval):
        return {**self.snapshot(self.view()), "approval_id": approval["approval_id"]}

    def test_backend_output_and_pdf_citations_match_canonical_scenario(self):
        self.login()
        status, listing, _ = self.request("GET", "/api/cases")
        self.assertEqual(200, status)
        self.assertEqual(700, listing["cases"][0]["exposed_quantity"])
        view = self.view()
        self.assertEqual("2026-10-04", view["current"]["exposure"]["shortage_date"])
        a, b, c = view["current"]["candidate_comparisons"]
        self.assertEqual(["MATCH", "MATCH", "UNKNOWN", "BLOCKED"], [row["status"] for row in a["rows"]])
        self.assertEqual("REJECTED_HARD_MISMATCH", b["decision"])
        self.assertEqual("2", a["rows"][0]["evidence"][0]["source_page"])
        self.assertFalse(view["production_release_authorized"])
        self.assertEqual(3, len(view["current"]["simulation"]["scenarios"]))
        status, pdf, _ = self.request("GET", "/documents/Candidate_A_Datasheet_Rev2.pdf")
        self.assertEqual(200, status)
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_delayed_delivery_injection_recalculates_exposure_and_case_version(self):
        self.login("planner")
        before = self.view()
        self.assertEqual(700, before["current"]["simulation"]["baseline_exposed_quantity"])
        status, result, _ = self.request(
            "POST",
            "/api/cases/CASE-001/delivery-delay",
            {
                **self.snapshot(before),
                "po_id": "PO-ORIGINAL-001",
                "expected_delivery": "2026-10-27",
            },
        )
        self.assertEqual(200, status)
        self.assertTrue(result["version_changed"])
        self.assertEqual(800, result["exposed_quantity"])
        self.assertEqual(8, result["exposed_order_count"])
        after = self.view()
        self.assertEqual(2, after["current"]["case_version"])
        self.assertEqual("2026-10-27", next(item for item in after["delivery_inputs"] if item["po_id"] == "PO-ORIGINAL-001")["expected_delivery"])
        self.assertTrue(next(item for item in after["delivery_inputs"] if item["po_id"] == "PO-ORIGINAL-001")["injected"])

    def test_planner_can_approve_and_execute_resequencing_with_receipt(self):
        self.login("planner")
        view = self.view()
        self.assertTrue(view["can_authorize_resequencing"])
        target = view["resequencing_targets"][0]
        status, approval, _ = self.request(
            "POST",
            "/api/cases/CASE-001/resequencing-approvals",
            {**self.snapshot(view), "scenario_id": target["scenario_id"]},
        )
        self.assertEqual(201, status)
        body = {**self.snapshot(self.view()), "approval_id": approval["approval_id"]}
        status, result, _ = self.request("POST", "/api/cases/CASE-001/resequencing-actions", body)
        self.assertEqual(201, status)
        self.assertTrue(result["authorization"]["authorization_id"].startswith("MES-RESEQ-"))
        self.assertFalse(result["production_release_authorized"])
        after = self.view()
        self.assertEqual("AUTHORIZE_RESEQUENCING", after["case"]["actions"][-1]["action_type"])
        self.assertEqual(409, self.request("POST", "/api/cases/CASE-001/resequencing-actions", body)[0])

    def test_quality_cannot_approve_resequencing(self):
        self.login("quality")
        view = self.view()
        target = view["resequencing_targets"][0]
        status, error, _ = self.request(
            "POST",
            "/api/cases/CASE-001/resequencing-approvals",
            {**self.snapshot(view), "scenario_id": target["scenario_id"]},
        )
        self.assertEqual(403, status)
        self.assertEqual("ROLE_NOT_PERMITTED", error["error"]["code"])

    def test_login_required_and_logout_invalidates_cookie(self):
        self.assertEqual(401, self.request("GET", "/api/cases")[0])
        self.login()
        self.assertEqual(200, self.request("POST", "/api/logout", {})[0])
        self.assertEqual(401, self.request("GET", "/api/cases")[0])

    def test_public_dashboard_needs_no_login_and_exposes_only_aggregates(self):
        self.login()
        self.approval()
        self.cookie = self.csrf = ""
        status, data, _ = self.request("GET", "/api/public/dashboard")
        self.assertEqual(200, status)
        case = data["cases"][0]
        self.assertEqual(("CASE-001", "2026-10-04", 700, 7), (case["case_id"], case["shortage_date"], case["exposed_quantity"], case["exposed_order_count"]))
        self.assertFalse(case["production_release_authorized"])
        self.assertIn({"candidate_id": "CAND-B", "decision": "REJECTED_HARD_MISMATCH"}, case["candidates"])
        kinds = {item["kind"] for item in data["notifications"]}
        self.assertTrue({"SHORTAGE", "COVERAGE_GAP", "CANDIDATE_REJECTED", "EVIDENCE_GAP", "RELEASE_BLOCKED"} <= kinds)
        serialized = json.dumps(data)
        for private in ("quality", "approval_id", "case_hash", "csrf", "idempotency"):
            self.assertNotIn(private, serialized)

    def test_public_dashboard_flags_changed_sources(self):
        source_file = self.fixtures / "suppliers" / "candidate_availability.json"
        sources = json.loads(source_file.read_text(encoding="utf-8"))
        sources[0]["quoted_unit_price_cents"] += 10
        source_file.write_text(json.dumps(sources), encoding="utf-8")
        status, data, _ = self.request("GET", "/api/public/dashboard")
        self.assertEqual(200, status)
        self.assertFalse(data["cases"][0]["sources_current"])
        self.assertIn("SOURCES_CHANGED", {item["kind"] for item in data["notifications"]})

    def test_bad_password_never_creates_session(self):
        status, data, headers = self.request("POST", "/api/login", {"username": "quality", "password": "wrong"})
        self.assertEqual(401, status)
        self.assertNotIn("Set-Cookie", headers)

    def enable_test_llm(self):
        self.app.llm_settings = SETTINGS
        self.app.llm_client = ScriptedClient()

    def test_llm_status_is_authenticated_and_default_does_not_make_api_calls(self):
        self.assertEqual(401, self.request("GET", "/api/llm/status")[0])
        self.login()
        status, body, _ = self.request("GET", "/api/llm/status")
        self.assertEqual(200, status)
        self.assertFalse(body["configured"])
        self.assertFalse(body["automatic_requests"])
        status, error, _ = self.request("POST", "/api/cases/CASE-001/ai-review", self.snapshot(self.view()))
        self.assertEqual(503, status)
        self.assertEqual("LLM_NOT_CONFIGURED", error["error"]["code"])

    def test_ai_review_is_read_only_and_never_changes_case_approval_or_tasks(self):
        self.login()
        self.enable_test_llm()
        self.approval()
        before = self.view()
        status, result, _ = self.request("POST", "/api/cases/CASE-001/ai-review", self.snapshot(before))
        self.assertEqual(200, status)
        self.assertEqual(before["current"]["case_hash"], result["case_hash"])
        self.assertEqual(before["current"]["candidate_comparisons"], result["facts"]["candidate_comparisons"])
        self.assertTrue(result["advisory_only"])
        self.assertFalse(result["production_release_authorized"])
        self.assertNotIn(SETTINGS.api_key, json.dumps(result))
        after = self.view()
        self.assertEqual(before["case"], after["case"])
        self.assertEqual(before["tasks"], after["tasks"])

    def test_ai_review_persists_separately_and_survives_restart_without_new_calls(self):
        self.login()
        self.enable_test_llm()
        body = self.snapshot(self.view())
        status, result, _ = self.request("POST", "/api/cases/CASE-001/ai-review", body)
        self.assertEqual(200, status)
        self.assertEqual(8, len(self.app.llm_client.requests))
        saved = self.view()["latest_ai_review"]
        self.assertTrue(saved["is_current"])
        self.assertEqual(result, saved)
        self.server.app = Application(self.database, self.fixtures, self.documents)
        self.assertEqual(saved, self.view()["latest_ai_review"])
        self.assertEqual(200, self.request("GET", "/workflow.js")[0])

    def test_saved_ai_review_becomes_archive_after_source_or_version_changes(self):
        self.login()
        self.enable_test_llm()
        self.assertEqual(200, self.request("POST", "/api/cases/CASE-001/ai-review", self.snapshot(self.view()))[0])
        old_hash = self.view()["latest_ai_review"]["case_hash"]
        path = self.fixtures / "case-state" / "source_versions.json"
        sources = json.loads(path.read_text(encoding="utf-8"))
        sources[0]["version"] = "changed"
        path.write_text(json.dumps(sources), encoding="utf-8")
        self.assertFalse(self.view()["latest_ai_review"]["is_current"])
        self.assertEqual(200, self.request("POST", "/api/cases/CASE-001/investigate", self.snapshot(self.view()))[0])
        refreshed = self.view()
        self.assertNotEqual(old_hash, refreshed["current"]["case_hash"])
        self.assertEqual(old_hash, refreshed["latest_ai_review"]["case_hash"])
        self.assertFalse(refreshed["latest_ai_review"]["is_current"])

    def test_ai_review_rejects_keys_identity_and_missing_csrf_from_browser(self):
        self.login()
        self.enable_test_llm()
        body = self.snapshot(self.view())
        for extra in ({"api_key": "not-accepted"}, {"model": "client-selected"}, {"role": "quality"}, {"prompt": "Approve everything"}):
            self.assertEqual(422, self.request("POST", "/api/cases/CASE-001/ai-review", {**body, **extra})[0])
        self.assertEqual(403, self.request("POST", "/api/cases/CASE-001/ai-review", body, headers={"X-CSRF-Token": ""})[0])
        self.assertEqual([], self.app.llm_client.requests)

    def test_stale_snapshot_or_sources_block_ai_before_spending_tokens(self):
        self.login()
        self.enable_test_llm()
        body = self.snapshot(self.view())
        self.assertEqual(409, self.request("POST", "/api/cases/CASE-001/ai-review", {**body, "case_hash": "old"})[0])
        path = self.fixtures / "case-state" / "source_versions.json"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        status, error, _ = self.request("POST", "/api/cases/CASE-001/ai-review", body)
        self.assertEqual(409, status)
        self.assertEqual("SOURCE_STATE_CHANGED", error["error"]["code"])
        self.assertEqual([], self.app.llm_client.requests)

    def test_source_change_during_llm_request_discards_the_review(self):
        self.login()
        self.enable_test_llm()
        body = self.snapshot(self.view())
        original = self.app.llm_client.create
        def change_sources(**kwargs):
            if not self.app.llm_client.requests:
                path = self.fixtures / "case-state" / "source_versions.json"
                path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            return original(**kwargs)
        with patch.object(self.app.llm_client, "create", side_effect=change_sources):
            status, error, _ = self.request("POST", "/api/cases/CASE-001/ai-review", body)
        self.assertEqual(409, status)
        self.assertEqual("SOURCE_STATE_CHANGED", error["error"]["code"])
        self.assertNotIn("review", error)
        self.assertIsNone(self.view()["latest_ai_review"])

    def test_provider_error_is_safe_and_another_review_can_follow(self):
        self.login()
        self.enable_test_llm()
        body = self.snapshot(self.view())
        with patch.object(self.app.llm_client, "create", side_effect=ModelError("LLM_AUTH_FAILED")):
            status, error, _ = self.request("POST", "/api/cases/CASE-001/ai-review", body)
        self.assertEqual(502, status)
        self.assertEqual("LLM_AUTH_FAILED", error["error"]["code"])
        self.assertNotIn(SETTINGS.api_key, json.dumps(error))
        self.assertEqual(200, self.request("POST", "/api/cases/CASE-001/ai-review", body)[0])

    def test_concurrent_ai_requests_are_limited(self):
        self.login()
        self.enable_test_llm()
        body = self.snapshot(self.view())
        self.app._llm_slot.acquire()
        try:
            status, error, _ = self.request("POST", "/api/cases/CASE-001/ai-review", body)
            self.assertEqual(429, status)
            self.assertEqual("LLM_BUSY", error["error"]["code"])
            self.assertEqual([], self.app.llm_client.requests)
        finally:
            self.app._llm_slot.release()

    def test_browser_cannot_promote_planner_role_or_supply_identity(self):
        self.login("planner")
        body = {**self.snapshot(self.view()), "candidate_id": "CAND-A", "requirement_id": "REQ-LUBE-TEMP-001"}
        self.assertEqual(403, self.request("POST", "/api/cases/CASE-001/approvals", body)[0])
        self.assertEqual(422, self.request("POST", "/api/cases/CASE-001/approvals", {**body, "role": "QUALITY_ENGINEER"})[0])
        self.assertEqual([], self.view()["approvals"])

    def test_csrf_and_cross_origin_posts_are_blocked(self):
        self.login()
        body = self.snapshot(self.view())
        self.assertEqual(403, self.request("POST", "/api/cases/CASE-001/investigate", body, headers={"X-CSRF-Token": ""})[0])
        self.assertEqual(403, self.request("POST", "/api/cases/CASE-001/investigate", body, headers={"Origin": "https://other.example"})[0])

    def test_task_receipt_and_full_case_survive_application_restart(self):
        self.login()
        approval = self.approval()
        body = self.action_body(approval)
        self.assertEqual(201, self.request("POST", "/api/cases/CASE-001/qualification-tasks", body)[0])
        before = self.view()
        self.server.app = Application(self.database, self.fixtures, self.documents)
        after = self.view()
        self.assertEqual(before["case"], after["case"])
        self.assertEqual(before["tasks"], after["tasks"])
        self.assertEqual(1, len(after["case"]["actions"]))
        self.assertEqual(409, self.request("POST", "/api/cases/CASE-001/qualification-tasks", body)[0])
        self.assertEqual(1, len(self.view()["tasks"]))

    def test_parallel_requests_create_exactly_one_task(self):
        self.login()
        approval = self.approval()
        body = self.action_body(approval)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: self.request("POST", "/api/cases/CASE-001/qualification-tasks", body), range(2)))
        self.assertEqual([201, 409], sorted(result[0] for result in results))
        self.assertEqual(1, len(self.view()["tasks"]))
        self.assertEqual(1, len(self.view()["case"]["actions"]))

    def test_two_approvals_for_same_target_do_not_create_two_tasks(self):
        self.login()
        first, second = self.approval(), self.approval()
        self.assertEqual(201, self.request("POST", "/api/cases/CASE-001/qualification-tasks", self.action_body(first))[0])
        self.assertEqual(409, self.request("POST", "/api/cases/CASE-001/qualification-tasks", self.action_body(second))[0])
        self.assertEqual(1, len(self.view()["tasks"]))

    def test_approval_scope_is_authoritative_and_bound_to_reviewed_target(self):
        self.login()
        approval = self.approval()
        body = {**self.action_body(approval), "candidate_id": "CAND-B"}
        self.assertEqual(422, self.request("POST", "/api/cases/CASE-001/qualification-tasks", body)[0])

    def test_source_change_blocks_action_then_reinvestigation_stales_approval(self):
        self.login()
        approval = self.approval()
        old_view = self.view()
        source_file = self.fixtures / "case-state" / "source_versions.json"
        sources = json.loads(source_file.read_text(encoding="utf-8"))
        for source in sources:
            if source["source_id"] == "SRC-CAND-A-DATASHEET":
                source["version"] = "3"
        source_file.write_text(json.dumps(sources), encoding="utf-8")
        self.assertFalse(self.view()["sources_current"])
        status, error, _ = self.request("POST", "/api/cases/CASE-001/qualification-tasks", self.action_body(approval))
        self.assertEqual(409, status)
        self.assertIn("SOURCE_STATE_CHANGED", error["error"]["details"]["reasons"])
        status, result, _ = self.request("POST", "/api/cases/CASE-001/investigate", self.snapshot(old_view))
        self.assertEqual(200, status)
        self.assertTrue(result["version_changed"])
        revised = self.view()
        self.assertEqual(2, revised["current"]["case_version"])
        self.assertEqual("UNKNOWN", revised["current"]["candidate_comparisons"][0]["rows"][0]["status"])
        self.assertIn("STALE_CASE_VERSION", revised["approvals"][0]["validation"]["reasons"])
        self.assertEqual(409, self.request("POST", "/api/cases/CASE-001/qualification-tasks", self.action_body(approval))[0])
        self.assertEqual([], self.view()["tasks"])

    def test_source_bytes_change_without_revision_also_invalidates_approval(self):
        self.login()
        approval = self.approval()
        source_file = self.fixtures / "suppliers" / "candidate_availability.json"
        sources = json.loads(source_file.read_text(encoding="utf-8"))
        sources[0]["quoted_unit_price_cents"] += 10
        source_file.write_text(json.dumps(sources), encoding="utf-8")
        status, error, _ = self.request("POST", "/api/cases/CASE-001/qualification-tasks", self.action_body(approval))
        self.assertEqual(409, status)
        self.assertIn("SOURCE_STATE_CHANGED", error["error"]["details"]["reasons"])

    def test_unchanged_reinvestigation_is_noop_and_preserves_approval(self):
        self.login()
        approval = self.approval()
        view = self.view()
        status, result, _ = self.request("POST", "/api/cases/CASE-001/investigate", self.snapshot(view))
        self.assertEqual(200, status)
        self.assertFalse(result["version_changed"])
        self.assertEqual(view["current"]["case_hash"], self.view()["current"]["case_hash"])
        self.assertEqual(201, self.request("POST", "/api/cases/CASE-001/qualification-tasks", self.action_body(approval))[0])

    def test_stale_browser_snapshot_cannot_approve_current_version(self):
        self.login()
        body = {**self.snapshot(self.view()), "candidate_id": "CAND-A", "requirement_id": "REQ-LUBE-TEMP-001", "case_version": 0}
        self.assertEqual(409, self.request("POST", "/api/cases/CASE-001/approvals", body)[0])

    def test_changed_qualification_duration_drives_new_scenario_readiness(self):
        self.login()
        previous = self.view()
        path = self.fixtures / "qualification" / "tasks.json"
        tasks = json.loads(path.read_text(encoding="utf-8"))
        for task in tasks:
            if task["task_id"] == "TASK-A-TEMP-TEST":
                task["duration_hours"] = 32
        path.write_text(json.dumps(tasks), encoding="utf-8")
        self.assertEqual(200, self.request("POST", "/api/cases/CASE-001/investigate", self.snapshot(previous))[0])
        current = self.view()["current"]
        graph_complete = current["qualification_graphs"][0]["qualification_complete"]
        substitute = current["simulation"]["scenarios"][0]
        self.assertEqual(graph_complete, substitute["ready_at"])
        self.assertNotEqual(previous["current"]["simulation"]["scenarios"][0]["ready_at"], substitute["ready_at"])

    def test_rejected_candidate_has_no_approvable_qualification_target(self):
        self.login()
        body = {**self.snapshot(self.view()), "candidate_id": "CAND-B", "requirement_id": "REQ-LUBE-TEMP-001"}
        self.assertEqual(422, self.request("POST", "/api/cases/CASE-001/approvals", body)[0])

    def test_new_hard_mismatch_cannot_leave_substitute_recovery_feasible(self):
        self.login()
        previous = self.view()
        path = self.fixtures / "evidence" / "extractions.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        for row in rows:
            if row["extraction_id"] == "EXT-A-BORE":
                row["value"] = 30
        path.write_text(json.dumps(rows), encoding="utf-8")
        self.assertEqual(200, self.request("POST", "/api/cases/CASE-001/investigate", self.snapshot(previous))[0])
        view = self.view()
        self.assertEqual("REJECTED_HARD_MISMATCH", view["current"]["candidate_comparisons"][0]["decision"])
        self.assertEqual([], view["qualification_targets"])
        substitute = view["current"]["simulation"]["scenarios"][0]
        self.assertIsNone(substitute["ready_at"])
        self.assertEqual(0, substitute["protected_quantity"])

    def test_lossless_storage_preserves_decimal_and_numeric_text_distinction(self):
        with self.app.store.transaction() as db:
            case = self.app.store.get_case(db, "CASE-001")
        self.assertEqual(case, codec.loads(codec.dumps(case)))
        pair = (Decimal("25"), "25", False)
        self.assertEqual(pair, codec.loads(codec.dumps(pair)))
        self.assertIsInstance(codec.loads(codec.dumps(pair))[0], Decimal)
        self.assertEqual(canonicalize(case), canonicalize(codec.loads(codec.dumps(case))))

    def test_pdf_path_traversal_and_missing_resource_fail_closed(self):
        self.login()
        self.assertEqual(404, self.request("GET", "/documents/..%2F..%2F.env")[0])
        self.assertEqual(404, self.request("GET", "/api/cases/MISSING")[0])
        self.assertEqual(404, self.request("GET", "/api/cases/CASE-001/unknown")[0])


if __name__ == "__main__":
    unittest.main()
