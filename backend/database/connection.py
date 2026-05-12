"""
SQLite connection management.

Each thread gets its own sqlite3 connection (thread-local), but every
connection points to the same on-disk database file. WAL mode is enabled
so reads do not block writes.

Public API:
    configure(db_path)   -- override the default path (tests, deployments)
    get_connection()     -- get the connection for the current thread
    default_db_path()    -- resolve the default SQLite file path
    close_current()      -- close the current thread's connection (tests)
"""

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def default_db_path() -> Path:
    """Resolve the default DB path: backend/database/skills.db."""
    return Path(__file__).resolve().parent / "skills.db"


class _ConnectionFactory:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._local = threading.local()

    def _open(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
            timeout=10,
            isolation_level="DEFERRED",
        )
        conn.row_factory = sqlite3.Row
        # Pragmas: enable WAL for concurrent reads, FK enforcement, sane sync.
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        return conn

    def get(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._open()
            self._local.conn = conn
        return conn

    def close_current(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None


_factory: Optional[_ConnectionFactory] = None
_factory_lock = threading.Lock()


def configure(db_path: Optional[Path] = None) -> None:
    """(Re)configure the connection factory. Idempotent."""
    global _factory
    target = Path(db_path) if db_path else default_db_path()
    with _factory_lock:
        if _factory is not None and _factory.db_path == target:
            return
        if _factory is not None:
            _factory.close_current()
        _factory = _ConnectionFactory(target)
        logger.info("[skills_db] configured at %s", target)


def get_connection() -> sqlite3.Connection:
    global _factory
    if _factory is None:
        configure()
    return _factory.get()


def close_current() -> None:
    global _factory
    if _factory is not None:
        _factory.close_current()


def current_db_path() -> Optional[Path]:
    """Return the currently configured DB path, or None if not yet configured."""
    return _factory.db_path if _factory is not None else None
