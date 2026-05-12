"""
Persistent skill registry backed by SQLite.

The registry organically grows as new skills are observed in resumes and
job descriptions. The ATS layer (not yet refactored) is the future
consumer; this module is intentionally framework-free.

Public API
----------
    init()                 -- explicit (optional) schema bootstrap
    lookup(skill)          -- SkillRecord | None  (no writes)
    observe(skill, ...)    -- SkillRecord         (auto-learns if missing)
    observe_many(skills)   -- list[SkillRecord]
    get_canonical(skill)   -> str                 (convenience)
    get_display(skill)     -> str                 (convenience)
    stats()                -> dict                (size, top categories)

Design notes
------------
- `lookup()` is the hot path used during scoring; it is read-only and
  fully cached. `observe()` is the ingestion path that learns new skills
  and increments usage counters.
- Caching is per-process LRU keyed by the normalized lookup form. The
  cache is invalidated on any write that touches a given canonical row.
- Writes are serialized through a module-level lock to keep SQLite from
  returning SQLITE_BUSY under modest concurrency. SQLite's WAL mode (set
  by the connection layer) keeps reads from blocking writes.
- This module never imports the scorer / matcher / app. It is a leaf
  service so the upcoming ATS refactor can wire it in cleanly.
"""

import json
import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable, List, Optional

from backend.database import connection, schema
from backend.intelligence.categorizer import categorize, DEFAULT_CATEGORY
from backend.intelligence.display import format_display
from backend.intelligence.normalizer import normalize
from backend.services import registry_seeds

logger = logging.getLogger(__name__)


# ── Data shape ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SkillRecord:
    id: int
    canonical_name: str
    display_name: str
    category: str
    aliases: tuple
    confidence_score: float
    source: str
    first_seen_at: str
    last_seen_at: str
    usage_count: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "canonical_name": self.canonical_name,
            "display_name": self.display_name,
            "category": self.category,
            "aliases": list(self.aliases),
            "confidence_score": self.confidence_score,
            "source": self.source,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
            "usage_count": self.usage_count,
        }


# ── Module state ────────────────────────────────────────────────────────────
_initialized = False
_init_lock = threading.Lock()
_write_lock = threading.Lock()

_CACHE_MAX = 4096
_cache_lock = threading.Lock()
_cache: "OrderedDict[str, SkillRecord]" = OrderedDict()


# ── Initialization ──────────────────────────────────────────────────────────
def init() -> None:
    """Eagerly create the database and schema. Safe to call repeatedly."""
    _ensure_initialized()


def _ensure_initialized() -> None:
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        conn = connection.get_connection()
        schema.initialize(conn)
        registry_seeds.seed_defaults(conn)
        _initialized = True


# ── Cache ───────────────────────────────────────────────────────────────────
def _cache_get(key: str) -> Optional[SkillRecord]:
    with _cache_lock:
        rec = _cache.get(key)
        if rec is not None:
            _cache.move_to_end(key)
        return rec


def _cache_put(key: str, record: SkillRecord) -> None:
    if not key or record is None:
        return
    with _cache_lock:
        _cache[key] = record
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


def _cache_invalidate(canonical_name: Optional[str] = None) -> None:
    with _cache_lock:
        if canonical_name is None:
            _cache.clear()
            return
        for key in [k for k, v in _cache.items() if v.canonical_name == canonical_name]:
            _cache.pop(key, None)


# ── Helpers ─────────────────────────────────────────────────────────────────
# Display formatting now lives in `intelligence.display`. Re-export for any
# legacy callers that import from this module.
_smart_display = format_display


def _row_to_record(row) -> Optional[SkillRecord]:
    if row is None:
        return None
    try:
        aliases = tuple(json.loads(row["aliases"] or "[]"))
    except (ValueError, TypeError):
        aliases = ()
    return SkillRecord(
        id=row["id"],
        canonical_name=row["canonical_name"],
        display_name=row["display_name"],
        category=row["category"],
        aliases=aliases,
        confidence_score=float(row["confidence_score"]),
        source=row["source"],
        first_seen_at=row["first_seen_at"],
        last_seen_at=row["last_seen_at"],
        usage_count=int(row["usage_count"]),
    )


def _fetch_by_canonical(conn, canonical: str) -> Optional[SkillRecord]:
    row = conn.execute(
        "SELECT * FROM skills_registry WHERE canonical_name = ?",
        (canonical,),
    ).fetchone()
    return _row_to_record(row)


def _fetch_by_alias(conn, alias: str) -> Optional[SkillRecord]:
    row = conn.execute(
        """
        SELECT s.*
          FROM skill_aliases a
          JOIN skills_registry s ON s.canonical_name = a.canonical_name
         WHERE a.alias = ?
        """,
        (alias,),
    ).fetchone()
    return _row_to_record(row)


# ── Public read path ────────────────────────────────────────────────────────
def lookup(skill: str) -> Optional[SkillRecord]:
    """Return the SkillRecord for `skill` if known. Read-only."""
    _ensure_initialized()
    key = normalize(skill)
    if not key:
        return None

    cached = _cache_get(key)
    if cached is not None:
        return cached

    conn = connection.get_connection()
    record = _fetch_by_canonical(conn, key) or _fetch_by_alias(conn, key)
    if record is not None:
        _cache_put(key, record)
        if record.canonical_name != key:
            _cache_put(record.canonical_name, record)
    return record


