from google import genai
from google.genai import types
import json
import logging
import re

logger = logging.getLogger(__name__)

_client_cache = {}


def get_client(api_key):
    if api_key not in _client_cache:
        _client_cache[api_key] = genai.Client(api_key=api_key)
    return _client_cache[api_key]


# Skill normalization and grouping used by the resume builder/output layer.
_NORMALIZATIONS = {
    "nodejs": "Node.js", "node": "Node.js",
    "reactjs": "React", "react.js": "React",
    "vuejs": "Vue.js", "vue": "Vue.js",
    "angularjs": "Angular", "angular.js": "Angular",
    "expressjs": "Express.js", "express": "Express.js",
    "nextjs": "Next.js", "next.js": "Next.js",
    "github": "Git", "git/github": "Git", "git & github": "Git",
    "tailwindcss": "Tailwind CSS", "tailwind": "Tailwind CSS",
    "html5": "HTML", "css3": "CSS",
    "restful": "REST APIs", "rest api": "REST APIs", "rest apis": "REST APIs",
    "ml": "Machine Learning", "dl": "Deep Learning",
    "sklearn": "scikit-learn", "scikit learn": "scikit-learn",
    "postgres": "PostgreSQL", "postgressql": "PostgreSQL",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch",
}

_EXCLUDED = frozenset({
    "vs code", "vscode", "visual studio code", "visual studio", "intellij",
    "intellij idea", "pycharm", "webstorm", "eclipse", "netbeans", "xcode",
    "android studio", "sublime text", "atom", "vim", "emacs",
    "data structures", "algorithms", "operating systems", "dbms",
    "database management", "computer networks", "object oriented programming",
    "oop", "oops", "software engineering", "computer science",
    "web development", "software development",
    "full stack", "frontend", "backend", "front-end", "back-end",
    "artificial intelligence", "ai", "computer vision", "big data",
    "cloud computing", "internet of things", "iot", "blockchain",
    "programming", "coding", "development", "debugging",
    "windows", "macos", "ubuntu",
})

_PROGRAMMING = frozenset({
    "python", "javascript", "typescript", "java", "c", "c++", "c#", "go",
    "rust", "ruby", "php", "swift", "kotlin", "r", "scala", "matlab",
    "perl", "bash", "shell", "html", "css", "sql",
})

_FRAMEWORKS = frozenset({
    "react", "vue.js", "angular", "node.js", "express.js", "next.js",
    "nuxt.js", "django", "flask", "fastapi", "spring", "spring boot",
    "rails", "laravel", "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "scipy", "bootstrap", "tailwind css", "jquery",
    "redux", "svelte", "fastify", "nest.js",
})

_DATABASES = frozenset({
    "mysql", "postgresql", "sqlite", "mongodb", "redis", "cassandra",
    "dynamodb", "oracle", "sql server", "elasticsearch", "firebase",
    "supabase", "neo4j", "couchdb", "mariadb", "influxdb",
})

_TOOLS = frozenset({
    "docker", "kubernetes", "git", "linux", "aws", "gcp", "azure",
    "rest apis", "graphql", "nginx", "apache", "jenkins", "ci/cd",
    "github actions", "gitlab ci", "webpack", "vite", "jest", "pytest",
    "postman", "swagger", "terraform", "ansible", "helm", "prometheus",
    "grafana", "kafka", "rabbitmq", "celery", "machine learning",
    "deep learning", "nlp",
})

_SKILL_KEYS = ("technical", "soft", "languages")
_SKILL_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite-preview",
)

_EMPTY_SKILL_STRUCTURE = {key: [] for key in _SKILL_KEYS}

_FORBIDDEN_SKILL_PHRASES = (
    "best practices",
    "high quality",
    "performance",
    "reliability",
    "seamless",
    "interaction",
    "professional",
    "structured",
)

_EXTRACTION_NORMALIZATIONS = {
    "react.js": "react",
    "reactjs": "react",
    "python3": "python",
    "node": "node.js",
    "nodejs": "node.js",
    "express": "express.js",
    "expressjs": "express.js",
    "nextjs": "next.js",
    "vue": "vue.js",
    "vuejs": "vue.js",
    "angularjs": "angular",
    "angular.js": "angular",
    "tailwindcss": "tailwind css",
    "restful": "rest apis",
    "rest api": "rest apis",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "postgres": "postgresql",
    "postgressql": "postgresql",
    "ml": "machine learning",
    "dl": "deep learning",
}

