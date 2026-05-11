from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import io
import logging
import threading
import signal
import uuid
from dotenv import load_dotenv
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_AI_TEXT_CHARS = 3000
REQUEST_TIMEOUT_SECONDS = 25

ai_semaphore = threading.Semaphore(1)

class RequestTimeoutException(Exception):
    pass

def request_timeout_handler(signum, frame):
    raise RequestTimeoutException("Global request timeout")


def _trim_ai_text(value, max_chars=MAX_AI_TEXT_CHARS):
    return " ".join(str(value or "").split())[:max_chars]


def _start_request_timeout(seconds=REQUEST_TIMEOUT_SECONDS):
    if hasattr(signal, 'alarm') and threading.current_thread() is threading.main_thread():
        old_handler = signal.signal(signal.SIGALRM, request_timeout_handler)
        signal.alarm(seconds)
        return old_handler
    return None


def _clear_request_timeout(old_handler):
    if old_handler is not None and hasattr(signal, 'alarm') and threading.current_thread() is threading.main_thread():
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def _local_gap_suggestions(user_skills_flat, jd_flat):
    user_skills = {str(skill or "").strip().lower() for skill in user_skills_flat if str(skill or "").strip()}
    jd_skills = []
    seen = set()

    for skill in jd_flat:
        normalized = str(skill or "").strip().lower()
        if normalized and normalized not in seen:
            jd_skills.append(normalized)
            seen.add(normalized)

    missing = [skill for skill in jd_skills if skill not in user_skills][:4]
    if not missing:
        return ["Your skills closely match the job requirements."]

    return [f"Add proof of {skill} with a project, metric, or resume bullet." for skill in missing]

from backend.parser import extract_text
from backend.skill_extractor import extract_and_categorize_skills, filter_and_group_skills, analyze_resume_and_jd
from backend.rewriter import generate_structured_resume, optimize_resume_for_jd, generate_resume_from_inputs
from backend import scorer
from backend.pdf_generator import generate_pdf_from_html


def _flatten_skills(skills_dict):
    if not isinstance(skills_dict, dict):
        return []
    return list(skills_dict.get("technical") or []) + \
           list(skills_dict.get("soft") or []) + \
           list(skills_dict.get("languages") or [])


def _canonicalize_skill_struct(skills_dict):
    """Canonicalize each category of a {technical,soft,languages} dict."""
    if not isinstance(skills_dict, dict):
        return {"technical": [], "soft": [], "languages": []}
    return {
        "technical": scorer.canonicalize_skill_list(skills_dict.get("technical") or []),
        "soft": scorer.canonicalize_skill_list(skills_dict.get("soft") or []),
        "languages": scorer.canonicalize_skill_list(skills_dict.get("languages") or []),
    }


def _canonicalize_resume_skills(resume_json):
    """Canonicalize skill fields in a structured resume dict in-place."""
    if not isinstance(resume_json, dict):
        return resume_json
    resume_json["technical_skills"] = scorer.canonicalize_skill_list(resume_json.get("technical_skills") or [])
    resume_json["soft_skills"] = scorer.canonicalize_skill_list(resume_json.get("soft_skills") or [])
    resume_json["languages"] = scorer.canonicalize_skill_list(resume_json.get("languages") or [])
    return resume_json

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

CORS(app, resources={r"/*": {"origins": "*"}})

