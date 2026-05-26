import json
import logging
import re
import signal
import threading

from google import genai
from google.genai import types

from . import scorer

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash-lite"
AI_TIMEOUT_SECONDS = 50          # Generous: Render cold-start + Gemini latency can exceed 25 s
MAX_TEXT_CHARS = 3000


class AITimeoutException(Exception):
    pass


def _timeout_handler(signum, frame):
    raise AITimeoutException("AI request timed out")


def _extract_json(raw_output):
    raw_output = (raw_output or "").strip()

    match = re.search(r"`{3}(?:json)?\s*([\s\S]*?)\s*`{3}", raw_output)
    if match:
        return match.group(1).strip()

    start = raw_output.find("{")
    end = raw_output.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw_output[start:end + 1]

    return raw_output


def _repair_json(text):
    """Fix common Gemini JSON quirks that cause json.loads to fail."""
    if not text:
        return text
    # Strip trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Strip single-line // comments
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _cap_text(text, max_chars=MAX_TEXT_CHARS):
    return re.sub(r"\s+", " ", str(text or "")).strip()[:max_chars]


def _cap_list(values, max_items=12, item_max_chars=80):
    items = []
    for value in values or []:
        item = _cap_text(value, item_max_chars)
        if item:
            items.append(item)
        if len(items) >= max_items:
            break
    return items


def _schema_template():
    return {
        "name": "[Add Name]",
        "title": "[Add Title]",
        "email": "[Add Email]",
        "phone": "[Add Phone]",
        "linkedin": "[Add LinkedIn]",
        "github": "[Add GitHub]",
        "summary": "",
        "technical_skills": [],
        "soft_skills": [],
        "languages": [],
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": [],
    }


def _coerce_text(value, fallback="", max_chars=200):
    value = _cap_text(value, max_chars)
    return value or fallback


def _coerce_string_list(values, max_items, item_max_chars=120):
    return _cap_list(values if isinstance(values, list) else [], max_items=max_items, item_max_chars=item_max_chars)


def _coerce_experience(entries):
    cleaned = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        cleaned.append({
            "role": _coerce_text(entry.get("role"), max_chars=120),
            "company": _coerce_text(entry.get("company"), max_chars=120),
            "duration": _coerce_text(entry.get("duration"), max_chars=80),
            "points": _coerce_string_list(entry.get("points"), max_items=5, item_max_chars=160),
        })
        if len(cleaned) >= 5:
            break
    return cleaned


def _coerce_projects(entries, limit=None):
    cleaned = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        cleaned.append({
            "title": _coerce_text(entry.get("title"), max_chars=120),
            "tech_stack": _coerce_string_list(entry.get("tech_stack"), max_items=6, item_max_chars=60),
            "points": _coerce_string_list(entry.get("points"), max_items=4, item_max_chars=160),
        })
        if limit and len(cleaned) >= limit:
            break
        if len(cleaned) >= 6:
            break
    return cleaned


def _coerce_education(entries):
    cleaned = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        cleaned.append({
            "degree": _coerce_text(entry.get("degree"), max_chars=140),
            "institution": _coerce_text(entry.get("institution"), max_chars=140),
            "year": _coerce_text(entry.get("year"), max_chars=40),
        })
        if len(cleaned) >= 4:
            break
    return cleaned


def _fallback_resume(skills=None, base=None):
    fallback = _schema_template()
    if isinstance(base, dict):
        fallback.update({
            "name": _coerce_text(base.get("name"), fallback["name"], max_chars=120),
            "title": _coerce_text(base.get("title"), fallback["title"], max_chars=120),
            "email": _coerce_text(base.get("email"), fallback["email"], max_chars=120),
            "phone": _coerce_text(base.get("phone"), fallback["phone"], max_chars=60),
            "linkedin": _coerce_text(base.get("linkedin"), fallback["linkedin"], max_chars=200),
            "github": _coerce_text(base.get("github"), fallback["github"], max_chars=200),
            "summary": _coerce_text(base.get("summary"), "", max_chars=400),
            "experience": _coerce_experience(base.get("experience")),
            "projects": _coerce_projects(base.get("projects")),
            "education": _coerce_education(base.get("education")),
            "certifications": _coerce_string_list(base.get("certifications"), max_items=6, item_max_chars=120),
        })

    skill_data = skills if isinstance(skills, dict) else {}
    base_technical = base.get("technical_skills", []) if isinstance(base, dict) else []
    base_soft = base.get("soft_skills", []) if isinstance(base, dict) else []
    base_languages = base.get("languages", []) if isinstance(base, dict) else []

    fallback["technical_skills"] = _coerce_string_list(
        skill_data.get("technical") or base_technical,
        max_items=50,
        item_max_chars=60,
    )
    fallback["soft_skills"] = _coerce_string_list(
        skill_data.get("soft") or base_soft,
        max_items=30,
        item_max_chars=60,
    )
    fallback["languages"] = _coerce_string_list(
        skill_data.get("languages") or base_languages,
        max_items=20,
        item_max_chars=40,
    )
    return fallback


