from google import genai
from google.genai import types
import json
import re
import signal
import logging
import threading

logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    pass

def _timeout_handler(signum, frame):
    raise TimeoutException("Execution timed out")

_client_cache = {}

def get_client(api_key):
    if api_key not in _client_cache:
        _client_cache[api_key] = genai.Client(api_key=api_key)
    return _client_cache[api_key]


# ── Skill normalization & category sets ──────────────────────────────────────

_NORMALIZATIONS = {
    'nodejs': 'Node.js', 'node': 'Node.js',
    'reactjs': 'React', 'react.js': 'React',
    'vuejs': 'Vue.js', 'vue': 'Vue.js',
    'angularjs': 'Angular', 'angular.js': 'Angular',
    'expressjs': 'Express.js', 'express': 'Express.js',
    'nextjs': 'Next.js', 'next.js': 'Next.js',
    'github': 'Git', 'git/github': 'Git', 'git & github': 'Git',
    'tailwindcss': 'Tailwind CSS', 'tailwind': 'Tailwind CSS',
    'html5': 'HTML', 'css3': 'CSS',
    'restful': 'REST APIs', 'rest api': 'REST APIs', 'rest apis': 'REST APIs',
    'ml': 'Machine Learning', 'dl': 'Deep Learning',
    'sklearn': 'scikit-learn', 'scikit learn': 'scikit-learn',
    'postgres': 'PostgreSQL', 'postgressql': 'PostgreSQL',
    'tensorflow': 'TensorFlow', 'pytorch': 'PyTorch',
}

_EXCLUDED = frozenset({
    # IDEs & editors
    'vs code', 'vscode', 'visual studio code', 'visual studio', 'intellij',
    'intellij idea', 'pycharm', 'webstorm', 'eclipse', 'netbeans', 'xcode',
    'android studio', 'sublime text', 'atom', 'vim', 'emacs',
    # Generic CS subjects
    'data structures', 'algorithms', 'operating systems', 'dbms',
    'database management', 'computer networks', 'object oriented programming',
    'oop', 'oops', 'software engineering', 'computer science',
    'web development', 'software development',
    'full stack', 'frontend', 'backend', 'front-end', 'back-end',
    # Vague domains (not tied to specific tools)
    'artificial intelligence', 'ai', 'computer vision', 'big data',
    'cloud computing', 'internet of things', 'iot', 'blockchain',
    # Generic filler
    'programming', 'coding', 'development', 'debugging',
    'windows', 'macos', 'ubuntu',
})

_PROGRAMMING = frozenset({
    'python', 'javascript', 'typescript', 'java', 'c', 'c++', 'c#', 'go',
    'rust', 'ruby', 'php', 'swift', 'kotlin', 'r', 'scala', 'matlab',
    'perl', 'bash', 'shell', 'html', 'css', 'sql',
})

_FRAMEWORKS = frozenset({
    'react', 'vue.js', 'angular', 'node.js', 'express.js', 'next.js',
    'nuxt.js', 'django', 'flask', 'fastapi', 'spring', 'spring boot',
    'rails', 'laravel', 'tensorflow', 'pytorch', 'keras', 'scikit-learn',
    'pandas', 'numpy', 'scipy', 'bootstrap', 'tailwind css', 'jquery',
    'redux', 'svelte', 'fastify', 'nest.js',
})

_DATABASES = frozenset({
    'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis', 'cassandra',
    'dynamodb', 'oracle', 'sql server', 'elasticsearch', 'firebase',
    'supabase', 'neo4j', 'couchdb', 'mariadb', 'influxdb',
})

_TOOLS = frozenset({
    'docker', 'kubernetes', 'git', 'linux', 'aws', 'gcp', 'azure',
    'rest apis', 'graphql', 'nginx', 'apache', 'jenkins', 'ci/cd',
    'github actions', 'gitlab ci', 'webpack', 'vite', 'jest', 'pytest',
    'postman', 'swagger', 'terraform', 'ansible', 'helm', 'prometheus',
    'grafana', 'kafka', 'rabbitmq', 'celery', 'machine learning',
    'deep learning', 'nlp',
})


