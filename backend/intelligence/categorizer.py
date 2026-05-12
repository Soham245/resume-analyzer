"""
Heuristic skill categorization.

Strategy:
  1. SEED_HINTS  - tiny per-category sets of unambiguous tokens used to
                   bootstrap inference (e.g. "python" -> Programming).
  2. PATTERNS    - regex patterns over the normalized key for unknowns
                   ("*sql*" -> Databases, "*db" -> Databases, "*ops"
                   -> Cloud/DevOps, "*.js"-ecosystem terms -> Frameworks).
  3. Fallback    -> "Technical Skills"

Multi-category skills are supported via `categorize_all` (returns a tuple of
labels). The single-best label is returned by `categorize`.

Unknown technologies are categorized, never discarded. Confidence in the
return value lets the registry decide whether to lock the category in or
keep it provisional.
"""

import logging
import re
from functools import lru_cache
from typing import Tuple

logger = logging.getLogger(__name__)

# ── Canonical category labels ────────────────────────────────────────────────
CATEGORY_PROGRAMMING  = "Programming Languages"
CATEGORY_FRAMEWORKS   = "Frameworks/Libraries"
CATEGORY_DATABASES    = "Databases"
CATEGORY_CLOUD        = "Cloud/DevOps"
CATEGORY_AI_ML        = "AI/ML"
CATEGORY_TOOLS        = "Tools"
CATEGORY_SOFT         = "Soft Skills"
CATEGORY_LANGUAGES    = "Human Languages"
CATEGORY_TECHNICAL    = "Technical Skills"   # default fallback

DEFAULT_CATEGORY = CATEGORY_TECHNICAL

# ── Layer 1: tiny seed hints ─────────────────────────────────────────────────
# Each set holds *unambiguous* normalized keys. Kept deliberately small —
# the regex layer below carries most of the load for unknowns.
_SEED_PROGRAMMING = frozenset({
    "python", "java", "javascript", "typescript", "c", "c++", "c#",
    "go", "rust", "ruby", "php", "swift", "kotlin", "scala", "perl",
    "r", "matlab", "bash", "shell", "html", "css", "sql", "dart",
})

_SEED_FRAMEWORKS = frozenset({
    "react", "vue", "angular", "node", "express", "next", "nuxt",
    "django", "flask", "spring", "rails", "laravel", "bootstrap",
    "tailwind", "svelte", "astro", "remix", "nest", "fastify",
})

_SEED_DATABASES = frozenset({
    "mysql", "postgresql", "sqlite", "mongodb", "redis", "cassandra",
    "dynamodb", "oracle", "elasticsearch", "neo4j", "mariadb",
    "couchdb", "influxdb",
})

_SEED_CLOUD = frozenset({
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
    "ansible", "helm", "jenkins", "nginx", "apache", "prometheus",
    "grafana", "vercel", "netlify", "heroku", "fly",
})

_SEED_AI_ML = frozenset({
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas",
    "numpy", "scipy", "langchain", "huggingface", "openai",
})

_SEED_TOOLS = frozenset({
    "git", "github", "gitlab", "jira", "postman", "swagger",
    "figma", "notion", "linear", "webpack", "vite", "jest", "pytest",
})

_SEED_LANGUAGES = frozenset({
    "english", "hindi", "spanish", "french", "german", "arabic",
    "mandarin", "chinese", "japanese", "korean", "portuguese",
    "italian", "russian", "bengali", "tamil", "telugu", "marathi",
    "urdu", "gujarati", "punjabi", "dutch", "polish", "turkish",
})

# Soft skills are tiny — most show up as multi-word noun phrases anyway,
# and the spec wants this discovered via heuristics rather than hard lists.
_SOFT_TOKENS = frozenset({
    "leadership", "teamwork", "communication", "collaboration",
    "problem-solving", "adaptability", "creativity", "mentoring",
    "ownership", "accountability", "empathy",
})

