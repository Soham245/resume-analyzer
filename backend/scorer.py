"""
ATS scoring engine.

Weighted breakdown (100 total):
  - Skills Match              35
  - Experience Relevance      25
  - Projects                  15
  - Education                 10
  - Certifications            10
  - Structure / Readability    5

Scores are computed entirely from the resume data passed in (dict or raw text)
against the job description. There is no caching, no hardcoded fallback, and
no static "improvement" floor.
"""

import json
import re
from collections import Counter

MAX_TEXT_CHARS = 6000

CATEGORY_WEIGHTS = {
    "skills": 35,
    "experience": 25,
    "projects": 15,
    "education": 10,
    "certifications": 10,
    "structure": 5,
}

# ── Canonical skill registry ────────────────────────────────────────────────
# canonical display form -> set of lowercase aliases
CANONICAL_SKILLS = {
    "JavaScript": {"javascript", "js", "ecmascript", "java script"},
    "TypeScript": {"typescript", "ts"},
    "Python": {"python", "python3", "py"},
    "Java": {"java"},
    "C++": {"c++", "cpp", "cplusplus"},
    "C#": {"c#", "csharp"},
    "C": {"c"},
    "Go": {"go", "golang"},
    "Rust": {"rust"},
    "Ruby": {"ruby"},
    "PHP": {"php"},
    "Swift": {"swift"},
    "Kotlin": {"kotlin"},
    "Scala": {"scala"},
    "MATLAB": {"matlab"},
    "Perl": {"perl"},
    "Bash": {"bash"},
    "Shell": {"shell", "shell scripting"},
    "HTML": {"html", "html5"},
    "CSS": {"css", "css3"},
    "SQL": {"sql"},
    "React": {"react", "reactjs", "react.js"},
    "React Native": {"react native", "react-native"},
    "Vue.js": {"vue", "vuejs", "vue.js"},
    "Angular": {"angular", "angularjs", "angular.js"},
    "Node.js": {"node", "nodejs", "node.js", "node js"},
    "Express.js": {"express", "expressjs", "express.js"},
    "Next.js": {"next", "nextjs", "next.js"},
    "Nuxt.js": {"nuxt", "nuxtjs", "nuxt.js"},
    "Django": {"django"},
    "Flask": {"flask"},
    "FastAPI": {"fastapi", "fast api"},
    "Spring": {"spring"},
    "Spring Boot": {"spring boot", "springboot"},
    "Rails": {"rails", "ruby on rails"},
    "Laravel": {"laravel"},
    "TensorFlow": {"tensorflow", "tensor flow"},
    "PyTorch": {"pytorch", "torch"},
    "Keras": {"keras"},
    "scikit-learn": {"sklearn", "scikit-learn", "scikit learn"},
    "Pandas": {"pandas"},
    "NumPy": {"numpy"},
    "SciPy": {"scipy"},
    "Bootstrap": {"bootstrap"},
    "Tailwind CSS": {"tailwind", "tailwindcss", "tailwind css"},
    "jQuery": {"jquery"},
    "Redux": {"redux"},
    "Svelte": {"svelte"},
    "MySQL": {"mysql"},
    "PostgreSQL": {"postgresql", "postgres", "postgressql", "psql"},
    "SQLite": {"sqlite"},
    "MongoDB": {"mongodb", "mongo"},
    "Redis": {"redis"},
    "Cassandra": {"cassandra"},
    "DynamoDB": {"dynamodb", "dynamo"},
    "Oracle": {"oracle"},
    "SQL Server": {"sql server", "mssql", "ms sql"},
    "Elasticsearch": {"elasticsearch", "elastic search"},
    "Firebase": {"firebase"},
    "Supabase": {"supabase"},
    "Neo4j": {"neo4j"},
    "MariaDB": {"mariadb"},
    "Docker": {"docker"},
    "Kubernetes": {"kubernetes", "k8s"},
    "Git": {"git"},
    "GitHub": {"github"},
    "GitHub Actions": {"github actions"},
    "GitLab CI": {"gitlab ci", "gitlab-ci"},
    "Linux": {"linux", "unix"},
    "AWS": {"aws", "amazon web services"},
    "GCP": {"gcp", "google cloud", "google cloud platform"},
    "Azure": {"azure", "microsoft azure"},
    "REST APIs": {"rest", "rest api", "rest apis", "restful", "restful api", "restful apis"},
    "GraphQL": {"graphql", "graph ql"},
    "Nginx": {"nginx"},
    "Apache": {"apache"},
    "Jenkins": {"jenkins"},
    "CI/CD": {"ci/cd", "cicd", "ci cd"},
    "Webpack": {"webpack"},
    "Vite": {"vite"},
    "Jest": {"jest"},
    "Pytest": {"pytest"},
    "Postman": {"postman"},
    "Swagger": {"swagger", "openapi"},
    "Terraform": {"terraform"},
    "Ansible": {"ansible"},
    "Helm": {"helm"},
    "Prometheus": {"prometheus"},
    "Grafana": {"grafana"},
    "Kafka": {"kafka", "apache kafka"},
    "RabbitMQ": {"rabbitmq", "rabbit mq"},
    "Celery": {"celery"},
    "Machine Learning": {"machine learning", "ml"},
    "Deep Learning": {"deep learning", "dl"},
    "NLP": {"nlp", "natural language processing"},
    "Computer Vision": {"computer vision"},
    "Data Analysis": {"data analysis", "data analytics"},
    "Data Engineering": {"data engineering"},
    "ETL": {"etl"},
    "Tableau": {"tableau"},
    "Power BI": {"power bi", "powerbi"},
    "Excel": {"excel", "microsoft excel"},
    "Figma": {"figma"},
    "Jira": {"jira"},
    "Agile": {"agile"},
    "Scrum": {"scrum"},
    "Kanban": {"kanban"},
}

