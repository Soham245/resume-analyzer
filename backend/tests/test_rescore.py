"""
/rescore endpoint — edit-loop and state-synchronization regression tests.

Uses Flask's test_client so no live HTTP is required. Confirms:
  - /rescore is stateless (same payload -> same response)
  - edits to each section (skills / experience / projects / certifications /
    education) move the score and the relevant breakdown row in the right
    direction
  - add-and-revert round-trips to the exact baseline (no hysteresis)
  - interleaved requests don't leak state across the registry process
  - the registry stays bounded across the full edit loop

Run with pytest (`python -m pytest backend/tests/test_rescore.py`) or as a
plain script (`python backend/tests/test_rescore.py`).
"""
import copy
import json
import sys

from backend.tests.conftest import configure_isolated_registry


def _client():
    """Build a fresh isolated test_client. Resets the registry per test."""
    configure_isolated_registry()
    import importlib
    import backend.app as app_module
    # The app module caches the connection factory at import. Re-import so
    # any service that bound the prior factory pointer gets a fresh handle.
    importlib.reload(app_module)
    return app_module.app.test_client()


BASE = {
    "name": "Alex Sample", "title": "SWE", "email": "a@a.com",
    "summary": "Built React apps with Node.js and PostgreSQL.",
    "technical_skills": ["React", "Node.js", "PostgreSQL"],
    "soft_skills": ["Communication"],
    "languages": ["English"],
    "experience": [
        {"role": "Engineer", "company": "Acme", "duration": "2020-2024",
         "points": ["Shipped React + Node.js APIs serving 100k users.",
                    "Reduced latency 40% with PostgreSQL query optimization."]}
    ],
    "projects": [],
    "education": [{"degree": "BSc CS", "institution": "MIT", "year": "2020"}],
    "certifications": [],
}
JD = "Required: React, Node.js, PostgreSQL, Docker, Kubernetes. Nice: AWS, Python, ML."
JD_SKILLS = ["React", "Node.js", "PostgreSQL", "Docker", "Kubernetes",
             "AWS", "Python", "Machine Learning"]


def _rescore(client, resume, original=None):
    body = {"resume": resume, "jd_text": JD, "jd_skills_flat": JD_SKILLS}
    if original is not None:
        body["original_score"] = original
    r = client.post("/rescore", json=body)
    assert r.status_code == 200, (r.status_code, r.get_json())
    return r.get_json()


# ── Statelessness ───────────────────────────────────────────────────────────
def test_rescore_is_stateless_across_repeated_identical_calls():
    client = _client()
    bodies = [json.dumps(_rescore(client, BASE), sort_keys=True, default=str)
              for _ in range(5)]
    assert len(set(bodies)) == 1, "identical payload produced different responses"


def test_rescore_no_state_leak_when_interleaved_with_different_resumes():
    client = _client()
    baseline = _rescore(client, BASE)["optimized_score"]["score"]
    mod = copy.deepcopy(BASE)
    mod["technical_skills"] = list(mod["technical_skills"]) + ["Docker"]
    # A B A C A pattern — every A must equal the original baseline.
    a1 = _rescore(client, BASE)["optimized_score"]["score"]
    _ = _rescore(client, mod)
    a2 = _rescore(client, BASE)["optimized_score"]["score"]
    less = copy.deepcopy(BASE); less["technical_skills"] = ["React"]
    _ = _rescore(client, less)
    a3 = _rescore(client, BASE)["optimized_score"]["score"]
    assert a1 == a2 == a3 == baseline


# ── Section-level edits each affect the right breakdown row ────────────────
def test_adding_missing_skill_raises_skills_row_and_moves_skill_to_matched():
    client = _client()
    base = _rescore(client, BASE)
    edited = copy.deepcopy(BASE)
    edited["technical_skills"] = list(edited["technical_skills"]) + ["Docker"]
    after = _rescore(client, edited)
    assert after["optimized_score"]["breakdown"]["skills"] > base["optimized_score"]["breakdown"]["skills"]
    assert "Docker" in after["matched_skills"]
    assert "Docker" not in after["missing_skills"]


