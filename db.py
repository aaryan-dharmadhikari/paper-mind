import json
import sqlite3
from datetime import datetime, timezone
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '[]',
    abstract TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    raw_text TEXT NOT NULL DEFAULT '',
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS paper_concepts (
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    concept_id INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    PRIMARY KEY (paper_id, concept_id)
);

CREATE TABLE IF NOT EXISTS concept_links (
    concept_a INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    concept_b INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (concept_a, concept_b)
);

CREATE TABLE IF NOT EXISTS user_knowledge (
    concept_id INTEGER PRIMARY KEY REFERENCES concepts(id) ON DELETE CASCADE,
    confidence REAL NOT NULL DEFAULT 0.0,
    last_tested TEXT
);

CREATE TABLE IF NOT EXISTS user_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    takeaway TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    agent_type TEXT NOT NULL CHECK(agent_type IN ('teach', 'zealot')),
    messages_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with _conn() as conn:
        conn.executescript(SCHEMA)
        # Migrations
        cols = {r[1] for r in conn.execute("PRAGMA table_info(papers)").fetchall()}
        if "self_rating" not in cols:
            conn.execute("ALTER TABLE papers ADD COLUMN self_rating REAL")


# ── Papers ──────────────────────────────────────────────────────────────

def insert_paper(title: str, authors: list[str], abstract: str, summary: str,
                 source_url: str, raw_text: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO papers (title, authors, abstract, summary, source_url, raw_text, added_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, json.dumps(authors), abstract, summary, source_url, raw_text, now),
        )
        return cur.lastrowid


def get_paper(paper_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["authors"] = json.loads(d["authors"])
    return d


def get_paper_by_filename(filename: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE source_url = ?", (filename,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["authors"] = json.loads(d["authors"])
    return d


def get_paper_by_title(title: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE LOWER(title) = LOWER(?)", (title,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["authors"] = json.loads(d["authors"])
    return d


def update_paper_title(paper_id: int, title: str):
    with _conn() as conn:
        conn.execute("UPDATE papers SET title = ? WHERE id = ?", (title, paper_id))


def delete_paper(paper_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM paper_concepts WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM user_notes WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM chat_history WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        conn.execute("""
            DELETE FROM concepts WHERE id NOT IN (
                SELECT DISTINCT concept_id FROM paper_concepts
            )
        """)


def update_paper_summary(paper_id: int, summary: str):
    with _conn() as conn:
        conn.execute("UPDATE papers SET summary = ? WHERE id = ?", (summary, paper_id))


def update_paper_self_rating(paper_id: int, rating: float):
    with _conn() as conn:
        conn.execute("UPDATE papers SET self_rating = ? WHERE id = ?",
                     (max(0.0, min(1.0, rating)), paper_id))


def list_papers() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT id, title, authors, abstract, summary, self_rating, added_at FROM papers ORDER BY added_at DESC").fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["authors"] = json.loads(d["authors"])
        results.append(d)
    return results


# ── Concepts ────────────────────────────────────────────────────────────

def upsert_concept(name: str, description: str = "") -> int:
    normalized = name.strip().lower()
    with _conn() as conn:
        row = conn.execute("SELECT id FROM concepts WHERE name = ?", (normalized,)).fetchone()
        if row:
            if description:
                conn.execute("UPDATE concepts SET description = ? WHERE id = ?", (description, row["id"]))
            return row["id"]
        cur = conn.execute("INSERT INTO concepts (name, description) VALUES (?, ?)", (normalized, description))
        return cur.lastrowid


def get_concept(concept_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,)).fetchone()
    return dict(row) if row else None


def list_concepts() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM concepts ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_concepts_for_paper(paper_id: int) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT c.* FROM concepts c "
            "JOIN paper_concepts pc ON c.id = pc.concept_id "
            "WHERE pc.paper_id = ? ORDER BY c.name",
            (paper_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Paper-Concept links ────────────────────────────────────────────────

def link_paper_concept(paper_id: int, concept_id: int):
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO paper_concepts (paper_id, concept_id) VALUES (?, ?)",
            (paper_id, concept_id),
        )


# ── Concept Links ──────────────────────────────────────────────────────

def upsert_concept_link(concept_a_id: int, concept_b_id: int, relationship: str = ""):
    a, b = sorted([concept_a_id, concept_b_id])
    with _conn() as conn:
        conn.execute(
            "INSERT INTO concept_links (concept_a, concept_b, relationship) VALUES (?, ?, ?) "
            "ON CONFLICT(concept_a, concept_b) DO UPDATE SET relationship = excluded.relationship",
            (a, b, relationship),
        )


def get_all_concept_links() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT cl.*, ca.name AS name_a, cb.name AS name_b "
            "FROM concept_links cl "
            "JOIN concepts ca ON cl.concept_a = ca.id "
            "JOIN concepts cb ON cl.concept_b = cb.id"
        ).fetchall()
    return [dict(r) for r in rows]


# ── User Knowledge ─────────────────────────────────────────────────────

def get_user_knowledge() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT uk.*, c.name, c.description FROM user_knowledge uk "
            "JOIN concepts c ON uk.concept_id = c.id "
            "ORDER BY uk.confidence ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_user_knowledge(concept_id: int, confidence: float):
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO user_knowledge (concept_id, confidence, last_tested) VALUES (?, ?, ?) "
            "ON CONFLICT(concept_id) DO UPDATE SET confidence = excluded.confidence, last_tested = excluded.last_tested",
            (concept_id, max(0.0, min(1.0, confidence)), now),
        )


# ── User Notes ──────────────────────────────────────────────────────────

def add_note(paper_id: int, takeaway: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO user_notes (paper_id, takeaway, created_at) VALUES (?, ?, ?)",
            (paper_id, takeaway, now),
        )
        return cur.lastrowid


def get_notes_for_paper(paper_id: int) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM user_notes WHERE paper_id = ? ORDER BY created_at DESC",
            (paper_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Chat History ────────────────────────────────────────────────────────

def create_chat(paper_id: int, agent_type: str = "teach") -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO chat_history (paper_id, agent_type, messages_json, created_at) VALUES (?, ?, '[]', ?)",
            (paper_id, agent_type, now),
        )
        return cur.lastrowid


def get_or_create_chat_for_paper(paper_id: int) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM chat_history WHERE paper_id = ? ORDER BY created_at DESC LIMIT 1",
            (paper_id,),
        ).fetchone()
    if row:
        return row["id"]
    return create_chat(paper_id)


