"""
Heuristic skill categorization.

This is a deliberately small, easy-to-extend mapping that produces a
best-effort category bucket for a normalized skill. It is *not* a master
registry of every skill — unknown skills fall back to "Technical Skills"
and the registry can be refined over time (by the auto-learning flow or
by manual edits to the DB).

When the full ATS refactor lands later, the registry's stored `category`
column becomes the authority and this module shrinks to a bootstrap
helper that only seeds the category for newly-observed skills.
"""

DEFAULT_CATEGORY = "Technical Skills"

CATEGORY_PROGRAMMING = "Programming Languages"
CATEGORY_FRAMEWORKS  = "Frameworks/Libraries"
CATEGORY_DATABASES   = "Databases"
CATEGORY_CLOUD       = "Cloud/DevOps"
CATEGORY_TOOLS       = "Tools"
CATEGORY_AI_ML       = "AI/ML"

# Each bucket holds *normalized* lookup keys (lowercase, post-suffix-strip).
_PROGRAMMING = frozenset({
    "python", "java", "javascript", "typescript", "c", "c++", "c#",
    "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "scala",
    "perl", "r", "matlab", "bash", "shell", "html", "css", "sql",
    "objective-c", "objective c", "dart",
})

_FRAMEWORKS = frozenset({
    "react", "vue", "angular", "node", "express", "next", "nuxt",
    "django", "flask", "fastapi", "spring", "spring boot", "rails",
    "laravel", "bootstrap", "tailwind", "tailwind css", "jquery",
    "redux", "svelte", "nest", "fastify", "remix", "astro",
})

_DATABASES = frozenset({
    "mysql", "postgresql", "postgres", "sqlite", "mongodb", "redis",
    "cassandra", "dynamodb", "oracle", "elasticsearch", "firebase",
    "supabase", "neo4j", "mariadb", "couchdb", "influxdb",
    "sql server", "mssql",
})

_CLOUD = frozenset({
    "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "terraform",
    "ansible", "helm", "jenkins", "ci/cd", "github actions",
    "gitlab ci", "nginx", "apache", "prometheus", "grafana",
    "cloudformation", "lambda", "ec2", "s3", "rds", "fargate",
})

_TOOLS = frozenset({
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "postman", "swagger", "openapi", "webpack", "vite", "jest",
    "pytest", "figma", "notion", "slack", "linear",
})

_AI_ML = frozenset({
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "pandas", "numpy", "scipy", "huggingface", "transformers",
    "langchain", "openai", "anthropic", "llm",
})

# Substring fallbacks for unknown skills. Checked in order.
_SUBSTRING_HINTS = (
    ("sql", CATEGORY_DATABASES),
    ("db",  CATEGORY_DATABASES),
    ("kube", CATEGORY_CLOUD),
    ("docker", CATEGORY_CLOUD),
    ("aws",  CATEGORY_CLOUD),
    ("cloud", CATEGORY_CLOUD),
    ("devops", CATEGORY_CLOUD),
    ("ml",   CATEGORY_AI_ML),
    ("ai",   CATEGORY_AI_ML),
    ("nlp",  CATEGORY_AI_ML),
    ("api",  CATEGORY_TOOLS),
)


def categorize(normalized_skill: str) -> str:
    """
    Return a heuristic category for the given *normalized* skill key.
    Falls back to "Technical Skills" when no rule matches.
    """
    if not normalized_skill:
        return DEFAULT_CATEGORY

    key = normalized_skill.strip().lower()
    if not key:
        return DEFAULT_CATEGORY

    if key in _PROGRAMMING: return CATEGORY_PROGRAMMING
    if key in _FRAMEWORKS:  return CATEGORY_FRAMEWORKS
    if key in _DATABASES:   return CATEGORY_DATABASES
    if key in _CLOUD:       return CATEGORY_CLOUD
    if key in _AI_ML:       return CATEGORY_AI_ML
    if key in _TOOLS:       return CATEGORY_TOOLS

    for needle, bucket in _SUBSTRING_HINTS:
        if needle in key:
            return bucket

    return DEFAULT_CATEGORY