def _project_limit(resume_data):
    experience_count = len((resume_data or {}).get("experience", []) or [])
    if experience_count == 0:
        return 6
    if experience_count <= 2:
        return 4
    if experience_count == 3:
        return 3
    return 2


def _prepare_resume_input(resume_text, skills, jd_text):
    if isinstance(resume_text, dict):
        prepared = _fallback_resume(skills, resume_text)
        prepared["projects"] = scorer.rank_projects_by_overlap(prepared["projects"], jd_text)
        return prepared

    fallback = _fallback_resume(skills)
    return {
        "raw_resume": _cap_text(resume_text),
        "seed": fallback,
    }


def _start_timeout():
    if hasattr(signal, "alarm") and threading.current_thread() is threading.main_thread():
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(AI_TIMEOUT_SECONDS)
        return old_handler
    return None


def _clear_timeout(old_handler):
    if old_handler is not None and hasattr(signal, "alarm") and threading.current_thread() is threading.main_thread():
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def _generate_json(prompt, api_key, label):
    old_handler = _start_timeout()
    try:
        logger.info("[%s] STAGE-1 Calling Gemini model=%s", label, MODEL_NAME)
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0),
        )
        raw_text = getattr(response, "text", "") or ""
        logger.info("[%s] STAGE-2 Gemini raw response length=%d chars, first 300: %.300s",
                    label, len(raw_text), raw_text)

        cleaned = _extract_json(raw_text)
        if not cleaned:
            logger.warning("[%s] STAGE-3 _extract_json returned empty. Raw (first 500): %s",
                           label, raw_text[:500])
            return None
        logger.info("[%s] STAGE-3 _extract_json OK, cleaned length=%d", label, len(cleaned))

        # First attempt: parse as-is
        try:
            parsed = json.loads(cleaned)
            logger.info("[%s] STAGE-4 json.loads succeeded on first attempt", label)
        except json.JSONDecodeError as first_err:
            logger.info("[%s] STAGE-4 json.loads FAILED: %s — trying repair", label, first_err)
            # Second attempt: repair common Gemini quirks (trailing commas, comments)
            repaired = _repair_json(cleaned)
            try:
                parsed = json.loads(repaired)
                logger.info("[%s] STAGE-4 json.loads succeeded after repair", label)
            except json.JSONDecodeError as je:
                logger.warning("[%s] STAGE-4 json.loads FAILED even after repair: %s. "
                               "Cleaned (first 800): %.800s", label, je, cleaned)
                return None

        # Log which top-level keys are present and which sections have data
        if isinstance(parsed, dict):
            section_summary = {
                k: len(v) if isinstance(v, list) else ("present" if v else "empty")
                for k, v in parsed.items()
            }
            logger.info("[%s] STAGE-5 parsed keys: %s", label, section_summary)
        else:
            logger.warning("[%s] STAGE-5 parsed is not a dict: type=%s", label, type(parsed).__name__)

        return parsed
    except AITimeoutException:
        logger.warning("[%s] STAGE-ERR AI request timed out after %s seconds", label, AI_TIMEOUT_SECONDS)
        return None
    except Exception as exc:
        logger.warning("[%s] STAGE-ERR AI request failed: %s", label, exc)
        return None
    finally:
        _clear_timeout(old_handler)


def _pick(result, fallback, key):
    """Return result[key] if it's a non-empty list, else fallback[key].

    Unlike the `or` pattern, this only falls back when the AI truly
    didn't return the field (None) — an explicit empty list from the AI
    is still overridden by the fallback so the user never sees blanks.
    """
    val = result.get(key)
    if isinstance(val, list) and len(val) > 0:
        fb = fallback.get(key) or []
        logger.info("[_pick] key=%s → using AI result (len=%d), fallback had len=%d",
                    key, len(val), len(fb))
        return val
    fb = fallback.get(key) or []
    logger.info("[_pick] key=%s → AI value=%s, falling back (len=%d)",
                key, type(val).__name__ if val is not None else "None", len(fb))
    return fb


