"""
ATS intelligence pipeline.

Module order (leaves -> root):
    text_utils    -> tokenization, section detection
    normalizer    -> rule-based normalization (no alias maps)
    display       -> small branding exception layer + generic fallback
    categorizer   -> heuristic categorization with naming patterns
    extractor     -> contextual keyword/phrase extraction
    matcher       -> canonical-form matching
    scoring       -> section-aware ATS scoring
    pipeline      -> single public entrypoint that wires it all together

Persistent state lives in `backend.services.skill_registry` (SQLite). Nothing
in this package imports `scorer`, `app`, or `matcher` from `backend/` — the
intelligence layer is a leaf that the old modules delegate into.
"""
