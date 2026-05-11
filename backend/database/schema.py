"""
SQLite schema for the skill registry.

A single normalized table (skills_registry) holds canonical skills along
with a JSON aliases column. A secondary index table (skill_aliases) keeps
alias -> canonical lookups O(1) without scanning the JSON.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)

SCHEMA_STATEMENTS = (
    # Canonical skill table.
    """
    CREATE TABLE IF NOT EXISTS skills_registry (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_name   TEXT    NOT NULL UNIQUE,
        display_name     TEXT    NOT NULL,
        category         TEXT    NOT NULL DEFAULT 'Technical Skills',
        aliases          TEXT    NOT NULL DEFAULT '[]',
        confidence_score REAL    NOT NULL DEFAULT 0.5,
        source           TEXT    NOT NULL DEFAULT 'inferred',
        first_seen_at    TEXT    NOT NULL DEFAULT (datetime('now')),
        last_seen_at     TEXT    NOT NULL DEFAULT (datetime('now')),
        usage_count      INTEGER NOT NULL DEFAULT 1
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_skills_category ON skills_registry(category)",
    "CREATE INDEX IF NOT EXISTS idx_skills_last_seen ON skills_registry(last_seen_at)",

    # Alias index table (fast alias -> canonical lookup).
    """
    CREATE TABLE IF NOT EXISTS skill_aliases (
        alias          TEXT NOT NULL PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        FOREIGN KEY (canonical_name) REFERENCES skills_registry(canonical_name)
            ON UPDATE CASCADE ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_aliases_canonical ON skill_aliases(canonical_name)",
)


def initialize(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they don't already exist. Idempotent."""
    cur = conn.cursor()
    try:
        for stmt in SCHEMA_STATEMENTS:
            cur.execute(stmt)
        conn.commit()
        logger.info("[skills_db] schema initialized")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
