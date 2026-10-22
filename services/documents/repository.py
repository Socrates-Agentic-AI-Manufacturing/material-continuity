"""Immutable PDF bytes/identity, mutable processing and explicit authority pointers."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import secrets

from .extraction import EXTRACTOR_VERSION, extract_evidence
from .parser import DocumentError, MAX_PDF_BYTES, PARSER_VERSION, parse_pdf


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class DocumentRepository:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def get(db, revision_id):
        row = db.execute("SELECT payload FROM document_revisions WHERE revision_id=?", (revision_id,)).fetchone()
        if row is None:
            raise KeyError(revision_id)
        return json.loads(row["payload"])

    @staticmethod
    def save(db, item):
        db.execute("UPDATE document_revisions SET payload=? WHERE revision_id=?", (json.dumps(item), item["revision_id"]))

    def listing(self):
        with self.store.transaction() as db:
            active = {row["revision_id"] for row in db.execute("SELECT revision_id FROM active_documents")}
            items = [json.loads(row["payload"]) for row in db.execute("SELECT payload FROM document_revisions ORDER BY rowid DESC")]
        return [{**{key: value for key, value in item.items() if key not in ("pages", "extraction")},
                 "active": item["revision_id"] in active, "page_count": len(item["pages"]),
                 "filename": item["revision_id"] + ".pdf"} for item in items]

    def detail(self, revision_id):
        with self.store.transaction() as db:
            item = self.get(db, revision_id)
            pointer = db.execute("SELECT revision_id FROM active_documents WHERE candidate_id=? AND document_id=?", (item["candidate_id"], item["document_id"])).fetchone()
        return {**item, "active_revision_id": pointer["revision_id"] if pointer else None}

    def upload(self, metadata, content, actor):
        for key in ("document_id", "revision"):
            if not isinstance(metadata.get(key), str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,60}", metadata[key]):
                raise DocumentError("INVALID_DOCUMENT_METADATA")
        if metadata.get("candidate_id") not in ("CAND-A", "CAND-B", "CAND-C"):
            raise DocumentError("INVALID_DOCUMENT_METADATA")
        name = metadata.get("filename")
        if not isinstance(name, str) or not re.fullmatch(r"[^\x00-\x1f/\\:]{1,140}\.pdf", name, re.I):
            raise DocumentError("INVALID_PDF_FILENAME")
        if not isinstance(content, bytes) or not content.startswith(b"%PDF-") or len(content) > MAX_PDF_BYTES:
            raise DocumentError("PDF_INVALID_OR_TOO_LARGE")
        checksum = sha256(content).hexdigest()
        with self.store.transaction() as db:
            existing = db.execute("SELECT revision_id, sha256 FROM document_revisions WHERE candidate_id=? AND document_id=? AND revision=?", (metadata["candidate_id"], metadata["document_id"], metadata["revision"])).fetchone()
            if existing:
                if existing["sha256"] != checksum:
                    raise DocumentError("REVISION_IMMUTABLE_USE_NEW_REVISION")
                return self.get(db, existing["revision_id"])
            quota = db.execute("SELECT COUNT(*), COALESCE(SUM(length(content)),0) FROM document_revisions").fetchone()
            if quota[0] >= 100 or quota[1] + len(content) > 20 * 1024 * 1024:
                raise DocumentError("LOCAL_DOCUMENT_QUOTA")
            item = {
                "revision_id": "PDF-" + secrets.token_hex(12), "candidate_id": metadata["candidate_id"],
                "document_id": metadata["document_id"], "revision": metadata["revision"],
                "original_name": name, "sha256": checksum, "uploaded_by": actor,
                "uploaded_at": self.now(), "status": "TEXT_PENDING", "error": None,
                "parser_version": PARSER_VERSION, "pages": [], "extraction": None,
                "reviewed_by": None, "accepted_rows": [],
            }
            db.execute("INSERT INTO document_revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                item["revision_id"], item["candidate_id"], item["document_id"], item["revision"],
                checksum, name, content, json.dumps(item),
            ))
        try:
            item["pages"] = parse_pdf(content)
            item["status"] = "TEXT_READY"
        except DocumentError as error:
            item.update(status="TEXT_FAILED", error=str(error))
        with self.store.transaction() as db:
            self.save(db, item)
        return item

    def extract(self, revision_id, client):
        item = self.detail(revision_id)
        if item["extraction"] is not None:
            return item  # Successful results are immutable; refresh/retry never pays again.
        if not item["pages"]:
            raise DocumentError("PDF_TEXT_NOT_READY")
        cache_key = digest({key: item[key] for key in ("sha256", "candidate_id", "document_id", "revision", "parser_version")} | {
            "extractor": EXTRACTOR_VERSION, "model": client.settings.model,
        })
        try:
            proposal = extract_evidence(item, client)
        except Exception as error:
            # Only safe application-owned codes are persisted, never upstream text.
            from services.llm.openai import ModelError
            code = error.code if isinstance(error, ModelError) else "LLM_INVALID_EVIDENCE"
            with self.store.transaction() as db:
                current = self.get(db, revision_id)
                current.update(status="EXTRACTION_FAILED", error=code)
                self.save(db, current)
            raise
        with self.store.transaction() as db:
            item = self.get(db, revision_id)
            item.update(status="AWAITING_REVIEW", error=None, extraction={
                **proposal, "cache_key": cache_key, "extractor_version": EXTRACTOR_VERSION,
                "created_at": self.now(),
            })
            item["extraction_hash"] = digest(item["extraction"])
            self.save(db, item)
        return item

    def review(self, revision_id, body, actor):
        with self.store.transaction() as db:
            item = self.get(db, revision_id)
            if item["extraction"] is None or body.get("extraction_hash") != item.get("extraction_hash"):
                raise DocumentError("STALE_EXTRACTION_REVIEW")
            if item["reviewed_by"]:
                raise DocumentError("EVIDENCE_REVIEW_IMMUTABLE")
            selected = body.get("accepted_rows")
            if not isinstance(selected, list) or len(selected) != len(set(selected)) or any(type(index) is not int or not 0 <= index < len(item["extraction"]["rows"]) for index in selected):
                raise DocumentError("INVALID_EVIDENCE_SELECTION")
            if body.get("confirm_scope") is not True:
                raise DocumentError("EVIDENCE_SCOPE_CONFIRMATION_REQUIRED")
            if any(item["extraction"]["rows"][index]["value"] is None for index in selected):
                raise DocumentError("MISSING_EVIDENCE_CANNOT_BE_ACCEPTED")
            item.update(reviewed_by=actor, reviewed_at=self.now(), accepted_rows=selected, status="REVIEWED")
            self.save(db, item)
        return item

    def activate(self, revision_id, body, actor):
        with self.store.transaction() as db:
            item = self.get(db, revision_id)
            previous = db.execute("SELECT revision_id FROM active_documents WHERE candidate_id=? AND document_id=?", (item["candidate_id"], item["document_id"])).fetchone()
            if "expected_active_revision_id" not in body or body["expected_active_revision_id"] != (previous["revision_id"] if previous else None):
                raise DocumentError("ACTIVE_REVISION_CHANGED")
            if body.get("confirm_invalidation") is not True:
                raise DocumentError("ACTIVATION_CONFIRMATION_REQUIRED")
            db.execute("INSERT INTO active_documents VALUES (?, ?, ?, ?, ?) ON CONFLICT(candidate_id,document_id) DO UPDATE SET revision_id=excluded.revision_id, activated_by=excluded.activated_by, activated_at=excluded.activated_at", (
                item["candidate_id"], item["document_id"], revision_id, actor, self.now(),
            ))
        return {"active_revision_id": revision_id, "reinvestigation_required": True}

    def active_state(self, db=None):
        if db is None:
            with self.store.transaction() as connection:
                return self.active_state(connection)
        return [json.loads(row["payload"]) for row in db.execute(
            "SELECT r.payload FROM document_revisions r JOIN active_documents a USING(revision_id) ORDER BY r.candidate_id, r.document_id"
        )]

    def content(self, revision_id):
        with self.store.transaction() as db:
            row = db.execute("SELECT content FROM document_revisions WHERE revision_id=?", (revision_id,)).fetchone()
            if row is None:
                raise KeyError(revision_id)
            return bytes(row["content"])
