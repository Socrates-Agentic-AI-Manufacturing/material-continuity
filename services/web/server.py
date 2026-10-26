"""Same-origin local HTTP API and static web host for synthetic review workflows."""

from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import base64
from pathlib import Path
from urllib.parse import unquote, urlsplit

from core.case_state.serialization import canonicalize

from .application import ApplicationError
from services.documents.parser import DocumentError


LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "apps" / "web"
MAX_BODY = 16_384


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, app, web_root=WEB_ROOT, allowed_hosts=()):
        if address[0] not in ("127.0.0.1", "localhost", "0.0.0.0"):
            raise ValueError("unsupported bind address")
        self.app, self.web_root = app, web_root
        self.allowed_hosts = set(allowed_hosts)
        super().__init__(address, ReviewHandler)


class ReviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def log_message(self, format, *args):
        # No request bodies, passwords, cookies, or tokens enter access logs.
        LOGGER.info("%s %s", self.command, urlsplit(self.path).path)

    def handle_request(self, mutation):
        try:
            self.check_origin()
            self.route(mutation)
        except ApplicationError as error:
            self.json_response(error.status, {"error": {"code": error.code, "message": error.message, "details": error.details}})
        except DocumentError as error:
            self.json_response(422, {"error": {"code": str(error), "message": "Dokumen belum dapat diproses: " + str(error) + ". Periksa PDF/revisi dan muat ulang detail."}})
        except KeyError:
            self.json_response(404, {"error": {"code": "NOT_FOUND", "message": "Kasus atau resource tidak ditemukan."}})
        except (ValueError, TypeError):
            self.json_response(422, {"error": {"code": "INVALID_INPUT", "message": "Data request tidak valid. Periksa field dan muat ulang kasus."}})
        except Exception:
            LOGGER.exception("Web request failed")
            self.json_response(500, {"error": {"code": "INTERNAL_ERROR", "message": "Request gagal. Periksa log server dan sumber data, lalu coba kembali."}})

    def check_origin(self):
        port = self.server.server_port
        allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"} | self.server.allowed_hosts
        host = self.headers.get("Host", "")
        if host not in allowed_hosts:
            raise ApplicationError(403, "INVALID_HOST", "Host aplikasi belum dikonfigurasi untuk deployment ini.")
        origin = self.headers.get("Origin")
        allowed_origins = {f"http://{host}", f"https://{host}"}
        if origin and origin not in allowed_origins:
            raise ApplicationError(403, "INVALID_ORIGIN", "Request lintas origin tidak diperbolehkan.")

    def token(self):
        cookie = SimpleCookie()
        cookie.load(self.headers.get("Cookie", ""))
        return cookie["mc_session"].value if "mc_session" in cookie else ""

    def body(self, allowed, maximum=MAX_BODY):
        if self.headers.get_content_type() != "application/json":
            raise ApplicationError(415, "JSON_REQUIRED", "Request harus berupa JSON.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ApplicationError(400, "INVALID_LENGTH", "Ukuran request tidak valid.") from None
        if not 0 < length <= maximum:
            raise ApplicationError(413, "INVALID_BODY_SIZE", "Request kosong atau melebihi batas ukuran yang diizinkan.")
        try:
            value = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            raise ApplicationError(400, "INVALID_JSON", "JSON request tidak valid.") from None
        if not isinstance(value, dict) or set(value) - set(allowed):
            raise ApplicationError(422, "UNEXPECTED_FIELDS", "Request mengandung field yang tidak didukung.")
        return value

    def route(self, mutation):
        path = unquote(urlsplit(self.path).path)
        app = self.server.app
        if not mutation and path == "/api/health":
            self.json_response(200, {"status": "ok", "mode": "local-synthetic", "llm_configured": app.llm_settings.status()["configured"]})
            return
        if not mutation and path == "/api/joule/exposure":
            expected_user = os.environ.get("MATERIAL_CONTINUITY_JOULE_USER", "")
            expected_password = os.environ.get("MATERIAL_CONTINUITY_JOULE_PASSWORD", "")
            expected = "Basic " + base64.b64encode(f"{expected_user}:{expected_password}".encode()).decode()
            if not expected_user or not expected_password or self.headers.get("Authorization", "") != expected:
                self.send_response(401)
                self.send_header("WWW-Authenticate", "Basic realm=material-continuity")
                self.end_headers()
                return
            cases = app.list_cases()
            first_case = cases[0] if cases else {}
            self.json_response(200, {
                "cases": cases,
                "case_count": len(cases),
                "has_active_case": bool(cases),
                "case_id": first_case.get("case_id"),
                "material_id": first_case.get("material_id"),
                "shortage_date": first_case.get("shortage_date"),
                "exposed_quantity": first_case.get("exposed_quantity"),
                "affected_order_count": first_case.get("exposed_order_count"),
                "source": "local-synthetic",
                "message": "No active material exposure cases." if not cases else "Active material exposure cases available.",
            })
            return
        if not mutation and path.startswith("/api/joule/case"):
            expected_user = os.environ.get("MATERIAL_CONTINUITY_JOULE_USER", "")
            expected_password = os.environ.get("MATERIAL_CONTINUITY_JOULE_PASSWORD", "")
            expected = "Basic " + base64.b64encode(f"{expected_user}:{expected_password}".encode()).decode()
            if not expected_user or not expected_password or self.headers.get("Authorization", "") != expected:
                self.send_response(401); self.send_header("WWW-Authenticate", "Basic realm=material-continuity"); self.end_headers(); return
            case_id = unquote(path.rsplit("/", 1)[-1]) if path.count("/") > 3 else "CASE-001"
            self.json_response(200, app.joule_case(case_id))
            return
        if mutation and path == "/api/login":
            body = self.body(("username", "password"))
            if not all(isinstance(body.get(name), str) for name in ("username", "password")):
                raise ApplicationError(422, "INVALID_LOGIN_INPUT", "Isi username dan password.")
            token, session = app.login(body["username"], body["password"], self.token())
            self.json_response(200, session, cookie=f"mc_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800")
            return
        if path.startswith("/api/") or path.startswith("/documents/"):
            session = app.session(self.token(), self.headers.get("X-CSRF-Token", "") if mutation else None)
        else:
            session = None
        if not mutation:
            if path == "/api/session":
                self.json_response(200, session)
            elif path == "/api/llm/status":
                self.json_response(200, app.llm_settings.status())
            elif path == "/api/cases":
                self.json_response(200, {"cases": app.list_cases()})
            elif path == "/api/documents":
                self.json_response(200, {"documents": app.documents(), "revisions": app.document_repository.listing(), "mode": "synthetic-enterprise-data", "upload_available": True})
            elif path.startswith("/api/document-revisions/"):
                revision_id = path.removeprefix("/api/document-revisions/")
                self.json_response(200, app.document_repository.detail(revision_id))
            elif path.startswith("/api/cases/"):
                parts = path.strip("/").split("/")
                if len(parts) not in (3, 4):
                    raise ApplicationError(404, "NOT_FOUND", "Route tidak ditemukan.")
                view = app.case_view(parts[2], session)
                if len(parts) == 3:
                    response = view
                elif parts[3] == "evidence":
                    response = {"candidate_comparisons": view["current"]["candidate_comparisons"]}
                elif parts[3] == "scenarios":
                    response = view["current"]["simulation"]
                else:
                    raise ApplicationError(404, "NOT_FOUND", "Route tidak ditemukan.")
                self.json_response(200, response)
            elif path.startswith("/documents/"):
                name = path.removeprefix("/documents/")
                if name.startswith("PDF-") and name.endswith(".pdf") and "/" not in name:
                    payload = app.document_repository.content(name[:-4])
                    self.response_headers(200, "application/pdf", len(payload))
                    self.wfile.write(payload)
                    return
                known = {row["filename"] for row in app.documents()}
                if name not in known:
                    raise ApplicationError(404, "DOCUMENT_NOT_FOUND", "Dokumen tidak ditemukan.")
                self.file_response(app.document_root / name, "application/pdf")
            elif path in ("/", "/index.html", "/app.js", "/workflow.js", "/style.css"):
                name = "index.html" if path == "/" else path[1:]
                mime = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8", "workflow.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}[name]
                self.file_response(self.server.web_root / name, mime)
            else:
                raise ApplicationError(404, "NOT_FOUND", "Route tidak ditemukan.")
            return
        if path == "/api/logout":
            self.body(())
            app.logout(self.token())
            self.json_response(200, {"logged_out": True}, cookie="mc_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
            return
        if path == "/api/documents":
            result = app.mutate_document("upload", None, self.body(("candidate_id", "document_id", "revision", "filename", "content_base64"), 2_900_000), session)
            self.json_response(201, result)
            return
        if path.startswith("/api/document-revisions/"):
            parts = path.strip("/").split("/")
            if len(parts) != 4:
                raise KeyError(path)
            allowed = {"extract": ("consent_openai",), "review": ("extraction_hash", "accepted_rows", "confirm_scope"), "activate": ("expected_active_revision_id", "confirm_invalidation")}
            if parts[3] not in allowed:
                raise KeyError(path)
            result = app.mutate_document(parts[3], parts[2], self.body(allowed[parts[3]]), session)
            self.json_response(200, result)
            return
        parts = path.strip("/").split("/")
        if len(parts) != 4 or parts[:2] != ["api", "cases"]:
            raise ApplicationError(404, "NOT_FOUND", "Route tidak ditemukan.")
        case_id, action = parts[2:]
        if action == "investigate":
            result = app.reinvestigate(case_id, self.body(("case_version", "case_hash")))
            self.json_response(200, result)
        elif action == "ai-review":
            result = app.ai_review(case_id, self.body(("case_version", "case_hash")))
            self.json_response(200, result)
        elif action == "approvals":
            result = app.approve(case_id, self.body(("case_version", "case_hash", "candidate_id", "requirement_id")), session)
            self.json_response(201, result)
        elif action == "qualification-tasks":
            result = app.execute(case_id, self.body(("case_version", "case_hash", "approval_id")), session)
            self.json_response(201, result)
        else:
            raise ApplicationError(404, "NOT_FOUND", "Route tidak ditemukan.")

    def response_headers(self, status, content_type, length, cookie=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def json_response(self, status, value, cookie=None):
        payload = json.dumps(canonicalize(value), ensure_ascii=False).encode("utf-8")
        self.response_headers(status, "application/json; charset=utf-8", len(payload), cookie)
        self.wfile.write(payload)

    def file_response(self, path, content_type):
        payload = path.read_bytes()
        self.response_headers(200, content_type, len(payload))
        self.wfile.write(payload)
