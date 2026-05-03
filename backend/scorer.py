import re
import json
from functools import lru_cache

TECH_ALIASES = {
    "reactjs": "react",
    "nodejs": "node",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "ml": "machinelearning",
    "ai": "artificialintelligence"
}

PHRASE_ALIASES = {
    "react native": "react",
    "amazon web services": "aws",
    "node js": "node",
    "machine learning": "machinelearning",
    "deep learning": "deeplearning"
}

def normalize_phrase(text):
    text = str(text).lower()
    for k, v in PHRASE_ALIASES.items():
        text = text.replace(k, v)
    return text

def normalize_token(token):
    token = token.lower()
    return TECH_ALIASES.get(token, token)

def normalize_text(text):
    if not text:
        return []
    text = normalize_phrase(text)
    tokens = re.findall(r'\b[a-zA-Z]+\b', text)
    return [normalize_token(t) for t in tokens]

def rank_projects_tfidf(projects, jd_text):
    if not projects:
        return []
    if not jd_text or not str(jd_text).strip():
        return projects

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        corpus = [jd_text] + [
            str(p.get("title", "")) + " " + " ".join(p.get("tech_stack", []))
            for p in projects
        ]
        
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform(corpus)
        
        jd_vec = tfidf[0]
        proj_vecs = tfidf[1:]
        
        scores = cosine_similarity(jd_vec, proj_vecs)[0]
        
        ranked = []
        for score, p in zip(scores, projects):
            text_len = len((str(p.get("title", "")) + " " + " ".join(p.get("tech_stack", []))).split())
            length_penalty = 1 / (1 + text_len * 0.01)
            final_score = score * length_penalty
            ranked.append((final_score, p))
            
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in ranked]
    except ImportError:
        print("TF-IDF ranking failed: sklearn not installed. Returning original order.")
        return projects
    except Exception as e:
        print(f"TF-IDF ranking failed: {e}")
        return projects

def generate_insights(resume_tokens, jd_tokens, resume_skills, jd_skills):
    insights = []
    
    missing_skills = set(jd_skills) - set(resume_skills)
    if missing_skills:
        insights.append(f"Missing key skills: {', '.join(list(missing_skills)[:3])}")
        
    missing_keywords = set(jd_tokens) - set(resume_tokens)
    if missing_keywords:
        insights.append("Resume is weakly aligned with the job description")
        
    if len(resume_tokens) < 200:
        insights.append("Resume is too short — add more impact and measurable results")
        
    # We will compute a rough relevance measure here or pass it later, but using intersection is fine
    if len(jd_tokens.intersection(resume_tokens)) / max(1, len(jd_tokens)) > 0.4:
        insights.append("Projects are highly relevant to the target role")
        
    return insights[:4]

def confidence_score(resume_tokens):
    length_factor = min(len(resume_tokens) / 300, 1)
    return int(60 + length_factor * 40)

