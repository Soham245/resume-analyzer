"""
Tokenization and section detection for resume / JD text.

Deterministic, regex-only. No NLP libraries. Functions here MUST stay cheap
because the scoring pipeline calls them on every request.

Three public concepts:

  tokenize(text)              -> list[str]   word tokens (lowercased)
  ngrams(tokens, n)           -> list[str]   space-joined n-grams
  split_sections(text)        -> dict        section_label -> raw text
  section_weight(label)       -> float       importance weight for ATS

The section detector recognises typical resume / JD headings using a small,
ordered pattern list. Anything unmatched falls into "body".
"""

import re
from typing import Dict, List, Tuple

# ── Tokenization ─────────────────────────────────────────────────────────────
# Allow internal "+", "#", "/", ".", "-" so "c++", "c#", "ci/cd", "node.js",
# "react-native" all survive tokenisation as single units.
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#./\-]*")


def tokenize(text: str) -> List[str]:
    if not text:
        return []
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def ngrams(tokens: List[str], n: int) -> List[str]:
    if n <= 0 or len(tokens) < n:
        return []
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def iter_phrases(tokens: List[str], max_n: int = 3):
    """Yield (n, phrase) for n in 1..max_n. Memory-light alternative to building lists."""
    for n in range(1, max_n + 1):
        if len(tokens) < n:
            return
        for i in range(len(tokens) - n + 1):
            yield n, " ".join(tokens[i:i + n])


# ── Section detection ────────────────────────────────────────────────────────
# Ordered: more specific patterns first. The label on the left is what the
# scorer uses to look up a section_weight().
_SECTION_PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("required_skills",
     re.compile(r"^\s*(?:required|must[\s-]?have|key)\s+(?:skills|qualifications|requirements)\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("requirements",
     re.compile(r"^\s*(?:requirements?|qualifications?|what\s+you[''']?ll\s+need)\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("responsibilities",
     re.compile(r"^\s*(?:responsibilities|duties|what\s+you[''']?ll\s+do|the\s+role)\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("preferred",
     re.compile(r"^\s*(?:preferred|nice[\s-]?to[\s-]?have|bonus|good[\s-]?to[\s-]?have)\s*(?:skills|qualifications)?\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("technical_skills",
     re.compile(r"^\s*(?:technical\s+skills|technologies|tech\s+stack|skills)\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("experience",
     re.compile(r"^\s*(?:experience|work\s+experience|professional\s+experience|employment)\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("projects",
     re.compile(r"^\s*projects?\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("education",
     re.compile(r"^\s*education\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("certifications",
     re.compile(r"^\s*certifications?\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("summary",
     re.compile(r"^\s*(?:summary|profile|about|objective)\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("benefits",
     re.compile(r"^\s*(?:benefits|perks|what\s+we\s+offer|compensation)\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
    ("company",
     re.compile(r"^\s*(?:about\s+(?:us|the\s+company|the\s+team)|our\s+mission|who\s+we\s+are)\s*[:\-]?\s*$",
                re.IGNORECASE | re.MULTILINE)),
)


def split_sections(text: str) -> Dict[str, str]:
    """
    Split `text` into labelled sections. Returns a dict of
    {section_label: text}. Text before the first detected heading is
    placed under "body".
    """
    if not text:
        return {}

    # Find every heading hit across all patterns, then sort by position.
    hits: List[Tuple[int, int, str]] = []  # (start, end, label)
    for label, pat in _SECTION_PATTERNS:
        for match in pat.finditer(text):
            hits.append((match.start(), match.end(), label))

    if not hits:
        return {"body": text}

    hits.sort(key=lambda h: h[0])

    sections: Dict[str, str] = {}
    leading = text[: hits[0][0]].strip()
    if leading:
        sections["body"] = leading

    for index, (_, end, label) in enumerate(hits):
        next_start = hits[index + 1][0] if index + 1 < len(hits) else len(text)
        chunk = text[end:next_start].strip()
        if chunk:
            sections[label] = (sections.get(label, "") + "\n" + chunk).strip() if label in sections else chunk

    return sections


# ── Section weights ──────────────────────────────────────────────────────────
# Importance multipliers applied during scoring. Values are deliberate and
# bounded — keeping the range narrow keeps ATS scores stable and explainable.
_SECTION_WEIGHTS: Dict[str, float] = {
    "required_skills":  1.50,
    "requirements":     1.40,
    "technical_skills": 1.30,
    "responsibilities": 1.20,
    "experience":       1.15,
    "preferred":        1.05,
    "projects":         1.00,
    "summary":          0.90,
    "education":        0.85,
    "certifications":   0.85,
    "body":             1.00,
    "benefits":         0.40,
    "company":          0.40,
}


def section_weight(label: str) -> float:
    """Return the ATS importance multiplier for a section label."""
    return _SECTION_WEIGHTS.get(label, 1.0)


# ── Cue patterns ─────────────────────────────────────────────────────────────
# Sentence-level cues that lift the importance of skills mentioned nearby.
# These are intentionally short — the scoring layer interprets them as
# multipliers, not gates.
_CUE_PATTERNS: Tuple[Tuple[re.Pattern, float], ...] = (
    (re.compile(r"\b(?:required|must[\s-]?have|essential)\b", re.IGNORECASE), 1.40),
    (re.compile(r"\b(?:proficient|strong|expert|advanced|deep)\s+(?:in|with|knowledge)\b", re.IGNORECASE), 1.25),
    (re.compile(r"\b(?:experience|familiarity|familiar)\s+(?:with|in)\b", re.IGNORECASE), 1.15),
    (re.compile(r"\b(?:preferred|nice[\s-]?to[\s-]?have|bonus|plus)\b", re.IGNORECASE), 0.85),
    (re.compile(r"\b(?:responsib(?:le|ility|ilities)|duties)\b", re.IGNORECASE), 1.10),
)


def cue_weight(sentence: str) -> float:
    """
    Multiplier derived from sentence-level cues. Multiple cues compound
    multiplicatively, capped to [0.5, 2.0] so a single sentence cannot
    distort the overall score.
    """
    if not sentence:
        return 1.0
    weight = 1.0
    for pat, mult in _CUE_PATTERNS:
        if pat.search(sentence):
            weight *= mult
    return max(0.5, min(2.0, weight))


# ── Sentence splitting ───────────────────────────────────────────────────────
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+|•|·|•")


def sentences(text: str) -> List[str]:
    """Cheap sentence splitter — periods, newlines, bullet glyphs."""
    if not text:
        return []
    return [chunk.strip() for chunk in _SENT_SPLIT_RE.split(text) if chunk and chunk.strip()]
