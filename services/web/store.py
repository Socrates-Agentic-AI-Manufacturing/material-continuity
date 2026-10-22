"""SQLite persistence with serial read/check/write transactions for case actions."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from . import codec


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY, payload TEXT NOT NULL, trace TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY, role TEXT NOT NULL,
                    salt TEXT NOT NULL, password_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                    csrf_token TEXT NOT NULL, expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approval_scopes (
                    approval_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL, requirement_id TEXT NOT NULL,
                    task_name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    case_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (case_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS ai_reviews (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ai_reviews_case ON ai_reviews(case_id, review_id DESC);
                CREATE TABLE IF NOT EXISTS document_revisions (
                    revision_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL,
                    document_id TEXT NOT NULL, revision TEXT NOT NULL,
                    sha256 TEXT NOT NULL, original_name TEXT NOT NULL,
                    content BLOB NOT NULL, payload TEXT NOT NULL,
                    UNIQUE(candidate_id, document_id, revision)
                );
                CREATE TABLE IF NOT EXISTS active_documents (
                    candidate_id TEXT NOT NULL, document_id TEXT NOT NULL,
                    revision_id TEXT NOT NULL, activated_by TEXT NOT NULL,
                    activated_at TEXT NOT NULL,
                    PRIMARY KEY(candidate_id, document_id)
                );
            """)

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def get_case(db, case_id):
        row = db.execute("SELECT payload FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(case_id)
        return codec.loads(row["payload"])

    @staticmethod
    def save_case(db, case, trace):
        db.execute(
            "INSERT INTO cases VALUES (?, ?, ?) ON CONFLICT(case_id) "
            "DO UPDATE SET payload=excluded.payload, trace=excluded.trace",
            (case.case_id, codec.dumps(case), trace),
        )

    @staticmethod
    def update_case(db, case):
        db.execute("UPDATE cases SET payload = ? WHERE case_id = ?", (codec.dumps(case), case.case_id))
