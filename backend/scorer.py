"""
ATS scoring — thin compatibility shim.

The real work happens in `backend.intelligence.pipeline`. This module
exists only because the rest of the codebase already imports symbols
from `backend.scorer`. New code should import from
`backend.intelligence.pipeline` directly.

Public surface kept identical to pre-refactor:

    canonicalize_skill(skill)
    canonicalize_skill_list(skills)
    find_skill_counts(text, skills)
    detect_matched_skills(resume_or_text, jd_skills)
    detect_missing_skills(resume_or_text, jd_skills, jd_text="")
    compute_ats_score(resume, jd_text, jd_skills=None, debug=False)
    cached_ats_score(resume_text, jd_text, jd_skills=None, debug=False)
    score_label(score)
    rank_projects_by_overlap(projects, jd_text)
    rank_projects_tfidf(projects, jd_text)
    CATEGORY_WEIGHTS
"""

import json
import logging
from typing import Optional, Union

from backend.intelligence import pipeline
from backend.intelligence.scoring import CATEGORY_WEIGHTS  # noqa: F401

logger = logging.getLogger(__name__)


# ── Re-exports ─────────────────────────────────────────────────────────────
canonicalize_skill        = pipeline.canonicalize_skill
canonicalize_skill_list   = pipeline.canonicalize_skill_list
find_skill_counts         = pipeline.find_skill_counts
detect_matched_skills     = pipeline.detect_matched_skills
detect_missing_skills     = pipeline.detect_missing_skills
compute_ats_score         = pipeline.compute_ats_score
score_label               = pipeline.score_label
rank_projects_by_overlap  = pipeline.rank_projects_by_overlap
rank_projects_tfidf       = pipeline.rank_projects_tfidf


def cached_ats_score(resume_text, jd_text, jd_skills=None, debug=False):
    """
    Compatibility wrapper. Despite the name, scoring is NOT cached — the
    score must always reflect the current resume state.
    """
    if isinstance(resume_text, dict):
        try:
            resume_payload = json.loads(json.dumps(resume_text))
        except Exception:
            resume_payload = resume_text
    else:
        resume_payload = str(resume_text or "")
    return compute_ats_score(resume_payload, jd_text, jd_skills=jd_skills, debug=debug)