def get_chat(chat_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM chat_history WHERE id = ?", (chat_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["messages_json"] = json.loads(d["messages_json"])
    return d


def update_chat_messages(chat_id: int, messages: list[dict]):
    with _conn() as conn:
        conn.execute(
            "UPDATE chat_history SET messages_json = ? WHERE id = ?",
            (json.dumps(messages), chat_id),
        )


def list_chats(paper_id: int | None = None, limit: int = 20) -> list[dict]:
    with _conn() as conn:
        if paper_id is not None:
            rows = conn.execute(
                "SELECT ch.id, ch.paper_id, ch.agent_type, ch.created_at, p.title AS paper_title "
                "FROM chat_history ch JOIN papers p ON ch.paper_id = p.id "
                "WHERE ch.paper_id = ? ORDER BY ch.created_at DESC LIMIT ?",
                (paper_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ch.id, ch.paper_id, ch.agent_type, ch.created_at, p.title AS paper_title "
                "FROM chat_history ch JOIN papers p ON ch.paper_id = p.id "
                "ORDER BY ch.created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


# ── Maintenance ─────────────────────────────────────────────────────────

def prune_duplicate_papers():
    """Delete duplicate papers by source_url, keeping the latest entry."""
    with _conn() as conn:
        # Find duplicates by filename (source_url), keep max(id) for each
        dupes = conn.execute("""
            SELECT id FROM papers
            WHERE source_url != ''
              AND id NOT IN (
                SELECT MAX(id) FROM papers
                WHERE source_url != ''
                GROUP BY source_url
              )
        """).fetchall()
        ids = [r["id"] for r in dupes]
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM paper_concepts WHERE paper_id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM user_notes WHERE paper_id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM chat_history WHERE paper_id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM papers WHERE id IN ({placeholders})", ids)
        # Clean up orphaned concepts
        conn.execute("""
            DELETE FROM concepts WHERE id NOT IN (
                SELECT DISTINCT concept_id FROM paper_concepts
            )
        """)
        return len(ids)


# ── Stats ───────────────────────────────────────────────────────────────

def get_stats() -> dict:
    with _conn() as conn:
        paper_count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        concept_count = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        chat_count = conn.execute("SELECT COUNT(*) FROM chat_history").fetchone()[0]
        avg_confidence = conn.execute("SELECT AVG(confidence) FROM user_knowledge").fetchone()[0]
    return {
        "paper_count": paper_count,
        "concept_count": concept_count,
        "chat_count": chat_count,
        "avg_confidence": avg_confidence or 0.0,
    }
