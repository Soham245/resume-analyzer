"""
Shared fixtures for backend tests.

Each test module gets a fresh on-disk SQLite registry under a temp dir so
tests can't pollute the developer's local skills.db.
"""
import os
import sys
import tempfile

# Ensure the repo root is on sys.path when running pytest from anywhere.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def configure_isolated_registry():
    """
    Point the registry connection at a fresh DB in a temp dir.

    Returns the temp DB path. Idempotent within a process — re-pointing
    swaps the active connection factory.
    """
    from backend.database import connection
    tmp = tempfile.mkdtemp(prefix="ats_test_")
    db_path = os.path.join(tmp, "skills.db")
    connection.configure(db_path)
    return db_path