# ── Public write path (auto-learning) ───────────────────────────────────────
def _insert_new(conn, canonical: str, raw_input: str, source: str) -> None:
    display = format_display(canonical)
    category = categorize(canonical) or DEFAULT_CATEGORY
    logger.debug("[skill_registry] new skill: key=%r display=%r category=%r source=%r",
                 canonical, display, category, source)
    initial_aliases = []
    raw_clean = (raw_input or "").strip()
    if raw_clean and raw_clean.lower() != canonical:
        initial_aliases.append(raw_clean)
    conn.execute(
        """
        INSERT INTO skills_registry
            (canonical_name, display_name, category, aliases, confidence_score, source)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (canonical, display, category, json.dumps(initial_aliases), 0.5, source),
    )
    if initial_aliases:
        conn.execute(
            "INSERT OR IGNORE INTO skill_aliases (alias, canonical_name) VALUES (?, ?)",
            (raw_clean, canonical),
        )


def _record_usage(conn, canonical: str, raw_input: str) -> None:
    conn.execute(
        """
        UPDATE skills_registry
           SET usage_count  = usage_count + 1,
               last_seen_at = datetime('now')
         WHERE canonical_name = ?
        """,
        (canonical,),
    )

    raw_clean = (raw_input or "").strip()
    if not raw_clean or raw_clean.lower() == canonical:
        return

    # Add the surface alias if we haven't seen it before.
    inserted = conn.execute(
        "INSERT OR IGNORE INTO skill_aliases (alias, canonical_name) VALUES (?, ?)",
        (raw_clean, canonical),
    ).rowcount

    if inserted:
        row = conn.execute(
            "SELECT aliases FROM skills_registry WHERE canonical_name = ?",
            (canonical,),
        ).fetchone()
        try:
            existing = json.loads(row["aliases"] or "[]") if row else []
        except (ValueError, TypeError):
            existing = []
        if raw_clean not in existing:
            existing.append(raw_clean)
            conn.execute(
                "UPDATE skills_registry SET aliases = ? WHERE canonical_name = ?",
                (json.dumps(existing), canonical),
            )


def observe(skill: str, *, source: str = "inferred",
            record_usage: bool = True) -> Optional[SkillRecord]:
    """
    Ingest `skill`. If known, increment its usage counter and refresh
    last_seen_at; if unknown, auto-create a registry entry with a
    heuristic category and a sensible default display form.

    Returns the updated SkillRecord (or None for unusable input).
    """
    _ensure_initialized()
    raw = (skill or "").strip()
    key = normalize(raw)
    if not key:
        return None

    conn = connection.get_connection()

    with _write_lock:
        existing = _fetch_by_canonical(conn, key) or _fetch_by_alias(conn, key)

        try:
            if existing is None:
                _insert_new(conn, key, raw, source)
                # Re-fetch so the returned record reflects DB defaults.
                existing = _fetch_by_canonical(conn, key)

            if existing is not None and record_usage:
                _record_usage(conn, existing.canonical_name, raw)

            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.warning("[skill_registry] observe(%r) failed: %s", raw, exc)
            # Best-effort: re-fetch what's actually in the DB.
            existing = _fetch_by_canonical(conn, key) or _fetch_by_alias(conn, key)
            if existing is None:
                return None

    # Refresh cache with the latest row.
    fresh = _fetch_by_canonical(conn, existing.canonical_name)
    if fresh is not None:
        _cache_invalidate(fresh.canonical_name)
        _cache_put(key, fresh)
        if raw and raw.lower() != key:
            _cache_put(raw.lower(), fresh)
        _cache_put(fresh.canonical_name, fresh)
    return fresh


def observe_many(skills: Iterable[str], *, source: str = "inferred") -> List[SkillRecord]:
    out: List[SkillRecord] = []
    for skill in skills or ():
        rec = observe(skill, source=source)
        if rec is not None:
            out.append(rec)
    return out


# ── Convenience wrappers ────────────────────────────────────────────────────
def get_canonical(skill: str) -> str:
    rec = lookup(skill)
    return rec.canonical_name if rec else normalize(skill)


def get_display(skill: str) -> str:
    rec = lookup(skill)
    return rec.display_name if rec else format_display(normalize(skill))


# ── Diagnostics ─────────────────────────────────────────────────────────────
def stats() -> dict:
    """Lightweight registry stats. For debug/admin only."""
    _ensure_initialized()
    conn = connection.get_connection()
    total = conn.execute("SELECT COUNT(*) AS n FROM skills_registry").fetchone()["n"]
    by_cat = conn.execute(
        "SELECT category, COUNT(*) AS n "
        "FROM skills_registry "
        "GROUP BY category "
        "ORDER BY n DESC"
    ).fetchall()
    return {
        "total_skills": total,
        "by_category": {row["category"]: row["n"] for row in by_cat},
        "cache_size": len(_cache),
    }
