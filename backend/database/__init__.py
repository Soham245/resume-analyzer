"""Database package — SQLite-backed persistence for the skill registry."""

from . import connection, schema  # noqa: F401

__all__ = ["connection", "schema"]
