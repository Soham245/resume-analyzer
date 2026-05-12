"""
Pipeline orchestrator.

Single entrypoint for everything ATS-related. Other modules in this package
are leaves; this module is the only one that wires them together and is the
only one the legacy `scorer.py` shim delegates into.

Public surface (mirrors what the old scorer.py exposed so callers don't
have to change):

  canonicalize_skill(skill)            -> display form
  canonicalize_skill_list(skills)      -> de-duped list of display forms
  detect_matched_skills(resume, jd_keys)
  detect_missing_skills(resume, jd_keys, jd_text="")
  compute_ats_score(resume, jd_text, jd_skills=None, debug=False)
  score_label(score)
  rank_projects_by_overlap(projects, jd_text)
  find_skill_counts(text, skills)      -> Counter (legacy compat)

The registry (services.skill_registry) is the canonical store for aliases
and display names. Callers should treat its output as authoritative. When
the registry doesn't know a skill, we fall back to `display.format_display`
on the normalized key.
"""

import logging
from collections import Counter
from typing import Dict, Iterable, List, Optional, Union

from . import scoring
from .display import format_display
from .matcher import scan_text
from .normalizer import normalize
from .text_utils import tokenize

logger = logging.getLogger(__name__)


# ── Display form resolution ─────────────────────────────────────────────────
def _registry_display(key: str) -> Optional[str]:
    """
    Return the registry's stored display_name for `key`, or None. Read-only.
    The registry import is local so the module loads even if the DB is not
    yet configured (tests, scripts).
    """
    if not key:
        return None
    try:
        from backend.services import skill_registry
        rec = skill_registry.lookup(key)
    except Exception as exc:
        logger.debug("[pipeline] registry lookup failed for %r: %s", key, exc)
        return None
    return rec.display_name if rec is not None else None


def _observe(key: str, source: str = "extracted") -> None:
    """Auto-learn the skill if the registry is reachable. Failures are non-fatal."""
    if not key:
        return
    try:
        from backend.services import skill_registry
        skill_registry.observe(key, source=source)
    except Exception as exc:
        logger.debug("[pipeline] registry observe failed for %r: %s", key, exc)


def canonicalize_skill(skill: str) -> str:
    """Return the display form for `skill`. Empty string on invalid input."""
    if not skill or not isinstance(skill, str):
        return ""
    key = normalize(skill)
    if not key:
        return ""
    display = _registry_display(key)
    if display:
        return display
    return format_display(key)


def canonicalize_skill_list(skills: Iterable[str]) -> List[str]:
    """Canonicalize + de-duplicate. Preserves first-seen order. Observes registry."""
    seen = set()
    out: List[str] = []
    for raw in skills or ():
        if not isinstance(raw, str) or not raw.strip():
            continue
        key = normalize(raw)
        if not key:
            continue
        _observe(key, source="extracted")
        display = _registry_display(key) or format_display(key)
        low = display.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(display)
    if out:
        logger.debug("[pipeline] canonicalize_skill_list -> %s", out[:8])
    return out


# ── Skill detection / scoring helpers (display-form outputs) ────────────────
def _resume_text(resume: Union[dict, str]) -> str:
    return scoring._resume_full_text(resume)


def _display_for_key(key: str) -> str:
    return _registry_display(key) or format_display(key)


def find_skill_counts(text: str, skills: Iterable[str]) -> Counter:
    """
    Legacy-compatible wrapper: count occurrences in `text` for each skill
    in `skills`. Returns a Counter keyed by the **display form** so existing
    callers see the same shape they did before the refactor.
    """
    keys: List[str] = []
    seen = set()
    for s in skills or ():
        k = normalize(s)
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    counts = scan_text(text or "", keys)
    return Counter({_display_for_key(k): c for k, c in counts.items()})


def detect_matched_skills(resume_or_text: Union[dict, str], jd_skills: Iterable[str]) -> List[str]:
    text = _resume_text(resume_or_text)
    keys: List[str] = []
    seen = set()
    for s in jd_skills or ():
        k = normalize(s)
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    counts = scan_text(text, keys)
    return [_display_for_key(k) for k in keys if counts.get(k, 0) > 0]


def detect_missing_skills(resume_or_text: Union[dict, str], jd_skills: Iterable[str],
                          jd_text: str = "") -> List[str]:
    text = _resume_text(resume_or_text)
    keys: List[str] = []
    seen = set()
    for s in jd_skills or ():
        k = normalize(s)
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    counts = scan_text(text, keys)

    # Rank missing by JD-derived weight, falling back to JD raw frequency.
    from .extractor import extract_weighted_terms, weight_map
    weights = weight_map(extract_weighted_terms(jd_text or "")) if jd_text else {}

    missing = [k for k in keys if counts.get(k, 0) == 0]
    missing.sort(key=lambda k: weights.get(k, 0.0), reverse=True)
    if not weights:
        # No JD text supplied — fall back to keys' surface frequency in `jd_skills`
        order = {k: i for i, k in enumerate(keys)}
        missing.sort(key=lambda k: order.get(k, 0))

    return [_display_for_key(k) for k in missing]


# ── ATS scoring + label ────────────────────────────────────────────────────
def compute_ats_score(resume: Union[dict, str], jd_text: str,
                      jd_skills: Optional[Iterable[str]] = None,
                      *, debug: bool = False) -> dict:
    """
    Compute an ATS score. Returns the same dict shape the legacy scorer did,
    with `matched_skills` / `missing_skills` as **display forms**.
    """
    jd_key_list = None
    if jd_skills is not None:
        jd_key_list = []
        seen = set()
        for s in jd_skills:
            k = normalize(s)
            if k and k not in seen:
                seen.add(k)
                jd_key_list.append(k)
                _observe(k, source="extracted")

    raw = scoring.compute(resume, jd_text, jd_keys=jd_key_list, debug=debug)

    # Convert keys back to display form before returning.
    raw["matched_skills"] = [_display_for_key(k) for k in raw.get("matched_skills", [])]
    raw["missing_skills"] = [_display_for_key(k) for k in raw.get("missing_skills", [])]

    # scoring._insights builds the "Missing key skills" line from the
    # normalized key list (lowercase). Re-render it now that we have the
    # display forms, so the UI shows "Docker" rather than "docker" and
    # "GitHub Actions" rather than "github actions".
    insights = list(raw.get("insights") or [])
    if insights and raw["missing_skills"]:
        for i, line in enumerate(insights):
            if isinstance(line, str) and line.startswith("Missing key skills:"):
                insights[i] = f"Missing key skills: {', '.join(raw['missing_skills'][:3])}"
                break
        raw["insights"] = insights
    return raw


def score_label(score: int) -> str:
    return scoring.score_label(score)


# ── Project ranking (used by rewriter) ─────────────────────────────────────
def rank_projects_by_overlap(projects, jd_text: str):
    if not projects:
        return []
    jd_tokens = set(tokenize(jd_text or ""))
    if not jd_tokens:
        return list(projects)
    ranked = []
    for index, project in enumerate(projects):
        project_text = " ".join([
            str(project.get("title", "")),
            " ".join(project.get("tech_stack", []) or []),
            " ".join(project.get("points", []) or []),
        ])
        score = len(jd_tokens & set(tokenize(project_text)))
        ranked.append((score, index, project))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [p for _, _, p in ranked]


def rank_projects_tfidf(projects, jd_text: str):
    return rank_projects_by_overlap(projects, jd_text)