_ALIAS_TO_CANONICAL = {}
for _canon, _aliases in CANONICAL_SKILLS.items():
    _ALIAS_TO_CANONICAL[_canon.lower()] = _canon
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[_alias.lower()] = _canon


# ── Capitalization / normalization helpers ──────────────────────────────────
_PRESERVE_UPPER = frozenset({"aws", "gcp", "sql", "html", "css", "nlp", "etl", "api", "ai", "ml"})


def _capitalize_token(token):
    if not token:
        return token
    lower = token.lower()
    if lower in _PRESERVE_UPPER:
        return lower.upper()
    if "." in token:
        head, _, tail = token.partition(".")
        return head[:1].upper() + head[1:].lower() + "." + tail.lower()
    return token[:1].upper() + token[1:].lower()


def _smart_titlecase(text):
    parts = re.split(r"([\s/\-])", text)
    return "".join(_capitalize_token(p) if not re.match(r"^[\s/\-]+$", p or "") else p for p in parts)


def canonicalize_skill(skill):
    """Return canonical display form for a skill string."""
    if not skill or not isinstance(skill, str):
        return ""
    cleaned = re.sub(r"\s+", " ", skill).strip().strip(",;:.|/")
    if not cleaned:
        return ""
    canonical = _ALIAS_TO_CANONICAL.get(cleaned.lower())
    if canonical:
        return canonical
    return _smart_titlecase(cleaned)


def canonicalize_skill_list(skills):
    """Canonicalize and de-duplicate a list of skill strings."""
    seen = set()
    out = []
    for raw in skills or []:
        canon = canonicalize_skill(raw)
        if not canon:
            continue
        key = canon.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(canon)
    return out


# ── Skill detection in text ─────────────────────────────────────────────────
_SKILL_PATTERN_CACHE = {}


def _skill_pattern(canonical):
    if canonical in _SKILL_PATTERN_CACHE:
        return _SKILL_PATTERN_CACHE[canonical]
    aliases = set(CANONICAL_SKILLS.get(canonical, set()))
    aliases.add(canonical.lower())
    # Sort by length desc so longer aliases match first.
    parts = sorted({re.escape(a) for a in aliases if a}, key=len, reverse=True)
    pattern = r"(?<![A-Za-z0-9])(?:" + "|".join(parts) + r")(?![A-Za-z0-9])"
    compiled = re.compile(pattern, re.IGNORECASE)
    _SKILL_PATTERN_CACHE[canonical] = compiled
    return compiled