# ── Layer 2: pattern-based heuristics for unknowns ───────────────────────────
# Each entry: (compiled regex, category, confidence)
_PATTERN_RULES: Tuple[Tuple[re.Pattern, str, float], ...] = (
    # Databases
    (re.compile(r"\bsql\b"),                CATEGORY_DATABASES, 0.85),
    (re.compile(r"(?<=[a-z])db$"),          CATEGORY_DATABASES, 0.75),
    (re.compile(r"\borm\b"),                CATEGORY_DATABASES, 0.70),
    (re.compile(r"^(?:postgres|mongo)"),    CATEGORY_DATABASES, 0.85),

    # Cloud / DevOps
    (re.compile(r"\b(?:aws|gcp|azure)\b"),  CATEGORY_CLOUD, 0.95),
    (re.compile(r"\b(?:cloud|devops|sre)\b"), CATEGORY_CLOUD, 0.85),
    (re.compile(r"\b(?:k8s|kube)"),         CATEGORY_CLOUD, 0.90),
    (re.compile(r"\b(?:docker|container)"), CATEGORY_CLOUD, 0.85),
    (re.compile(r"\b(?:ci/cd|cicd|pipeline)\b"), CATEGORY_CLOUD, 0.80),
    (re.compile(r"\b(?:lambda|fargate|ec2|s3|rds|iam|vpc)\b"), CATEGORY_CLOUD, 0.80),
    (re.compile(r"(?<=[a-z])ops$"),         CATEGORY_CLOUD, 0.65),

    # AI / ML
    (re.compile(r"\b(?:machine|deep)\s+learning\b"), CATEGORY_AI_ML, 0.95),
    (re.compile(r"\b(?:nlp|llm|rag|gpt|transformer)\b"), CATEGORY_AI_ML, 0.90),
    (re.compile(r"\b(?:tensor|torch|keras|sklearn|scikit)"), CATEGORY_AI_ML, 0.90),
    (re.compile(r"\b(?:computer\s+vision|reinforcement\s+learning)\b"), CATEGORY_AI_ML, 0.95),
    (re.compile(r"\b(?:lang(?:chain|graph)|crewai|llamaindex)\b"), CATEGORY_AI_ML, 0.85),
    (re.compile(r"\bai\b"),                 CATEGORY_AI_ML, 0.55),

    # Frameworks / libraries — common JS-ecosystem suffixes survive normalizer
    (re.compile(r"\.js$"),                  CATEGORY_FRAMEWORKS, 0.80),
    (re.compile(r"^(?:react|vue|angular|svelte|astro|remix|next|nuxt|nest|fastify)\b"),
                                            CATEGORY_FRAMEWORKS, 0.90),
    (re.compile(r"(?<=[a-z])ui$"),          CATEGORY_FRAMEWORKS, 0.60),

    # Tools (catch-all for "*api" things, *kit, *cli, *ide)
    (re.compile(r"\bapi\b"),                CATEGORY_TOOLS, 0.55),
    (re.compile(r"(?<=[a-z])kit$"),         CATEGORY_TOOLS, 0.60),
    (re.compile(r"(?<=[a-z])cli$"),         CATEGORY_TOOLS, 0.65),
    (re.compile(r"(?<=[a-z])ide$"),         CATEGORY_TOOLS, 0.65),
)


def _seed_lookup(key: str):
    """Return (category, confidence) if `key` is in a seed set, else (None, 0)."""
    if key in _SEED_PROGRAMMING: return CATEGORY_PROGRAMMING, 0.98
    if key in _SEED_FRAMEWORKS:  return CATEGORY_FRAMEWORKS,  0.95
    if key in _SEED_DATABASES:   return CATEGORY_DATABASES,   0.95
    if key in _SEED_CLOUD:       return CATEGORY_CLOUD,       0.95
    if key in _SEED_AI_ML:       return CATEGORY_AI_ML,       0.95
    if key in _SEED_TOOLS:       return CATEGORY_TOOLS,       0.90
    if key in _SEED_LANGUAGES:   return CATEGORY_LANGUAGES,   0.98
    if key in _SOFT_TOKENS:      return CATEGORY_SOFT,        0.90
    return None, 0.0


def _pattern_lookup(key: str):
    """Best pattern match by confidence. Returns (category, confidence) or (None, 0)."""
    best = (None, 0.0)
    for pat, cat, conf in _PATTERN_RULES:
        if pat.search(key) and conf > best[1]:
            best = (cat, conf)
    return best


@lru_cache(maxsize=4096)
def categorize(normalized_skill: str):
    """
    Return the best heuristic category for the given *normalized* skill key.
    Unknowns fall back to "Technical Skills" with low confidence rather
    than being discarded.
    """
    if not normalized_skill or not isinstance(normalized_skill, str):
        return DEFAULT_CATEGORY

    key = normalized_skill.strip().lower()
    if not key:
        return DEFAULT_CATEGORY

    cat, _conf = _seed_lookup(key)
    if cat:
        return cat

    cat, _conf = _pattern_lookup(key)
    if cat:
        return cat

    # Multi-word unknowns: try the first/last token before giving up.
    if " " in key:
        for tok in (key.split()[-1], key.split()[0]):
            cat, _conf = _seed_lookup(tok)
            if cat:
                return cat
            cat, _conf = _pattern_lookup(tok)
            if cat:
                return cat

    return DEFAULT_CATEGORY


@lru_cache(maxsize=4096)
def categorize_with_confidence(normalized_skill: str):
    """
    Like `categorize` but returns (category, confidence). Confidence is
    a coarse 0..1 signal — the registry uses it to decide whether to
    revisit categories of provisional entries later.
    """
    if not normalized_skill or not isinstance(normalized_skill, str):
        return (DEFAULT_CATEGORY, 0.2)

    key = normalized_skill.strip().lower()
    if not key:
        return (DEFAULT_CATEGORY, 0.2)

    cat, conf = _seed_lookup(key)
    if cat:
        return (cat, conf)

    cat, conf = _pattern_lookup(key)
    if cat:
        return (cat, conf)

    if " " in key:
        for tok in (key.split()[-1], key.split()[0]):
            cat, conf = _seed_lookup(tok)
            if cat:
                return (cat, max(0.4, conf * 0.7))
            cat, conf = _pattern_lookup(tok)
            if cat:
                return (cat, max(0.4, conf * 0.7))

    return (DEFAULT_CATEGORY, 0.25)
