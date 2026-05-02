from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import io
from dotenv import load_dotenv
from pathlib import Path

from backend.parser import extract_text
from backend.skill_extractor import extract_and_categorize_skills, generate_gap_suggestions, filter_and_group_skills
from backend.rewriter import generate_structured_resume, optimize_resume_for_jd, generate_resume_from_inputs
from backend.pdf_generator import generate_pdf_from_html

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        resp = app.make_response("")
        resp.headers["Access-Control-Allow-Origin"]  = request.headers.get("Origin", "*")
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Max-Age"]       = "86400"
        return resp

print("API KEY LOADED:", "YES" if api_key else "NO")

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    if 'resume' not in request.files or 'jd' not in request.form:
        return jsonify({"error": "Missing resume or job description"}), 400

    pdf_file = request.files['resume']
    jd_text = request.form['jd']

    if not api_key:
        return jsonify({"error": "Gemini API Key is missing from .env"}), 500

    try:
        resume_text = extract_text(pdf_file)
        if "Error reading PDF" in resume_text:
            return jsonify({"error": resume_text}), 422

        resume_skills = extract_and_categorize_skills(resume_text, api_key)
        jd_skills = extract_and_categorize_skills(jd_text, api_key)

        resume_flat = resume_skills["technical"] + resume_skills["soft"] + resume_skills["languages"]
        jd_flat = jd_skills["technical"] + jd_skills["soft"] + jd_skills["languages"]
        suggestions = generate_gap_suggestions(resume_flat, jd_flat, api_key)

        return jsonify({
            "resume_skills": resume_skills,
            "jd_skills": jd_skills,
            "suggestions": suggestions,
            "raw_text": resume_text
        }), 200

    except Exception as e:
        print(f"Error during analysis: {e}")
        return jsonify({"error": "An internal server error occurred during analysis."}), 500


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
        structured_json = optimize_resume_for_jd(raw_text, jd_text, skills, api_key)
        structured_json['skill_groups'] = filter_and_group_skills(structured_json.get('technical_skills') or [])
        return jsonify(structured_json), 200
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
        debug=True
    )