def find_skill_counts(text, skill_list):
    """
    Scan `text` for each skill in `skill_list` (canonicalized first).
    Returns Counter: {canonical_skill: occurrence_count}.
    """
    text = str(text or "")
    counts = Counter()
    if not text:
        return counts
    for skill in skill_list or []:
        canon = canonicalize_skill(skill)
        if not canon or canon in counts:
            continue
        pattern = _skill_pattern(canon)
        n = len(pattern.findall(text))
        if n > 0:
            counts[canon] = n
    return counts


# ── Resume text assembly ────────────────────────────────────────────────────
def _limit_text(text, max_chars=MAX_TEXT_CHARS):
    return str(text or "")[:max_chars]


def _resume_full_text(resume_json):
    if isinstance(resume_json, str):
        return _limit_text(resume_json)
    if not isinstance(resume_json, dict):
        return ""

    parts = [
        str(resume_json.get("name", "")),
        str(resume_json.get("title", "")),
        str(resume_json.get("summary", "")),
        " ".join(resume_json.get("technical_skills", []) or []),
        " ".join(resume_json.get("soft_skills", []) or []),
        " ".join(resume_json.get("languages", []) or []),
    ]
    for exp in resume_json.get("experience", []) or []:
        parts.append(str(exp.get("role", "")))
        parts.append(str(exp.get("company", "")))
        parts.append(str(exp.get("duration", "")))
        parts.append(" ".join(exp.get("points", []) or []))
    for proj in resume_json.get("projects", []) or []:
        parts.append(str(proj.get("title", "")))
        parts.append(" ".join(proj.get("tech_stack", []) or []))
        parts.append(" ".join(proj.get("points", []) or []))
    for edu in resume_json.get("education", []) or []:
        parts.append(str(edu.get("degree", "")))
        parts.append(str(edu.get("institution", "")))
        parts.append(str(edu.get("year", "")))
    parts.append(" ".join(resume_json.get("certifications", []) or []))
    return _limit_text(" ".join(p for p in parts if p))


def _experience_text(resume_json):
    if not isinstance(resume_json, dict):
        return ""
    chunks = []
    for exp in resume_json.get("experience", []) or []:
        chunks.append(str(exp.get("role", "")))
        chunks.append(str(exp.get("company", "")))
        chunks.append(" ".join(exp.get("points", []) or []))
    return " ".join(c for c in chunks if c)


def _project_text(resume_json):
    if not isinstance(resume_json, dict):
        return ""
    chunks = []
    for proj in resume_json.get("projects", []) or []:
        chunks.append(str(proj.get("title", "")))
        chunks.append(" ".join(proj.get("tech_stack", []) or []))
        chunks.append(" ".join(proj.get("points", []) or []))
    return " ".join(c for c in chunks if c)


# ── Project ranking (used by rewriter) ──────────────────────────────────────
def _tokenize(text):
    return set(re.findall(r"[a-zA-Z]{2,}", str(text or "").lower()))


def rank_projects_by_overlap(projects, jd_text):
    if not projects:
        return []
    jd_tokens = _tokenize(jd_text)
    if not jd_tokens:
        return list(projects)
    ranked = []
    for index, project in enumerate(projects):
        project_text = " ".join([
            str(project.get("title", "")),
            " ".join(project.get("tech_stack", []) or []),
            " ".join(project.get("points", []) or []),
        ])
        score = len(jd_tokens & _tokenize(project_text))
        ranked.append((score, index, project))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [project for _, _, project in ranked]


def rank_projects_tfidf(projects, jd_text):
    return rank_projects_by_overlap(projects, jd_text)


