"""
Section-aware ATS scoring.

Layout (100 points total, unchanged from the previous engine):

    Skills          35
    Experience      25
    Projects        15
    Education       10
    Certifications  10
    Structure        5

Differences vs. the legacy scorer:

  * Skill weights come from `extractor.extract_weighted_terms(jd_text)` —
    a JD-side TF-style weight that already factors section + cue. A skill
    appearing under "Required Skills" outweighs the same skill under
    "Benefits" automatically.

  * Skill detection uses `intelligence.matcher.scan_text`, so
    registry-known aliases collapse onto the canonical form (RESTful APIs
    -> rest api, ML -> machine learning when the registry knows it).

  * Unknown technologies are *not* discarded. Anything in `jd_keys` is
    matched against the resume; registry presence is optional.

Public surface is `compute(resume_json, jd_text, jd_keys=None, debug=False)`
returning a dict with the same shape the legacy scorer produced, so the
public `scorer.compute_ats_score` shim is a one-liner.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Union

from . import text_utils
from .extractor import extract_weighted_terms, weight_map
from .matcher import canonical_set, match, scan_text
from .normalizer import normalize

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 6000

CATEGORY_WEIGHTS = {
    "skills":         35,
    "experience":     25,
    "projects":       15,
    "education":      10,
    "certifications": 10,
    "structure":       5,
}

# ── Hint patterns kept for raw-text fallbacks ────────────────────────────────
_EXPERIENCE_HINTS = re.compile(
    r"\b(experience|worked|employed|intern(ship)?|engineer|developer|designer|"
    r"manager|analyst|consultant|years?|present|full-?time|part-?time)\b",
    re.IGNORECASE,
)
_PROJECT_HINTS = re.compile(
    r"\b(project|built|developed|implemented|designed|created|launched|deployed)\b",
    re.IGNORECASE,
)
_EDUCATION_HINTS = re.compile(
    r"\b(b\.?tech|m\.?tech|b\.?sc|m\.?sc|b\.?e\b|m\.?e\b|b\.?a\b|m\.?a\b|"
    r"bachelor|master|ph\.?d|degree|university|college|institute|school|gpa|cgpa)\b",
    re.IGNORECASE,
)
_CERT_HINTS = re.compile(r"\b(certif(ied|ication|icate)|credential)\b", re.IGNORECASE)

_ACHIEVEMENT_PATTERN = re.compile(
    r"(\b\d+(?:[\.,]\d+)?\s?(?:%|percent|x|times|users|customers|requests|"
    r"hours|hrs|seconds|secs|ms|days|weeks|months|years|k|m|million|billion|"
    r"\+)\b)",
    re.IGNORECASE,
)
_NUMBER_PATTERN = re.compile(r"\b\d+(?:[\.,]\d+)?\b")


# ── Text assembly ───────────────────────────────────────────────────────────
def _limit(text: str, max_chars: int = MAX_TEXT_CHARS) -> str:
    return str(text or "")[:max_chars]


def _resume_full_text(resume: Union[dict, str]) -> str:
    if isinstance(resume, str):
        return _limit(resume)
    if not isinstance(resume, dict):
        return ""
    parts = [
        str(resume.get("name", "")),
        str(resume.get("title", "")),
        str(resume.get("summary", "")),
        " ".join(resume.get("technical_skills", []) or []),
        " ".join(resume.get("soft_skills", []) or []),
        " ".join(resume.get("languages", []) or []),
    ]
    for exp in resume.get("experience", []) or []:
        parts += [str(exp.get("role", "")), str(exp.get("company", "")),
                  str(exp.get("duration", "")), " ".join(exp.get("points", []) or [])]
    for proj in resume.get("projects", []) or []:
        parts += [str(proj.get("title", "")), " ".join(proj.get("tech_stack", []) or []),
                  " ".join(proj.get("points", []) or [])]
    for edu in resume.get("education", []) or []:
        parts += [str(edu.get("degree", "")), str(edu.get("institution", "")), str(edu.get("year", ""))]
    parts.append(" ".join(resume.get("certifications", []) or []))
    return _limit(" ".join(p for p in parts if p))


def _experience_text(resume: dict) -> str:
    chunks = []
    for exp in resume.get("experience", []) or []:
        chunks += [str(exp.get("role", "")), str(exp.get("company", "")),
                   " ".join(exp.get("points", []) or [])]
    return " ".join(c for c in chunks if c)


def _project_text(resume: dict) -> str:
    chunks = []
    for proj in resume.get("projects", []) or []:
        chunks += [str(proj.get("title", "")), " ".join(proj.get("tech_stack", []) or []),
                   " ".join(proj.get("points", []) or [])]
    return " ".join(c for c in chunks if c)


def _count_achievements(text: str) -> int:
    if not text:
        return 0
    return len(_ACHIEVEMENT_PATTERN.findall(text)) + len(_NUMBER_PATTERN.findall(text)) // 2


def _token_set(text: str) -> set:
    return set(text_utils.tokenize(text))


# ── Category scorers ────────────────────────────────────────────────────────
def _score_skills(resume_text: str, jd_keys: List[str], jd_weights: Dict[str, float]) -> Tuple[int, List[str], List[str], dict]:
    weight_cap = CATEGORY_WEIGHTS["skills"]
    if not jd_keys:
        return 0, [], [], {"reason": "no_jd_skills"}

    result = match(resume_text or "", jd_keys, jd_weights=jd_weights)
    matched, missing, counts = result.matched, result.missing, result.counts

    coverage = len(matched) / len(jd_keys)
    flat_pts = coverage * weight_cap

    # JD-weighted coverage: skills with higher importance (required / required-skills section)
    # contribute more.
    total_w = sum(jd_weights.get(k, 1.0) for k in jd_keys) or 1.0
    matched_w = sum(jd_weights.get(k, 1.0) for k in matched)
    weighted_coverage = matched_w / total_w
    weighted_pts = weighted_coverage * weight_cap

    base = 0.5 * flat_pts + 0.5 * weighted_pts

    # Keyword-stuffing penalty
    stuff_penalty = 0.0
    for k, c in counts.items():
        if c > 5:
            stuff_penalty += min(2.0, (c - 5) * 0.5)
    base = max(0.0, base - stuff_penalty)

    points = int(round(min(weight_cap, base)))
    logger.debug(
        "[scoring.skills] coverage=%.2f weighted=%.2f stuff=%.2f -> %d/%d  matched_top=%s missing_top=%s",
        coverage, weighted_coverage, stuff_penalty, points, weight_cap,
        matched[:5], missing[:5],
    )
    return points, matched, missing, {
        "coverage": round(coverage, 3),
        "weighted_coverage": round(weighted_coverage, 3),
        "stuff_penalty": round(stuff_penalty, 2),
        "matched": matched,
        "missing": missing[:10],
    }


def _score_experience(resume: Union[dict, str], jd_text: str, jd_keys: List[str]) -> Tuple[int, dict]:
    cap = CATEGORY_WEIGHTS["experience"]
    if not isinstance(resume, dict):
        text = _resume_full_text(resume)
        if not text or not _EXPERIENCE_HINTS.search(text):
            return 0, {"reason": "no_experience_signal"}
        return _score_experience_text(text, jd_text, jd_keys, cap, has_structure=False)

    entries = resume.get("experience", []) or []
    if not entries:
        return 0, {"reason": "no_experience"}
    return _score_experience_text(_experience_text(resume), jd_text, jd_keys, cap,
                                  has_structure=True, entry_count=len(entries))


def _score_experience_text(text: str, jd_text: str, jd_keys: List[str], cap: int,
                           has_structure: bool, entry_count: int = 0) -> Tuple[int, dict]:
    if not text:
        return 0, {"reason": "empty_experience"}

    presence_pts = 4 if has_structure and entry_count > 0 else 0

    skill_counts = scan_text(text, jd_keys) if jd_keys else {}
    overlap = (len(skill_counts) / len(jd_keys)) if jd_keys else 0
    overlap_pts = overlap * 12

    jd_tokens = _token_set(jd_text)
    exp_tokens = _token_set(text)
    keyword_overlap = (len(jd_tokens & exp_tokens) / len(jd_tokens)) if jd_tokens else 0
    keyword_pts = keyword_overlap * 5

    achievements = _count_achievements(text)
    achievement_pts = min(4.0, achievements * 0.8)

    raw = presence_pts + overlap_pts + keyword_pts + achievement_pts
    points = int(round(min(cap, raw)))
    return points, {
        "presence_pts": presence_pts,
        "skill_overlap": round(overlap, 3),
        "keyword_overlap": round(keyword_overlap, 3),
        "achievements": achievements,
        "raw": round(raw, 2),
    }


def _score_projects(resume: Union[dict, str], jd_text: str, jd_keys: List[str]) -> Tuple[int, dict]:
    cap = CATEGORY_WEIGHTS["projects"]
    if not isinstance(resume, dict):
        text = _resume_full_text(resume)
        if not text or not _PROJECT_HINTS.search(text):
            return 0, {"reason": "no_project_signal"}
        skill_counts = scan_text(text, jd_keys) if jd_keys else {}
        overlap = (len(skill_counts) / len(jd_keys)) if jd_keys else 0
        raw = 2 + overlap * 6 + min(2.0, _count_achievements(text) * 0.4)
        return int(round(min(cap, raw))), {"reason": "raw_text", "skill_overlap": round(overlap, 3)}

    projects = resume.get("projects", []) or []
    if not projects:
        return 0, {"reason": "no_projects"}
    text = _project_text(resume)
    if not text:
        return 0, {"reason": "empty_projects"}

    skill_counts = scan_text(text, jd_keys) if jd_keys else {}
    overlap = (len(skill_counts) / len(jd_keys)) if jd_keys else 0
    raw = 3 + overlap * 7 + min(3.0, _count_achievements(text) * 0.6) + min(2.0, max(0, len(projects) - 1) * 0.7)
    points = int(round(min(cap, raw)))
    return points, {
        "count": len(projects),
        "skill_overlap": round(overlap, 3),
        "achievements": _count_achievements(text),
        "raw": round(raw, 2),
    }


def _score_education(resume: Union[dict, str]) -> Tuple[int, dict]:
    cap = CATEGORY_WEIGHTS["education"]
    if not isinstance(resume, dict):
        text = _resume_full_text(resume)
        if text and _EDUCATION_HINTS.search(text):
            return 5, {"reason": "raw_text_match"}
        return 0, {"reason": "raw_text_no_match"}

    education = resume.get("education", []) or []
    if not education:
        return 0, {"reason": "no_education"}

    pts = 0
    well_structured = 0
    for entry in education:
        if not isinstance(entry, dict):
            continue
        degree = str(entry.get("degree", "")).strip()
        institution = str(entry.get("institution", "")).strip()
        year = str(entry.get("year", "")).strip()
        if degree and institution:
            pts += 4
            if year:
                well_structured += 1
    pts += min(3, well_structured)
    return int(round(min(cap, pts))), {"count": len(education), "well_structured": well_structured}


def _score_certifications(resume: Union[dict, str], jd_text: str, jd_keys: List[str]) -> Tuple[int, dict]:
    cap = CATEGORY_WEIGHTS["certifications"]
    if not isinstance(resume, dict):
        text = _resume_full_text(resume)
        if text and _CERT_HINTS.search(text):
            return 4, {"reason": "raw_text_match"}
        return 0, {"reason": "raw_text_no_match"}

    certs = resume.get("certifications", []) or []
    if not certs:
        return 0, {"reason": "no_certifications"}

    count = sum(1 for c in certs if str(c or "").strip())
    if count == 0:
        return 0, {"reason": "blank_certifications"}

    base = 6 if count >= 3 else 4 if count == 2 else 3
    cert_text = " ".join(str(c or "") for c in certs)
    skill_hits = len(scan_text(cert_text, jd_keys)) if jd_keys else 0
    jd_tokens = _token_set(jd_text)
    keyword_hits = len(jd_tokens & _token_set(cert_text)) if jd_tokens else 0
    relevance = min(4.0, skill_hits * 1.5 + keyword_hits * 0.2)
    return int(round(min(cap, base + relevance))), {
        "count": count, "skill_hits": skill_hits, "relevance": round(relevance, 2),
    }


def _score_structure(resume: Union[dict, str]) -> Tuple[int, dict]:
    cap = CATEGORY_WEIGHTS["structure"]
    if not isinstance(resume, dict):
        text = str(resume or "")
        if len(text) >= 1200:
            return 3, {"reason": "raw_text_full"}
        if len(text) >= 400:
            return 2, {"reason": "raw_text_partial"}
        return 0, {"reason": "raw_text_short"}

    score = 0.0
    if str(resume.get("email", "")).strip() and not str(resume.get("email", "")).startswith("["):
        score += 1
    if str(resume.get("name", "")).strip() and not str(resume.get("name", "")).startswith("["):
        score += 0.5
    if str(resume.get("title", "")).strip() and not str(resume.get("title", "")).startswith("["):
        score += 0.5
    if str(resume.get("summary", "")).strip():
        score += 1
    if resume.get("technical_skills"):
        score += 1

    bullet_count = 0
    for exp in resume.get("experience", []) or []:
        bullet_count += len(exp.get("points", []) or [])
    for proj in resume.get("projects", []) or []:
        bullet_count += len(proj.get("points", []) or [])
    if bullet_count >= 3:
        score += 1

    return int(round(min(cap, score))), {"score": score, "bullet_count": bullet_count}


def _confidence(resume: Union[dict, str], jd_keys: List[str]) -> int:
    if not isinstance(resume, dict):
        text = str(resume or "")
        return max(55, min(85, 55 + len(text) // 60))

    filled = 0
    for k in ("summary", "technical_skills", "experience", "projects", "education", "certifications"):
        if resume.get(k):
            filled += 1
    base = 60 + int(filled / 6 * 30)
    if jd_keys and len(jd_keys) >= 5:
        base += 3
    return min(95, base)


def _insights(pieces: dict, matched: List[str], missing: List[str], resume: Union[dict, str]) -> List[str]:
    out = []
    if missing:
        out.append(f"Missing key skills: {', '.join(missing[:3])}")
    s = pieces.get("skills", 0)
    if s >= 28:
        out.append("Skills align strongly with the job description")
    elif s < 12:
        out.append("Weak skill overlap with the job description")
    if isinstance(resume, dict):
        if not resume.get("experience"):
            out.append("Add work experience to strengthen relevance")
        if not resume.get("projects"):
            out.append("Add projects to demonstrate practical skill use")
        if not resume.get("certifications"):
            out.append("Adding a relevant certification can boost credibility")
    if pieces.get("experience", 0) and pieces.get("experience", 0) < 8:
        out.append("Experience bullets need measurable impact (numbers, %, scale)")
    return out[:4]


# ── Public entry point ──────────────────────────────────────────────────────
def compute(
    resume: Union[dict, str],
    jd_text: str,
    jd_keys: Optional[List[str]] = None,
    *,
    debug: bool = False,
) -> dict:
    """
    Compute the ATS score. `jd_keys` may be:
      * None         -> derive from JD text via the extractor (top weighted terms)
      * list[str]    -> trusted skill list (normalized internally)
    """
    jd_text = _limit(jd_text)
    resume_text = _resume_full_text(resume)

    # Build the JD weight map from the JD text. This gives every term a
    # section-/cue-aware importance, regardless of whether the LLM
    # extracted it explicitly.
    jd_terms = extract_weighted_terms(jd_text) if jd_text else {}
    jd_weight_map = weight_map(jd_terms)

    if jd_keys is None or len(jd_keys) == 0:
        # Derive a working JD keyword set from the extractor output. Keep
        # only terms with weight >= 1.0 (a light threshold) and cap at 60.
        derived = [t for t in jd_terms.values() if t.weight >= 1.0]
        derived.sort(key=lambda t: -t.weight)
        canonical_jd_keys = [t.normalized for t in derived[:60]]
    else:
        canonical_jd_keys = canonical_set(jd_keys)

    # Ensure every canonical JD key has a weight (use a 1.0 floor for ones
    # the extractor didn't surface independently).
    for k in canonical_jd_keys:
        jd_weight_map.setdefault(k, 1.0)

    skills_pts, matched, missing, skills_dbg = _score_skills(resume_text, canonical_jd_keys, jd_weight_map)
    exp_pts,  exp_dbg  = _score_experience(resume, jd_text, canonical_jd_keys)
    proj_pts, proj_dbg = _score_projects(resume, jd_text, canonical_jd_keys)
    edu_pts,  edu_dbg  = _score_education(resume)
    cert_pts, cert_dbg = _score_certifications(resume, jd_text, canonical_jd_keys)
    struct_pts, struct_dbg = _score_structure(resume)

    total = max(0, min(100, skills_pts + exp_pts + proj_pts + edu_pts + cert_pts + struct_pts))

    breakdown = {
        "skills": skills_pts,
        "experience": exp_pts,
        "projects": proj_pts,
        "education": edu_pts,
        "certifications": cert_pts,
        "structure": struct_pts,
    }

    # Sort missing by JD weight desc for the UI.
    missing.sort(key=lambda k: jd_weight_map.get(k, 0.0), reverse=True)

    insights = _insights(breakdown, matched, missing, resume)
    confidence = _confidence(resume, canonical_jd_keys)

    logger.info(
        "[scoring] total=%d skills=%d/%d exp=%d proj=%d edu=%d cert=%d struct=%d "
        "jd_terms=%d matched=%d missing=%d",
        total, skills_pts, CATEGORY_WEIGHTS["skills"], exp_pts, proj_pts,
        edu_pts, cert_pts, struct_pts, len(canonical_jd_keys),
        len(matched), len(missing),
    )

    result = {
        "score": total,
        "breakdown": breakdown,
        "insights": insights,
        "confidence": confidence,
        "matched_skills": matched,
        "missing_skills": missing,
    }

    if debug:
        result["_debug"] = {
            "skills": skills_dbg,
            "experience": exp_dbg,
            "projects": proj_dbg,
            "education": edu_dbg,
            "certifications": cert_dbg,
            "structure": struct_dbg,
            "jd_canonical": canonical_jd_keys,
            "jd_weights": {k: round(v, 2) for k, v in sorted(jd_weight_map.items(), key=lambda kv: -kv[1])[:30]},
        }
    return result


def score_label(score: int) -> str:
    if score >= 80: return "Excellent"
    if score >= 65: return "Good"
    if score >= 50: return "Needs Improvement"
    return "Poor"