_CANONICAL_ALIASES = {}
for alias, canonical in _EXTRACTION_NORMALIZATIONS.items():
    _CANONICAL_ALIASES.setdefault(canonical, set()).update({alias, canonical})

_KNOWN_TECHNICAL_SKILLS = frozenset(
    set(_PROGRAMMING) | set(_FRAMEWORKS) | set(_DATABASES) | set(_TOOLS)
)

_KNOWN_HUMAN_LANGUAGES = frozenset({
    "english", "hindi", "spanish", "french", "german", "arabic", "mandarin",
    "chinese", "japanese", "korean", "portuguese", "italian", "russian",
    "bengali", "tamil", "telugu", "marathi", "urdu", "gujarati", "punjabi",
    "dutch", "polish", "turkish",
})


def _empty_skill_structure():
    return {key: [] for key in _SKILL_KEYS}


def filter_and_group_skills(technical_list):
    """
    Filter and group a flat technical skills list into categories.
    Returns dict with keys 'programming', 'frameworks', 'databases', 'tools'.
    Empty categories are omitted. Each category is capped at 4 items.
    """
    seen = set()
    groups = {"programming": [], "frameworks": [], "databases": [], "tools": []}

    for raw in (technical_list or []):
        if not raw or not raw.strip():
            continue

        key = raw.strip().lower()
        normalized = _NORMALIZATIONS.get(key, raw.strip())
        norm_key = normalized.lower()

        if norm_key in _EXCLUDED or key in _EXCLUDED:
            continue
        if norm_key in seen:
            continue
        seen.add(norm_key)

        if norm_key in _PROGRAMMING:
            bucket = "programming"
        elif norm_key in _FRAMEWORKS:
            bucket = "frameworks"
        elif norm_key in _DATABASES:
            bucket = "databases"
        elif norm_key in _TOOLS:
            bucket = "tools"
        else:
            bucket = "tools"

        if len(groups[bucket]) < 4:
            groups[bucket].append(normalized)

    return {key: value for key, value in groups.items() if value}


def _extract_json(raw_output):
    """Extract JSON from a model response that may contain markdown or extra text."""
    if not raw_output:
        return None

    raw_output = raw_output.strip()
    match = re.search(r"`{3}(?:json)?\s*([\s\S]*?)\s*`{3}", raw_output)
    if match:
        return match.group(1).strip()

    start = raw_output.find("{")
    end = raw_output.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw_output[start:end + 1]

    return None


def _clean_whitespace(value):
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize_skill(skill):
    cleaned = _clean_whitespace(skill).lower().strip(" ,;:.|/-")
    if not cleaned:
        return ""
    return _EXTRACTION_NORMALIZATIONS.get(cleaned, cleaned)


def _tokenize_for_match(text):
    return re.findall(r"[a-z0-9][a-z0-9.+#/-]*", (text or "").lower())


def _candidate_variants(raw_skill, normalized_skill):
    variants = {
        _clean_whitespace(raw_skill).lower(),
        normalized_skill,
    }
    variants.update(_CANONICAL_ALIASES.get(normalized_skill, set()))
    for variant in list(variants):
        canonical = _EXTRACTION_NORMALIZATIONS.get(variant)
        if canonical:
            variants.add(canonical)
            variants.update(_CANONICAL_ALIASES.get(canonical, set()))
    return {variant for variant in variants if variant}


def _tokens_contain_phrase(source_tokens, candidate_tokens):
    if not candidate_tokens or len(candidate_tokens) > len(source_tokens):
        return False

    limit = len(source_tokens) - len(candidate_tokens) + 1
    for index in range(limit):
        if source_tokens[index:index + len(candidate_tokens)] == candidate_tokens:
            return True
    return False


def _skill_exists_in_source(raw_skill, normalized_skill, source_tokens):
    for candidate in _candidate_variants(raw_skill, normalized_skill):
        candidate_tokens = _tokenize_for_match(candidate)
        if _tokens_contain_phrase(source_tokens, candidate_tokens):
            return True
    return False


