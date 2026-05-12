"""
Deprecated. Re-exports from `backend.intelligence.normalizer`.

The original normalizer lived here while the registry was being scaffolded.
The single source of truth is now `backend.intelligence.normalizer`. This
shim exists so older imports don't break — new code should import the
intelligence module directly.
"""

from backend.intelligence.normalizer import normalize, normalize_many  # noqa: F401
