from google import genai
import json
import re
import traceback
from . import scorer


def _extract_json(raw_output):
    """
    Robustly extract a JSON object from a model response.
    Handles: markdown code blocks (with or without leading text),
    raw JSON, and JSON followed by trailing explanation text.
    """
    raw_output = raw_output.strip()

    # Case 1: JSON wrapped in a ```json ... ``` or ``` ... ``` block
    # Use re.search so leading text like "Here is the JSON:" is ignored
    match = re.search(r'`{3}(?:json)?\s*([\s\S]*?)\s*`{3}', raw_output)
    if match:
        return match.group(1).strip()

    # Case 2: No code block — find the outermost { ... }
    # rfind('}') handles trailing text after the JSON object
    start = raw_output.find('{')
    end   = raw_output.rfind('}')
    if start != -1 and end != -1 and end > start:
        return raw_output[start:end + 1]

    # Fallback: return as-is and let json.loads surface the error
    return raw_output


def validate_resume(result, selected_projects):
    return (
        isinstance(result, dict)
        and "projects" in result
        and len(result["projects"]) == len(selected_projects)
    )


def optimize_resume_for_jd(resume_text, jd_text, skills, api_key):
    """
    skills: { technical: [], soft: [], languages: [] }
    Returns structured resume JSON with technical_skills / soft_skills / languages.
    """
    client = genai.Client(api_key=api_key)

    # Guard: ensure skills is always a dict, never None
    if not isinstance(skills, dict):
        skills = {}
    technical = skills.get("technical") or []
    soft      = skills.get("soft")      or []
    languages = skills.get("languages") or []

    # Parse resume if it is raw text
    parsed_resume = resume_text
    if isinstance(resume_text, str):
        try:
            parsed_resume = json.loads(resume_text)
        except json.JSONDecodeError:
            parsed_resume = generate_structured_resume(resume_text, api_key)
            if not parsed_resume:
                raise RuntimeError("Failed to parse resume into structured data.")

    experience_count = len(parsed_resume.get("experience", []))

    if experience_count == 0:
        project_limit = 6
    elif experience_count <= 2:
        project_limit = 4
    elif experience_count == 3:
        project_limit = 3
    else:
        project_limit = 2

    projects = parsed_resume.get("projects", [])
    selected_projects = scorer.rank_projects_tfidf(projects, jd_text)[:project_limit]

    parsed_resume["projects"] = selected_projects

    prompt = f"""
    You are an ATS Resume Optimization Specialist. Rewrite the resume to maximize ATS match against the Job Description.

    WRITING STYLE:
    - Concise, professional. No fluff, no filler phrases.
    - Bullet points: max 15 words each. Start with a past-tense action verb.
    - Summary: 2-3 sentences max. Dense with JD keywords.
    - Focus on achievements and measurable impact.

    OPTIMIZATION RULES:
    1. Inject JD keywords and exact phrases naturally throughout.
    2. Reframe existing experience to align with JD — even ~10% relevance is enough.
    3. Use EXACTLY the provided skill lists. Do not add or remove skills.
    4. Preserve all jobs and projects. Reword aggressively, never fabricate new roles.
    5. Use '[Add X]' placeholders for any missing contact fields.

    You are given structured resume data.

    IMPORTANT:
    * The list of projects provided is FINAL.
    * DO NOT add, remove, merge, reorder, or duplicate projects.
    * DO NOT change the number of projects.

    Your task is ONLY to rewrite and improve clarity, impact, and relevance.

    OUTPUT RULE:
    Return ONLY valid JSON. No explanations.

    Skills (authoritative — use exactly as provided):
    Technical: {json.dumps(technical)}
    Soft: {json.dumps(soft)}
    Languages: {json.dumps(languages)}

    Return ONLY valid JSON. No explanation text before or after. Matching this schema:
    {{
        "name": "Full Name",
        "title": "Title aligned to JD",
        "email": "...", "phone": "...", "linkedin": "...", "github": "...",
        "summary": "2-3 sentence ATS-optimized summary",
        "technical_skills": {json.dumps(technical)},
        "soft_skills": {json.dumps(soft)},
        "languages": {json.dumps(languages)},
        "experience": [
            {{ "role": "...", "company": "...", "duration": "...", "points": ["action-led bullet max 15 words"] }}
        ],
        "projects": [
            {{ "title": "...", "tech_stack": ["Tech1", "Tech2"], "points": ["what built", "key feature", "outcome"] }}
        ],
        "education": [
            {{ "degree": "...", "institution": "...", "year": "..." }}
        ],
        "certifications": ["cert name — org (date)"]
    }}

    Job Description:
    {jd_text}

    Resume Data:
    {json.dumps(parsed_resume)}
    """

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=prompt
            )
            raw_output = response.text.strip()
            print(f"[optimize] Attempt {attempt+1} - Raw model output (first 300 chars): {raw_output[:300]}")

            cleaned = _extract_json(raw_output)
            if not cleaned:
                continue
                
            result = json.loads(cleaned)
            
            if validate_resume(result, selected_projects):
                return result
            else:
                if isinstance(result, dict):
                    result["projects"] = selected_projects
                    return result
        except json.JSONDecodeError as e:
            print(f"[optimize] Attempt {attempt+1} JSON parse error: {e}")
            print(f"[optimize] Full raw output:\n{raw_output}")
        except Exception as e:
            print(f"[optimize] Attempt {attempt+1} API call failed: {e}")
            traceback.print_exc()

    print("[optimize] All 3 attempts failed. Falling back to original parsed_resume.")
    parsed_resume["projects"] = selected_projects
    return parsed_resume


