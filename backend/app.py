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

ai_semaphore = threading.Semaphore(2)

class RequestTimeoutException(Exception):
    pass

def request_timeout_handler(signum, frame):
    raise RequestTimeoutException("Global request timeout")

from backend.parser import extract_text
from backend.skill_extractor import extract_and_categorize_skills, generate_gap_suggestions, filter_and_group_skills, analyze_resume_and_jd
from backend.rewriter import generate_structured_resume, optimize_resume_for_jd, generate_resume_from_inputs
from backend import scorer
from backend.pdf_generator import generate_pdf_from_html

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

print("API KEY LOADED:", "YES" if api_key else "NO")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Backend is running"}), 200

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] --- [START /analyze] ---")
    if 'resume' not in request.files or 'jd' not in request.form:
        logger.error(f"[{request_id}] Missing resume or job description in request.")
        return jsonify({"error": "Missing resume or job description"}), 400

    pdf_file = request.files['resume']
    if pdf_file.filename == '':
        logger.error("No selected file.")
        return jsonify({"error": "No selected file"}), 400

    jd_text = request.form['jd']
    
    # Limit JD text to prevent huge AI payloads
    if len(jd_text) > 6000:
        jd_text = jd_text[:6000]
        logger.info("Truncated job description to 6000 characters.")

    if not api_key:
        logger.error("Gemini API Key is missing from .env")
        return jsonify({"error": "Gemini API Key is missing from .env"}), 500

    if hasattr(signal, 'alarm') and threading.current_thread() is threading.main_thread():
        old_handler = signal.signal(signal.SIGALRM, request_timeout_handler)
        signal.alarm(20)

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

        # 2. LIMIT INPUT SIZE (Ensure both are capped to max 4000 chars)
        if len(resume_text) > 4000:
            resume_text = resume_text[:4000]
            logger.info(f"[{request_id}] Truncated resume text to 4000 characters before AI call.")
            
        if len(jd_text) > 4000:
            jd_text = jd_text[:4000]
            logger.info(f"[{request_id}] Truncated job description to 4000 characters before AI call.")

        # 1 & 6. COMBINE AI CALLS & ADD STEP-LEVEL LOGGING
        logger.info(f"[{request_id}] Sending {len(resume_text)} chars of resume and {len(jd_text)} chars of JD for combined AI analysis...")
        
        # ADD CONCURRENCY CONTROL (CRITICAL) & AI TIMEOUT PROTECTION
        with ai_semaphore:
            analysis_result = analyze_resume_and_jd(resume_text, jd_text, api_key)
        
        # HANDLE STRUCTURED ERROR FROM AI & FIX SUGGESTIONS INDEXING BUG
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
        logger.error(f"[{request_id}] Global request timed out after 20 seconds.")
        return jsonify({"error": "Request timed out. The server is overloaded."}), 504
    except Exception as e:
        logger.error(f"[{request_id}] Error during analysis: {e}", exc_info=True)
        # REMOVE INTERNAL ERROR LEAKING
        return jsonify({"error": "An internal server error occurred during analysis."}), 500
    finally:
        if hasattr(signal, 'alarm') and threading.current_thread() is threading.main_thread():
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


@app.route('/optimize', methods=['POST'])
def optimize_resume():
    # Guard: request.json is None if Content-Type header is missing/wrong
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request: body must be JSON with Content-Type application/json"}), 400

    raw_text = data.get('raw_text', '').strip()
    jd_text  = data.get('jd_text',  '').strip()
    # Guard: skills may be null from client; always fall back to empty dict
    skills   = data.get('skills') or {"technical": [], "soft": [], "languages": []}

    if not raw_text:
        return jsonify({"error": "Resume text is empty. Please run Analyze first."}), 400
    if not jd_text:
        return jsonify({"error": "Job description is empty. Please provide a JD."}), 400
    if not api_key:
        return jsonify({"error": "Gemini API key is missing from .env"}), 500

    try:
        initial_score_data = scorer.cached_ats_score(raw_text, jd_text)

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
        print(f"[/optimize] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/generate-from-inputs', methods=['POST'])
def generate_from_inputs():
    data = request.json
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
        structured = generate_resume_from_inputs(inputs, api_key)
        structured['skill_groups'] = filter_and_group_skills(structured.get('technical_skills') or [])
        return jsonify(structured), 200
    except Exception as e:
        print(f"[/generate-from-inputs] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/analyze-manual', methods=['POST'])
def analyze_manual():
    """Extract JD skills and generate gap suggestions using manual user skill inputs."""
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    jd_text        = (data.get('jd_text')        or '').strip()
    user_skills_flat = data.get('user_skills_flat') or []

    if not jd_text:
        return jsonify({"error": "Job description is required"}), 400
    if not api_key:
        return jsonify({"error": "Gemini API key missing from .env"}), 500

    try:
        jd_skills  = extract_and_categorize_skills(jd_text, api_key)
        jd_flat    = jd_skills["technical"] + jd_skills["soft"] + jd_skills["languages"]
        suggestions = generate_gap_suggestions(user_skills_flat, jd_flat, api_key)

        return jsonify({"jd_skills": jd_skills, "suggestions": suggestions}), 200

    except Exception as e:
        print(f"[/analyze-manual] Error: {e}")
        return jsonify({"error": "An internal server error occurred during analysis."}), 500


@app.route('/rewrite', methods=['POST'])
def rewrite_resume():
    data = request.json
    raw_text = data.get('raw_text')

    if not raw_text or not api_key:
        return jsonify({"error": "Missing data or API key"}), 400

    structured_json = generate_structured_resume(raw_text, api_key)
    if not structured_json:
        return jsonify({"error": "Failed to rewrite resume"}), 500

    return jsonify(structured_json), 200


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