# ── Category scorers ────────────────────────────────────────────────────────
_ACHIEVEMENT_PATTERN = re.compile(
    r"(\b\d+(?:[\.,]\d+)?\s?(?:%|percent|x|times|users|customers|requests|"
    r"hours|hrs|seconds|secs|ms|days|weeks|months|years|k|m|million|billion|"
    r"\+)\b)",
    re.IGNORECASE,
)
_NUMBER_PATTERN = re.compile(r"\b\d+(?:[\.,]\d+)?\b")


def _count_achievements(text):
    if not text:
        return 0
    return len(_ACHIEVEMENT_PATTERN.findall(text)) + len(_NUMBER_PATTERN.findall(text)) // 2


def _score_skills(resume_text, jd_skills_canonical, jd_freq):
    """Return (points 0..35, matched list, missing list, debug dict)."""
    weight = CATEGORY_WEIGHTS["skills"]
    if not jd_skills_canonical:
        return 0, [], [], {"reason": "no_jd_skills"}

    resume_counts = find_skill_counts(resume_text, jd_skills_canonical)
    matched = [s for s in jd_skills_canonical if s in resume_counts]
    missing = [s for s in jd_skills_canonical if s not in resume_counts]

    coverage = len(matched) / len(jd_skills_canonical)
    base = coverage * weight

    # Weighted coverage: skills that appear more often in JD count more.
    total_weight = sum(jd_freq.get(s, 1) for s in jd_skills_canonical)
    matched_weight = sum(jd_freq.get(s, 1) for s in matched)
    weighted_coverage = matched_weight / max(1, total_weight)
    base = 0.5 * base + 0.5 * weighted_coverage * weight

    # Penalize keyword stuffing: any single skill appearing >5 times.
    stuff_penalty = 0
    for skill, count in resume_counts.items():
        if count > 5:
            stuff_penalty += min(2, (count - 5) * 0.5)
    base = max(0, base - stuff_penalty)

    points = int(round(min(weight, base)))
    debug = {
        "coverage": round(coverage, 3),
        "weighted_coverage": round(weighted_coverage, 3),
        "stuff_penalty": round(stuff_penalty, 2),
        "matched": matched,
        "missing": missing[:10],
    }
    return points, matched, missing, debug


_EXPERIENCE_HINTS = re.compile(
    r"\b(experience|worked|employed|intern(ship)?|engineer|developer|designer|"
    r"manager|analyst|consultant|years?|present|full-?time|part-?time)\b",
    re.IGNORECASE,
)
_PROJECT_HINTS = re.compile(r"\b(project|built|developed|implemented|designed|created|launched|deployed)\b", re.IGNORECASE)
_EDUCATION_HINTS = re.compile(
    r"\b(b\.?tech|m\.?tech|b\.?sc|m\.?sc|b\.?e\b|m\.?e\b|b\.?a\b|m\.?a\b|"
    r"bachelor|master|ph\.?d|degree|university|college|institute|school|gpa|cgpa)\b",
    re.IGNORECASE,
)
_CERT_HINTS = re.compile(r"\b(certif(ied|ication|icate)|credential)\b", re.IGNORECASE)


def _score_experience(resume_json, jd_text, jd_skills_canonical):
    weight = CATEGORY_WEIGHTS["experience"]
    if not isinstance(resume_json, dict):
        text = _resume_full_text(resume_json)
        if not text or not _EXPERIENCE_HINTS.search(text):
            return 0, {"reason": "no_experience_signal"}
        return _score_experience_text(text, jd_text, jd_skills_canonical, weight, has_structure=False)

    experiences = resume_json.get("experience", []) or []
    if not experiences:
        return 0, {"reason": "no_experience"}

    text = _experience_text(resume_json)
    return _score_experience_text(text, jd_text, jd_skills_canonical, weight, has_structure=True,
                                  entry_count=len(experiences))


