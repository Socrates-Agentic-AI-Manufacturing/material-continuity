"""Real PDF bytes → extracted text → reviewed evidence → version-bound actions.

Network is faked here, not the parser. Live smoke tests remain explicit/paid.
"""

import base64
from copy import deepcopy
import io
import unittest

from services.documents.extraction import validate_rows
from services.documents.parser import DocumentError, parse_pdf
from services.llm.openai import ModelError
from services.web.application import Application
from tests.integration import test_web_workflow as web_tests
from tests.openai_fakes import SETTINGS, ScriptedClient, function_response

ROOT = web_tests.ROOT


def rows(value="25"):
    return [
        {"property": "BORE_DIAMETER", "value": value, "unit": "mm", "page": 2,
         "quote": f"Bore diameter | {value} mm | tolerance 0 / -0.010 mm", "applicability": "BEARING-SEAT-25MM"},
        {"property": "DYNAMIC_LOAD", "value": "16", "unit": "kN", "page": 3,
         "quote": "Basic dynamic load rating | 16 kN", "applicability": "BEARING-SEAT-25MM"},
    ]


class DocumentWorkflowTests(unittest.TestCase):
    setUp = web_tests.WebWorkflowTests.setUp
    close_server = web_tests.WebWorkflowTests.close_server
    request = web_tests.WebWorkflowTests.request
    login = web_tests.WebWorkflowTests.login
    view = web_tests.WebWorkflowTests.view
    snapshot = staticmethod(web_tests.WebWorkflowTests.snapshot)
    approval = web_tests.WebWorkflowTests.approval
    action_body = web_tests.WebWorkflowTests.action_body

    def upload(self, revision="2", content=None, **overrides):
        content = content if content is not None else (ROOT / "data/documents/Candidate_A_Datasheet_Rev2.pdf").read_bytes()
        return self.request("POST", "/api/documents", {
            "candidate_id": "CAND-A", "document_id": "DS-CAND-A", "revision": revision,
            "filename": "supplier.pdf", "content_base64": base64.b64encode(content).decode(), **overrides,
        })

    def operation(self, document, action, body):
        return self.request("POST", f"/api/document-revisions/{document['revision_id']}/{action}", body)

    def extract_review(self, document, value="25"):
        self.app.llm_settings = SETTINGS
        self.app.llm_client = ScriptedClient([function_response("submitEvidence", {"rows": rows(value)})])
        status, extracted, _ = self.operation(document, "extract", {"consent_openai": True})
        self.assertEqual(200, status, extracted)
        self.assertEqual(1, len(self.app.llm_client.requests))
        status, reviewed, _ = self.operation(document, "review", {
            "extraction_hash": extracted["extraction_hash"], "accepted_rows": [0, 1], "confirm_scope": True,
        })
        self.assertEqual(200, status, reviewed)
        return reviewed

    def activate(self, document, previous=None):
        status, result, _ = self.operation(document, "activate", {"expected_active_revision_id": previous, "confirm_invalidation": True})
        self.assertEqual(200, status, result)

    def investigate(self):
        status, data, _ = self.request("POST", "/api/cases/CASE-001/investigate", self.snapshot(self.view()))
        self.assertEqual(200, status, data)
        return self.view()

    def test_pdf_upload_preserves_original_pages_and_immutable_identity(self):
        self.login()
        original = self.view()
        status, document, _ = self.upload()
        self.assertEqual(201, status)
        self.assertEqual("TEXT_READY", document["status"])
        self.assertIn("Bore diameter | 25 mm", document["pages"][1])
        self.assertEqual(4, len(document["pages"]))
        status, pdf, _ = self.request("GET", f"/documents/{document['revision_id']}.pdf")
        self.assertEqual(200, status)
        self.assertEqual((ROOT / "data/documents/Candidate_A_Datasheet_Rev2.pdf").read_bytes(), pdf)
        self.assertTrue(self.view()["sources_current"])
        self.assertEqual(original["current"]["case_hash"], self.view()["current"]["case_hash"])
        self.assertEqual(document["revision_id"], self.upload()[1]["revision_id"])
        self.assertEqual(422, self.upload(content=pdf + b"\n")[0])

    def test_planner_csrf_unknown_fields_and_path_metadata_fail_closed(self):
        self.login("planner")
        self.assertEqual(403, self.upload()[0])
        self.login()
        self.assertEqual(422, self.upload(filename="../escape.pdf")[0])
        self.assertEqual(422, self.upload(candidate_id="CAND-X")[0])
        self.assertEqual(422, self.upload(revision="../3")[0])
        self.csrf = "wrong"
        self.assertEqual(403, self.upload()[0])

    def test_pending_revision_blocks_old_actions_immediately_and_unknown_after_investigation(self):
        self.login()
        approval = self.approval()
        _, document, _ = self.upload()
        self.activate(document)
        pending = self.view()
        self.assertFalse(pending["sources_current"])
        self.assertEqual(409, self.request("POST", "/api/cases/CASE-001/qualification-tasks", self.action_body(approval))[0])
        current = self.investigate()
        self.assertEqual("UNKNOWN", current["current"]["candidate_comparisons"][0]["rows"][0]["status"])
        self.assertEqual("BLOCKED", current["current"]["candidate_comparisons"][0]["rows"][3]["status"])
        self.assertEqual("BLOCKED", current["approvals"][0]["validation"]["status"])

    def test_real_rev2_to_rev3_drives_mismatch_history_and_restart_without_json_edits(self):
        self.login()
        fixture_bytes = (self.fixtures / "evidence/extractions.json").read_bytes()
        _, revision2, _ = self.upload()
        self.extract_review(revision2)
        self.activate(revision2)
        version2 = self.investigate()
        a = version2["current"]["candidate_comparisons"][0]
        self.assertEqual(["MATCH", "MATCH", "UNKNOWN", "BLOCKED"], [row["status"] for row in a["rows"]])
        self.assertEqual(revision2["revision_id"] + ".pdf", a["rows"][0]["evidence"][0]["source_document"])
        self.assertEqual("2", a["rows"][0]["evidence"][0]["source_page"])
        approval = self.approval()
        status, receipt, _ = self.request("POST", "/api/cases/CASE-001/qualification-tasks", self.action_body(approval))
        self.assertEqual(201, status)
        self.assertFalse(receipt["production_release_authorized"])
        self.assertEqual(409, self.request("POST", "/api/cases/CASE-001/qualification-tasks", self.action_body(approval))[0])
        _, revision3, _ = self.upload("3", (ROOT / "data/demo/Candidate_A_Datasheet_Rev3.pdf").read_bytes())
        self.assertIn("Bore diameter | 30 mm", revision3["pages"][1])
        self.activate(revision3, revision2["revision_id"])
        self.assertFalse(self.view()["sources_current"])
        self.extract_review(revision3, "30")
        version3 = self.investigate()
        a = version3["current"]["candidate_comparisons"][0]
        self.assertEqual("REJECTED_HARD_MISMATCH", a["decision"])
        self.assertEqual("30", a["rows"][0]["observed_value"])
        self.assertGreater(version3["current"]["case_version"], version2["current"]["case_version"])
        self.assertNotEqual(version2["current"]["case_hash"], version3["current"]["case_hash"])
        self.assertFalse(any(item["candidate_id"] == "CAND-A" for item in version3["qualification_targets"]))
        self.assertEqual("BLOCKED", version3["approvals"][0]["validation"]["status"])
        self.assertIsNone(version3["current"]["simulation"]["scenarios"][0]["ready_at"])
        self.assertEqual(fixture_bytes, (self.fixtures / "evidence/extractions.json").read_bytes())
        restarted = Application(self.database, self.fixtures, self.documents)
        reopened = restarted.case_view("CASE-001", {"user_id": "quality", "role": "QUALITY_ENGINEER"})
        self.assertEqual(version3["current"]["case_hash"], reopened["current"]["case_hash"])
        self.assertTrue(reopened["sources_current"])
        self.assertEqual(1, len(reopened["tasks"]))
        self.assertEqual(2, len(restarted.document_repository.listing()))

    def test_extraction_is_explicit_cached_and_review_is_version_bound(self):
        self.login()
        _, document, _ = self.upload()
        self.assertEqual(422, self.operation(document, "extract", {})[0])
        reviewed = self.extract_review(document)
        status, repeated, _ = self.operation(document, "extract", {"consent_openai": True})
        self.assertEqual(200, status)
        self.assertEqual(1, len(self.app.llm_client.requests))
        self.assertEqual(reviewed["extraction_hash"], repeated["extraction_hash"])
        self.assertEqual(422, self.operation(document, "review", {"accepted_rows": [], "extraction_hash": "stale", "confirm_scope": True})[0])
        self.assertEqual(422, self.operation(document, "review", {"accepted_rows": [], "extraction_hash": reviewed["extraction_hash"], "confirm_scope": True})[0])
        self.assertTrue(self.view()["sources_current"])
        self.activate(document)
        self.assertEqual(422, self.operation(document, "activate", {"expected_active_revision_id": None, "confirm_invalidation": True})[0])

    def test_failed_extraction_never_restores_fixture_evidence_for_active_candidate(self):
        self.login()
        _, document, _ = self.upload()
        self.activate(document)
        self.app.llm_settings = SETTINGS
        fabricated = rows("25")
        fabricated[0]["quote"] = "Bore diameter 25 mm invented text"
        self.app.llm_client = ScriptedClient([function_response("submitEvidence", {"rows": fabricated})])
        self.assertEqual(502, self.operation(document, "extract", {"consent_openai": True})[0])
        detail = self.request("GET", "/api/document-revisions/" + document["revision_id"])[1]
        self.assertEqual("EXTRACTION_FAILED", detail["status"])
        self.assertEqual("UNKNOWN", self.investigate()["current"]["candidate_comparisons"][0]["rows"][0]["status"])

    def test_corrupt_pdf_is_recorded_as_failed_and_does_not_pay(self):
        self.login()
        status, document, _ = self.upload(content=b"%PDF-1.4\nnot a PDF")
        self.assertEqual(201, status)
        self.assertEqual("TEXT_FAILED", document["status"])
        self.assertEqual([], document["pages"])
        self.app.llm_settings = SETTINGS
        self.app.llm_client = ScriptedClient([])
        self.assertEqual(422, self.operation(document, "extract", {"consent_openai": True})[0])
        self.assertEqual([], self.app.llm_client.requests)