def compute_ats_score(resume_json, jd_text, jd_skills=None):
    if not jd_text or not str(jd_text).strip():
        return {"score": 0, "breakdown": {"keywords": 0, "skills": 0, "experience": 0, "projects": 0}, "insights": []}
        
    jd_tokens = set(normalize_text(jd_text))
    if not jd_tokens:
        return {"score": 0, "breakdown": {"keywords": 0, "skills": 0, "experience": 0, "projects": 0}, "insights": []}
        
    if jd_skills is None:
        jd_skills = list(jd_tokens)[:20] # Surrogate if none provided
    else:
        jd_skills = normalize_text(" ".join(jd_skills))
        
    if isinstance(resume_json, str):
        resume_tokens = set(normalize_text(resume_json))
        keyword_overlap = len(jd_tokens.intersection(resume_tokens))
        keyword_score_pct = min(100, (keyword_overlap / max(1, len(jd_tokens))) * 100)
        keyword_pts = int(keyword_score_pct * 0.40)
        
        insights = generate_insights(resume_tokens, jd_tokens, [], jd_skills)
        confidence = confidence_score(resume_tokens)
        
        score = max(0, min(keyword_pts, 100))
        return {
            "score": score,
            "breakdown": {"keywords": keyword_pts, "skills": 0, "experience": 0, "projects": 0},
            "insights": insights,
            "confidence": confidence
        }

    # Extract all text for overall keyword match
    resume_text = ""
    resume_text += str(resume_json.get("summary", "")) + " "
    resume_skills_raw = resume_json.get("technical_skills", []) + resume_json.get("soft_skills", []) + resume_json.get("languages", [])
    resume_text += " ".join(resume_skills_raw) + " "
    for exp in resume_json.get("experience", []):
        resume_text += str(exp.get("role", "")) + " "
        resume_text += " ".join(exp.get("points", [])) + " "
    for proj in resume_json.get("projects", []):
        resume_text += str(proj.get("title", "")) + " "
        resume_text += " ".join(proj.get("tech_stack", [])) + " "
        resume_text += " ".join(proj.get("points", [])) + " "
        
    resume_tokens = set(normalize_text(resume_text))
    keyword_overlap = len(jd_tokens.intersection(resume_tokens))
    keyword_score_pct = min(100, (keyword_overlap / max(1, len(jd_tokens))) * 100)
    keyword_pts = int(keyword_score_pct * 0.40)
    
    # Skills Match
    resume_skills = set()
    for s in resume_skills_raw:
        resume_skills.update(normalize_text(s))
        
    jd_skill_keywords = set(jd_skills).intersection(resume_skills)
    skill_score_pct = min(100, (len(jd_skill_keywords) / max(1, len(jd_skills))) * 100) if jd_skills else 0
    skill_pts = int(skill_score_pct * 0.30)
    
    # Experience
    exp_score_pct = 0
    experiences = resume_json.get("experience", [])
    if experiences:
        exp_text = " ".join([str(e.get("role", "")) + " " + " ".join(e.get("points", [])) for e in experiences])
        exp_tokens = set(normalize_text(exp_text))
        exp_overlap = len(jd_tokens.intersection(exp_tokens))
        exp_score_pct = min(100, (exp_overlap / max(1, len(jd_tokens) * 0.5)) * 100)
    exp_pts = int(exp_score_pct * 0.20)
    
    # Projects
    proj_score_pct = 0
    projects = resume_json.get("projects", [])
    if projects:
        proj_text = " ".join([str(p.get("title", "")) + " " + " ".join(p.get("tech_stack", [])) + " ".join(p.get("points", [])) for p in projects])
        proj_tokens = set(normalize_text(proj_text))
        proj_overlap = len(jd_tokens.intersection(proj_tokens))
        proj_score_pct = min(100, (proj_overlap / max(1, len(jd_tokens) * 0.3)) * 100)
    proj_pts = int(proj_score_pct * 0.10)
    
    total_score = keyword_pts + skill_pts + exp_pts + proj_pts
    total_score = max(0, min(total_score, 100))
    
    insights = generate_insights(list(resume_tokens), list(jd_tokens), list(resume_skills), list(jd_skills))
    confidence = confidence_score(list(resume_tokens))
    
    return {
        "score": total_score,
        "breakdown": {
            "keywords": keyword_pts,
            "skills": skill_pts,
            "experience": exp_pts,
            "projects": proj_pts
        },
        "insights": insights,
        "confidence": confidence
    }

def score_label(score):
    if score >= 80:
        return "Excellent"
    elif score >= 65:
        return "Good"
    elif score >= 50:
        return "Needs Improvement"
    else:
        return "Poor"

@lru_cache(maxsize=100)
def _cached_ats_score_internal(resume_str, jd_text):
    try:
        resume_data = json.loads(resume_str)
    except Exception:
        resume_data = resume_str
    return compute_ats_score(resume_data, jd_text)

def cached_ats_score(resume_text, jd_text):
    if isinstance(resume_text, dict):
        resume_str = json.dumps(resume_text, sort_keys=True)
    else:
        resume_str = str(resume_text)
    return _cached_ats_score_internal(resume_str, jd_text)