def _has_forbidden_phrase(skill):
    return any(phrase in skill for phrase in _FORBIDDEN_SKILL_PHRASES)


def _resolve_skill_category(skill, original_category):
    if skill in _KNOWN_TECHNICAL_SKILLS:
        return "technical"
    if skill in _KNOWN_HUMAN_LANGUAGES:
        return "languages"
    return original_category if original_category in _SKILL_KEYS else "soft"


def _validate_skill_candidate(raw_skill, category, source_tokens, seen_skills):
    if not isinstance(raw_skill, str):
        return None, "not_a_string"

    normalized_skill = _normalize_skill(raw_skill)
    if not normalized_skill:
        return None, "empty"

    if _has_forbidden_phrase(normalized_skill):
        return None, "forbidden_phrase"

    if len(normalized_skill.split()) > 3:
        return None, "too_many_words"

    if normalized_skill in seen_skills:
        return None, "duplicate"

    if not _skill_exists_in_source(raw_skill, normalized_skill, source_tokens):
        return None, "missing_from_source"

    return (normalized_skill, _resolve_skill_category(normalized_skill, category)), None


def _validate_skill_structure(skill_payload, source_text, source_label):
    if not isinstance(skill_payload, dict):
        logger.warning("[%s] Invalid skill payload type: %s", source_label, type(skill_payload).__name__)
        logger.info("[%s] Filtered output: %s", source_label, _EMPTY_SKILL_STRUCTURE)
        logger.info("[%s] Removed skills: %s", source_label, [{"skill": None, "reason": "invalid_payload"}])
        return _empty_skill_structure()

    source_tokens = _tokenize_for_match(source_text)
    cleaned = _empty_skill_structure()
    seen_skills = set()
    removed_skills = []

    for category in _SKILL_KEYS:
        raw_values = skill_payload.get(category, [])
        if not isinstance(raw_values, list):
            removed_skills.append({
                "category": category,
                "skill": raw_values,
                "reason": "category_not_list",
            })
            continue

        for raw_skill in raw_values:
            validated_result, reason = _validate_skill_candidate(
                raw_skill,
                category,
                source_tokens,
                seen_skills,
            )

            if not validated_result:
                removed_skills.append({
                    "category": category,
                    "skill": raw_skill,
                    "reason": reason,
                })
                continue

            normalized_skill, resolved_category = validated_result
            seen_skills.add(normalized_skill)
            cleaned[resolved_category].append(normalized_skill)

    # Rebalance after normalization so known languages/technologies land in stable buckets.
    rebalanced = _empty_skill_structure()
    for category in _SKILL_KEYS:
        for skill in cleaned[category]:
            resolved_category = _resolve_skill_category(skill, category)
            if skill not in rebalanced[resolved_category]:
                rebalanced[resolved_category].append(skill)

    logger.info("[%s] Filtered output: %s", source_label, rebalanced)
    logger.info("[%s] Removed skills: %s", source_label, removed_skills)
    return rebalanced


def _parse_skill_payload(raw_output, source_text, source_label):
    logger.info("[%s] Raw AI output: %s", source_label, raw_output)

    extracted = _extract_json(raw_output)
    if not extracted:
        logger.warning("[%s] No JSON found in AI output.", source_label)
        return _empty_skill_structure()

    try:
        parsed = json.loads(extracted)
    except json.JSONDecodeError as exc:
        logger.warning("[%s] Failed to parse skill JSON: %s", source_label, exc)
        return _empty_skill_structure()

    required_keys = set(_SKILL_KEYS)
    if not isinstance(parsed, dict) or not required_keys.issubset(parsed.keys()):
        logger.warning("[%s] Skill JSON missing required keys.", source_label)
        return _empty_skill_structure()

    return _validate_skill_structure(parsed, source_text, source_label)


def _generate_json_response(prompt, api_key, source_label):
    client = get_client(api_key)

    for model_name in _SKILL_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0),
            )
            logger.info("[%s] Skill extraction succeeded with model %s", source_label, model_name)
            return (response.text or "").strip()
        except Exception as exc:
            logger.warning("[%s] Skill extraction failed with model %s: %s", source_label, model_name, exc)

    raise RuntimeError(f"All skill extraction models failed for {source_label}.")