def filter_and_group_skills(technical_list):
    """
    Filter and group a flat technical skills list into categories.
    Returns dict with keys 'programming', 'frameworks', 'databases', 'tools'.
    Empty categories are omitted. Each category is capped at 4 items.
    """
    seen   = set()
    groups = {'programming': [], 'frameworks': [], 'databases': [], 'tools': []}

    for raw in (technical_list or []):
        if not raw or not raw.strip():
            continue

        key        = raw.strip().lower()
        normalized = _NORMALIZATIONS.get(key, raw.strip())
        norm_key   = normalized.lower()

        if norm_key in _EXCLUDED or key in _EXCLUDED:
            continue
        if norm_key in seen:
            continue
        seen.add(norm_key)

        if norm_key in _PROGRAMMING:
            bucket = 'programming'
        elif norm_key in _FRAMEWORKS:
            bucket = 'frameworks'
        elif norm_key in _DATABASES:
            bucket = 'databases'
        elif norm_key in _TOOLS:
            bucket = 'tools'
        else:
            bucket = 'tools'  # catch-all for unrecognised technical items

        if len(groups[bucket]) < 4:
            groups[bucket].append(normalized)

    return {k: v for k, v in groups.items() if v}


def _extract_json(raw_output):
    """Extract JSON from a model response that may contain markdown or leading/trailing text."""
    if not raw_output:
        return None
    raw_output = raw_output.strip()
    match = re.search(r'`{3}(?:json)?\s*([\s\S]*?)\s*`{3}', raw_output)
    if match:
        return match.group(1).strip()
    start = raw_output.find('{')
    end   = raw_output.rfind('}')
    if start != -1 and end != -1 and end > start:
        return raw_output[start:end + 1]
    return None


def extract_and_categorize_skills(text, api_key):
    """Returns { technical: [], soft: [], languages: [] }"""
    if not text or text.isspace():
        return {"technical": [], "soft": [], "languages": []}

    client = genai.Client(api_key=api_key)

    prompt = f"""
    Scan the text below and extract all skills. Classify each into exactly one category:
    - technical: programming languages, frameworks, tools, platforms, technologies, software, databases
    - soft: interpersonal skills, leadership, communication, teamwork, problem-solving, time management
    - languages: spoken/written human languages only (English, French, Hindi, etc.)

    RULES:
    - Return ONLY valid JSON. No extra text.
    - Normalize names (e.g. "React.js" -> "React", "ML" -> "Machine Learning")
    - Each skill appears in exactly one category

    Format:
    {{
        "technical": ["skill1", "skill2"],
        "soft": ["skill1"],
        "languages": ["language1"]
    }}

    TEXT:
    {text}
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )
        raw = response.text.strip()
        parsed = json.loads(_extract_json(raw))
        return {
            "technical": [s.strip() for s in parsed.get("technical", []) if s.strip()],
            "soft":      [s.strip() for s in parsed.get("soft", [])      if s.strip()],
            "languages": [s.strip() for s in parsed.get("languages", []) if s.strip()],
        }
    except Exception as e:
        print(f"Categorize skills error: {e}")
        return {"technical": [], "soft": [], "languages": []}


def generate_gap_suggestions(resume_flat, jd_flat, api_key):
    """Returns a list of 2-4 short actionable suggestion strings."""
    missing = list(set(s.lower() for s in jd_flat) - set(s.lower() for s in resume_flat))

    if not missing:
        return ["Your skills closely match the job requirements."]

    client = genai.Client(api_key=api_key)

    prompt = f"""
    A candidate is missing these skills for a job: {', '.join(missing[:20])}

    Give 2-4 short, actionable suggestions to close the gap.
    Rules:
    - One sentence each. No fluff.
    - Name specific tools, courses, or certifications where possible.
    - Return ONLY a JSON array of strings.

    Example: ["Earn AWS Certified Solutions Architect", "Build a project using Kubernetes and Docker"]
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        raw = response.text.strip()
        # Suggestions come back as a JSON array, not an object
        # Find [ ... ] instead of { ... }
        match = re.search(r'`{3}(?:json)?\s*([\s\S]*?)\s*`{3}', raw)
        if match:
            raw = match.group(1).strip()
        else:
            start = raw.find('[')
            end   = raw.rfind(']')
            if start != -1 and end != -1 and end > start:
                raw = raw[start:end + 1]
        return json.loads(raw)
    except Exception as e:
        print(f"Gap suggestions error: {e}")
        return ["Review the job description and target the top missing skills.", "Consider relevant certifications or side projects to bridge the gap."]

