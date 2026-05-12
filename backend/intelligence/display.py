"""
Display formatting — turns a normalized lookup key into a presentable string.

This module deliberately stays small. Three layers, in priority order:

  1. BRAND_EXCEPTIONS  -- exact-match branding (Node.js, PostgreSQL, GitHub).
                          ~30 entries, *only* for officially-cased names that
                          generic title-casing would mangle.

  2. UPPERCASE_TOKENS  -- tokens that should always be uppercase (AWS, SQL,
                          HTML, API, …). Applied per-token during fallback
                          title-casing.

  3. Generic fallback  -- title-case each space-separated token, preserve
                          dotted suffixes, preserve "+" / "#" punctuation.

If a registry entry has a stored `display_name`, callers should use it
directly; this module is the formatter the registry itself uses when
creating a new entry, and the fallback when nothing is in the registry yet.
"""

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# ── Layer 1: brand exceptions (small, curated) ───────────────────────────────
# Keys are *normalized* lookup keys (post-normalizer output).
# Values are official display strings.
BRAND_EXCEPTIONS = {
    "javascript":    "JavaScript",
    "typescript":    "TypeScript",
    "node":          "Node.js",
    "express":       "Express.js",
    "next":          "Next.js",
    "nuxt":          "Nuxt.js",
    "vue":           "Vue.js",
    "nest":          "Nest.js",
    "fastify":       "Fastify",
    "fastapi":       "FastAPI",
    "github":        "GitHub",
    "gitlab":        "GitLab",
    "bitbucket":     "Bitbucket",
    "mongodb":       "MongoDB",
    "postgresql":    "PostgreSQL",
    "mysql":         "MySQL",
    "sqlite":        "SQLite",
    "mariadb":       "MariaDB",
    "dynamodb":      "DynamoDB",
    "graphql":       "GraphQL",
    "scikit-learn":  "scikit-learn",
    "pytorch":       "PyTorch",
    "tensorflow":    "TensorFlow",
    "numpy":         "NumPy",
    "scipy":         "SciPy",
    "jquery":        "jQuery",
    "macos":         "macOS",
    "ios":           "iOS",
    "openai":        "OpenAI",
    "huggingface":   "Hugging Face",
}

# ── Layer 2: always-uppercase tokens ─────────────────────────────────────────
# Applied during the generic fallback to individual tokens.
UPPERCASE_TOKENS = frozenset({
    "aws", "gcp", "sql", "html", "css", "nlp", "etl", "api", "apis",
    "ai", "ml", "ui", "ux", "cdn", "ssr", "csr", "cors", "jwt", "rpc",
    "tcp", "udp", "ssh", "ssl", "tls", "json", "xml", "yaml", "csv",
    "pdf", "url", "uri", "http", "https", "rest", "graphql",
    "orm", "ide", "sdk", "cli", "gui", "saas", "paas", "iaas",
    "k8s", "ci", "cd", "qa", "dns", "vpc", "ec2", "s3", "rds", "iam",
    "gpu", "cpu", "ram", "os", "io", "db",
})

# ── Layer 3: generic fallback ────────────────────────────────────────────────
_PUNCT_PRESERVE = ".+#"


def _format_token(token: str) -> str:
    if not token:
        return token
    lower = token.lower()
    if lower in UPPERCASE_TOKENS:
        return lower.upper()
    # Preserve dotted forms (".net", "node.js")
    if "." in token:
        head, _, tail = token.partition(".")
        return _format_token(head) + "." + tail.lower()
    # Preserve trailing punctuation like "++", "#"
    if token[-1] in _PUNCT_PRESERVE:
        head = token.rstrip(_PUNCT_PRESERVE)
        tail = token[len(head):]
        return _format_token(head) + tail if head else token
    return token[:1].upper() + token[1:].lower()


@lru_cache(maxsize=4096)
def format_display(normalized_key: str) -> str:
    """
    Return a presentable display string for the given *normalized* key.
    Examples:
        "react"            -> "React"
        "node"             -> "Node.js"
        "aws"              -> "AWS"
        "astro"            -> "Astro"
        "drizzle orm"      -> "Drizzle ORM"
        "machine learning" -> "Machine Learning"
    """
    if not normalized_key or not isinstance(normalized_key, str):
        return ""

    key = normalized_key.strip().lower()
    if not key:
        return ""

    # Brand exception wins outright
    brand = BRAND_EXCEPTIONS.get(key)
    if brand:
        return brand

    # Token-by-token fallback
    parts = key.split(" ")
    return " ".join(_format_token(p) for p in parts if p)
