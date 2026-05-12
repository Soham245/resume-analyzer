"""
Rule-based skill normalization.

This module is intentionally *generic*. It does not know that "reactjs" is
React, or that "k8s" is Kubernetes — those are facts that live in the
registry's alias table (auto-learned over time) and, for branding
edge-cases, in `display.py`.

What this module does know:

  * lowercase, trim, collapse whitespace and punctuation
  * collapse runs of separators ("/", "-", "_") to single spaces
  * normalize repeated dots
  * strip JS-ecosystem ".js" / "js" suffixes that vary in spelling
    (ReactJS, react.js, react js, react-js -> "react")
  * strip plural / version noise that does not change identity
    (REST APIs -> "rest api", Python3 -> "python", C++17 -> "c++")

The output is a *lookup key*, not a display form. Two different surface
forms of the same skill must produce the same key, and the key must be
stable so the registry can use it as a primary key.

The function is pure and side-effect free, with a small LRU cache because
the same surface forms appear many times per request.
"""

import logging
import re
from functools import lru_cache

logger = logging.getLogger(__name__)

# ── Step 1: peel outer junk ──────────────────────────────────────────────────
_OUTER_PUNCT = re.compile(r"^[\s\-_/,.;:|()\[\]{}]+|[\s\-_/,.;:|()\[\]{}]+$")
_COLLAPSE_WS = re.compile(r"\s+")

# ── Step 2: separator + punctuation rules ────────────────────────────────────
_COLLAPSE_SEP = re.compile(r"[\s/_]+")    # whitespace / slash / underscore -> single space
_DASH_BETWEEN_WORDS = re.compile(r"(?<=[A-Za-z0-9])-(?=[A-Za-z0-9])")
_DUP_DOTS = re.compile(r"\.{2,}")

# ── Step 3: suffix rules ─────────────────────────────────────────────────────
# JS-ecosystem suffix: matches "JS", ".JS", or " JS" at the end. Guard the
# minimum length so the bare token "js" doesn't collapse.
_JS_SUFFIX = re.compile(r"(?:\s*\.|\s+|(?<=[a-z]))js$", re.IGNORECASE)

# Plural "s" on multi-word phrases ending in "api" / "apis"
_API_PLURAL = re.compile(r"\bapis\b")

# Version noise: trailing version after a language/library name. Conservative
# — only strips when the preceding token is alphabetic (so "c++17" -> "c++"
# but "ec2" stays as "ec2").
_TRAILING_VERSION = re.compile(r"(?<=[a-z+#])\s*\d{1,4}(?:\.\d+)*$", re.IGNORECASE)

# Common synonym suffixes that don't change identity. Tiny, generic — *not*
# a brand alias list.
_SYNONYM_TAIL = re.compile(r"\s+(?:framework|library|language|programming|technology)$", re.IGNORECASE)


_MIN_AFTER_STRIP = 2  # never reduce a skill to fewer than 2 chars


def _apply_rules(raw: str) -> str:
    s = raw.strip().lower()
    if not s:
        return ""

    # Outer junk
    s = _OUTER_PUNCT.sub("", s)
    s = _COLLAPSE_WS.sub(" ", s).strip()
    if not s:
        return ""

    # Internal punctuation collapse. Dashes between word chars become spaces
    # so "react-native" -> "react native" but "c#" / "c++" survive.
    s = _DASH_BETWEEN_WORDS.sub(" ", s)
    s = _COLLAPSE_SEP.sub(" ", s)
    s = _DUP_DOTS.sub(".", s).strip()

    # JS suffix collapse (e.g. "node.js" -> "node", "reactjs" -> "react").
    candidate = _JS_SUFFIX.sub("", s)
    if len(candidate) >= _MIN_AFTER_STRIP:
        s = candidate

    # Version / plural / synonym-tail noise
    s = _API_PLURAL.sub("api", s)
    candidate = _TRAILING_VERSION.sub("", s)
    if len(candidate) >= _MIN_AFTER_STRIP:
        s = candidate
    s = _SYNONYM_TAIL.sub("", s).strip()

    # Trailing punctuation introduced by rule rewrites
    s = _OUTER_PUNCT.sub("", s)
    s = _COLLAPSE_WS.sub(" ", s).strip()

    return s


@lru_cache(maxsize=4096)
def normalize(skill: str) -> str:
    """
    Return the canonical lookup key for `skill`. Empty string on falsy /
    invalid input. Pure and idempotent: normalize(normalize(x)) == normalize(x).
    """
    if not skill or not isinstance(skill, str):
        return ""
    key = _apply_rules(skill)
    if not key:
        return ""
    # Idempotence guard: if a second pass would change the result we've
    # missed a rule. Log it so the dataset can be reviewed, but still
    # converge to the fixed point.
    second = _apply_rules(key)
    if second != key:
        logger.debug("[normalizer] non-idempotent input %r: %r -> %r", skill, key, second)
        return second
    return key


def normalize_many(skills) -> list:
    """Normalize an iterable, dropping empties but preserving order + uniqueness."""
    seen = set()
    out = []
    for raw in skills or ():
        key = normalize(raw)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out