print("API KEY LOADED:", "YES" if api_key else "NO")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Backend is running"}), 200

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    request_id = str(uuid.uuid4())
    old_handler = None
    resume_text = ""
    jd_text = ""
    logger.info(f"[{request_id}] --- [START /analyze] ---")
    if 'resume' not in request.files or 'jd' not in request.form:
        logger.error(f"[{request_id}] Missing resume or job description in request.")
        return jsonify({"error": "Missing resume or job description"}), 400

    pdf_file = request.files['resume']
    if pdf_file.filename == '':
        logger.error("No selected file.")
        return jsonify({"error": "No selected file"}), 400

    jd_text = _trim_ai_text(request.form['jd'])

    if not api_key:
        logger.error("Gemini API Key is missing from .env")
        return jsonify({"error": "Gemini API Key is missing from .env"}), 500

    old_handler = _start_request_timeout()

    try:
        logger.info(f"[{request_id}] Starting PDF text extraction...")
        resume_text = extract_text(pdf_file)
        if resume_text.startswith("Error reading PDF"):
            logger.error(f"[{request_id}] Failed to parse PDF: {resume_text}")
            return jsonify({"error": resume_text}), 422

        # 4. ADD EARLY EXIT CONDITIONS
        if not resume_text or len(resume_text.strip()) < 50:
            logger.error(f"[{request_id}] Extracted resume text is too short or empty.")
            return jsonify({"error": "Resume text is too short or unreadable. Please check the PDF."}), 422

        resume_text = _trim_ai_text(resume_text)
        jd_text = _trim_ai_text(jd_text)

        logger.info(f"[{request_id}] Sending {len(resume_text)} chars of resume and {len(jd_text)} chars of JD for combined AI analysis...")
        
        with ai_semaphore:
            analysis_result = analyze_resume_and_jd(resume_text, jd_text, api_key)
        
        if analysis_result.get("error"):
            logger.error(f"[{request_id}] AI call failed: {analysis_result.get('message')}")
            return jsonify({"error": analysis_result.get("message")}), 504

        logger.info(f"[{request_id}] Successfully completed AI analysis. Building response...")

        resume_skills = _canonicalize_skill_struct(analysis_result["resume_skills"])
        jd_skills = _canonicalize_skill_struct(analysis_result["jd_skills"])

        # Missing skills against the FULL raw resume text (all sections, not just skills list).
        jd_flat = _flatten_skills(jd_skills)
        matched_skills = scorer.detect_matched_skills(resume_text, jd_flat)
        missing_skills = scorer.detect_missing_skills(resume_text, jd_flat, jd_text)

        logger.info(f"[{request_id}] --- [SUCCESS /analyze] ---")
        return jsonify({
            "resume_skills": resume_skills,
            "jd_skills": jd_skills,
            "jd_skills_flat": jd_flat,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "suggestions": analysis_result["suggestions"],
            "raw_text": resume_text
        }), 200

    except RequestTimeoutException:
        logger.error(f"[{request_id}] Global request timed out after {REQUEST_TIMEOUT_SECONDS} seconds.")
        return jsonify({"error": "Request timed out. The server is overloaded."}), 504
    except Exception as e:
        logger.error(f"[{request_id}] Error during analysis: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred during analysis."}), 500
    finally:
        _clear_request_timeout(old_handler)
        pdf_file.close()
        resume_text = None
        jd_text = None