def _score_experience_text(text, jd_text, jd_skills_canonical, weight, has_structure, entry_count=0):
    if not text:
        return 0, {"reason": "empty_experience"}

    # Presence: 4pts (only if structured)
    presence_pts = 4 if has_structure and entry_count > 0 else 0

    # Skill overlap in experience: up to 12pts
    skill_counts = find_skill_counts(text, jd_skills_canonical)
    if jd_skills_canonical:
        overlap = len(skill_counts) / len(jd_skills_canonical)
    else:
        overlap = 0
    overlap_pts = overlap * 12

    # JD keyword overlap (non-skill tokens): up to 5pts
    jd_tokens = _tokenize(jd_text)
    exp_tokens = _tokenize(text)
    if jd_tokens:
        keyword_overlap = len(jd_tokens & exp_tokens) / len(jd_tokens)
    else:
        keyword_overlap = 0
    keyword_pts = keyword_overlap * 5

    # Measurable achievements: up to 4pts
    achievements = _count_achievements(text)
    achievement_pts = min(4, achievements * 0.8)

    raw = presence_pts + overlap_pts + keyword_pts + achievement_pts
    points = int(round(min(weight, raw)))
    debug = {
        "presence_pts": presence_pts,
        "skill_overlap": round(overlap, 3),
        "keyword_overlap": round(keyword_overlap, 3),
        "achievements": achievements,
        "raw": round(raw, 2),
    }
    return points, debug


def _score_projects(resume_json, jd_text, jd_skills_canonical):
    weight = CATEGORY_WEIGHTS["projects"]
    if not isinstance(resume_json, dict):
        text = _resume_full_text(resume_json)
        if not text or not _PROJECT_HINTS.search(text):
            return 0, {"reason": "no_project_signal"}
        # Partial credit: assume one "project-like" block, no measurable bonus.
        skill_counts = find_skill_counts(text, jd_skills_canonical)
        if jd_skills_canonical:
            skill_overlap = len(skill_counts) / len(jd_skills_canonical)
        else:
            skill_overlap = 0
        raw = 2 + skill_overlap * 6 + min(2, _count_achievements(text) * 0.4)
        return int(round(min(weight, raw))), {"reason": "raw_text", "skill_overlap": round(skill_overlap, 3)}

    projects = resume_json.get("projects", []) or []
    if not projects:
        return 0, {"reason": "no_projects"}

    text = _project_text(resume_json)
    if not text:
        return 0, {"reason": "empty_projects"}

    # Presence: 3pts
    presence_pts = 3

    # Tech stack / skill match: up to 7pts
    skill_counts = find_skill_counts(text, jd_skills_canonical)
    if jd_skills_canonical:
        skill_overlap = len(skill_counts) / len(jd_skills_canonical)
    else:
        skill_overlap = 0
    skill_pts = skill_overlap * 7

    # Measurable bullets: up to 3pts
    achievements = _count_achievements(text)
    achievement_pts = min(3, achievements * 0.6)

    # Bonus for multiple projects: up to 2pts
    multi_pts = min(2, max(0, len(projects) - 1) * 0.7)

    raw = presence_pts + skill_pts + achievement_pts + multi_pts
    points = int(round(min(weight, raw)))
    debug = {
        "count": len(projects),
        "skill_overlap": round(skill_overlap, 3),
        "achievements": achievements,
        "raw": round(raw, 2),
    }
    return points, debug


def _score_education(resume_json):
    weight = CATEGORY_WEIGHTS["education"]
    if not isinstance(resume_json, dict):
        text = _resume_full_text(resume_json)
        if text and _EDUCATION_HINTS.search(text):
            return 5, {"reason": "raw_text_match"}
        return 0, {"reason": "raw_text_no_match"}

    education = resume_json.get("education", []) or []
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
    points = int(round(min(weight, pts)))
    debug = {"count": len(education), "well_structured": well_structured}
    return points, debug


