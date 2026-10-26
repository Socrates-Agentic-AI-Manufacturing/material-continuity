"""Application use cases for the local, synthetic-data web MVP."""

from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac, sha256
import hmac
import json
from pathlib import Path
import secrets
import threading
import logging

from agents.recovery_supervisor import RecoverySupervisorRequest, run_recovery_workflow
from agents.recovery_supervisor.openai_review import run_openai_review
from core.actions import CreateQualificationTaskCommand, create_qualification_task
from core.approval import (
    ALLOWED_ACTIONS_BY_ROLE, ApprovalValidationRequest, ApproverRole,
    AuthenticatedPrincipal, ControlledAction, validate_approval,
)
from core.case_state import ApprovalRecord, RecoveryCaseUpdate, TriggerType, append_approval, update_case
from core.case_state.serialization import canonicalize
from core.qualification.models import TaskType
from core.requirements import CandidateDecision
from services.llm.openai import ModelError, OpenAIResponsesClient, OpenAISettings

from .store import Store
from .tools import WebFixtureTools
from services.documents.repository import DocumentRepository


DEMO_USERS = {
    "engineering": ApproverRole.ENGINEERING_REVIEWER,
    "quality": ApproverRole.QUALITY_ENGINEER,
    "planner": ApproverRole.PRODUCTION_PLANNER,
}


class ApplicationError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details
        super().__init__(message)


LOGGER = logging.getLogger(__name__)