def _finalize_resume(result, fallback, project_limit=None):
    if not isinstance(result, dict):
        logger.warning("[finalize] STAGE-6 AI returned non-dict result (%s), using fallback entirely",
                       type(result).__name__)
        result = {}
    else:
        logger.info("[finalize] STAGE-6 AI result has %d keys: %s", len(result), list(result.keys()))

    final = _schema_template()
    final["name"] = _coerce_text(result.get("name"), fallback["name"], max_chars=120)
    final["title"] = _coerce_text(result.get("title"), fallback["title"], max_chars=120)
    final["email"] = _coerce_text(result.get("email"), fallback["email"], max_chars=120)
    final["phone"] = _coerce_text(result.get("phone"), fallback["phone"], max_chars=60)
    final["linkedin"] = _coerce_text(result.get("linkedin"), fallback["linkedin"], max_chars=200)
    final["github"] = _coerce_text(result.get("github"), fallback["github"], max_chars=200)
    final["summary"] = _coerce_text(result.get("summary"), fallback["summary"], max_chars=500)

    final["technical_skills"] = _coerce_string_list(
        _pick(result, fallback, "technical_skills"),
        max_items=50,
        item_max_chars=60,
    )
    final["soft_skills"] = _coerce_string_list(
        _pick(result, fallback, "soft_skills"),
        max_items=30,
        item_max_chars=60,
    )
    final["languages"] = _coerce_string_list(
        _pick(result, fallback, "languages"),
        max_items=20,
        item_max_chars=40,
    )
    final["experience"] = _coerce_experience(_pick(result, fallback, "experience"))
    final["projects"] = _coerce_projects(
        _pick(result, fallback, "projects"),
        limit=project_limit,
    )
    final["education"] = _coerce_education(_pick(result, fallback, "education"))
    final["certifications"] = _coerce_string_list(
        _pick(result, fallback, "certifications"),
        max_items=6,
        item_max_chars=120,
    )

    # STAGE-7: Log final result summary
    final_summary = {
        k: len(v) if isinstance(v, list) else ("present" if v else "empty")
        for k, v in final.items()
    }
    logger.info("[finalize] STAGE-7 final result: %s", final_summary)

    empty_sections = [k for k in ("experience", "projects", "education", "certifications",
                                   "technical_skills", "summary")
                      if not final.get(k)]
    if empty_sections:
        logger.warning("[finalize] STAGE-7 ⚠ EMPTY sections: %s. "
                       "AI result keys: %s, fallback keys: %s",
                       empty_sections, list(result.keys()), list(fallback.keys()))

    return final


def validate_resume(result, selected_projects):
    if not isinstance(result, dict):
        return False
    if not isinstance(result.get("projects"), list):
        return False
    if not selected_projects:
        return len(result["projects"]) == 0
    return len(result["projects"]) <= max(1, len(selected_projects))


def optimize_resume_for_jd(resume_text, jd_text, skills, api_key):
    """
    One AI call only. Works with raw resume text or structured resume JSON.
    """
    jd_text = _cap_text(jd_text)
    resume_seed = _prepare_resume_input(resume_text, skills or {}, jd_text)
    fallback_base = resume_seed if isinstance(resume_text, dict) else resume_seed.get("seed", {})
    fallback = _fallback_resume(skills or {}, fallback_base)
    selected_projects = scorer.rank_projects_by_overlap(fallback["projects"], jd_text)
    project_limit = _project_limit(fallback)

    if selected_projects:
        fallback["projects"] = selected_projects[:project_limit]

    prompt = f"""
Return JSON only with this schema:
{{
  "name": "",
  "title": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "github": "",
  "summary": "",
  "technical_skills": [],
  "soft_skills": [],
  "languages": [],
  "experience": [{{"role": "", "company": "", "duration": "", "points": []}}],
  "projects": [{{"title": "", "tech_stack": [], "points": []}}],
  "education": [{{"degree": "", "institution": "", "year": ""}}],
  "certifications": []
}}

Rules:
- Use exactly the provided skills lists. Do not add new skills.
- Do not invent roles, companies, dates, projects, or certifications.
- Keep bullets short and specific.
- Keep at most {project_limit} projects.

Job Description:
{jd_text}

Resume Input:
{json.dumps(resume_seed)}

Authoritative Skills:
{json.dumps({
    "technical_skills": fallback["technical_skills"],
    "soft_skills": fallback["soft_skills"],
    "languages": fallback["languages"],
})}
"""

    result = _generate_json(prompt, api_key, "optimize")
    if result is None:
        logger.warning("[optimize] Gemini returned no usable JSON — using fallback resume")
    finalized = _finalize_resume(result, fallback, project_limit=project_limit)

    if fallback["projects"] and not finalized["projects"]:
        finalized["projects"] = fallback["projects"]
    elif fallback["projects"] and not validate_resume(finalized, fallback["projects"]):
        finalized["projects"] = fallback["projects"]

    # Signal to frontend whether AI generation succeeded or fell back
    finalized["_generation_ok"] = result is not None and isinstance(result, dict)

    return finalized