def test_removing_matched_skill_lowers_skills_row_and_moves_skill_to_missing():
    client = _client()
    base = _rescore(client, BASE)
    edited = copy.deepcopy(BASE)
    edited["technical_skills"] = [s for s in edited["technical_skills"] if s != "Node.js"]
    edited["summary"] = "Built React apps with PostgreSQL."
    edited["experience"] = [{
        "role": "Engineer", "company": "Acme", "duration": "2020-2024",
        "points": ["Shipped React APIs serving 100k users.",
                   "Reduced latency 40% with PostgreSQL query optimization."]
    }]
    after = _rescore(client, edited)
    assert after["optimized_score"]["breakdown"]["skills"] < base["optimized_score"]["breakdown"]["skills"]
    assert "Node.js" not in after["matched_skills"]
    assert "Node.js" in after["missing_skills"]


def test_adding_experience_entry_raises_experience_row():
    client = _client()
    base = _rescore(client, BASE)
    edited = copy.deepcopy(BASE)
    edited["experience"].append({
        "role": "Senior Developer", "company": "Initech", "duration": "2018-2020",
        "points": ["Led migration of 12 services to AWS.",
                   "Reduced cloud bill by 25% over 6 months.",
                   "Mentored 4 engineers across 3 teams."]
    })
    after = _rescore(client, edited)
    assert after["optimized_score"]["breakdown"]["experience"] > base["optimized_score"]["breakdown"]["experience"]


def test_adding_project_raises_projects_row():
    client = _client()
    base = _rescore(client, BASE)
    edited = copy.deepcopy(BASE)
    edited["projects"].append({
        "title": "Resume Optimizer", "tech_stack": ["Python", "React", "Docker"],
        "points": ["Built ML pipeline that processes 50k resumes/day.",
                   "Deployed to AWS with Kubernetes."]
    })
    after = _rescore(client, edited)
    assert after["optimized_score"]["breakdown"]["projects"] > base["optimized_score"]["breakdown"]["projects"]


def test_adding_certifications_raises_certifications_row():
    client = _client()
    base = _rescore(client, BASE)
    edited = copy.deepcopy(BASE)
    edited["certifications"] = ["AWS Certified Solutions Architect",
                                "Certified Kubernetes Administrator (CKA)"]
    after = _rescore(client, edited)
    assert after["optimized_score"]["breakdown"]["certifications"] > base["optimized_score"]["breakdown"]["certifications"]


def test_adding_education_entry_does_not_decrease_education_row():
    client = _client()
    base = _rescore(client, BASE)
    edited = copy.deepcopy(BASE)
    edited["education"].append({"degree": "MSc CS", "institution": "Stanford", "year": "2022"})
    after = _rescore(client, edited)
    assert after["optimized_score"]["breakdown"]["education"] >= base["optimized_score"]["breakdown"]["education"]


# ── Round-trip ──────────────────────────────────────────────────────────────
def test_add_and_revert_returns_exactly_to_baseline():
    client = _client()
    base = _rescore(client, BASE)
    added = copy.deepcopy(BASE); added["technical_skills"] = list(added["technical_skills"]) + ["Docker"]
    _ = _rescore(client, added)
    reverted = copy.deepcopy(added); reverted["technical_skills"] = [s for s in reverted["technical_skills"] if s != "Docker"]
    after = _rescore(client, reverted)
    assert after["optimized_score"]["score"]      == base["optimized_score"]["score"]
    assert after["optimized_score"]["breakdown"] == base["optimized_score"]["breakdown"]
    assert set(after["matched_skills"]) == set(base["matched_skills"])
    assert set(after["missing_skills"]) == set(base["missing_skills"])


# ── Registry stability across the edit loop ─────────────────────────────────
def test_registry_stays_bounded_across_full_edit_loop():
    client = _client()
    # Exercise every section in turn.
    _ = _rescore(client, BASE)
    a = copy.deepcopy(BASE); a["technical_skills"] = list(a["technical_skills"]) + ["Docker"]
    _ = _rescore(client, a)
    b = copy.deepcopy(BASE); b["projects"] = [{"title": "P", "tech_stack": ["Python", "React"], "points": ["Built X."]}]
    _ = _rescore(client, b)
    c = copy.deepcopy(BASE); c["certifications"] = ["AWS Solutions Architect"]
    _ = _rescore(client, c)
    _ = _rescore(client, BASE)

    from backend.database import connection
    conn = connection.get_connection()
    canonicals = conn.execute("SELECT COUNT(*) AS n FROM skills_registry").fetchone()["n"]
    aliases    = conn.execute("SELECT COUNT(*) AS n FROM skill_aliases").fetchone()["n"]
    # Generous upper bound: 19 seeded + at most a few dozen organic skills.
    assert canonicals < 100, f"registry grew unexpectedly: {canonicals} canonicals"
    assert aliases    < 200, f"alias table grew unexpectedly: {aliases} aliases"


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