def analyze_resume_and_jd(resume_text, jd_text, api_key):
    """Combine resume skills, JD skills, and gap suggestions into a single AI call."""
    if not resume_text or not resume_text.strip() or not jd_text or not jd_text.strip():
        return {
            "error": True,
            "message": "Please provide valid resume and job description text.",
            "resume_skills": {"technical": [], "soft": [], "languages": []},
            "jd_skills": {"technical": [], "soft": [], "languages": []},
            "suggestions": []
        }

    # 1. INPUT SANITIZATION
    # Remove excessive whitespace
    resume_text = re.sub(r'\s+', ' ', resume_text).strip()
    jd_text = re.sub(r'\s+', ' ', jd_text).strip()
    
    # Trim to max 4000 characters
    resume_text = resume_text[:4000]
    jd_text = jd_text[:4000]

    if not resume_text or not jd_text:
        return {
            "error": True,
            "message": "Please provide valid resume and job description text.",
            "resume_skills": {"technical": [], "soft": [], "languages": []},
            "jd_skills": {"technical": [], "soft": [], "languages": []},
            "suggestions": []
        }

    client = get_client(api_key)

    # 4. OPTIMIZED PROMPT
    prompt = f"""Return ONLY valid JSON in this format:
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
  }},
  "suggestions": []
}}

Rules:
- Extract skills from resume and JD.
- Compare and return 2-4 short suggestions.
- No explanation text.
- No markdown.
- No extra keys.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}
"""

    # 2. MODEL FALLBACK SYSTEM
    models = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro"
    ]

    for model_name in models:
        logger.info(f"Attempting analysis with model: {model_name}")
        
        # 3. STRICT TIMEOUT CONTROL (~12s per model)
        if hasattr(signal, 'alarm') and threading.current_thread() is threading.main_thread():
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(12)

        try:
            # call AI
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            raw = response.text.strip()
            
            # 5. SAFE JSON EXTRACTION
            extracted = _extract_json(raw)
            if not extracted:
                raise ValueError("No valid JSON extracted from response.")
            
            parsed = json.loads(extracted)
            
            # validate structure
            if "resume_skills" not in parsed or "jd_skills" not in parsed or "suggestions" not in parsed:
                raise ValueError("Missing required keys in JSON structure.")
            
            logger.info(f"Successfully generated analysis using {model_name}")
            
            return {
                "error": False,
                "resume_skills": {
                    "technical": [s.strip() for s in parsed.get("resume_skills", {}).get("technical", []) if isinstance(s, str) and s.strip()],
                    "soft": [s.strip() for s in parsed.get("resume_skills", {}).get("soft", []) if isinstance(s, str) and s.strip()],
                    "languages": [s.strip() for s in parsed.get("resume_skills", {}).get("languages", []) if isinstance(s, str) and s.strip()]
                },
                "jd_skills": {
                    "technical": [s.strip() for s in parsed.get("jd_skills", {}).get("technical", []) if isinstance(s, str) and s.strip()],
                    "soft": [s.strip() for s in parsed.get("jd_skills", {}).get("soft", []) if isinstance(s, str) and s.strip()],
                    "languages": [s.strip() for s in parsed.get("jd_skills", {}).get("languages", []) if isinstance(s, str) and s.strip()]
                },
                "suggestions": [s.strip() for s in parsed.get("suggestions", []) if isinstance(s, str) and s.strip()]
            }

        except TimeoutException:
            logger.warning(f"Timeout occurred with model {model_name}")
            continue
        except Exception as e:
            logger.warning(f"Failed with model {model_name}. Error: {e}")
            continue
        finally:
            if hasattr(signal, 'alarm') and threading.current_thread() is threading.main_thread():
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

    # 7. FINAL FALLBACK
    logger.error("All models failed to analyze resume and JD.")
    return {
        "error": True,
        "message": "Analysis timed out or failed. Please try again with a shorter resume.",
        "resume_skills": {"technical": [], "soft": [], "languages": []},
        "jd_skills": {"technical": [], "soft": [], "languages": []},
        "suggestions": ["Analysis timed out. Please try again with a shorter resume."]
    }
