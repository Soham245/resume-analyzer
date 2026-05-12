"""
Legacy compare_skills helper — preserved for back-compat.

The real matching now lives in `backend.intelligence.matcher`. This shim
canonicalizes both lists before set-comparing so callers don't need to
care that "ReactJS" and "React" are the same skill.
"""

from backend.intelligence.normalizer import normalize


def compare_skills(resume_skills, jd_skills):
    """
    Return (matched, missing) lists. Inputs may use any surface form;
    comparison happens on the normalized lookup key but the returned values
    are taken from the resume / JD originals so display is preserved.
    """
    resume_by_key = {}
    for s in resume_skills or ():
        k = normalize(s)
        if k:
            resume_by_key.setdefault(k, s)

    jd_by_key = {}
    for s in jd_skills or ():
        k = normalize(s)
        if k:
            jd_by_key.setdefault(k, s)

    matched_keys = set(resume_by_key) & set(jd_by_key)
    missing_keys = set(jd_by_key) - set(resume_by_key)

    matched = [jd_by_key[k] for k in matched_keys]
    missing = [jd_by_key[k] for k in missing_keys]
    return matched, missing


def calculate_score(matched_count, total_required):
    if total_required == 0:
        return 0
    return round((matched_count / total_required) * 100, 2)
