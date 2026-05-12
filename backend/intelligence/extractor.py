"""
Contextual keyword and phrase extraction.

The extractor walks a piece of text section-by-section, splits into
sentences, scans 1..3-gram phrases, and assigns each candidate a
**weight** that combines:

  *  raw frequency
  *  section importance      (text_utils.section_weight)
  *  sentence-level cues     (text_utils.cue_weight — "required", "preferred")
  *  specificity bonus       (phrases with capitalization, hyphenation,
                              non-stoplist tokens score higher)
  *  length factor           (multi-word phrases get a small bonus so
                              "machine learning" survives over "learning")

There are no giant stoplists. A tiny ~40-entry FUNCTION_WORDS set is used
purely to reject pure-glue phrases like "to the" or "with our". Anything
content-bearing — including unknown technologies like "Bun", "Hono",
"LangGraph" — survives extraction.

Output is a dict keyed by *normalized* phrase. Callers can map normalized
keys back to a display form via `intelligence.display.format_display` or
the registry.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from . import text_utils
from .normalizer import normalize

logger = logging.getLogger(__name__)

# ── Tiny function-word set (40 entries, English only) ────────────────────────
# Used ONLY to reject phrases that contain no content tokens. Not a topical
# stoplist — domain terms like "experience", "team", "data" are deliberately
# NOT here so they can still surface when the cue/section weights lift them.
FUNCTION_WORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "by",
    "for", "with", "from", "as", "is", "are", "was", "were", "be", "been",
    "being", "this", "that", "these", "those", "it", "its", "their", "our",
    "your", "you", "we", "us", "they", "them", "but", "not", "no", "if",
    "than", "then", "so", "such", "into", "over", "via", "per", "etc",
})

# Tokens that look like skills almost regardless of context — give them a
# bonus so they survive even if they appear once.
_HIGH_SIGNAL_RE = re.compile(
    r"^(?:[a-z]+\+\+|[a-z]+#|[a-z]*[A-Z][A-Za-z0-9.+#-]*|[a-z]+\.[a-z]+)$"
)


@dataclass
class TermWeight:
    normalized: str
    display_phrase: str        # original-case phrase as it appeared in source
    count: int = 0
    weight: float = 0.0
    sections: Dict[str, int] = field(default_factory=dict)
    cue_max: float = 1.0

    def to_dict(self) -> dict:
        return {
            "normalized": self.normalized,
            "phrase": self.display_phrase,
            "count": self.count,
            "weight": round(self.weight, 3),
            "sections": dict(self.sections),
            "cue_max": round(self.cue_max, 2),
        }


# ── Helpers ──────────────────────────────────────────────────────────────────
def _content_tokens(tokens: List[str]) -> List[str]:
    """Tokens that aren't pure function words. Digits-only tokens dropped too."""
    return [t for t in tokens if t not in FUNCTION_WORDS and not t.isdigit() and len(t) >= 2]


def _is_meaningful(phrase: str, tokens: List[str]) -> bool:
    """Reject pure-glue phrases (all function words) or all-digit phrases."""
    content = _content_tokens(tokens)
    if not content:
        return False
    # Reject "ing"-only verbs that are clearly action words when standalone.
    # We keep them in multi-word phrases (e.g. "machine learning") because
    # the noun follows.
    if len(tokens) == 1 and tokens[0].endswith("ing") and tokens[0] in {
        "working", "using", "ensuring", "managing", "leading", "providing",
        "delivering", "supporting", "developing", "designing", "creating",
        "building", "implementing", "writing", "reading",
    }:
        return False
    return True


def _specificity_bonus(phrase: str, tokens: List[str]) -> float:
    """
    Specificity heuristic. Higher score = more likely to be a real skill.
        - Original-case phrase contains uppercase or digits   -> +0.30
        - Phrase contains hyphen, dot, "+", "#"               -> +0.20
        - Phrase token matches a high-signal pattern          -> +0.40
    """
    bonus = 0.0
    if any(c.isupper() for c in phrase) or any(c.isdigit() for c in phrase):
        bonus += 0.30
    if any(c in "-.+#" for c in phrase):
        bonus += 0.20
    if any(_HIGH_SIGNAL_RE.match(tok) for tok in phrase.split()):
        bonus += 0.40
    return bonus