def _build_single_text_skill_prompt(text):
    return f"""
Return ONLY valid JSON with this exact schema:
{{
  "technical": [],
  "soft": [],
  "languages": []
}}

Extract skills from the TEXT below using these strict rules:
- Only include skills that are explicitly written in the text.
- Copy the exact skill wording from the text before normalization. Do not infer, paraphrase, expand, summarize, or rewrite.
- Never convert a sentence, clause, responsibility, or achievement into a skill.
- Reject vague phrases and generic descriptors such as "best practices", "high quality", "performance", "reliability", "professional", or "structured".
- Reject any item longer than 3 words.
- technical: tools, technologies, programming languages, frameworks, databases, platforms, software, and specific domain terms or processes (e.g., "data annotation", "visual reasoning"). If a technical phrase exists in the text and is 1-3 words, allow it.
- soft: directly named interpersonal or workplace skills only.
- languages: human languages only.
- If unsure, omit the item.
- No markdown. No explanation. No extra keys.

TEXT:
{text}
"""


def _build_combined_skill_prompt(resume_text, jd_text):
    return f"""
Return ONLY valid JSON with this exact schema:
{{
  "resume_skills": {{
    "technical": [],
    "soft": [],
    "languages": []
  }},
  "jd_skills": {{
    "technical": [],
    "soft": [],
    "languages": []
  }}
}}

Extract skills from each section independently using these strict rules:
- Only include skills that are explicitly written in that section.
- Copy the exact skill wording from the section before normalization. Do not infer, paraphrase, expand, summarize, or rewrite.
- Never convert sentences, achievements, or responsibilities into skills.
- Reject vague phrases and generic descriptors such as "best practices", "high quality", "performance", "reliability", "professional", or "structured".
- Reject any item longer than 3 words.
- technical: tools, technologies, programming languages, frameworks, databases, platforms, software, and specific domain terms or processes (e.g., "data annotation", "visual reasoning"). If a technical phrase exists in the text and is 1-3 words, allow it.
- soft: directly named interpersonal or workplace skills only.
- languages: human languages only.
- If unsure, omit the item.
- No markdown. No explanation. No extra keys.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}
"""


import collections
from string import punctuation

def _fallback_keyword_extraction(text):
    """Fallback to simple frequency analysis for keywords if LLM returns empty."""
    stop_words = frozenset({"the", "and", "to", "of", "a", "in", "for", "is", "with", "on", 
                            "that", "by", "this", "or", "as", "be", "are", "from", "at", 
                            "your", "have", "will", "what", "where", "when", "about", "which",
                            "an", "can", "our", "you", "we", "not", "it", "all", "work", "team",
                            "experience", "years", "skills", "knowledge", "ability", "working",
                            "development", "design", "new", "strong", "understanding", "using",
                            "business", "data", "requirements", "support", "management", "required",
                            "including", "other", "their", "such", "ensure", "provide", "within"})
    
    words = [w.strip(punctuation).lower() for w in text.split() if len(w.strip(punctuation)) > 2]
    filtered = [w for w in words if w not in stop_words and not w.isdigit()]
    
    counts = collections.Counter(filtered)
    # Return top 8 frequent words as potential technical keywords
    return [word for word, count in counts.most_common(8)]

def extract_and_categorize_skills(text, api_key):
    """Return a stable {technical, soft, languages} structure for a single text blob."""
    if not text or text.isspace():
        return _empty_skill_structure()

    prompt = _build_single_text_skill_prompt(text)

    try:
        raw_output = _generate_json_response(prompt, api_key, "single_text")
        return _parse_skill_payload(raw_output, text, "single_text")
    except Exception as exc:
        logger.error("Categorize skills error: %s", exc)
        return _empty_skill_structure()


