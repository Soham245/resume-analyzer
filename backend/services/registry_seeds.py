"""
Bootstrap seeds for the skill registry.

Each entry is an industry-standard abbreviation, brand-canonical form, or
multi-token brand name that is NOT learnable from organic surface forms
alone. Seeding happens once when the registry is first initialized and is
idempotent — existing canonical rows are never overwritten.

Design contract
---------------
- Seeds are facts about how well-known technologies should be spelled.
- They are NOT the giant alias maps the legacy code carried.
- An entry exists only when the rule-based normalizer + display fallback
  would produce a clearly wrong result (e.g. `ts` -> `Ts` instead of
  `TypeScript`, `k8s` -> `K8S` instead of `Kubernetes`).
- Adding a seed is a deliberate act. Default behavior for unknown skills
  is heuristic categorization + auto-learning, not pre-seeded entries.
"""

import json
import logging
import sqlite3

from backend.intelligence.categorizer import (
    CATEGORY_AI_ML,
    CATEGORY_CLOUD,
    CATEGORY_DATABASES,
    CATEGORY_FRAMEWORKS,
    CATEGORY_PROGRAMMING,
    CATEGORY_TOOLS,
)
from backend.intelligence.normalizer import normalize

logger = logging.getLogger(__name__)


# (canonical_form, display_name, category, [alternate_surface_forms])
# `canonical_form` and each surface form are normalized at load time, so
# you can spell them naturally here.
SEEDS = [
    # Programming languages — abbreviations the LLM commonly emits.
    ("typescript",       "TypeScript",       CATEGORY_PROGRAMMING, ["ts"]),
    ("javascript",       "JavaScript",       CATEGORY_PROGRAMMING, ["js", "ecmascript"]),
    ("c++",              "C++",              CATEGORY_PROGRAMMING, ["cplusplus", "cpp"]),
    ("c#",               "C#",               CATEGORY_PROGRAMMING, ["csharp", "c sharp"]),

    # Databases — common abbreviations / misspellings of PostgreSQL.
    ("postgresql",       "PostgreSQL",       CATEGORY_DATABASES,   ["postgres", "psql", "postgressql"]),

    # Cloud / DevOps — long-form names that should canonicalize to acronym,
    # plus multi-token brand names that title-case fallback gets wrong.
    ("aws",              "AWS",              CATEGORY_CLOUD,       ["amazon web services"]),
    ("gcp",              "GCP",              CATEGORY_CLOUD,       ["google cloud", "google cloud platform"]),
    ("azure",            "Azure",            CATEGORY_CLOUD,       ["microsoft azure"]),
    ("kubernetes",       "Kubernetes",       CATEGORY_CLOUD,       ["k8s", "kube"]),
    ("ci/cd",            "CI/CD",            CATEGORY_CLOUD,       ["cicd"]),
    ("github actions",   "GitHub Actions",   CATEGORY_CLOUD,       []),
    ("gitlab ci",        "GitLab CI",        CATEGORY_CLOUD,       ["gitlab-ci"]),

    # AI / ML — abbreviations and long-form spellings.
    ("machine learning", "Machine Learning", CATEGORY_AI_ML,       ["ml"]),
    ("deep learning",    "Deep Learning",    CATEGORY_AI_ML,       ["dl"]),
    ("nlp",              "NLP",              CATEGORY_AI_ML,       ["natural language processing"]),

    # Frameworks / libraries — multi-token names that title-case mishandles.
    ("react native",     "React Native",     CATEGORY_FRAMEWORKS,  []),
    ("spring boot",      "Spring Boot",      CATEGORY_FRAMEWORKS,  ["springboot"]),
    ("tailwind css",     "Tailwind CSS",     CATEGORY_FRAMEWORKS,  ["tailwind", "tailwindcss"]),

    # Tools — REST API spelling variants the normalizer can't unify on its own.
    ("rest api",         "REST APIs",        CATEGORY_TOOLS,       ["rest", "restful", "restful api"]),
]


def seed_defaults(conn: sqlite3.Connection) -> dict:
    """
    Insert seed entries into the registry. Existing canonical rows are
    skipped. Aliases are inserted with INSERT OR IGNORE.

    Returns a small report dict — useful in tests and for an init-time log.
    """
    new_canonicals = 0
    new_aliases = 0
    skipped = 0

    cur = conn.cursor()
    try:
        for canonical_raw, display, category, surface_forms in SEEDS:
            canonical = normalize(canonical_raw)
            if not canonical:
                continue

            normalized_aliases = []
            for surface in surface_forms or ():
                n = normalize(surface)
                if not n or n == canonical or n in normalized_aliases:
                    continue
                normalized_aliases.append(n)

            existing = cur.execute(
                "SELECT 1 FROM skills_registry WHERE canonical_name = ?",
                (canonical,),
            ).fetchone()

            if existing is None:
                cur.execute(
                    """
                    INSERT INTO skills_registry
                        (canonical_name, display_name, category, aliases,
                         confidence_score, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (canonical, display, category,
                     json.dumps(normalized_aliases), 1.0, "seed"),
                )
                new_canonicals += 1
            else:
                skipped += 1

            for alias in normalized_aliases:
                inserted = cur.execute(
                    "INSERT OR IGNORE INTO skill_aliases (alias, canonical_name) VALUES (?, ?)",
                    (alias, canonical),
                ).rowcount
                if inserted:
                    new_aliases += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

    report = {
        "new_canonicals": new_canonicals,
        "new_aliases": new_aliases,
        "skipped_existing": skipped,
    }
    logger.info("[skill_registry] seeded %s", report)
    return report
