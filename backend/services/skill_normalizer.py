"""
Lightweight skill normalization — temporary registry-lookup entrypoint.

The job here is *not* to produce the user-facing display form. It is to
collapse alternate spellings of the same skill onto one stable lookup
key so the registry can be queried consistently:

    "ReactJS", "react.js", "react js", "react-js"  ->  "react"
    "Node.JS",  "nodejs",  "node js"               ->  "node"
    "PostgreSQL", "Postgres"                       ->  unchanged here
                                                       (the registry's
                                                       alias table maps
                                                       them onto each
                                                       other)

A full normalization refactor (with semantic mappings) will replace this
helper once the registry has grown organically.
"""

import re

_TRIM_BOUNDARY = re.compile(r"^[\s\-_/,.;:|]+|[\s\-_/,.;:|]+$")
_COLLAPSE_SEP = re.compile(r"[\s/\-_]+")
_DUP_DOTS = re.compile(r"\.{2,}")
_JS_SUFFIX = re.compile(r"(?:\s+js|\.js|js)$")


def normalize(skill: str) -> str:
    """
    Return the lookup key for `skill`. Empty string for falsy/invalid input.

    Rules:
      - lowercase
      - trim outer whitespace and trailing punctuation
      - collapse runs of separators ("/", "-", "_", whitespace) to one space
      - collapse repeated dots
      - strip trailing "js" / ".js" / " js" suffix (provided the result
        retains at least 2 characters, so "js" itself survives)
    """
    if not skill or not isinstance(skill, str):
        return ""

    s = skill.strip().lower()
    if not s:
        return ""

    s = _TRIM_BOUNDARY.sub("", s)
    s = _COLLAPSE_SEP.sub(" ", s).strip()
    s = _DUP_DOTS.sub(".", s)

    # JS-style suffix collapse — guarded so we never reduce a skill to
    # fewer than 2 characters (otherwise "js" itself would collapse).
    stripped = _JS_SUFFIX.sub("", s)
    if stripped and len(stripped) >= 2:
        s = stripped

    return s.strip()
