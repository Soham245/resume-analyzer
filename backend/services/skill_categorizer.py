"""
Deprecated. Re-exports from `backend.intelligence.categorizer`.

The original heuristic categorizer lived here while the registry was being
scaffolded. The single source of truth is now
`backend.intelligence.categorizer`. This shim exists so older imports don't
break — new code should import the intelligence module directly.
"""

from backend.intelligence.categorizer import (  # noqa: F401
    categorize,
    categorize_with_confidence,
    DEFAULT_CATEGORY,
    CATEGORY_PROGRAMMING,
    CATEGORY_FRAMEWORKS,
    CATEGORY_DATABASES,
    CATEGORY_CLOUD,
    CATEGORY_AI_ML,
    CATEGORY_TOOLS,
    CATEGORY_SOFT,
    CATEGORY_LANGUAGES,
    CATEGORY_TECHNICAL,
)
