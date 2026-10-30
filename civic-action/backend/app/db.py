import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config as C

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tracking_code TEXT UNIQUE NOT NULL,
  text TEXT NOT NULL,
  image_path TEXT,
  user_category TEXT,
  lat REAL NOT NULL, lng REAL NOT NULL, address TEXT, ward TEXT,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'Submitted',
  assignee TEXT,
  category TEXT, summary TEXT, signals TEXT, ai_mode TEXT,
  priority_score INTEGER DEFAULT 0, priority_band TEXT DEFAULT 'Low', reasons TEXT DEFAULT '[]',
  duplicate_of INTEGER REFERENCES reports(id), duplicate_score REAL,
  cluster_id INTEGER,
  citizen_session TEXT
);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_dup ON reports(duplicate_of);
CREATE TABLE IF NOT EXISTS clusters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  centroid_lat REAL, centroid_lng REAL, radius_m REAL, report_count INTEGER,
  categories TEXT, ward TEXT, member_key TEXT, brief TEXT, ai_mode TEXT
);
CREATE TABLE IF NOT EXISTS status_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id INTEGER NOT NULL REFERENCES reports(id),
  status TEXT NOT NULL, note TEXT, assignee TEXT, at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_report ON status_events(report_id);
"""

JSON_FIELDS = ("signals", "reasons", "categories")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    C.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(C.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        # Migrate existing database if column not present
        cols = [r[1] for r in conn.execute("PRAGMA table_info(reports)").fetchall()]
        if "citizen_session" not in cols:
            conn.execute("ALTER TABLE reports ADD COLUMN citizen_session TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_session ON reports(citizen_session)")


def reset_db() -> None:
    with connect() as conn:
        conn.executescript("DROP TABLE IF EXISTS status_events; DROP TABLE IF EXISTS clusters; DROP TABLE IF EXISTS reports;")
        conn.executescript(SCHEMA)


def row(r: sqlite3.Row | None) -> dict | None:
    """sqlite row -> dict with JSON columns decoded."""
    if r is None:
        return None
    d = dict(r)
    for k in JSON_FIELDS:
        if k in d and isinstance(d[k], str):
            d[k] = json.loads(d[k])
    return d


def add_event(conn, report_id: int, status: str, note: str | None = None, assignee: str | None = None, at: str | None = None):
    conn.execute(
        "INSERT INTO status_events(report_id,status,note,assignee,at) VALUES(?,?,?,?,?)",
        (report_id, status, note, assignee, at or now_iso()),
    )
