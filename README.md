# AI Resume Analyzer & Builder

A full-stack resume optimization platform that analyzes resumes against job descriptions, identifies missing ATS keywords, scores compatibility, and generates optimized ATS-friendly resumes.

Built with a deterministic ATS intelligence pipeline, dynamic skill registry, PDF round-trip validation, and real-time rescoring.

---

# Features

## Resume Analysis

* Upload resume PDFs or use manual entry mode
* Parse and extract resume content automatically
* Analyze resumes against job descriptions
* Generate ATS compatibility scores with detailed breakdowns

## ATS Intelligence Engine

* Deterministic ATS scoring pipeline
* Dynamic skill normalization and canonicalization
* Context-aware keyword extraction
* Missing skill detection
* Match vs missing skill analysis
* Real-time rescoring after edits

## Smart Skill Registry

* SQLite-backed dynamic skill registry
* Automatic learning of unknown technologies
* Canonical skill normalization
* Industry abbreviation seeding
* Stable alias handling
* Deterministic matching behavior

## Resume Optimization

* AI-assisted resume rewriting
* ATS-focused improvements
* Resume section enhancement
* Optimized keyword placement
* Resume regeneration and PDF export

## PDF Pipeline

* PDF upload + parsing
* Browser preview consistency
* Playwright-based PDF generation
* Round-trip PDF validation
* Deterministic PDF output

## Frontend Experience

* Real-time ATS updates
* Interactive editing workflow
* Manual skill editing
* Dynamic rescoring
* Responsive resume preview

---

# Tech Stack

## Frontend

* HTML
* CSS
* JavaScript

## Backend

* Python
* Flask

## AI / ATS Intelligence

* Gemini API
* Deterministic ATS scoring engine
* Contextual keyword extraction
* Dynamic skill registry

## Database

* SQLite

## PDF Tooling

* Playwright
* PDF parsing utilities

## Testing

* Pytest
* Regression test suites
* Determinism verification
* PDF flow validation

---

# Project Architecture

```text
backend/
│
├── app.py
├── scorer.py
├── matcher.py
├── pdf_generator.py
├── skill_extractor.py
│
├── intelligence/
│   ├── pipeline.py
│   ├── extractor.py
│   ├── matcher.py
│   ├── scoring.py
│   ├── categorizer.py
│   ├── normalizer.py
│   └── display.py
│
├── services/
│   ├── skill_registry.py
│   ├── skill_normalizer.py
│   └── skill_categorizer.py
│
├── database/
│   ├── connection.py
│   ├── schema.py
│   └── skills.db
│
├── tests/
│   ├── test_intelligence.py
│   ├── test_rescore.py
│   └── test_pdf_flow.py
│
frontend/
│
├── index.html
├── style.css
├── script.js
└── templates.js
```

---

# ATS Intelligence Pipeline

```text
Resume / JD
    ↓
Extraction
    ↓
Normalization
    ↓
Registry Canonicalization
    ↓
Categorization
    ↓
Matching
    ↓
ATS Scoring
    ↓
Optimization
    ↓
PDF Generation
```

---

# Key Engineering Highlights

## Deterministic ATS Scoring

The scoring engine is designed to remain stable across:

* repeated runs
* cache resets
* app restarts
* registry warm/cold states

Identical inputs always produce identical outputs.

## Dynamic Skill Registry

Instead of relying on massive hardcoded technology maps, the system:

* normalizes technologies dynamically
* stores discovered skills in SQLite
* learns aliases over time
* gracefully handles unknown technologies

Examples:

* Bun
* Hono
* LangGraph
* CrewAI
* Astro

## Regression-Tested Pipeline

The project includes:

* ATS determinism tests
* rescoring stability tests
* PDF round-trip tests
* registry growth validation
* canonicalization consistency tests

---

# Local Setup

## 1. Clone the Repository

```bash
git clone <your-repo-url>
cd AI-Resume-Analyzer
```

## 2. Create Virtual Environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

## 5. Run the Backend

```bash
python backend/app.py
```

## 6. Open Frontend

Open:

```text
frontend/index.html
```

or serve with a local server.

---

# Running Tests

## Run Full Test Suite

```bash
pytest backend/tests/
```

## Individual Test Suites

```bash
pytest backend/tests/test_intelligence.py
pytest backend/tests/test_rescore.py
pytest backend/tests/test_pdf_flow.py
```

---

# Stability Guarantees

Verified behaviors:

* deterministic ATS scoring
* stateless rescoring
* stable canonicalization
* bounded registry growth
* PDF generation consistency
* browser/PDF rendering parity

---

# Future Improvements

* Authentication system
* Resume templates
* Resume version history
* Multi-language resume support
* Advanced analytics dashboard
* Resume tailoring memory
* Cloud deployment pipeline
* Team/collaboration support

---

# License

MIT License

---

# Author

Soham Kanrar

Built as a production-focused ATS resume optimization platform with deterministic scoring, dynamic skill intelligence, and real-world PDF workflow validation.
