"""
Canonical-form matching.

Everything in this module operates on **normalized** skill keys. Raw text
is normalized once on entry; matching is then deterministic and cheap.

Three public helpers:

  scan_text(text, keys)        -> Counter  occurrences of each key in `text`
  match(resume_terms, jd_terms) -> MatchResult  matched + missing sets
  canonical_set(skills)         -> list of canonicals, de-duped

The "semantic" matching the spec asks for ("REST APIs ≈ RESTful APIs",
"ML ≈ Machine Learning") comes for free here:

  * `normalizer` collapses suffix/punctuation noise        (RESTful -> rest)
  * registry alias rows merge surface forms                (ml -> machine learning)
  * categorizer keeps unknown tech in matchable buckets    (Bun, Hono)

If the registry knows about a key it always wins. Otherwise the normalized
form itself is used as the canonical.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .normalizer import normalize

logger = logging.getLogger(__name__)

# Cheap word-boundary scan. Cached per key per process.
_PATTERN_CACHE: Dict[str, re.Pattern] = {}


def _word_pattern(key: str) -> re.Pattern:
    """
    Compile a word-boundary regex for a normalized key. We must allow the
    key's own internal punctuation ("c++", "c#", "node.js") so we don't
    bake an escape that fails to match.
    """
    cached = _PATTERN_CACHE.get(key)
    if cached is not None:
        return cached
    escaped = re.escape(key)
    # Loosen up: collapse multiple whitespace patterns so "c plus plus" matches
    # "c plus plus" with arbitrary whitespace. (Useful for normalized forms
    # that contain spaces.)
    escaped = escaped.replace(r"\ ", r"\s+")
    pat = re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)
    _PATTERN_CACHE[key] = pat
    return pat


def _registry_aliases(key: str) -> List[str]:
    """
    Return additional surface forms for `key` from the registry, if known.
    Read-only; never triggers a write.
    """
    try:
        from backend.services import skill_registry
        rec = skill_registry.lookup(key)
    except Exception as exc:
        logger.debug("[matcher] registry lookup failed for %r: %s", key, exc)
        return []
    if rec is None:
        return []
    return list(rec.aliases or ())


def scan_text(text: str, keys: Iterable[str]) -> Counter:
    """
    Count occurrences of each normalized key in `text`. Aliases from the
    registry (if present) are scanned too — they all credit the canonical key.
    """
    if not text:
        return Counter()
    text_lc = text  # patterns are IGNORECASE; no need to lowercase here
    counts: Counter = Counter()
    seen = set()
    for raw_key in keys or ():
        key = normalize(raw_key)
        if not key or key in seen:
            continue
        seen.add(key)

        forms = {key}
        for alias in _registry_aliases(key):
            alias_norm = normalize(alias)
            if alias_norm:
                forms.add(alias_norm)

        total = 0
        for form in forms:
            total += len(_word_pattern(form).findall(text_lc))
        if total > 0:
            counts[key] = total
    return counts


# ── Match results ───────────────────────────────────────────────────────────
@dataclass
class MatchResult:
    matched: List[str] = field(default_factory=list)   # canonical keys
    missing: List[str] = field(default_factory=list)   # canonical keys
    counts: Dict[str, int] = field(default_factory=dict)
    debug: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "matched": list(self.matched),
            "missing": list(self.missing),
            "counts": dict(self.counts),
        }


def match(
    resume_text: str,
    jd_keys: Iterable[str],
    *,
    jd_weights: Optional[Dict[str, float]] = None,
) -> MatchResult:
    """
    Match canonical `jd_keys` against `resume_text`. `jd_weights` (optional)
    is used to sort `missing` by importance descending.
    """
    keys = []
    seen = set()
    for raw in jd_keys or ():
        k = normalize(raw)
        if k and k not in seen:
            seen.add(k)
            keys.append(k)

    if not keys:
        return MatchResult(matched=[], missing=[], counts={}, debug={"reason": "no_jd_keys"})

    counts = scan_text(resume_text or "", keys)
    matched = [k for k in keys if counts.get(k, 0) > 0]
    missing = [k for k in keys if counts.get(k, 0) == 0]

    if jd_weights:
        missing.sort(key=lambda k: jd_weights.get(k, 0.0), reverse=True)

    logger.debug(
        "[matcher] matched=%d/%d missing_top=%s",
        len(matched), len(keys), missing[:5],
    )

    return MatchResult(
        matched=matched,
        missing=missing,
        counts=dict(counts),
        debug={"jd_size": len(keys)},
    )


def canonical_set(skills: Iterable[str]) -> List[str]:
    """De-dup + normalize a skill list. Preserves first-seen order."""
    seen = set()
    out: List[str] = []
    for s in skills or ():
        k = normalize(s)
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out