@app.route('/optimize', methods=['POST'])
def optimize_resume():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request: body must be JSON with Content-Type application/json"}), 400

    raw_text = _trim_ai_text(data.get('raw_text', ''))
    jd_text = _trim_ai_text(data.get('jd_text', ''))
    skills = data.get('skills') or {"technical": [], "soft": [], "languages": []}

    if not raw_text:
        return jsonify({"error": "Resume text is empty. Please run Analyze first."}), 400
    if not jd_text:
        return jsonify({"error": "Job description is empty. Please provide a JD."}), 400
    if not api_key:
        return jsonify({"error": "Gemini API key is missing from .env"}), 500

    try:
        # Extract JD skills first so both scoring calls use the same canonical set.
        with ai_semaphore:
            jd_skill_struct = extract_and_categorize_skills(jd_text, api_key)
        jd_skill_struct = _canonicalize_skill_struct(jd_skill_struct)
        jd_flat = _flatten_skills(jd_skill_struct)

        # 1) Original score from the raw uploaded resume text.
        initial_score_data = scorer.compute_ats_score(raw_text, jd_text, jd_skills=jd_flat)

        # 2) AI optimization.
        with ai_semaphore:
            structured_json = optimize_resume_for_jd(raw_text, jd_text, skills, api_key)
        _canonicalize_resume_skills(structured_json)
        structured_json['skill_groups'] = filter_and_group_skills(structured_json.get('technical_skills') or [])

        # 3) Optimized score from the structured AI-rewritten resume.
        improved_score_data = scorer.compute_ats_score(structured_json, jd_text, jd_skills=jd_flat)

        improvement = max(0, improved_score_data["score"] - initial_score_data["score"])

        logger.info({
            "experience_count": len(structured_json.get("experience", [])),
            "project_count": len(structured_json.get("projects", [])),
            "initial_score": initial_score_data["score"],
            "initial_breakdown": initial_score_data["breakdown"],
            "final_score": improved_score_data["score"],
            "final_breakdown": improved_score_data["breakdown"],
            "improvement": improvement,
            "missing_skills": improved_score_data["missing_skills"][:5],
        })

        response_payload = {
            "original_score": initial_score_data,
            "optimized_score": improved_score_data,
            "improvement": improvement,
            "original_label": scorer.score_label(initial_score_data["score"]),
            "optimized_label": scorer.score_label(improved_score_data["score"]),
            "confidence": improved_score_data["confidence"],
            "insights": improved_score_data["insights"],
            "matched_skills": improved_score_data["matched_skills"],
            "missing_skills": improved_score_data["missing_skills"],
            "jd_skills": jd_skill_struct,
            "jd_skills_flat": jd_flat,
            "resume": structured_json,
        }

        return jsonify(response_payload), 200
    except Exception as e:
        logger.error("[/optimize] Error: %s", e, exc_info=True)
        return jsonify({"error": "An internal server error occurred during optimization."}), 500
    finally:
        data = None
        raw_text = None
        jd_text = None