def _score_certifications(resume_json, jd_text, jd_skills_canonical):
    weight = CATEGORY_WEIGHTS["certifications"]
    if not isinstance(resume_json, dict):
        text = _resume_full_text(resume_json)
        if text and _CERT_HINTS.search(text):
            return 4, {"reason": "raw_text_match"}
        return 0, {"reason": "raw_text_no_match"}

    certs = resume_json.get("certifications", []) or []
    if not certs:
        return 0, {"reason": "no_certifications"}

    count = sum(1 for c in certs if str(c or "").strip())
    if count == 0:
        return 0, {"reason": "blank_certifications"}

    # Base on count
    if count >= 3:
        base = 6
    elif count == 2:
        base = 4
    else:
        base = 3

    # Relevance bonus: certs that mention JD skills/keywords
    cert_text = " ".join(str(c or "") for c in certs)
    skill_hits = len(find_skill_counts(cert_text, jd_skills_canonical))
    jd_tokens = _tokenize(jd_text)
    keyword_hits = len(jd_tokens & _tokenize(cert_text)) if jd_tokens else 0
    relevance = min(4, skill_hits * 1.5 + keyword_hits * 0.2)

    points = int(round(min(weight, base + relevance)))
    debug = {"count": count, "skill_hits": skill_hits, "relevance": round(relevance, 2)}
    return points, debug


def _score_structure(resume_json):
    weight = CATEGORY_WEIGHTS["structure"]
    if not isinstance(resume_json, dict):
        text = str(resume_json or "")
        if len(text) >= 1200:
            return 3, {"reason": "raw_text_full"}
        if len(text) >= 400:
            return 2, {"reason": "raw_text_partial"}
        return 0, {"reason": "raw_text_short"}

    score = 0
    # Contact info present
    has_contact = bool(
        str(resume_json.get("email", "")).strip()
        and not str(resume_json.get("email", "")).startswith("[")
    )
    if has_contact:
        score += 1
    # Name + title
    if str(resume_json.get("name", "")).strip() and not str(resume_json.get("name", "")).startswith("["):
        score += 0.5
    if str(resume_json.get("title", "")).strip() and not str(resume_json.get("title", "")).startswith("["):
        score += 0.5
    # Summary
    if str(resume_json.get("summary", "")).strip():
        score += 1
    # Skills present
    if resume_json.get("technical_skills"):
        score += 1
    # Bulleted experience/projects
    bullet_count = 0
    for exp in resume_json.get("experience", []) or []:
        bullet_count += len(exp.get("points", []) or [])
    for proj in resume_json.get("projects", []) or []:
        bullet_count += len(proj.get("points", []) or [])
    if bullet_count >= 3:
        score += 1

    points = int(round(min(weight, score)))
    debug = {"score": score, "bullet_count": bullet_count}
    return points, debug