def _length_factor(n: int) -> float:
    """Slight bonus for multi-word phrases — keeps 'machine learning' over 'learning'."""
    if n == 1: return 1.00
    if n == 2: return 1.15
    return 1.20


# ── Core extraction ──────────────────────────────────────────────────────────
def extract_weighted_terms(
    text: str,
    *,
    sections: Optional[Dict[str, str]] = None,
    max_n: int = 3,
    min_weight: float = 0.0,
) -> Dict[str, TermWeight]:
    """
    Walk `text` and return a {normalized_phrase: TermWeight} map.

    If `sections` is provided, it is treated as the pre-split labelled
    sections. Otherwise sections are detected from `text` directly.
    """
    if not text:
        return {}

    if sections is None:
        sections = text_utils.split_sections(text) or {"body": text}

    terms: Dict[str, TermWeight] = {}

    for label, body in sections.items():
        sec_w = text_utils.section_weight(label)
        for sentence in text_utils.sentences(body):
            cue_w = text_utils.cue_weight(sentence)
            tokens = text_utils.tokenize(sentence)
            if not tokens:
                continue

            # Slide n-grams up to max_n
            for n, phrase_lower in text_utils.iter_phrases(tokens, max_n=max_n):
                phrase_tokens = phrase_lower.split()
                if not _is_meaningful(phrase_lower, phrase_tokens):
                    continue

                normalized = normalize(phrase_lower)
                if not normalized:
                    continue
                # If normalization stripped the phrase to a function word,
                # skip it.
                if normalized in FUNCTION_WORDS:
                    continue

                # Find the original-cased phrase from the sentence for nicer
                # display. Cheap regex find.
                display_phrase = _find_original_case(sentence, phrase_lower) or phrase_lower

                spec = _specificity_bonus(display_phrase, phrase_tokens)
                base = (1.0 + spec) * _length_factor(n)
                contribution = base * sec_w * cue_w

                rec = terms.get(normalized)
                if rec is None:
                    rec = TermWeight(
                        normalized=normalized,
                        display_phrase=display_phrase,
                    )
                    terms[normalized] = rec

                rec.count += 1
                rec.weight += contribution
                rec.sections[label] = rec.sections.get(label, 0) + 1
                if cue_w > rec.cue_max:
                    rec.cue_max = cue_w

    # Subsumption: when a longer phrase is dominant, downweight its subsumed
    # shorter forms so "machine learning" beats "learning".
    _apply_subsumption(terms)

    if min_weight > 0:
        terms = {k: v for k, v in terms.items() if v.weight >= min_weight}

    return terms


def _find_original_case(sentence: str, phrase_lower: str) -> Optional[str]:
    if not sentence or not phrase_lower:
        return None
    idx = sentence.lower().find(phrase_lower)
    if idx < 0:
        return None
    return sentence[idx:idx + len(phrase_lower)]


def _apply_subsumption(terms: Dict[str, TermWeight]) -> None:
    """
    For every multi-word term, halve the weight of any single-word term
    fully subsumed by it whose count is no greater. Prevents 'learning'
    from outranking 'machine learning'.
    """
    if not terms:
        return
    multi = [t for t in terms.values() if " " in t.normalized]
    for mt in multi:
        parts = mt.normalized.split(" ")
        for part in parts:
            sub = terms.get(part)
            if sub is None or sub is mt:
                continue
            if sub.count <= mt.count and len(part) <= 4:
                # Strong subsumption — short subsumed tokens drop a lot.
                sub.weight *= 0.40
            elif sub.count <= mt.count:
                sub.weight *= 0.65


# ── Convenience views ───────────────────────────────────────────────────────
def top_terms(
    terms: Dict[str, TermWeight],
    *,
    limit: int = 30,
    floor: float = 0.0,
) -> List[TermWeight]:
    """Return terms sorted by weight desc, with optional floor + limit."""
    filtered = [t for t in terms.values() if t.weight >= floor]
    filtered.sort(key=lambda t: (-t.weight, t.normalized))
    return filtered[:limit] if limit else filtered


def weight_map(terms: Dict[str, TermWeight]) -> Dict[str, float]:
    """Flatten to {normalized: weight} — handy for matcher input."""
    return {k: v.weight for k, v in terms.items()}