class Application:
    def __init__(self, database: Path, fixture_root: Path, document_root: Path, *, demo_password="local-demo", llm_settings=None, llm_client=None):
        self.store = Store(database)
        self.document_repository = DocumentRepository(self.store)
        self.fixture_root, self.document_root = fixture_root, document_root
        # Opt in explicitly at launch; tests/default apps never discover keys or
        # make paid API calls merely because a key exists on the machine.
        self.llm_settings = llm_settings or OpenAISettings()
        self.llm_client = llm_client or OpenAIResponsesClient(self.llm_settings)
        self._llm_slot = threading.BoundedSemaphore(1)
        self.initialize(demo_password)

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    def tools(self, db=None):
        return WebFixtureTools(self.fixture_root, self.document_root, self.document_repository.active_state(db))

    def initialize(self, password):
        if not password:
            raise ValueError("demo password cannot be empty")
        with self.store.transaction() as db:
            for user_id, role in DEMO_USERS.items():
                salt = secrets.token_hex(16)
                password_hash = pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()
                db.execute(
                    "INSERT INTO users VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE "
                    "SET role=excluded.role, salt=excluded.salt, password_hash=excluded.password_hash",
                    (user_id, role.value, salt, password_hash),
                )
            if db.execute("SELECT 1 FROM cases WHERE case_id='CASE-001'").fetchone() is None:
                result = self.investigation("CASE-001", self.now(), db)
                self.store.save_case(db, result.case, json.dumps(canonicalize(result.tool_trace)))

    def investigation(self, case_id, created_at, db=None):
        return run_recovery_workflow(
            RecoverySupervisorRequest(
                case_id=case_id, event_id="EVT-DELAY-001",
                trigger_type=TriggerType.DELIVERY_DELAY, material_id="MAT-BRG-001",
                source_reference="purchase-order:PO-ORIGINAL-001",
                as_of=datetime(2026, 9, 29, tzinfo=timezone.utc),
                shortage_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
                created_at=created_at,
            ), tools=self.tools(db),
        )

    def login(self, user_id, password, old_token=None):
        with self.store.transaction() as db:
            row = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
            salt = bytes.fromhex(row["salt"]) if row else bytes(16)
            observed = pbkdf2_hmac("sha256", password.encode(), salt, 120_000).hex()
            if row is None or not hmac.compare_digest(observed, row["password_hash"]):
                raise ApplicationError(401, "INVALID_LOGIN", "Username atau password demo tidak sesuai.")
            if old_token:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (sha256(old_token.encode()).hexdigest(),))
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            expiry = self.now() + timedelta(hours=8)
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (self.now().isoformat(),))
            db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)", (sha256(token.encode()).hexdigest(), user_id, csrf, expiry.isoformat()))
            return token, {"user_id": user_id, "role": row["role"], "csrf_token": csrf, "expires_at": expiry.isoformat()}

    def session(self, token, csrf=None):
        if not token:
            raise ApplicationError(401, "LOGIN_REQUIRED", "Login dengan akun demo untuk melanjutkan.")
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT sessions.*, users.role FROM sessions JOIN users USING(user_id) WHERE token_hash=?",
                (sha256(token.encode()).hexdigest(),),
            ).fetchone()
        if row is None or datetime.fromisoformat(row["expires_at"]) <= self.now():
            raise ApplicationError(401, "SESSION_EXPIRED", "Session berakhir. Silakan login kembali.")
        if csrf is not None and not hmac.compare_digest(csrf, row["csrf_token"]):
            raise ApplicationError(403, "INVALID_CSRF", "Session request tidak sesuai. Muat ulang halaman.")
        return {"user_id": row["user_id"], "role": row["role"], "csrf_token": row["csrf_token"], "expires_at": row["expires_at"]}

    def logout(self, token):
        with self.store.transaction() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (sha256(token.encode()).hexdigest(),))

    @staticmethod
    def principal(session):
        return AuthenticatedPrincipal(session["user_id"], ApproverRole(session["role"]))

    def list_cases(self):
        with self.store.transaction() as db:
            cases = [self.store.get_case(db, row["case_id"]) for row in db.execute("SELECT case_id FROM cases ORDER BY case_id")]
        return [{
            "case_id": case.case_id, "case_version": case.current.case_version,
            "material_id": case.current.exposure.material_id, "status": case.current.status,
            "shortage_date": case.current.exposure.shortage_date,
            "exposed_quantity": case.current.simulation.baseline_exposed_quantity,
            "exposed_order_count": case.current.simulation.baseline_exposed_order_count,
            "updated_at": case.updated_at,
        } for case in cases]

    def joule_case(self, case_id="CASE-001"):
        """Return a redacted, read-only case briefing for Joule."""
        with self.store.transaction() as db:
            case = self.store.get_case(db, case_id)
            review_row = db.execute(
                "SELECT payload FROM ai_reviews WHERE case_id=? ORDER BY review_id DESC LIMIT 1",
                (case_id,),
            ).fetchone()
        return {
            "case_id": case.case_id,
            "case_version": case.current.case_version,
            "status": case.current.status,
            "material_id": case.current.exposure.material_id,
            "shortage_date": case.current.exposure.shortage_date,
            "exposed_quantity": case.current.simulation.baseline_exposed_quantity,
            "affected_order_count": case.current.simulation.baseline_exposed_order_count,
            "recovery_options": canonicalize(case.current.recovery_options),
            "latest_ai_review": json.loads(review_row["payload"]) if review_row else None,
            "approvals": canonicalize(case.approvals),
            "data_mode": "SYNTHETIC_FIXTURES",
        }

    def case_view(self, case_id, session):
        with self.store.transaction() as db:
            case = self.store.get_case(db, case_id)
            trace = json.loads(db.execute("SELECT trace FROM cases WHERE case_id=?", (case_id,)).fetchone()["trace"])
            tasks = [json.loads(row["payload"]) for row in db.execute("SELECT payload FROM tasks WHERE case_id=?", (case_id,))]
            scopes = {row["approval_id"]: dict(row) for row in db.execute("SELECT * FROM approval_scopes WHERE case_id=?", (case_id,))}
            review_row = db.execute("SELECT payload FROM ai_reviews WHERE case_id=? ORDER BY review_id DESC LIMIT 1", (case_id,)).fetchone()
        current_sources = self.tools().get_source_versions()
        sources_current = self.source_state(case.current.source_versions) == self.source_state(current_sources)
        latest_review = json.loads(review_row["payload"]) if review_row else None
        if latest_review:
            latest_review["is_current"] = sources_current and latest_review["case_hash"] == case.current.case_hash
        principal = self.principal(session)
        approvals = []
        for approval in case.approvals:
            scope = scopes[approval.approval_id]
            decision = validate_approval(case, ApprovalValidationRequest(
                approval_id=approval.approval_id, action=ControlledAction.CREATE_QUALIFICATION_TASK,
                principal=principal, evaluated_at=self.now(), current_source_versions=current_sources,
                idempotency_key=self.action_key(case, approval, scope),
            ))
            approvals.append({**canonicalize(approval), "scope": scope, "validation": canonicalize(decision)})
        return {
            "case": canonicalize(case), "current": canonicalize(case.current),
            "tool_trace": trace, "tasks": tasks, "approvals": approvals,
            "latest_ai_review": latest_review,
            "qualification_targets": self.qualification_targets(case),
            "sources_current": sources_current,
            "can_approve": ControlledAction.CREATE_QUALIFICATION_TASK in ALLOWED_ACTIONS_BY_ROLE[principal.role],
            "production_release_authorized": False,
            "data_mode": "SYNTHETIC_FIXTURES",
        }

    @staticmethod
    def source_state(sources):
        return {source.source_id: (source.source_type, source.version, source.content_hash) for source in sources}

    @staticmethod
    def check_snapshot(case, body):
        if body.get("case_version") != case.current.case_version or body.get("case_hash") != case.current.case_hash:
            raise ApplicationError(409, "STALE_REVIEW", "Kasus telah berubah. Muat ulang dan review versi terbaru sebelum melanjutkan.")

    def reinvestigate(self, case_id, body):
        with self.store.transaction() as db:
            case = self.store.get_case(db, case_id)
            self.check_snapshot(case, body)
            now = self.now()
            result = self.investigation(case_id, now, db)
            fresh = result.case.current
            updated = update_case(case, update=RecoveryCaseUpdate(
                exposure=fresh.exposure, recovery_options=fresh.recovery_options,
                candidate_comparisons=fresh.candidate_comparisons,
                qualification_graphs=fresh.qualification_graphs, simulation=fresh.simulation,
                source_versions=fresh.source_versions,
            ), change_reason="Web re-investigation of current local source data.", updated_at=now)
            self.store.save_case(db, updated.case, json.dumps(canonicalize(result.tool_trace)))
        return {"version_changed": updated.version_changed, "changed_source_ids": updated.changed_source_ids}

    def ai_review(self, case_id, body):
        """Explicit, potentially paid, read-only request against one snapshot.

        Do not hold a SQLite write lock while waiting for the provider. Recheck
        the case and source state afterwards; stale analysis is never returned
        as current. AI prose does not enter case hashes, approvals or receipts.
        """
        if not self._llm_slot.acquire(blocking=False):
            raise ApplicationError(429, "LLM_BUSY", "Review AI lain masih berjalan. Tunggu sampai selesai.")
        try:
            self.llm_settings.require_configured()
            with self.store.transaction() as db:
                case = self.store.get_case(db, case_id)
                self.check_snapshot(case, body)
                self.check_current_sources(case, db)
                version = case.current
            result = run_openai_review(version, self.llm_client)
            result["created_at"] = self.now().isoformat()
            with self.store.transaction() as db:
                current = self.store.get_case(db, case_id)
                self.check_snapshot(current, body)
                self.check_current_sources(current, db)
                # Advisory execution history lives separately from immutable
                # decision versions. Refresh/restart never requires a paid rerun.
                db.execute("INSERT INTO ai_reviews(case_id, payload) VALUES (?, ?)", (case_id, json.dumps(result)))
            result["is_current"] = True
            return result
        except ModelError as error:
            LOGGER.warning("AI review stopped: provider=%s code=%s", self.llm_settings.provider, error.code)
            messages = {
                "LLM_NOT_CONFIGURED": "Provider AI belum dikonfigurasi. Periksa provider, credential, dan model di backend.",
                "LLM_AUTH_FAILED": "Provider AI menolak credential. Periksa credential di backend; jangan kirim lewat chat.",
                "LLM_ACCESS_DENIED": "Akun/provider AI tidak memiliki akses model yang diminta.",
                "LLM_RATE_OR_QUOTA_LIMIT": "Batas permintaan atau kuota provider AI tercapai. Tidak ada retry otomatis.",
                "LLM_TIMEOUT": "Provider AI belum merespons dalam batas waktu. Review tidak disimpan.",
                "LLM_NETWORK_ERROR": "Backend tidak dapat terhubung ke provider AI. Periksa koneksi jaringan.",
            }
            status = 503 if error.code == "LLM_NOT_CONFIGURED" else 429 if error.code == "LLM_RATE_OR_QUOTA_LIMIT" else 504 if error.code == "LLM_TIMEOUT" else 502
            raise ApplicationError(status, error.code, messages.get(error.code, "Review AI dihentikan karena respons tidak valid atau batas investigasi tercapai. Kasus dan approval tidak diubah.")) from None
        finally:
            self._llm_slot.release()

    def check_current_sources(self, case, db=None):
        if self.source_state(case.current.source_versions) != self.source_state(self.tools(db).get_source_versions()):
            raise ApplicationError(409, "SOURCE_STATE_CHANGED", "Sumber berubah. Jalankan investigasi ulang sebelum review AI.")

    @staticmethod
    def qualification_targets(case):
        rejected = {item.candidate_id for item in case.current.candidate_comparisons if item.decision is CandidateDecision.REJECTED_HARD_MISMATCH}
        return [
            {"candidate_id": graph.candidate_id, "requirement_id": schedule.requirement_id, "task_name": schedule.name}
            for graph in case.current.qualification_graphs if graph.candidate_id not in rejected
            for schedule in graph.schedules if schedule.task_type is TaskType.TEST and schedule.requirement_id
        ]

    def approve(self, case_id, body, session):
        principal = self.principal(session)
        if ControlledAction.CREATE_QUALIFICATION_TASK not in ALLOWED_ACTIONS_BY_ROLE[principal.role]:
            raise ApplicationError(403, "ROLE_NOT_PERMITTED", "Role ini tidak dapat menyetujui qualification task.")
        with self.store.transaction() as db:
            case = self.store.get_case(db, case_id)
            self.check_snapshot(case, body)
            if self.source_state(case.current.source_versions) != self.source_state(self.tools(db).get_source_versions()):
                raise ApplicationError(409, "SOURCE_STATE_CHANGED", "Sumber berubah. Jalankan investigasi ulang sebelum approval.")
            target = next((item for item in self.qualification_targets(case) if item["candidate_id"] == body.get("candidate_id") and item["requirement_id"] == body.get("requirement_id")), None)
            if target is None:
                raise ApplicationError(422, "INVALID_QUALIFICATION_TARGET", "Kandidat atau requirement tidak memiliki qualification test yang berlaku.")
            now = self.now()
            approval = ApprovalRecord(
                approval_id="APR-" + secrets.token_hex(8).upper(), case_id=case_id,
                case_version=case.current.case_version, case_hash=case.current.case_hash,
                approver_id=principal.principal_id, approver_role=principal.role.value,
                permitted_action=ControlledAction.CREATE_QUALIFICATION_TASK.value,
                approved_at=now, expires_at=now + timedelta(hours=8),
            )
            case = append_approval(case, approval, updated_at=now)
            db.execute("INSERT INTO approval_scopes VALUES (?, ?, ?, ?, ?)", (approval.approval_id, case_id, target["candidate_id"], target["requirement_id"], target["task_name"]))
            self.store.update_case(db, case)
        return canonicalize(approval)

    @staticmethod
    def action_key(case, approval, scope):
        # A target can create at most one task per reviewed version, even if
        # multiple approvers issue separate approvals or requests run concurrently.
        return f"qualification:{case.case_id}:v{approval.case_version}:{scope['candidate_id']}:{scope['requirement_id']}"

    def execute(self, case_id, body, session):
        with self.store.transaction() as db:
            case = self.store.get_case(db, case_id)
            self.check_snapshot(case, body)
            scope = db.execute("SELECT * FROM approval_scopes WHERE approval_id=? AND case_id=?", (body.get("approval_id"), case_id)).fetchone()
            if scope is None:
                raise ApplicationError(404, "APPROVAL_NOT_FOUND", "Approval tidak ditemukan untuk kasus ini.")
            approval = next(item for item in case.approvals if item.approval_id == scope["approval_id"])
            key = self.action_key(case, approval, scope)
            result = create_qualification_task(case, CreateQualificationTaskCommand(
                candidate_id=scope["candidate_id"], requirement_id=scope["requirement_id"], task_name=scope["task_name"],
                approval=ApprovalValidationRequest(
                    approval_id=approval.approval_id, action=ControlledAction.CREATE_QUALIFICATION_TASK,
                    principal=self.principal(session), evaluated_at=self.now(),
                    current_source_versions=self.tools(db).get_source_versions(), idempotency_key=key,
                ),
            ))
            if not result.created:
                raise ApplicationError(409, "ACTION_BLOCKED", "Qualification task diblokir oleh pemeriksaan authorization.", {
                    "reasons": canonicalize(result.approval_decision.reasons),
                    "block_reasons": canonicalize(result.block_reasons),
                })
            db.execute("INSERT INTO tasks VALUES (?, ?, ?)", (case_id, key, json.dumps(canonicalize(result.task))))
            self.store.update_case(db, result.case)
        return {"task": canonicalize(result.task), "receipt": canonicalize(result.action_receipt), "production_release_authorized": False}

    def documents(self):
        manifest = json.loads((self.document_root / "manifest.json").read_text(encoding="utf-8"))
        corpus = [{**item, "checksum_valid": sha256((self.document_root / item["filename"]).read_bytes()).hexdigest() == item["sha256"]} for item in manifest["documents"]]
        return corpus + [{**item, "owner": "Uploader: " + item["uploaded_by"], "effective_date": None, "checksum_valid": True} for item in self.document_repository.listing()]

    def mutate_document(self, action, revision_id, body, session):
        if session["role"] not in (ApproverRole.ENGINEERING_REVIEWER.value, ApproverRole.QUALITY_ENGINEER.value):
            raise ApplicationError(403, "ROLE_NOT_PERMITTED", "Hanya Engineering atau Quality dapat mengubah dokumen bukti.")
        repository = self.document_repository
        if action == "upload":
            import base64
            content = base64.b64decode(body.get("content_base64", ""), validate=True)
            return repository.upload(body, content, session["user_id"])
        if action == "extract":
            if body.get("consent_openai") is not True:
                raise ApplicationError(422, "LLM_CONSENT_REQUIRED", "Konfirmasi pengiriman teks PDF ke OpenAI dan potensi biaya terlebih dahulu.")
            if not self._llm_slot.acquire(blocking=False):
                raise ApplicationError(429, "LLM_BUSY", "Permintaan AI lain masih berjalan.")
            try:
                self.llm_settings.require_configured()
                return repository.extract(revision_id, self.llm_client)
            except ModelError as error:
                raise ApplicationError(502, error.code, "Ekstraksi OpenAI gagal. Periksa konfigurasi/koneksi/kuota; tidak ada retry otomatis. Bukti lama tidak digantikan oleh output gagal.") from None
            finally:
                self._llm_slot.release()
        if action == "review":
            return repository.review(revision_id, body, session["user_id"])
        if action == "activate":
            return repository.activate(revision_id, body, session["user_id"])
        raise KeyError(action)