def generate_gap_suggestions(resume_flat, jd_flat, api_key):
    """Returns a list of 2-4 short actionable suggestion strings."""
    missing = list(set(skill.lower() for skill in jd_flat) - set(skill.lower() for skill in resume_flat))

    if not missing:
        return ["Your skills closely match the job requirements."]

    client = get_client(api_key)

    prompt = f"""
    A candidate is missing these skills for a job: {", ".join(missing[:20])}

    Give 2-4 short, actionable suggestions to close the gap.
    Rules:
    - One sentence each. No fluff.
    - Name specific tools, courses, or certifications where possible.
    - Return ONLY a JSON array of strings.

    Example: ["Earn AWS Certified Solutions Architect", "Build a project using Kubernetes and Docker"]
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3),
        )
        raw = (response.text or "").strip()

        match = re.search(r"`{3}(?:json)?\s*([\s\S]*?)\s*`{3}", raw)
        if match:
            raw = match.group(1).strip()
        else:
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1 and end > start:
                raw = raw[start:end + 1]

        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
    except Exception as exc:
        logger.warning("Gap suggestions error: %s", exc)

    return [
        "Review the job description and target the top missing skills.",
        "Consider relevant certifications or side projects to bridge the gap.",
    ]


def analyze_resume_and_jd(resume_text, jd_text, api_key):
    """Combine validated resume skills, validated JD skills, and gap suggestions."""
    if not resume_text or not resume_text.strip() or not jd_text or not jd_text.strip():
        return {
            "error": True,
            "message": "Please provide valid resume and job description text.",
            "resume_skills": _empty_skill_structure(),
            "jd_skills": _empty_skill_structure(),
            "suggestions": [],
        }

    resume_text = _clean_whitespace(resume_text)[:4000]
    jd_text = _clean_whitespace(jd_text)[:4000]

    if not resume_text or not jd_text:
        return {
            "error": True,
            "message": "Please provide valid resume and job description text.",
            "resume_skills": _empty_skill_structure(),
            "jd_skills": _empty_skill_structure(),
            "suggestions": [],
        }

    try:
        raw_output = _generate_json_response(
            _build_combined_skill_prompt(resume_text, jd_text),
            api_key,
            "resume_jd_combined",
        )

        logger.info("[resume_jd_combined] Raw AI output: %s", raw_output)
        extracted = _extract_json(raw_output)
        if not extracted:
            logger.warning("[resume_jd_combined] No JSON found in combined response.")
            parsed = {}
        else:
            try:
                parsed = json.loads(extracted)
            except json.JSONDecodeError as exc:
                logger.warning("[resume_jd_combined] Failed to parse combined JSON: %s", exc)
                parsed = {}
            if not isinstance(parsed, dict):
                logger.warning("[resume_jd_combined] Combined response was not a JSON object.")
                parsed = {}

        resume_payload = parsed.get("resume_skills", {})
        jd_payload = parsed.get("jd_skills", {})

        if not isinstance(resume_payload, dict):
            logger.warning("[resume_jd_combined] Missing or invalid resume_skills payload.")
            resume_payload = {}
        if not isinstance(jd_payload, dict):
            logger.warning("[resume_jd_combined] Missing or invalid jd_skills payload.")
            jd_payload = {}

        resume_skills = _validate_skill_structure(resume_payload, resume_text, "resume")
        jd_skills = _validate_skill_structure(jd_payload, jd_text, "job_description")

        if not jd_skills["technical"]:
            logger.info("[resume_jd_combined] No technical skills found in JD, using fallback extraction.")
            fallback_keywords = _fallback_keyword_extraction(jd_text)
            jd_skills["technical"] = fallback_keywords

        resume_flat = (
            resume_skills["technical"] +
            resume_skills["soft"] +
            resume_skills["languages"]
        )
        jd_flat = (
            jd_skills["technical"] +
            jd_skills["soft"] +
            jd_skills["languages"]
        )

        suggestions = generate_gap_suggestions(resume_flat, jd_flat, api_key)

        return {
            "error": False,
            "resume_skills": resume_skills,
            "jd_skills": jd_skills,
            "suggestions": suggestions,
        }

    except Exception as exc:
        logger.error("All models failed to analyze resume and JD: %s", exc)
        return {
            "error": True,
            "message": "Analysis timed out or failed. Please try again with a shorter resume.",
            "resume_skills": _empty_skill_structure(),
            "jd_skills": _empty_skill_structure(),
            "suggestions": ["Analysis timed out. Please try again with a shorter resume."],
        }