def generate_resume_from_inputs(inputs, api_key):
    name = _coerce_text(inputs.get("name"), "[Add Name]", max_chars=120)
    title = _coerce_text(inputs.get("title"), "[Add Title]", max_chars=120)
    email = _coerce_text(inputs.get("email"), "[Add Email]", max_chars=120)
    phone = _coerce_text(inputs.get("phone"), "[Add Phone]", max_chars=60)
    linkedin = _coerce_text(inputs.get("linkedin"), "[Add LinkedIn]", max_chars=200)
    github = _coerce_text(inputs.get("github"), "[Add GitHub]", max_chars=200)

    fallback = _fallback_resume({
        "technical": inputs.get("technical_skills") or [],
        "soft": inputs.get("soft_skills") or [],
        "languages": inputs.get("languages") or [],
    }, {
        "name": name,
        "title": title,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
    })

    user_payload = {
        "name": name,
        "title": title,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "education_text": _cap_text(inputs.get("education_text"), 800),
        "experience_text": _cap_text(inputs.get("experience_text"), 1000),
        "projects_text": _cap_text(inputs.get("projects_text"), 800),
        "certifications_text": _cap_text(inputs.get("certifications_text"), 400),
        "technical_skills": fallback["technical_skills"],
        "soft_skills": fallback["soft_skills"],
        "languages": fallback["languages"],
    }

    prompt = f"""
Return JSON only with this schema:
{{
  "name": "{name}",
  "title": "",
  "email": "{email}",
  "phone": "{phone}",
  "linkedin": "{linkedin}",
  "github": "{github}",
  "summary": "",
  "technical_skills": [],
  "soft_skills": [],
  "languages": [],
  "experience": [{{"role": "", "company": "", "duration": "", "points": []}}],
  "projects": [{{"title": "", "tech_stack": [], "points": []}}],
  "education": [{{"degree": "", "institution": "", "year": ""}}],
  "certifications": []
}}

Rules:
- Use only the provided details.
- Do not invent achievements, employers, or certifications.
- Keep bullets short.

User Input:
{json.dumps(user_payload)}
"""

    result = _generate_json(prompt, api_key, "generate_from_inputs")
    if result is None:
        logger.warning("[generate_from_inputs] Gemini returned no usable JSON — using fallback resume")
    finalized = _finalize_resume(result, fallback)
    finalized["_generation_ok"] = result is not None and isinstance(result, dict)
    return finalized


def generate_structured_resume(resume_text, api_key):
    raw_resume = _cap_text(resume_text)
    fallback = _fallback_resume({})

    prompt = f"""
Return JSON only with this schema:
{{
  "name": "",
  "title": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "github": "",
  "summary": "",
  "technical_skills": [],
  "soft_skills": [],
  "languages": [],
  "experience": [{{"role": "", "company": "", "duration": "", "points": []}}],
  "projects": [{{"title": "", "tech_stack": [], "points": []}}],
  "education": [{{"degree": "", "institution": "", "year": ""}}],
  "certifications": []
}}

Rules:
- Use only information explicitly present in the resume.
- Do not invent missing fields.
- Keep bullets short.
- If a field is missing, use placeholders for contact fields and empty lists elsewhere.

Resume:
{raw_resume}
"""

    result = _generate_json(prompt, api_key, "rewrite")
    if result is None:
        logger.warning("[rewrite] Gemini returned no usable JSON — using fallback resume")
    finalized = _finalize_resume(result, fallback)
    finalized["_generation_ok"] = result is not None and isinstance(result, dict)
    return finalized
