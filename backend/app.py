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

        # 7. KEEP API STRUCTURE SAME
        logger.info(f"[{request_id}] --- [SUCCESS /analyze] ---")
        return jsonify({
            "resume_skills": analysis_result["resume_skills"],
            "jd_skills": analysis_result["jd_skills"],
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
        initial_score_data = scorer.cached_ats_score(raw_text, jd_text)

        with ai_semaphore:
            structured_json = optimize_resume_for_jd(raw_text, jd_text, skills, api_key)
        structured_json['skill_groups'] = filter_and_group_skills(structured_json.get('technical_skills') or [])
        
        improved_score_data = scorer.cached_ats_score(structured_json, jd_text)
        
        # We need to copy the dictionaries since cached results shouldn't be mutated
        initial_score_data = dict(initial_score_data)
        improved_score_data = dict(improved_score_data)

        max_boost = min(25, int(initial_score_data.get("score", 0) * 0.4))
        improvement = improved_score_data.get("score", 0) - initial_score_data.get("score", 0)
        improvement = min(improvement, max_boost)
        improvement = max(0, improvement)
        
        improved_score_data["score"] = initial_score_data.get("score", 0) + improvement

        exp_count = len(structured_json.get("experience", []))
        proj_count = len(structured_json.get("projects", []))
        
        logger.info({
            "experience_count": exp_count,
            "project_limit": proj_count,
            "initial_score": initial_score_data["score"],
            "final_score": improved_score_data["score"],
            "improvement": improvement
        })

        response_payload = {
            "original_score": initial_score_data,
            "optimized_score": improved_score_data,
            "improvement": improvement,
            "original_label": scorer.score_label(initial_score_data["score"]),
            "optimized_label": scorer.score_label(improved_score_data["score"]),
            "confidence": improved_score_data.get("confidence", 75),
            "insights": improved_score_data.get("insights", []),
            "resume": structured_json
        }

        return jsonify(response_payload), 200
    except Exception as e:
        logger.error("[/optimize] Error: %s", e, exc_info=True)
        return jsonify({"error": "An internal server error occurred during optimization."}), 500
    finally:
        data = None
        raw_text = None
        jd_text = None


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
            jd_flat = jd_skills["technical"] + jd_skills["soft"] + jd_skills["languages"]
        suggestions = _local_gap_suggestions(user_skills_flat, jd_flat)

        return jsonify({"jd_skills": jd_skills, "suggestions": suggestions}), 200
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