class PDFValidationTests(unittest.TestCase):
    def test_all_twelve_corpus_files_are_read_from_pdf_bytes(self):
        for path in (ROOT / "data/documents").glob("*.pdf"):
            with self.subTest(path=path.name):
                self.assertTrue(all(parse_pdf(path.read_bytes())))

    def test_image_only_encrypted_oversized_and_invalid_pdfs_are_rejected(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        stream = io.BytesIO()
        writer.write(stream)
        with self.assertRaisesRegex(DocumentError, "PDF_NEEDS_OCR_OR_TEXT"):
            parse_pdf(stream.getvalue())
        writer.encrypt("test-only")
        stream = io.BytesIO()
        writer.write(stream)
        with self.assertRaisesRegex(DocumentError, "PDF_ENCRYPTED"):
            parse_pdf(stream.getvalue())
        for payload in (b"not pdf", b"%PDF-" + b"x" * (2 * 1024 * 1024)):
            with self.assertRaises(DocumentError):
                parse_pdf(payload)

    def test_provenance_scope_value_page_and_release_injection_are_rejected(self):
        pages = ["identity text", "Bore diameter | 25 mm | tolerance 0 / -0.010 mm", "Basic dynamic load rating | 16 kN"]
        self.assertEqual(2, len(validate_rows(rows(), pages)))
        for field, value in [("property", "PLANT_QUALIFICATION_RELEASE"), ("page", 99), ("value", "30"), ("value", "NaN"), ("applicability", "PLANT-A"), ("quote", "Bore diameter 25 mm fabricated")]:
            changed = deepcopy(rows())
            changed[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ModelError):
                validate_rows(changed, pages)

    def test_unseen_pdf_text_and_value_are_not_hardcoded_to_corpus(self):
        # Build-only pypdf helper makes a previously unseen supplier document.
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=600, height=400)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        contents = DecodedStreamObject()
        contents.set_data(b"BT /F1 12 Tf 40 350 Td (Unseen supplier CAND-C revision X - Bore diameter 27.5 mm) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(contents)
        buffer = io.BytesIO()
        writer.write(buffer)
        pages = parse_pdf(buffer.getvalue())
        proposal = rows("27.5")[:1]
        proposal[0].update(page=1, quote="Bore diameter 27.5 mm")
        self.assertEqual("27.5", validate_rows(proposal, pages)[0]["value"])


if __name__ == "__main__":
    unittest.main()