def generate_resume_from_inputs(inputs, api_key):
    """
    Build a complete structured resume from manual user inputs.
    """
    client = genai.Client(api_key=api_key)

    name      = (inputs.get('name')     or '').strip()
    title     = (inputs.get('title')    or '').strip()
    email     = (inputs.get('email')    or '[Add Email]').strip() or '[Add Email]'
    phone     = (inputs.get('phone')    or '[Add Phone]').strip() or '[Add Phone]'
    linkedin  = (inputs.get('linkedin') or '[Add LinkedIn]').strip() or '[Add LinkedIn]'
    github    = (inputs.get('github')   or '[Add GitHub]').strip()  or '[Add GitHub]'
    edu_text  = (inputs.get('education_text')      or '').strip()
    exp_text  = (inputs.get('experience_text')     or '').strip()
    proj_text = (inputs.get('projects_text')       or '').strip()
    cert_text = (inputs.get('certifications_text') or '').strip()
    technical = inputs.get('technical_skills') or []
    soft      = inputs.get('soft_skills')      or []
    languages = inputs.get('languages')        or []

    if not exp_text.strip():
        experience_count = 0
    else:
        date_pattern = r'(?:20\d{2}|19\d{2})\s*(?:-|to|–|—)\s*(?:Present|Current|20\d{2}|19\d{2})'
        matches = re.findall(date_pattern, exp_text, re.IGNORECASE)
        experience_count = len(matches) if matches else max(1, len([p for p in exp_text.split('\n\n') if p.strip()]))

    if experience_count == 0:
        project_limit = 6
    elif experience_count <= 2:
        project_limit = 4
    elif experience_count == 3:
        project_limit = 3
    else:
        project_limit = 2

    prompt = f"""
    You are an ATS Resume Writer. Build a complete, professional resume from the user inputs below.
    WRITING RULES:
    - Career summary: 2-3 sentences max.
    - Bullet points: max 15 words each.
    - Projects: MUST include EXACTLY {project_limit} projects.
    - Output: ONLY JSON.

    USER INPUTS:
    Name: {name}
    Target Role: {title}
    Email: {email}
    Phone: {phone}
    LinkedIn: {linkedin}
    GitHub: {github}
    Education: {edu_text or 'Not provided'}
    Experience: {exp_text or 'Not provided'}
    Projects: {proj_text or 'Not provided'}
    Certifications: {cert_text or 'Not provided'}
    Technical Skills: {json.dumps(technical)}
    Soft Skills: {json.dumps(soft)}
    Languages: {json.dumps(languages)}

    Return ONLY valid JSON. No explanation text before or after. Schema:
    {{
        "name": "{name}",
        "title": "polished title aligned to target role",
        "email": "{email}", "phone": "{phone}", "linkedin": "{linkedin}", "github": "{github}",
        "summary": "2-3 sentence AI-written career summary, no fluff",
        "technical_skills": {json.dumps(technical)},
        "soft_skills": {json.dumps(soft)},
        "languages": {json.dumps(languages)},
        "experience": [
            {{ "role": "...", "company": "...", "duration": "...", "points": ["action-led bullet max 15 words"] }}
        ],
        "projects": [
            {{ "title": "...", "tech_stack": ["Tech1", "Tech2"], "points": ["what built", "key feature", "outcome"] }}
        ],
        "education": [
            {{ "degree": "...", "institution": "...", "year": "..." }}
        ],
        "certifications": ["cert name — org (date)"]
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents=prompt
        )
        raw_output = response.text.strip()
        cleaned = _extract_json(raw_output)
        return json.loads(cleaned)
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"generate-from-inputs API call failed: {e}")


def generate_structured_resume(resume_text, api_key):
    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an elite Executive Resume Writer. Rewrite the following resume text.

    CRITICAL RULES:
    1. EXTRACT JOBS AND PROJECTS SEPARATELY: Map formal work experience to "experience". Map personal, academic, or hackathon projects to "projects".
    2. ZERO FLUFF: Eliminate all filler words.
    3. ACTION FIRST: Every bullet point MUST start with a strong, past-tense action verb.
    4. ACHIEVEMENTS & CERTS: Extract certifications, awards, achievements into 'certifications'. Return [] if none.
    5. CONTACT INFO: Use exact placeholders '[Add Email]', '[Add Phone]', '[Add LinkedIn]', '[Add GitHub]' for any missing fields.

    Return ONLY valid JSON. No explanation text before or after. Matching this schema:
    {{
        "name": "Full Name",
        "title": "Professional Title",
        "email": "...", "phone": "...", "linkedin": "...", "github": "...",
        "summary": "Impactful professional summary",
        "technical_skills": ["Skill 1"],
        "soft_skills": ["Skill 2"],
        "languages": ["Lang 1"],
        "experience": [
            {{ "role": "Job Title", "company": "Company", "duration": "Dates", "points": ["Action driven bullet point"] }}
        ],
        "projects": [
            {{ "title": "Project Name", "tech_stack": ["Tech1", "Tech2"], "points": ["What was built"] }}
        ],
        "education": [{{ "degree": "Degree Name", "institution": "School", "year": "Year" }}],
        "certifications": ["Certification/Achievement 1"]
    }}

    Raw Resume:
    {resume_text}
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents=prompt
        )
        raw_output = response.text.strip()
        cleaned = _extract_json(raw_output)
        return json.loads(cleaned)

    except Exception as e:
        traceback.print_exc()
        print(f"[rewrite] API Error: {e}")
        return None