@app.route('/rescore', methods=['POST'])
def rescore_resume():
    """
    Recompute the ATS score against the CURRENT edited resume state.
    Stateless — the caller supplies the latest resume JSON, the JD text,
    and (optionally) the JD skills list extracted earlier.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    resume_json = data.get('resume')
    jd_text = _trim_ai_text(data.get('jd_text', ''))
    jd_skills_flat = data.get('jd_skills_flat') or []
    original_score = data.get('original_score')

    if not isinstance(resume_json, dict) and not isinstance(resume_json, str):
        return jsonify({"error": "Resume payload is required."}), 400
    if not jd_text:
        return jsonify({"error": "Job description text is required."}), 400

    try:
        if isinstance(resume_json, dict):
            _canonicalize_resume_skills(resume_json)
            resume_json['skill_groups'] = filter_and_group_skills(resume_json.get('technical_skills') or [])

        canonical_jd_skills = scorer.canonicalize_skill_list(jd_skills_flat) if jd_skills_flat else None
        score_data = scorer.compute_ats_score(resume_json, jd_text, jd_skills=canonical_jd_skills)

        baseline = int(original_score) if isinstance(original_score, (int, float)) else None
        improvement = max(0, score_data["score"] - baseline) if baseline is not None else 0

        logger.info({
            "event": "rescore",
            "score": score_data["score"],
            "breakdown": score_data["breakdown"],
            "baseline": baseline,
            "improvement": improvement,
            "missing_skills": score_data["missing_skills"][:5],
        })

        return jsonify({
            "optimized_score": score_data,
            "improvement": improvement,
            "optimized_label": scorer.score_label(score_data["score"]),
            "confidence": score_data["confidence"],
            "insights": score_data["insights"],
            "matched_skills": score_data["matched_skills"],
            "missing_skills": score_data["missing_skills"],
            "resume": resume_json if isinstance(resume_json, dict) else None,
        }), 200
    except Exception as e:
        logger.error("[/rescore] Error: %s", e, exc_info=True)
        return jsonify({"error": "An internal server error occurred during rescoring."}), 500


@app.route('/generate-from-inputs', methods=['POST'])
def generate_from_inputs():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    inputs = data.get('inputs', {})
    if not (inputs.get('name') or '').strip():
        return jsonify({"error": "Full Name is required"}), 400
    if not (inputs.get('title') or '').strip():
        return jsonify({"error": "Target Role is required"}), 400
    if not api_key:
        return jsonify({"error": "Gemini API key missing from .env"}), 500

    try:
        with ai_semaphore:
            structured = generate_resume_from_inputs(inputs, api_key)
        _canonicalize_resume_skills(structured)
        structured['skill_groups'] = filter_and_group_skills(structured.get('technical_skills') or [])
        return jsonify(structured), 200
    except Exception as e:
        logger.error("[/generate-from-inputs] Error: %s", e, exc_info=True)
        return jsonify({"error": "An internal server error occurred during resume generation."}), 500
    finally:
        data = None


@app.route('/analyze-manual', methods=['POST'])
def analyze_manual():
    """Extract JD skills and generate gap suggestions using manual user skill inputs."""
    old_handler = None
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    jd_text = _trim_ai_text(data.get('jd_text'))
    user_skills_flat = data.get('user_skills_flat') or []

    if not jd_text:
        return jsonify({"error": "Job description is required"}), 400
    if not api_key:
        return jsonify({"error": "Gemini API key missing from .env"}), 500

    old_handler = _start_request_timeout()
    try:
        with ai_semaphore:
            jd_skills = extract_and_categorize_skills(jd_text, api_key)
        jd_skills = _canonicalize_skill_struct(jd_skills)
        jd_flat = _flatten_skills(jd_skills)

        canonical_user_skills = scorer.canonicalize_skill_list(user_skills_flat)
        matched_skills = scorer.detect_matched_skills(" ".join(canonical_user_skills), jd_flat)
        missing_skills = scorer.detect_missing_skills(" ".join(canonical_user_skills), jd_flat, jd_text)

        suggestions = _local_gap_suggestions(canonical_user_skills, jd_flat)

        return jsonify({
            "jd_skills": jd_skills,
            "jd_skills_flat": jd_flat,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "suggestions": suggestions,
        }), 200
    except RequestTimeoutException:
        logger.error("[/analyze-manual] Request timed out.")
        return jsonify({
            "jd_skills": {"technical": [], "soft": [], "languages": []},
            "suggestions": ["Manual analysis timed out. Please shorten the job description."],
        }), 504
    except Exception as e:
        logger.error("[/analyze-manual] Error: %s", e, exc_info=True)
        return jsonify({"error": "An internal server error occurred during analysis."}), 500
    finally:
        _clear_request_timeout(old_handler)
        data = None
        jd_text = None


@app.route('/rewrite', methods=['POST'])
def rewrite_resume():
    data = request.get_json(silent=True) or {}
    raw_text = _trim_ai_text(data.get('raw_text'))

    if not raw_text or not api_key:
        return jsonify({"error": "Missing data or API key"}), 400

    try:
        with ai_semaphore:
            structured_json = generate_structured_resume(raw_text, api_key)
        if not structured_json:
            return jsonify({"error": "Failed to rewrite resume"}), 500

        _canonicalize_resume_skills(structured_json)
        return jsonify(structured_json), 200
    except Exception as e:
        logger.error("[/rewrite] Error: %s", e, exc_info=True)
        return jsonify({"error": "An internal server error occurred during rewrite."}), 500
    finally:
        data = None
        raw_text = None


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    data = request.json
    html_content = data.get('html')

    if not html_content:
        return jsonify({"error": "Missing HTML content"}), 400

    try:
        pdf_bytes = generate_pdf_from_html(html_content)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='Optimized_Resume.pdf'
        )
    except Exception as e:
        print(f"PDF Error: {e}")
        return jsonify({"error": "Failed to generate PDF"}), 500


if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
