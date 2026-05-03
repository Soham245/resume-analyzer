import json
import re

MAX_TEXT_CHARS = 3000

TECH_ALIASES = {
    "reactjs": "react",
    "nodejs": "node",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "ml": "machinelearning",
    "ai": "artificialintelligence",
}

PHRASE_ALIASES = {
    "react native": "react",
    "amazon web services": "aws",
    "node js": "node",
    "machine learning": "machinelearning",
    "deep learning": "deeplearning",
}


def _limit_text(text, max_chars=MAX_TEXT_CHARS):
    return str(text or "")[:max_chars]


def normalize_phrase(text):
    text = _limit_text(text).lower()
    for source, target in PHRASE_ALIASES.items():
        text = text.replace(source, target)
    return text


def normalize_token(token):
    token = token.lower()
    return TECH_ALIASES.get(token, token)


def normalize_text(text):
    if not text:
        return []

    text = normalize_phrase(text)
    tokens = re.findall(r"\b[a-zA-Z]+\b", text)
    return [normalize_token(token) for token in tokens]


def simple_score(text, jd):
    text_words = set(normalize_text(text))
    jd_words = set(normalize_text(jd))
    return len(text_words & jd_words)


def rank_projects_by_overlap(projects, jd_text):
    if not projects:
        return []

    jd_tokens = set(normalize_text(jd_text))
    if not jd_tokens:
        return projects

    ranked = []
    for index, project in enumerate(projects):
        project_text = " ".join([
            str(project.get("title", "")),
            " ".join(project.get("tech_stack", []) or []),
            " ".join(project.get("points", []) or []),
        ])
        score = len(jd_tokens.intersection(normalize_text(project_text)))
        ranked.append((score, index, project))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [project for _, _, project in ranked]


def rank_projects_tfidf(projects, jd_text):
    """
    Backward-compatible alias for the old interface.
    Uses lightweight keyword overlap instead of TF-IDF.
    """
    return rank_projects_by_overlap(projects, jd_text)


def generate_insights(resume_tokens, jd_tokens, resume_skills, jd_skills):
    insights = []

    missing_skills = sorted(set(jd_skills) - set(resume_skills))
    if missing_skills:
        insights.append(f"Missing key skills: {', '.join(missing_skills[:3])}")

    if jd_tokens and len(jd_tokens.intersection(resume_tokens)) < max(2, len(jd_tokens) // 6):
        insights.append("Resume is weakly aligned with the job description")

    if len(resume_tokens) < 120:
        insights.append("Resume is too short - add more impact and measurable results")

    if jd_tokens and len(jd_tokens.intersection(resume_tokens)) >= max(3, len(jd_tokens) // 3):
        insights.append("Projects and experience align well with the target role")

    return insights[:4]


def confidence_score(resume_tokens):
    length_factor = min(len(resume_tokens) / 250, 1)
    return int(55 + length_factor * 35)


def _empty_score():
    return {
        "score": 0,
        "breakdown": {"keywords": 0, "skills": 0, "experience": 0, "projects": 0},
        "insights": [],
        "confidence": 55,
    }


def _resume_to_text(resume_json):
    if isinstance(resume_json, str):
        return _limit_text(resume_json)

    parts = [
        str(resume_json.get("summary", "")),
        " ".join(resume_json.get("technical_skills", []) or []),
        " ".join(resume_json.get("soft_skills", []) or []),
        " ".join(resume_json.get("languages", []) or []),
    ]

    for experience in resume_json.get("experience", []) or []:
        parts.append(str(experience.get("role", "")))
        parts.append(str(experience.get("company", "")))
        parts.append(" ".join(experience.get("points", []) or []))

    for project in resume_json.get("projects", []) or []:
        parts.append(str(project.get("title", "")))
        parts.append(" ".join(project.get("tech_stack", []) or []))
        parts.append(" ".join(project.get("points", []) or []))

    return _limit_text(" ".join(parts))


def compute_ats_score(resume_json, jd_text, jd_skills=None):
    jd_text = _limit_text(jd_text)
    if not jd_text.strip():
        return _empty_score()

    jd_tokens = set(normalize_text(jd_text))
    if not jd_tokens:
        return _empty_score()

    if jd_skills is None:
        jd_skills = list(jd_tokens)[:20]
    else:
        jd_skills = normalize_text(" ".join(jd_skills))

    if isinstance(resume_json, str):
        resume_text = _limit_text(resume_json)
        resume_tokens = set(normalize_text(resume_text))
        keyword_overlap = len(jd_tokens.intersection(resume_tokens))
        keyword_pts = int(min(40, keyword_overlap / max(1, len(jd_tokens)) * 40))

        insights = generate_insights(resume_tokens, jd_tokens, [], jd_skills)
        confidence = confidence_score(resume_tokens)

        return {
            "score": keyword_pts,
            "breakdown": {"keywords": keyword_pts, "skills": 0, "experience": 0, "projects": 0},
            "insights": insights,
            "confidence": confidence,
        }

    resume_text = _resume_to_text(resume_json)
    resume_tokens = set(normalize_text(resume_text))

    resume_skills_raw = (
        (resume_json.get("technical_skills", []) or []) +
        (resume_json.get("soft_skills", []) or []) +
        (resume_json.get("languages", []) or [])
    )
    resume_skills = set(normalize_text(" ".join(resume_skills_raw)))

    keyword_overlap = len(jd_tokens.intersection(resume_tokens))
    keyword_pts = int(min(40, keyword_overlap / max(1, len(jd_tokens)) * 40))

    matched_skills = len(set(jd_skills).intersection(resume_skills))
    skill_pts = int(min(30, matched_skills / max(1, len(jd_skills)) * 30)) if jd_skills else 0

    experience_text = _limit_text(" ".join(
        " ".join([
            str(exp.get("role", "")),
            str(exp.get("company", "")),
            " ".join(exp.get("points", []) or []),
        ])
        for exp in (resume_json.get("experience", []) or [])
    ))
    experience_pts = int(min(20, simple_score(experience_text, jd_text) / max(1, len(jd_tokens)) * 20))

    project_text = _limit_text(" ".join(
        " ".join([
            str(project.get("title", "")),
            " ".join(project.get("tech_stack", []) or []),
            " ".join(project.get("points", []) or []),
        ])
        for project in (resume_json.get("projects", []) or [])
    ))
    project_pts = int(min(10, simple_score(project_text, jd_text) / max(1, len(jd_tokens)) * 10))

    total_score = max(0, min(keyword_pts + skill_pts + experience_pts + project_pts, 100))
    insights = generate_insights(resume_tokens, jd_tokens, resume_skills, jd_skills)
    confidence = confidence_score(resume_tokens)

    return {
        "score": total_score,
        "breakdown": {
            "keywords": keyword_pts,
            "skills": skill_pts,
            "experience": experience_pts,
            "projects": project_pts,
        },
        "insights": insights,
        "confidence": confidence,
    }


def score_label(score):
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Needs Improvement"
    return "Poor"


def cached_ats_score(resume_text, jd_text):
    """
    Keep the existing function name but avoid caching large request payloads in memory.
    """
    if isinstance(resume_text, dict):
        try:
            resume_payload = json.loads(json.dumps(resume_text))
        except Exception:
            resume_payload = resume_text
    else:
        resume_payload = str(resume_text)

    return compute_ats_score(resume_payload, jd_text)