def _confidence(resume_json, jd_skills_canonical):
    """Confidence based on data completeness, not on score."""
    if not isinstance(resume_json, dict):
        text = str(resume_json or "")
        return max(55, min(85, 55 + len(text) // 60))

    filled_sections = 0
    total_sections = 6
    if resume_json.get("summary"):
        filled_sections += 1
    if resume_json.get("technical_skills"):
        filled_sections += 1
    if resume_json.get("experience"):
        filled_sections += 1
    if resume_json.get("projects"):
        filled_sections += 1
    if resume_json.get("education"):
        filled_sections += 1
    if resume_json.get("certifications"):
        filled_sections += 1

    base = 60 + int(filled_sections / total_sections * 30)
    if jd_skills_canonical and len(jd_skills_canonical) >= 5:
        base += 3
    return min(95, base)


def _build_insights(score_pieces, matched, missing, resume_json):
    insights = []
    if missing:
        top_missing = ", ".join(missing[:3])
        insights.append(f"Missing key skills: {top_missing}")

    skills_pts = score_pieces.get("skills", 0)
    if skills_pts >= 28:
        insights.append("Skills align strongly with the job description")
    elif skills_pts < 12:
        insights.append("Weak skill overlap with the job description")

    if isinstance(resume_json, dict):
        if not resume_json.get("experience"):
            insights.append("Add work experience to strengthen relevance")
        if not resume_json.get("projects"):
            insights.append("Add projects to demonstrate practical skill use")
        if not resume_json.get("certifications"):
            insights.append("Adding a relevant certification can boost credibility")

    exp_pts = score_pieces.get("experience", 0)
    if exp_pts and exp_pts < 8:
        insights.append("Experience bullets need measurable impact (numbers, %, scale)")

    return insights[:4]


# ── Missing-skills extraction ───────────────────────────────────────────────
def detect_missing_skills(resume_json_or_text, jd_skills, jd_text=""):
    """
    Returns canonical missing skills, ranked by JD frequency desc.
    Scans the entire resume content (all sections), not just the skills section.
    """
    jd_canonical = canonicalize_skill_list(jd_skills)
    resume_text = _resume_full_text(resume_json_or_text)
    resume_counts = find_skill_counts(resume_text, jd_canonical)

    jd_freq = find_skill_counts(jd_text or " ".join(jd_canonical), jd_canonical)
    missing = [s for s in jd_canonical if s not in resume_counts]
    missing.sort(key=lambda s: jd_freq.get(s, 0), reverse=True)
    return missing


def detect_matched_skills(resume_json_or_text, jd_skills):
    jd_canonical = canonicalize_skill_list(jd_skills)
    resume_text = _resume_full_text(resume_json_or_text)
    resume_counts = find_skill_counts(resume_text, jd_canonical)
    return [s for s in jd_canonical if s in resume_counts]


# ── Public entrypoint ───────────────────────────────────────────────────────
def compute_ats_score(resume_json, jd_text, jd_skills=None, debug=False):
    """
    Compute an ATS score from `resume_json` (dict or raw text) against `jd_text`.
    `jd_skills` is an optional list of skills extracted from the JD; if omitted,
    canonical skills are inferred from the JD text itself.
    """
    jd_text = _limit_text(jd_text)

    if jd_skills is None:
        jd_skills = list(_ALIAS_TO_CANONICAL.keys())  # consider all known skills
        # we'll filter by what actually appears in the JD below

    jd_canonical = canonicalize_skill_list(jd_skills)
    jd_freq_counter = find_skill_counts(jd_text, jd_canonical)
    # If caller passed `jd_skills=None`, restrict to skills actually present in JD.
    if jd_skills is None or (jd_skills and len(jd_skills) > 50):
        jd_canonical = [s for s in jd_canonical if s in jd_freq_counter]

    resume_text = _resume_full_text(resume_json)

    skills_pts, matched, missing, skills_debug = _score_skills(resume_text, jd_canonical, jd_freq_counter)
    exp_pts, exp_debug = _score_experience(resume_json, jd_text, jd_canonical)
    proj_pts, proj_debug = _score_projects(resume_json, jd_text, jd_canonical)
    edu_pts, edu_debug = _score_education(resume_json)
    cert_pts, cert_debug = _score_certifications(resume_json, jd_text, jd_canonical)
    struct_pts, struct_debug = _score_structure(resume_json)

    total = skills_pts + exp_pts + proj_pts + edu_pts + cert_pts + struct_pts
    total = max(0, min(100, total))

    breakdown = {
        "skills": skills_pts,
        "experience": exp_pts,
        "projects": proj_pts,
        "education": edu_pts,
        "certifications": cert_pts,
        "structure": struct_pts,
    }

    # Rank missing by JD frequency desc.
    missing.sort(key=lambda s: jd_freq_counter.get(s, 0), reverse=True)

    insights = _build_insights(breakdown, matched, missing, resume_json)
    confidence = _confidence(resume_json, jd_canonical)

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
            "skills": skills_debug,
            "experience": exp_debug,
            "projects": proj_debug,
            "education": edu_debug,
            "certifications": cert_debug,
            "structure": struct_debug,
            "jd_canonical": jd_canonical,
            "jd_freq": dict(jd_freq_counter),
        }
    return result


def score_label(score):
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Needs Improvement"
    return "Poor"


def cached_ats_score(resume_text, jd_text, jd_skills=None, debug=False):
    """
    Compatibility wrapper. Despite the name, scoring is NOT cached — the score
    must always reflect the current resume state.
    """
    if isinstance(resume_text, dict):
        try:
            resume_payload = json.loads(json.dumps(resume_text))
        except Exception:
            resume_payload = resume_text
    else:
        resume_payload = str(resume_text or "")
    return compute_ats_score(resume_payload, jd_text, jd_skills=jd_skills, debug=debug)
