"""
ATS intelligence — determinism and registry stability regression tests.

These guard the invariants verified during the ATS migration stabilization
pass. They bypass the LLM entirely: the scorer is called directly with
fixed resume + JD + jd_skills inputs and the response is checked for
deterministic output across repeats, cache resets, and module re-imports.

Run with pytest (`python -m pytest backend/tests/test_intelligence.py`) or
as a plain script (`python backend/tests/test_intelligence.py`).
"""
import hashlib
import json
import sys

from backend.tests.conftest import configure_isolated_registry


def _setup():
    """Fresh registry per module. Returns the scorer / registry modules."""
    configure_isolated_registry()
    # Import lazily so the connection factory is configured first.
    from backend import scorer
    from backend.services import skill_registry
    skill_registry.init()
    return scorer, skill_registry


def _fingerprint(result):
    return hashlib.sha256(
        json.dumps(result, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


# Representative resume + JD used by most determinism tests.
RESUME = {
    "name": "Alex Sample", "title": "SWE", "email": "a@a.com",
    "summary": "Built React apps with Node.js and PostgreSQL. Used Docker and k8s.",
    "technical_skills": ["React", "Node.js", "PostgreSQL", "Docker", "Kubernetes"],
    "soft_skills": ["Communication"],
    "languages": ["English"],
    "experience": [
        {"role": "Senior Engineer", "company": "Acme", "duration": "2020-2024",
         "points": ["Shipped React + Node.js APIs serving 100k users.",
                    "Reduced latency 40% with PostgreSQL query optimization.",
                    "Mentored 3 junior engineers."]}
    ],
    "projects": [
        {"title": "ServiceA", "tech_stack": ["Python", "FastAPI"],
         "points": ["Built ML pipeline with PyTorch.", "Improved accuracy 15%."]}
    ],
    "education": [{"degree": "BSc CS", "institution": "MIT", "year": "2020"}],
    "certifications": ["AWS Certified Solutions Architect"],
}
JD = "Required: React, Node.js, PostgreSQL. Nice-to-have: Docker, Kubernetes, AWS, Python."
JD_SKILLS = ["React", "Node.js", "PostgreSQL", "Docker", "Kubernetes", "AWS", "Python"]


# ── Determinism ─────────────────────────────────────────────────────────────
def test_compute_ats_score_is_deterministic_in_process():
    scorer, _ = _setup()
    results = [scorer.compute_ats_score(RESUME, JD, jd_skills=JD_SKILLS) for _ in range(10)]
    fps = {_fingerprint(r) for r in results}
    assert len(fps) == 1, f"non-deterministic responses: {fps}"


def test_compute_ats_score_survives_cold_caches():
    scorer, skill_registry = _setup()
    from backend.intelligence import normalizer
    warm = scorer.compute_ats_score(RESUME, JD, jd_skills=JD_SKILLS)
    normalizer.normalize.cache_clear()
    skill_registry._cache_invalidate(None)
    cold = scorer.compute_ats_score(RESUME, JD, jd_skills=JD_SKILLS)
    assert _fingerprint(warm) == _fingerprint(cold)


def test_compute_ats_score_survives_module_reimport():
    """A re-import drops every in-memory cache; the DB row is the only carry-over."""
    db_path = configure_isolated_registry()
    from backend import scorer as s1
    from backend.services import skill_registry as r1
    r1.init()
    warm = s1.compute_ats_score(RESUME, JD, jd_skills=JD_SKILLS)

    # Drop intelligence/services/scorer from sys.modules and re-import.
    for m in [k for k in list(sys.modules.keys())
              if k.startswith("backend.intelligence")
              or k == "backend.scorer"
              or k.startswith("backend.services")]:
        del sys.modules[m]
    from backend.database import connection as _conn
    _conn.configure(db_path)  # same DB
    from backend import scorer as s2
    from backend.services import skill_registry as r2
    r2.init()
    restart = s2.compute_ats_score(RESUME, JD, jd_skills=JD_SKILLS)
    assert _fingerprint(warm) == _fingerprint(restart)


def test_jd_skills_permutation_is_invariant_for_sets_and_scalars():
    scorer, _ = _setup()
    a = scorer.compute_ats_score(RESUME, JD, jd_skills=JD_SKILLS)
    b = scorer.compute_ats_score(RESUME, JD, jd_skills=list(reversed(JD_SKILLS)))
    assert a["score"] == b["score"]
    assert a["breakdown"] == b["breakdown"]
    assert set(a["matched_skills"]) == set(b["matched_skills"])
    assert set(a["missing_skills"]) == set(b["missing_skills"])


# ── Registry stability ──────────────────────────────────────────────────────
def test_registry_growth_is_bounded_by_unique_surface_forms():
    """Hammering canonicalize_skill_list with the same input must not grow rows."""
    scorer, _ = _setup()
    from backend.database import connection
    conn = connection.get_connection()
    before_c = conn.execute("SELECT COUNT(*) AS n FROM skills_registry").fetchone()["n"]
    before_a = conn.execute("SELECT COUNT(*) AS n FROM skill_aliases").fetchone()["n"]

    mix = ["ReactJS", "React.js", "react", "JS", "js", "TypeScript", "PostgreSQL",
           "postgres", "k8s", "kubernetes", "Tailwind CSS", "tailwind",
           "GitHub Actions", "github actions", "Machine Learning", "ML",
           "C++", "cplusplus", "REST APIs", "restful", "Docker", "Bun"]
    for _ in range(1000):
        scorer.canonicalize_skill_list(mix)
    after_c = conn.execute("SELECT COUNT(*) AS n FROM skills_registry").fetchone()["n"]
    after_a = conn.execute("SELECT COUNT(*) AS n FROM skill_aliases").fetchone()["n"]

    assert (after_c - before_c) <= len(mix), \
        f"canonicals grew by {after_c - before_c} (input had {len(mix)} unique forms)"
    assert (after_a - before_a) <= len(mix), \
        f"aliases grew by {after_a - before_a}"

    # Second sweep must not change anything further.
    for _ in range(500):
        scorer.canonicalize_skill_list(mix)
    final_c = conn.execute("SELECT COUNT(*) AS n FROM skills_registry").fetchone()["n"]
    final_a = conn.execute("SELECT COUNT(*) AS n FROM skill_aliases").fetchone()["n"]
    assert final_c == after_c
    assert final_a == after_a


def test_canonical_form_is_stable_across_repeated_calls():
    scorer, _ = _setup()
    samples = ["ReactJS", "react.js", "react-js", "NODE.JS", "nodejs",
               "C++", "cplusplus", "cpp", "PostgreSQL", "postgres", "psql", "postgressql",
               "K8s", "kube", "GitHub Actions", "github actions",
               "TS", "ts", "JS", "js", "tailwind", "tailwindcss", "Tailwind CSS",
               "REST APIs", "restful apis", "machine learning", "ML"]
    first = {s: scorer.canonicalize_skill(s) for s in samples}
    for _ in range(20):
        for s in samples:
            assert scorer.canonicalize_skill(s) == first[s], \
                f"drift: {s} -> {scorer.canonicalize_skill(s)} (was {first[s]})"


def test_normalize_is_idempotent():
    _setup()
    from backend.intelligence.normalizer import normalize
    samples = ["ReactJS", "react.js", "react-js", "NODE.JS", "nodejs",
               "C++", "cplusplus", "cpp", "PostgreSQL", "postgres", "psql", "postgressql",
               "K8s", "kube", "GitHub Actions", "github actions",
               "TS", "ts", "JS", "js", "tailwind", "tailwindcss", "Tailwind CSS",
               "REST APIs", "restful apis", "machine learning", "ML"]
    for s in samples:
        k1 = normalize(s)
        k2 = normalize(k1)
        k3 = normalize(k2)
        assert k1 == k2 == k3, f"non-idempotent: {s} -> {k1!r} -> {k2!r} -> {k3!r}"


# ── Standalone runner so this file works without pytest ─────────────────────
if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = []
    for fn in funcs:
        try:
            fn()
            print(f"[OK]   {fn.__name__}")
        except AssertionError as e:
            failed.append((fn.__name__, str(e)))
            print(f"[FAIL] {fn.__name__}: {e}")
        except Exception as e:
            failed.append((fn.__name__, f"{type(e).__name__}: {e}"))
            print(f"[ERR]  {fn.__name__}: {type(e).__name__}: {e}")
    if failed:
        print(f"\n{len(failed)}/{len(funcs)} failed")
        sys.exit(1)
    print(f"\nAll {len(funcs)} tests passed.")
