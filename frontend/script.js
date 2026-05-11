// ── Canonical skill registry (mirrors backend scorer.CANONICAL_SKILLS) ──
// Used for display capitalization so skills look professional everywhere
// (Your Skills, JD Requirements, missing skills, resume preview).
const CANONICAL_SKILL_ALIASES = {
    'javascript':'JavaScript','js':'JavaScript','ecmascript':'JavaScript',
    'typescript':'TypeScript','ts':'TypeScript',
    'python':'Python','py':'Python','python3':'Python',
    'java':'Java','c++':'C++','cpp':'C++','c#':'C#','csharp':'C#','c':'C',
    'go':'Go','golang':'Go','rust':'Rust','ruby':'Ruby','php':'PHP',
    'swift':'Swift','kotlin':'Kotlin','scala':'Scala','matlab':'MATLAB','perl':'Perl',
    'bash':'Bash','shell':'Shell','html':'HTML','html5':'HTML','css':'CSS','css3':'CSS','sql':'SQL',
    'react':'React','reactjs':'React','react.js':'React',
    'react native':'React Native','react-native':'React Native',
    'vue':'Vue.js','vuejs':'Vue.js','vue.js':'Vue.js',
    'angular':'Angular','angularjs':'Angular','angular.js':'Angular',
    'node':'Node.js','nodejs':'Node.js','node.js':'Node.js','node js':'Node.js',
    'express':'Express.js','expressjs':'Express.js','express.js':'Express.js',
    'next':'Next.js','nextjs':'Next.js','next.js':'Next.js',
    'nuxt':'Nuxt.js','nuxtjs':'Nuxt.js','nuxt.js':'Nuxt.js',
    'django':'Django','flask':'Flask','fastapi':'FastAPI','fast api':'FastAPI',
    'spring':'Spring','spring boot':'Spring Boot','springboot':'Spring Boot',
    'rails':'Rails','ruby on rails':'Rails','laravel':'Laravel',
    'tensorflow':'TensorFlow','pytorch':'PyTorch','torch':'PyTorch','keras':'Keras',
    'sklearn':'scikit-learn','scikit-learn':'scikit-learn','scikit learn':'scikit-learn',
    'pandas':'Pandas','numpy':'NumPy','scipy':'SciPy',
    'bootstrap':'Bootstrap','tailwind':'Tailwind CSS','tailwindcss':'Tailwind CSS','tailwind css':'Tailwind CSS',
    'jquery':'jQuery','redux':'Redux','svelte':'Svelte',
    'mysql':'MySQL','postgresql':'PostgreSQL','postgres':'PostgreSQL','psql':'PostgreSQL',
    'sqlite':'SQLite','mongodb':'MongoDB','mongo':'MongoDB','redis':'Redis',
    'cassandra':'Cassandra','dynamodb':'DynamoDB','oracle':'Oracle',
    'sql server':'SQL Server','mssql':'SQL Server','elasticsearch':'Elasticsearch',
    'firebase':'Firebase','supabase':'Supabase','neo4j':'Neo4j','mariadb':'MariaDB',
    'docker':'Docker','kubernetes':'Kubernetes','k8s':'Kubernetes',
    'git':'Git','github':'GitHub','github actions':'GitHub Actions','gitlab ci':'GitLab CI',
    'linux':'Linux','unix':'Linux',
    'aws':'AWS','amazon web services':'AWS',
    'gcp':'GCP','google cloud':'GCP','google cloud platform':'GCP',
    'azure':'Azure','microsoft azure':'Azure',
    'rest':'REST APIs','rest api':'REST APIs','rest apis':'REST APIs','restful':'REST APIs',
    'restful api':'REST APIs','restful apis':'REST APIs',
    'graphql':'GraphQL','nginx':'Nginx','apache':'Apache','jenkins':'Jenkins',
    'ci/cd':'CI/CD','cicd':'CI/CD','ci cd':'CI/CD',
    'webpack':'Webpack','vite':'Vite','jest':'Jest','pytest':'Pytest',
    'postman':'Postman','swagger':'Swagger','openapi':'Swagger',
    'terraform':'Terraform','ansible':'Ansible','helm':'Helm',
    'prometheus':'Prometheus','grafana':'Grafana',
    'kafka':'Kafka','apache kafka':'Kafka','rabbitmq':'RabbitMQ','celery':'Celery',
    'machine learning':'Machine Learning','ml':'Machine Learning',
    'deep learning':'Deep Learning','dl':'Deep Learning',
    'nlp':'NLP','natural language processing':'NLP','computer vision':'Computer Vision',
    'data analysis':'Data Analysis','data analytics':'Data Analysis',
    'data engineering':'Data Engineering','etl':'ETL',
    'tableau':'Tableau','power bi':'Power BI','powerbi':'Power BI',
    'excel':'Excel','microsoft excel':'Excel','figma':'Figma','jira':'Jira',
    'agile':'Agile','scrum':'Scrum','kanban':'Kanban',
};
const PRESERVE_UPPER = new Set(['aws','gcp','sql','html','css','nlp','etl','api','ai','ml']);

function canonicalizeSkill(skill) {
    if (!skill || typeof skill !== 'string') return '';
    const cleaned = skill.replace(/\s+/g, ' ').trim().replace(/^[,;:.|/]+|[,;:.|/]+$/g, '');
    if (!cleaned) return '';
    const direct = CANONICAL_SKILL_ALIASES[cleaned.toLowerCase()];
    if (direct) return direct;
    // Fallback: smart title-case preserving acronyms / dotted suffixes.
    return cleaned.split(/([\s/\-])/).map(part => {
        if (!part || /^[\s/\-]+$/.test(part)) return part;
        const lower = part.toLowerCase();
        if (PRESERVE_UPPER.has(lower)) return lower.toUpperCase();
        if (part.includes('.')) {
            const [h, ...rest] = part.split('.');
            return (h.charAt(0).toUpperCase() + h.slice(1).toLowerCase()) + '.' + rest.join('.').toLowerCase();
        }
        return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase();
    }).join('');
}

function canonicalizeSkillList(list) {
    const seen = new Set();
    const out = [];
    for (const raw of list || []) {
        const c = canonicalizeSkill(raw);
        if (!c) continue;
        const k = c.toLowerCase();
        if (seen.has(k)) continue;
        seen.add(k);
        out.push(c);
    }
    return out;
}

// ── Client-side skill filtering + grouping (mirrors backend filter_and_group_skills) ──
// Runs immediately on every data set so skill_groups is always populated,
// even when the Flask server hasn't been restarted with the new backend code.
function filterAndGroupSkills(technicalList) {
    const NORM = {
        'nodejs':'Node.js','node':'Node.js','reactjs':'React','react.js':'React',
        'vuejs':'Vue.js','vue':'Vue.js','angularjs':'Angular','angular.js':'Angular',
        'expressjs':'Express.js','express':'Express.js','nextjs':'Next.js','next.js':'Next.js',
        'github':'Git','git/github':'Git','git & github':'Git',
        'tailwindcss':'Tailwind CSS','tailwind':'Tailwind CSS','html5':'HTML','css3':'CSS',
        'restful':'REST APIs','rest api':'REST APIs','rest apis':'REST APIs',
        'ml':'Machine Learning','dl':'Deep Learning','sklearn':'scikit-learn',
        'postgres':'PostgreSQL','tensorflow':'TensorFlow','pytorch':'PyTorch',
    };
    const EXCL = new Set([
        'vs code','vscode','visual studio code','visual studio','intellij','intellij idea',
        'pycharm','webstorm','eclipse','netbeans','xcode','android studio','sublime text','atom','vim','emacs',
        'data structures','algorithms','operating systems','dbms','database management',
        'computer networks','object oriented programming','oop','oops',
        'software engineering','computer science','web development','software development',
        'full stack','frontend','backend','front-end','back-end',
        'artificial intelligence','ai','computer vision','big data','cloud computing',
        'internet of things','iot','blockchain','programming','coding','development','debugging',
        'windows','macos','ubuntu',
    ]);
    const PROG = new Set(['python','javascript','typescript','java','c','c++','c#','go','rust','ruby','php','swift','kotlin','r','scala','matlab','perl','bash','shell','html','css','sql']);
    const FWRK = new Set(['react','vue.js','angular','node.js','express.js','next.js','nuxt.js','django','flask','fastapi','spring','spring boot','rails','laravel','tensorflow','pytorch','keras','scikit-learn','pandas','numpy','scipy','bootstrap','tailwind css','jquery','redux','svelte','fastify','nest.js']);
    const DBS  = new Set(['mysql','postgresql','sqlite','mongodb','redis','cassandra','dynamodb','oracle','sql server','elasticsearch','firebase','supabase','neo4j','couchdb','mariadb','influxdb']);
    const TOOL = new Set(['docker','kubernetes','git','linux','aws','gcp','azure','rest apis','graphql','nginx','apache','jenkins','ci/cd','github actions','gitlab ci','webpack','vite','jest','pytest','postman','swagger','terraform','ansible','helm','prometheus','grafana','kafka','rabbitmq','celery','machine learning','deep learning','nlp']);

    const seen = new Set();
    const g = { programming:[], frameworks:[], databases:[], tools:[] };

    for (const raw of (technicalList || [])) {
        if (!raw?.trim()) continue;
        const key  = raw.trim().toLowerCase();
        const norm = NORM[key] || raw.trim();
        const nk   = norm.toLowerCase();
        if (EXCL.has(nk) || EXCL.has(key)) continue;
        if (seen.has(nk)) continue;
        seen.add(nk);
        const bucket = PROG.has(nk) ? 'programming' : FWRK.has(nk) ? 'frameworks' : DBS.has(nk) ? 'databases' : 'tools';
        if (g[bucket].length < 4) g[bucket].push(norm);
    }
    return Object.fromEntries(Object.entries(g).filter(([,v]) => v.length));
}

document.addEventListener('DOMContentLoaded', () => {
    const controllers = { analyze: null, optimize: null, manual: null, builder: null, pdf: null };
    const latestRequestIds = { analyze: 0, optimize: 0, manual: 0, builder: 0, pdf: 0 };
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const API_BASE_URL = 'https://resume-analyzer-c5s7.onrender.com';
    const apiUrl = (path) => `${API_BASE_URL}${path}`;

    function fetchWithTimeout(url, options = {}, timeout = 25000) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);
        
        return fetch(url, {
            ...options,
            signal: options.signal || controller.signal
        }).finally(() => clearTimeout(id));
    }

    // UI Elements
    const form           = document.getElementById('analyzer-form');
    const submitBtn      = document.getElementById('submit-btn');
    const btnText        = submitBtn.querySelector('span');
    const spinner        = document.getElementById('loading-spinner');
    const errorMessage   = document.getElementById('error-message');
    const resultsSection = document.getElementById('results-section');
    const pdfViewer      = document.getElementById('pdf-viewer');

    // Skill containers — Your Skills
    const skillContainers = {
        technical: document.getElementById('skills-technical'),
        soft:      document.getElementById('skills-soft'),
        languages: document.getElementById('skills-languages'),
    };
    // JD containers (read-only)
    const jdContainers = {
        technical: document.getElementById('jd-technical'),
        soft:      document.getElementById('jd-soft'),
        languages: document.getElementById('jd-languages'),
    };
    const suggestionsList    = document.getElementById('suggestions-list');
    const newSkillInput      = document.getElementById('new-skill-input');
    const newSkillCategory   = document.getElementById('new-skill-category');
    const addSkillBtn        = document.getElementById('add-skill-btn');

    const startRewriteBtn        = document.getElementById('start-rewrite-btn');
    const builderSection         = document.getElementById('builder-section');
    const manualAnalysisSection  = document.getElementById('manual-analysis-section');
    const manualSkillContainers  = {
        technical: document.getElementById('manual-skills-technical'),
        soft:      document.getElementById('manual-skills-soft'),
        languages: document.getElementById('manual-skills-languages'),
    };
    const manualJdContainers = {
        technical: document.getElementById('manual-jd-technical'),
        soft:      document.getElementById('manual-jd-soft'),
        languages: document.getElementById('manual-jd-languages'),
    };
    const manualSkillsMatched   = document.getElementById('manual-skills-matched');
    const manualSkillsMissing   = document.getElementById('manual-skills-missing');
    const manualSuggestionsList = document.getElementById('manual-suggestions-list');
    const resumeDocument  = document.getElementById('resume-document');
    const downloadPdfBtn  = document.getElementById('download-pdf-btn');
    const templateSelect  = document.getElementById('templateSelect');

    // File upload
    const fileInput         = document.getElementById('resume-file');
    const uploadText        = document.getElementById('upload-text');
    const fileNameContainer = document.getElementById('file-name');
    const fileNameText      = document.getElementById('file-name-text');

    // GLOBAL STATE
    let savedRawText  = "";
    let savedJdText   = "";
    let savedJdSkillsFlat = [];
    let originalScoreSnapshot = null;   // baseline for "Original Score" — set once after first /optimize
    let currentSkills = { technical: [], soft: [], languages: [] };
    let currentStructuredData = null;
    let activeSections = {
        experience: true, projects: true, certifications: true, education: true,
        technical: true,  soft: true,     languages: true,
    };

    // ── Stage state machine: idle → processing → analyzed ──────────────────
    const idleStage       = document.getElementById('input-section');
    const processingStage = document.getElementById('processing-stage');
    const analyzedStage   = document.getElementById('main-results-wrapper');
    const processingSteps = Array.from(document.querySelectorAll('#processing-steps .processing-step'));
    const processingTitle = document.getElementById('processing-title');
    const processingSubtitle = document.getElementById('processing-subtitle');
    const processingBarFill  = document.getElementById('processing-bar-fill');

    let appStage = 'idle';

    function setStage(stage) {
        if (stage === appStage) return;
        appStage = stage;
        document.body.classList.toggle('stage-analyzed', stage === 'analyzed');
        document.body.classList.toggle('stage-processing', stage === 'processing');
        // idle visibility — animate-out via is-leaving for a smooth slide.
        if (stage === 'idle') {
            idleStage.classList.remove('is-leaving', 'is-hidden');
            analyzedStage.classList.add('is-hidden');
            hideProcessingStage();
            errorMessage.classList.add('hidden');
        } else if (stage === 'processing') {
            // Trigger leave animation on idle, but keep it in the DOM during overlay.
            idleStage.classList.add('is-leaving');
            analyzedStage.classList.add('is-hidden');
            showProcessingStage();
        } else if (stage === 'analyzed') {
            idleStage.classList.add('is-hidden');
            idleStage.classList.remove('is-leaving');
            analyzedStage.classList.remove('is-hidden');
            hideProcessingStage();
            // Scroll to top of workspace so user lands on the score card.
            window.requestAnimationFrame(() => {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        }
    }

    function showProcessingStage() {
        processingStage.classList.remove('is-hidden');
        processingStage.setAttribute('aria-hidden', 'false');
        // Next frame so the transition can play.
        window.requestAnimationFrame(() => processingStage.classList.add('is-active'));
        resetProcessingSteps();
    }

    function hideProcessingStage() {
        processingStage.classList.remove('is-active');
        processingStage.setAttribute('aria-hidden', 'true');
        // Wait for the transition to finish before fully hiding.
        setTimeout(() => {
            if (!processingStage.classList.contains('is-active')) {
                processingStage.classList.add('is-hidden');
            }
        }, 340);
    }

    function resetProcessingSteps() {
        processingSteps.forEach(el => el.classList.remove('is-active', 'is-done'));
        if (processingBarFill) processingBarFill.style.width = '0%';
        if (processingSubtitle) processingSubtitle.textContent = 'Sit tight — this only takes a moment.';
    }

    function setProcessingStep(stepIndex) {
        const total = processingSteps.length;
        processingSteps.forEach((el, i) => {
            el.classList.remove('is-active', 'is-done');
            if (i < stepIndex)       el.classList.add('is-done');
            else if (i === stepIndex) el.classList.add('is-active');
        });
        const current = processingSteps[Math.min(stepIndex, total - 1)];
        if (current && processingSubtitle) {
            processingSubtitle.textContent = current.querySelector('.processing-step__label').textContent + '…';
        }
        if (processingBarFill) {
            const pct = Math.min(100, Math.round((stepIndex / total) * 100));
            processingBarFill.style.width = pct + '%';
        }
    }

    function markProcessingComplete() {
        processingSteps.forEach(el => {
            el.classList.remove('is-active');
            el.classList.add('is-done');
        });
        if (processingBarFill) processingBarFill.style.width = '100%';
        if (processingSubtitle) processingSubtitle.textContent = 'All set — opening your workspace.';
    }

    /**
     * Drive the processing stage. Runs `taskPromise` (the real backend work)
     * alongside a stepped animation, then enforces a minimum stage duration
     * so the transition feels intentional even when the backend is fast.
     */
    async function runProcessingStage(taskPromise, { minDurationMs = 1800, stepCadenceMs = 360 } = {}) {
        setStage('processing');
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const startedAt = Date.now();
        let stepIndex = 0;
        setProcessingStep(stepIndex);

        const stepTimer = setInterval(() => {
            if (stepIndex < processingSteps.length - 1) {
                stepIndex++;
                setProcessingStep(stepIndex);
            }
        }, reduceMotion ? 80 : stepCadenceMs);

        let result, error;
        try {
            result = await taskPromise;
        } catch (err) {
            error = err;
        } finally {
            clearInterval(stepTimer);
        }

        const elapsed = Date.now() - startedAt;
        const remaining = Math.max(0, minDurationMs - elapsed);
        if (remaining && !reduceMotion) {
            await new Promise(r => setTimeout(r, remaining));
        }

        markProcessingComplete();
        if (!reduceMotion) {
            await new Promise(r => setTimeout(r, 280));
        }

        if (error) {
            setStage('idle');
            throw error;
        }
        return result;
    }

    // Back button — returns user to the idle stage with their state preserved.
    const backToUploadBtn = document.getElementById('back-to-upload-btn');
    if (backToUploadBtn) {
        backToUploadBtn.addEventListener('click', () => {
            // Restore JD text if the textarea was cleared (it shouldn't have been,
            // but defensive — covers the case where user switched modes).
            const jdInput = document.getElementById('jd-text');
            if (jdInput && !jdInput.value && savedJdText) {
                jdInput.value = savedJdText;
            }
            const mJdInput = document.getElementById('m-jd-text');
            if (mJdInput && !mJdInput.value && savedJdText) {
                mJdInput.value = savedJdText;
            }
            setStage('idle');
            window.requestAnimationFrame(() => {
                idleStage.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        });
    }

    // Debounced rescore — fires whenever the user edits or adds resume entries.
    let rescoreTimer = null;
    let rescoreController = null;
    function scheduleRescore(delayMs = 600) {
        if (!currentStructuredData || !savedJdText) return;
        if (rescoreTimer) clearTimeout(rescoreTimer);
        rescoreTimer = setTimeout(runRescore, delayMs);
    }

    async function runRescore() {
        if (!currentStructuredData || !savedJdText) return;
        if (rescoreController) rescoreController.abort();
        rescoreController = new AbortController();
        const signal = rescoreController.signal;
        try {
            const res = await fetchWithTimeout(apiUrl('/rescore'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    resume: currentStructuredData,
                    jd_text: savedJdText,
                    jd_skills_flat: savedJdSkillsFlat,
                    original_score: originalScoreSnapshot,
                }),
                signal,
            }, 15000);
            if (!res.ok) return;
            const payload = await res.json();
            console.log('[rescore] score=', payload.optimized_score?.score,
                        'breakdown=', payload.optimized_score?.breakdown,
                        'missing=', (payload.missing_skills || []).slice(0, 5));
            // Re-shape payload to match updateScoreCard's expected fields.
            updateScoreCard({
                original_score: { score: originalScoreSnapshot ?? payload.optimized_score.score },
                optimized_score: payload.optimized_score,
                improvement: payload.improvement,
                optimized_label: payload.optimized_label,
                confidence: payload.confidence,
                insights: payload.insights,
            });
            renderMissingSkills(payload.missing_skills, payload.matched_skills);
        } catch (err) {
            if (err.name === 'AbortError') return;
            console.warn('[rescore] failed:', err);
        }
    }

    function renderMissingSkills(missing, matched) {
        // Manual mode panel
        if (manualSkillsMissing && manualSkillsMatched) {
            const matchedStyle = { bg:'rgba(16,185,129,0.12)', color:'#6ee7b7', border:'rgba(16,185,129,0.25)' };
            const missingStyle = { bg:'rgba(239,68,68,0.10)',  color:'#fca5a5', border:'rgba(239,68,68,0.20)' };
            manualSkillsMatched.innerHTML = '';
            manualSkillsMissing.innerHTML = '';
            (matched || []).forEach(s => manualSkillsMatched.appendChild(makeBadge(canonicalizeSkill(s), matchedStyle, null)));
            (missing || []).forEach(s => manualSkillsMissing.appendChild(makeBadge(canonicalizeSkill(s), missingStyle, null)));
        }
    }

    // ── Single setter: always computes skill_groups so templates always show grouped skills ──
    function setCurrentData(data) {
        currentStructuredData = data;
        // Canonicalize skill arrays so display capitalization is consistent everywhere.
        currentStructuredData.technical_skills = canonicalizeSkillList(currentStructuredData.technical_skills || []);
        currentStructuredData.soft_skills      = canonicalizeSkillList(currentStructuredData.soft_skills || []);
        currentStructuredData.languages        = canonicalizeSkillList(currentStructuredData.languages || []);
        // Always compute groups client-side; backend value takes precedence if present
        if (!currentStructuredData.skill_groups || !Object.keys(currentStructuredData.skill_groups).length) {
            currentStructuredData.skill_groups = filterAndGroupSkills(currentStructuredData.technical_skills || []);
        }
        console.log('[setCurrentData] skill_groups:', JSON.stringify(currentStructuredData.skill_groups));
    }

    // ── Badge style configs ──────────────────────────────────────────────────
    const userBadgeStyle = {
        technical: { bg: '#e0f2fe', color: '#0369a1', border: 'transparent' },
        soft:      { bg: '#ede9fe', color: '#6d28d9', border: 'transparent' },
        languages: { bg: '#dcfce7', color: '#166534', border: 'transparent' },
    };
    const jdBadgeStyle = {
        technical: { bg: '#e0f2fe', color: '#0369a1', border: 'transparent' },
        soft:      { bg: '#ede9fe', color: '#6d28d9', border: 'transparent' },
        languages: { bg: '#dcfce7', color: '#166534', border: 'transparent' },
    };

    // ── Render helpers ───────────────────────────────────────────────────────
    function makeBadge(text, style, onRemove) {
        const badge = document.createElement('div');
        badge.style.cssText = `display:inline-flex;align-items:center;gap:6px;padding:6px 10px;
            border-radius:999px;font-size:13.5px;font-weight:500;
            background:${style.bg};color:${style.color};border:1px solid ${style.border};`;

        const label = document.createElement('span');
        label.textContent = text;
        badge.appendChild(label);

        if (onRemove) {
            const x = document.createElement('button');
            x.textContent = '×';
            x.style.cssText = 'background:none;border:none;cursor:pointer;padding:0;font-size:14px;line-height:1;color:inherit;opacity:0.7;';
            x.addEventListener('click', onRemove);
            badge.appendChild(x);
        }
        return badge;
    }

    function renderUserSkills() {
        ['technical', 'soft', 'languages'].forEach(cat => {
            const container = skillContainers[cat];
            container.innerHTML = '';
            currentSkills[cat].forEach((skill, idx) => {
                container.appendChild(makeBadge(canonicalizeSkill(skill), userBadgeStyle[cat], () => {
                    currentSkills[cat].splice(idx, 1);
                    renderUserSkills();
                }));
            });
        });
    }

    function renderJdSkills(jdSkills) {
        ['technical', 'soft', 'languages'].forEach(cat => {
            const container = jdContainers[cat];
            container.innerHTML = '';
            (jdSkills[cat] || []).forEach(skill => {
                container.appendChild(makeBadge(canonicalizeSkill(skill), jdBadgeStyle[cat], null));
            });
        });
    }

    function renderTipList(container, tips) {
        container.innerHTML = '';
        (tips || []).forEach(tip => {
            const li = document.createElement('li');
            li.className = 'skill-panel__suggestion-item';
            li.innerHTML = `<span class="skill-panel__suggestion-marker">›</span><span>${tip}</span>`;
            container.appendChild(li);
        });
    }

    function renderSuggestions(suggestions) {
        renderTipList(suggestionsList, suggestions);
    }

    // ── Manual analysis render helpers ──────────────────────────────────────
    function renderManualAnalysis(userSkills, jdSkills, matchedSkills, missingSkills) {
        ['technical', 'soft', 'languages'].forEach(cat => {
            manualSkillContainers[cat].innerHTML = '';
            (userSkills[cat] || []).forEach(skill => {
                manualSkillContainers[cat].appendChild(makeBadge(canonicalizeSkill(skill), userBadgeStyle[cat], null));
            });
            manualJdContainers[cat].innerHTML = '';
            (jdSkills[cat] || []).forEach(skill => {
                manualJdContainers[cat].appendChild(makeBadge(canonicalizeSkill(skill), jdBadgeStyle[cat], null));
            });
        });

        const matchedStyle = { bg:'rgba(16,185,129,0.12)',  color:'#6ee7b7', border:'rgba(16,185,129,0.25)' };
        const missingStyle = { bg:'rgba(239,68,68,0.10)',   color:'#fca5a5', border:'rgba(239,68,68,0.20)' };

        manualSkillsMatched.innerHTML = '';
        manualSkillsMissing.innerHTML = '';
        // Trust backend matched/missing — those are computed against ALL resume content,
        // not just the flat "Your Skills" list (which misses skills mentioned only in
        // experience or projects).
        canonicalizeSkillList(matchedSkills || []).forEach(s =>
            manualSkillsMatched.appendChild(makeBadge(s, matchedStyle, null)));
        canonicalizeSkillList(missingSkills || []).forEach(s =>
            manualSkillsMissing.appendChild(makeBadge(s, missingStyle, null)));
    }

    function renderManualSuggestions(suggestions) {
        renderTipList(manualSuggestionsList, suggestions);
    }

    // ── Utility: parse comma-separated skill string → array ──────────────────
    function parseCommaList(str) {
        return str ? str.split(',').map(s => s.trim()).filter(Boolean) : [];
    }

    // ── State sync helpers ───────────────────────────────────────────────────
    // Set a nested value on obj using a path like "experience[0].role"
    function setPath(obj, path, value) {
        const parts = path.replace(/\[(\d+)\]/g, '.$1').split('.');
        let cur = obj;
        for (let i = 0; i < parts.length - 1; i++) {
            if (cur == null) return;
            cur = cur[parts[i]];
        }
        if (cur != null) cur[parts[parts.length - 1]] = value;
    }

    // Read all data-bind elements in the live DOM and flush their values
    // back into currentStructuredData before a re-render.
    function harvestEdits() {
        if (!currentStructuredData) return;
        resumeDocument.querySelectorAll('[data-bind]').forEach(el => {
            const path  = el.dataset.bind;
            const type  = el.dataset.bindType;
            const sep   = el.dataset.bindSep || '\n';
            const value = type === 'array'
                ? el.innerText.split(sep).map(s => s.trim()).filter(Boolean)
                : el.innerText.trim();
            setPath(currentStructuredData, path, value);
        });
    }

    // ── Render helper ────────────────────────────────────────────────────────
    function renderResume(skipHarvest = false) {
        if (!currentStructuredData) return;
        if (!skipHarvest) harvestEdits(); // persist any inline edits before replacing innerHTML
        const tpl = templateSelect.value || 'ats_classic';
        resumeDocument.style.cssText = 'display:flex;flex-direction:column;align-items:center;width:100%;padding:0;background:transparent;';
        resumeDocument.innerHTML = ResumeTemplates[tpl](currentStructuredData, activeSections);
        autoFitPage();
    }

    // ── Auto-fit page ─────────────────────────────────────────────────────────
    // Two-phase layout engine (document-flow model — no flex-grow stretching):
    //   Phase 1 — measure: sections render at natural content height.
    //   Phase 2 — fit:
    //     • Overflow  → scale down via transform:scale (wrapper clips at 1123px).
    //     • Underflow → apply a small, controlled gap increase to [data-role]
    //                   sections (8px baseline → up to 14px). Content never
    //                   stretches; remaining white space sits at the bottom.
    function autoFitPage() {
        const wrapper = resumeDocument.querySelector('.resume-wrapper');
        if (!wrapper) return;
        const scaler = wrapper.querySelector('.resume-scale-target');
        if (!scaler) return;

        // ── Phase 1: reset, let sections sit at natural content height ─────────
        scaler.style.transform       = '';
        scaler.style.transformOrigin = '';
        scaler.style.height          = '';

        const pageH   = wrapper.offsetHeight;  // always 1123px (wrapper is hard-locked)
        if (!pageH) return;

        // Sidebar layout: its children use height:100% against the scaler.
        // Clearing height above collapses them — restore the lock and bail out.
        // The wrapper's overflow:hidden already clips any sidebar overflow.
        if (scaler.querySelector('.t4-sidebar')) {
            scaler.style.height = pageH + 'px';
            return;
        }

        const naturalH = scaler.offsetHeight;  // genuine stacked content height

        // ── Phase 2: fit strategy ──────────────────────────────────────────────
        if (naturalH > pageH + 6) {
            // Overflow: scale down visually so content fits inside the A4 frame.
            const z = Math.max(0.72, pageH / naturalH);
            scaler.style.transform       = `scale(${z.toFixed(4)})`;
            scaler.style.transformOrigin = 'top left';
        } else {
            // Underflow: distribute slack as a slight margin-bottom increase on
            // data-role sections (max +6px each, capped at 14px total).
            // White space beyond that naturally falls at the bottom — no stretching.
            const slack = pageH - naturalH;
            if (slack > 0 && slack <= 150) {
                const sections = scaler.querySelectorAll('[data-role]');
                if (sections.length) {
                    const extra = Math.min(Math.floor(slack / sections.length), 6);
                    sections.forEach(s => {
                        const mb = parseFloat(getComputedStyle(s).marginBottom) || 8;
                        s.style.marginBottom = Math.min(mb + extra, 14) + 'px';
                    });
                }
            }
        }
    }

    // ── Mode toggle (Upload ↔ Manual Entry) ──────────────────────────────────
    const modeUploadBtn = document.getElementById('mode-upload');
    const modeManualBtn = document.getElementById('mode-manual');
    const uploadMode    = document.getElementById('upload-mode');
    const manualMode    = document.getElementById('manual-mode');

    function setMode(mode) {
        const isManual = mode === 'manual';
        uploadMode.classList.toggle('hidden',  isManual);
        manualMode.classList.toggle('hidden',  !isManual);
        modeManualBtn.classList.toggle('mode-tab--active',  isManual);
        modeUploadBtn.classList.toggle('mode-tab--active', !isManual);
        errorMessage.classList.add('hidden');
    }

    modeUploadBtn.addEventListener('click', () => setMode('upload'));
    modeManualBtn.addEventListener('click', () => setMode('manual'));

    // ── File upload ──────────────────────────────────────────────────────────
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadText.classList.add('hidden');
            fileNameText.textContent = e.target.files[0].name;
            fileNameContainer.classList.remove('hidden');
        } else {
            uploadText.classList.remove('hidden');
            fileNameContainer.classList.add('hidden');
        }
    });

    // ── Add skill ────────────────────────────────────────────────────────────
    addSkillBtn.addEventListener('click', () => {
        const val = newSkillInput.value.trim();
        const cat = newSkillCategory.value;
        if (!val) return;
        const canon = canonicalizeSkill(val);
        if (currentSkills[cat].map(s => s.toLowerCase()).includes(canon.toLowerCase())) return;
        currentSkills[cat].push(canon);
        // Mirror into structured resume so rescore sees the new skill in the right section.
        if (currentStructuredData) {
            const key = cat === 'technical' ? 'technical_skills'
                      : cat === 'soft'      ? 'soft_skills'
                      :                       'languages';
            currentStructuredData[key] = currentStructuredData[key] || [];
            if (!currentStructuredData[key].map(s => s.toLowerCase()).includes(canon.toLowerCase())) {
                currentStructuredData[key].push(canon);
            }
            currentStructuredData.skill_groups = filterAndGroupSkills(currentStructuredData.technical_skills || []);
        }
        newSkillInput.value = '';
        renderUserSkills();
        scheduleRescore();
    });

    newSkillInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); addSkillBtn.click(); }
    });

    // ── 1. ANALYSIS FLOW ─────────────────────────────────────────────────────
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (controllers.analyze) {
            controllers.analyze.abort();
            controllers.analyze = null;
        }
        controllers.analyze = new AbortController();
        const signal = controllers.analyze.signal;
        const requestId = ++latestRequestIds.analyze;

        errorMessage.classList.add('hidden');
        resultsSection.classList.add('hidden');
        builderSection.classList.add('hidden');

        submitBtn.disabled = true;
        btnText.textContent = 'Processing...';
        spinner.classList.remove('hidden');

        const resumeFile = document.getElementById('resume-file').files[0];
        savedJdText = document.getElementById('jd-text').value;

        pdfViewer.src = URL.createObjectURL(resumeFile) + "#toolbar=0&navpanes=0&view=Fit";

        const formData = new FormData();
        formData.append('resume', resumeFile);
        formData.append('jd', savedJdText);

        try {
            const data = await runProcessingStage(
                fetchWithTimeout(apiUrl('/analyze'), { method: 'POST', body: formData, signal })
                    .then(async (response) => {
                        if (!response.ok) {
                            let msg = 'Analysis Failed';
                            try { msg = (await response.json()).error || msg; } catch (_) {}
                            throw new Error(msg);
                        }
                        return response.json();
                    })
            );
            if (requestId !== latestRequestIds.analyze) return;

            savedRawText  = data.raw_text;
            savedJdSkillsFlat = canonicalizeSkillList(data.jd_skills_flat || []);
            currentSkills = {
                technical: canonicalizeSkillList(data.resume_skills?.technical || []),
                soft:      canonicalizeSkillList(data.resume_skills?.soft      || []),
                languages: canonicalizeSkillList(data.resume_skills?.languages || []),
            };

            renderUserSkills();
            renderJdSkills(data.jd_skills || {});
            renderSuggestions(data.suggestions || []);

            resultsSection.classList.remove('hidden');
            setStage('analyzed');

        } catch (error) {
            if (error.name === 'AbortError') return;
            errorMessage.textContent = `Backend Error: ${error.message}`;
            errorMessage.classList.remove('hidden');
            setStage('idle');
        } finally {
            if (requestId === latestRequestIds.analyze) {
                submitBtn.disabled = false;
                btnText.textContent = 'Analyze Resume';
                spinner.classList.add('hidden');
            }
        }
    });

    // ── 2. OPTIMIZE FLOW ─────────────────────────────────────────────────────
    startRewriteBtn.addEventListener('click', async () => {
        if (controllers.optimize) {
            controllers.optimize.abort();
            controllers.optimize = null;
        }
        controllers.optimize = new AbortController();
        const signal = controllers.optimize.signal;
        const requestId = ++latestRequestIds.optimize;
        
        // Pre-flight checks — show clear messages instead of silent failures
        if (!savedRawText || !savedRawText.trim()) {
            errorMessage.textContent = 'No resume text found. Please run Analyze first.';
            errorMessage.classList.remove('hidden');
            return;
        }
        if (!savedJdText || !savedJdText.trim()) {
            errorMessage.textContent = 'Job description is empty. Please provide a JD before optimizing.';
            errorMessage.classList.remove('hidden');
            return;
        }

        errorMessage.classList.add('hidden');
        startRewriteBtn.textContent = 'Analyzing resume...';
        startRewriteBtn.disabled = true;
        const mainResults = document.getElementById('main-results-wrapper');
        if (mainResults) mainResults.classList.add('loading-state');

        try {
            const res = await fetchWithTimeout(apiUrl('/optimize'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    raw_text: savedRawText,
                    jd_text:  savedJdText,
                    skills:   currentSkills
                }),
                signal
            });

            const payload = await res.json();
            if (requestId !== latestRequestIds.optimize) return;

            if (!res.ok) {
                // Show the actual backend error message, not a generic one
                throw new Error(payload.error || `Server error ${res.status}`);
            }

            console.log('[optimize] original=', payload.original_score?.score,
                        'optimized=', payload.optimized_score?.score,
                        '(+', payload.improvement, ')',
                        'breakdown=', payload.optimized_score?.breakdown,
                        'missing=', (payload.missing_skills || []).slice(0, 5));
            if (payload.original_score) {
                originalScoreSnapshot = payload.original_score.score;
                setTimeout(() => updateScoreCard(payload), 120);
            }
            if (payload.jd_skills_flat) {
                savedJdSkillsFlat = canonicalizeSkillList(payload.jd_skills_flat);
            }
            renderMissingSkills(payload.missing_skills, payload.matched_skills);
            setCurrentData(payload.resume || payload);
            builderSection.classList.remove('hidden');
            renderResume();
            requestAnimationFrame(() => autoFitPage()); // re-measure now section is visible
            builderSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (error) {
            if (error.name === 'AbortError') return;
            // Surface the real error to the user — not just a generic alert
            errorMessage.textContent = `Optimize failed: ${error.message}`;
            errorMessage.classList.remove('hidden');
            console.error('[optimize]', error);
        } finally {
            if (requestId === latestRequestIds.optimize) {
                startRewriteBtn.textContent = 'Optimize Resume for Job Description';
                startRewriteBtn.disabled = false;
                const mainResults = document.getElementById('main-results-wrapper');
                if (mainResults) mainResults.classList.remove('loading-state');
            }
        }
    });

    // ── 3. TEMPLATE SWITCHING ────────────────────────────────────────────────
    templateSelect.addEventListener('change', () => renderResume());

    // ── 4. ADD EXPERIENCE BLOCK ──────────────────────────────────────────────
    const toggleExpBtn  = document.getElementById('toggle-exp-form');
    const toggleExpIcon = document.getElementById('toggle-exp-icon');
    const expForm       = document.getElementById('exp-form');
    const addExpBtn     = document.getElementById('add-exp-btn');

    toggleExpBtn.addEventListener('click', () => {
        const isHidden = expForm.classList.toggle('hidden');
        toggleExpIcon.textContent = isHidden ? '+' : '−';
    });

    addExpBtn.addEventListener('click', () => {
        const role     = document.getElementById('exp-role').value.trim();
        const company  = document.getElementById('exp-company').value.trim();
        const duration = document.getElementById('exp-duration').value.trim();
        const desc     = document.getElementById('exp-desc').value.trim();

        if (!role || !company) {
            errorMessage.textContent = 'Role and Company are required to add an experience entry.';
            errorMessage.classList.remove('hidden');
            return;
        }
        if (!currentStructuredData) {
            errorMessage.textContent = 'Run "Optimize Resume" first, then add experience entries.';
            errorMessage.classList.remove('hidden');
            return;
        }

        errorMessage.classList.add('hidden');

        const points = desc
            ? desc.split('\n').map(l => l.replace(/^[-•*]\s*/, '').trim()).filter(Boolean)
            : [];

        currentStructuredData.experience = currentStructuredData.experience || [];
        currentStructuredData.experience.push({ role, company, duration, points });
        renderResume(true);
        scheduleRescore(200);

        // Clear and collapse form
        document.getElementById('exp-role').value     = '';
        document.getElementById('exp-company').value  = '';
        document.getElementById('exp-duration').value = '';
        document.getElementById('exp-desc').value     = '';
        expForm.classList.add('hidden');
        toggleExpIcon.textContent = '+';
    });

    // ── 5. MANUAL ENTRY — GENERATE FROM INPUTS ───────────────────────────────
    const generateManualBtn = document.getElementById('generate-manual-btn');
    const genBtnText        = document.getElementById('gen-btn-text');
    const genSpinner        = document.getElementById('gen-spinner');

    generateManualBtn.addEventListener('click', async () => {
        if (controllers.manual) {
            controllers.manual.abort();
            controllers.manual = null;
        }
        controllers.manual = new AbortController();
        const signal = controllers.manual.signal;
        const requestId = ++latestRequestIds.manual;
        
        const name    = document.getElementById('m-name').value.trim();
        const title   = document.getElementById('m-title').value.trim();
        const jdText  = document.getElementById('m-jd-text').value.trim();

        if (!name || !title) {
            errorMessage.textContent = 'Full Name and Target Role are required.';
            errorMessage.classList.remove('hidden');
            return;
        }

        const technical = parseCommaList(document.getElementById('m-technical').value);
        const soft      = parseCommaList(document.getElementById('m-soft').value);
        const languages = parseCommaList(document.getElementById('m-languages').value);

        const inputs = {
            name, title,
            email:    document.getElementById('m-email').value.trim(),
            phone:    document.getElementById('m-phone').value.trim(),
            linkedin: document.getElementById('m-linkedin').value.trim(),
            github:   document.getElementById('m-github').value.trim(),
            education_text:      document.getElementById('m-education').value.trim(),
            experience_text:     document.getElementById('m-experience').value.trim(),
            projects_text:       document.getElementById('m-projects').value.trim(),
            certifications_text: document.getElementById('m-certifications').value.trim(),
            technical_skills: technical,
            soft_skills:      soft,
            languages:        languages,
        };

        // Build plain-text representation used by /optimize
        savedRawText = [
            `Name: ${inputs.name}`,
            `Target Role: ${inputs.title}`,
            inputs.education_text      ? `Education:\n${inputs.education_text}`           : '',
            inputs.experience_text     ? `Experience:\n${inputs.experience_text}`         : '',
            inputs.projects_text       ? `Projects:\n${inputs.projects_text}`             : '',
            inputs.certifications_text ? `Certifications:\n${inputs.certifications_text}` : '',
            technical.length ? `Technical Skills: ${technical.join(', ')}` : '',
            soft.length      ? `Soft Skills: ${soft.join(', ')}`           : '',
            languages.length ? `Languages: ${languages.join(', ')}`        : '',
        ].filter(Boolean).join('\n\n');

        currentSkills = { technical, soft, languages };
        savedJdText   = jdText;

        errorMessage.classList.add('hidden');
        manualAnalysisSection.classList.add('hidden');
        genBtnText.textContent = 'Generating...';
        genSpinner.classList.remove('hidden');
        generateManualBtn.disabled = true;

        const manualPipeline = (async () => {
            if (jdText) {
                const analysisRes = await fetchWithTimeout(apiUrl('/analyze-manual'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        jd_text:         jdText,
                        user_skills_flat: [...technical, ...soft, ...languages],
                    }),
                    signal
                });
                const analysisData = await analysisRes.json();
                if (!analysisRes.ok) throw new Error(analysisData.error || `Analysis error ${analysisRes.status}`);

                const optimizeRes = await fetchWithTimeout(apiUrl('/optimize'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        raw_text: savedRawText,
                        jd_text:  jdText,
                        skills:   currentSkills,
                    }),
                    signal
                });
                const optimizePayload = await optimizeRes.json();
                if (!optimizeRes.ok) throw new Error(optimizePayload.error || `Optimize error ${optimizeRes.status}`);
                return { mode: 'jd', analysisData, optimizePayload };
            }

            const res = await fetchWithTimeout(apiUrl('/generate-from-inputs'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ inputs }),
                signal
            });
            const payload = await res.json();
            if (!res.ok) throw new Error(payload.error || `Server error ${res.status}`);
            return { mode: 'plain', payload };
        })();

        try {
            const outcome = await runProcessingStage(manualPipeline);
            if (requestId !== latestRequestIds.manual) return;

            if (outcome.mode === 'jd') {
                const { analysisData, optimizePayload } = outcome;
                renderManualAnalysis(
                    currentSkills,
                    analysisData.jd_skills || {},
                    analysisData.matched_skills || [],
                    analysisData.missing_skills || []
                );
                savedJdSkillsFlat = canonicalizeSkillList(analysisData.jd_skills_flat || []);
                renderManualSuggestions(analysisData.suggestions || []);
                manualAnalysisSection.classList.remove('hidden');

                console.log('[optimize-manual] original=', optimizePayload.original_score?.score,
                            'optimized=', optimizePayload.optimized_score?.score,
                            '(+', optimizePayload.improvement, ')',
                            'breakdown=', optimizePayload.optimized_score?.breakdown);
                if (optimizePayload.original_score) {
                    originalScoreSnapshot = optimizePayload.original_score.score;
                    setTimeout(() => updateScoreCard(optimizePayload), 120);
                }
                if (optimizePayload.jd_skills_flat) {
                    savedJdSkillsFlat = canonicalizeSkillList(optimizePayload.jd_skills_flat);
                }
                renderMissingSkills(optimizePayload.missing_skills, optimizePayload.matched_skills);
                setCurrentData(optimizePayload.resume || optimizePayload);
            } else {
                const { payload } = outcome;
                setCurrentData(payload);
                currentSkills = {
                    technical: payload.technical_skills || [],
                    soft:      payload.soft_skills      || [],
                    languages: payload.languages        || [],
                };
            }

            builderSection.classList.remove('hidden');
            renderResume();
            requestAnimationFrame(() => autoFitPage());
            setStage('analyzed');

        } catch (error) {
            if (error.name === 'AbortError') return;
            errorMessage.textContent = `Generation failed: ${error.message}`;
            errorMessage.classList.remove('hidden');
            console.error('[generate-from-inputs]', error);
            setStage('idle');
        } finally {
            if (requestId === latestRequestIds.manual) {
                genBtnText.textContent = '✨ Generate Resume from Inputs';
                genSpinner.classList.add('hidden');
                generateManualBtn.disabled = false;
            }
        }
    });

    // ── 5b. BUILDER — OPTIMIZE FOR JOB DESCRIPTION ───────────────────────────
    const toggleBuilderJd  = document.getElementById('toggle-builder-jd');
    const builderJdIcon    = document.getElementById('builder-jd-icon');
    const builderJdForm    = document.getElementById('builder-jd-form');
    const builderOptBtn    = document.getElementById('builder-optimize-btn');
    const builderOptText   = document.getElementById('builder-opt-text');
    const builderOptSpin   = document.getElementById('builder-opt-spinner');

    toggleBuilderJd.addEventListener('click', () => {
        const hidden = builderJdForm.classList.toggle('hidden');
        builderJdIcon.textContent = hidden ? '+' : '−';
    });

    builderOptBtn.addEventListener('click', async () => {
        if (controllers.builder) {
            controllers.builder.abort();
            controllers.builder = null;
        }
        controllers.builder = new AbortController();
        const signal = controllers.builder.signal;
        const requestId = ++latestRequestIds.builder;
        
        const jd = document.getElementById('builder-jd-text').value.trim();
        if (!jd) {
            errorMessage.textContent = 'Paste a job description to optimize the resume.';
            errorMessage.classList.remove('hidden');
            return;
        }
        if (!currentStructuredData) {
            errorMessage.textContent = 'Generate or analyze a resume first.';
            errorMessage.classList.remove('hidden');
            return;
        }
        if (!savedRawText) {
            errorMessage.textContent = 'No resume source text available for optimization.';
            errorMessage.classList.remove('hidden');
            return;
        }

        savedJdText = jd;
        errorMessage.classList.add('hidden');
        builderOptText.textContent = 'Optimizing...';
        builderOptSpin.classList.remove('hidden');
        builderOptBtn.disabled = true;
        const mainResults = document.getElementById('main-results-wrapper');
        if (mainResults) mainResults.classList.add('loading-state');

        try {
            const res = await fetchWithTimeout(apiUrl('/optimize'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    raw_text: savedRawText,
                    jd_text:  savedJdText,
                    skills:   currentSkills,
                }),
                signal
            });
            const payload = await res.json();
            if (requestId !== latestRequestIds.builder) return;
            if (!res.ok) throw new Error(payload.error || `Server error ${res.status}`);

            console.log('[builder-optimize] original=', payload.original_score?.score,
                        'optimized=', payload.optimized_score?.score,
                        '(+', payload.improvement, ')',
                        'breakdown=', payload.optimized_score?.breakdown);
            if (payload.original_score) {
                originalScoreSnapshot = payload.original_score.score;
                setTimeout(() => updateScoreCard(payload), 120);
            }
            if (payload.jd_skills_flat) {
                savedJdSkillsFlat = canonicalizeSkillList(payload.jd_skills_flat);
            }
            renderMissingSkills(payload.missing_skills, payload.matched_skills);
            setCurrentData(payload.resume || payload);
            renderResume();

            // Collapse the JD panel after success
            builderJdForm.classList.add('hidden');
            builderJdIcon.textContent = '+';

        } catch (error) {
            if (error.name === 'AbortError') return;
            errorMessage.textContent = `Optimization failed: ${error.message}`;
            errorMessage.classList.remove('hidden');
            console.error('[builder-optimize]', error);
        } finally {
            if (requestId === latestRequestIds.builder) {
                builderOptText.textContent = 'Optimize Resume';
                builderOptSpin.classList.add('hidden');
                builderOptBtn.disabled = false;
                const mainResults = document.getElementById('main-results-wrapper');
                if (mainResults) mainResults.classList.remove('loading-state');
            }
        }
    });

    // ── 6. SHARED ENTRY FORM UTILITY ─────────────────────────────────────────
    function setupEntryForm({ toggleId, iconId, formId, addBtnId, requiredIds, fieldIds, buildEntry, dataKey, errorText }) {
        const toggle = document.getElementById(toggleId);
        const icon   = document.getElementById(iconId);
        const form   = document.getElementById(formId);
        const addBtn = document.getElementById(addBtnId);

        toggle.addEventListener('click', () => {
            const hidden = form.classList.toggle('hidden');
            icon.textContent = hidden ? '+' : '−';
        });

        addBtn.addEventListener('click', () => {
            if (!currentStructuredData) {
                errorMessage.textContent = 'Run "Optimize Resume" first, then add entries.';
                errorMessage.classList.remove('hidden');
                return;
            }
            const missing = requiredIds.find(id => !document.getElementById(id).value.trim());
            if (missing) {
                errorMessage.textContent = errorText || 'Please fill all required fields.';
                errorMessage.classList.remove('hidden');
                return;
            }
            errorMessage.classList.add('hidden');

            const vals = {};
            fieldIds.forEach(id => { vals[id] = document.getElementById(id).value.trim(); });

            currentStructuredData[dataKey] = currentStructuredData[dataKey] || [];
            currentStructuredData[dataKey].push(buildEntry(vals));
            renderResume(true);
            scheduleRescore(200);

            fieldIds.forEach(id => { document.getElementById(id).value = ''; });
            form.classList.add('hidden');
            icon.textContent = '+';
        });
    }

    // Projects
    setupEntryForm({
        toggleId: 'toggle-proj-form', iconId: 'toggle-proj-icon',
        formId: 'proj-form',          addBtnId: 'add-proj-btn',
        requiredIds: ['proj-title'],
        fieldIds:    ['proj-title', 'proj-stack', 'proj-desc'],
        dataKey:     'projects',
        errorText:   'Project title is required.',
        buildEntry: (v) => ({
            title:      v['proj-title'],
            tech_stack: v['proj-stack']
                ? v['proj-stack'].split(',').map(s => s.trim()).filter(Boolean)
                : [],
            points: v['proj-desc']
                ? v['proj-desc'].split('\n').map(l => l.replace(/^[-•*]\s*/, '').trim()).filter(Boolean)
                : [],
        }),
    });

    // Education
    setupEntryForm({
        toggleId: 'toggle-edu-form', iconId: 'toggle-edu-icon',
        formId: 'edu-form',          addBtnId: 'add-edu-btn',
        requiredIds: ['edu-degree', 'edu-institution'],
        fieldIds:    ['edu-degree', 'edu-institution', 'edu-year', 'edu-gpa'],
        dataKey:     'education',
        errorText:   'Degree and Institution are required.',
        buildEntry: (v) => ({
            degree:      v['edu-gpa'] ? `${v['edu-degree']} (${v['edu-gpa']})` : v['edu-degree'],
            institution: v['edu-institution'],
            year:        v['edu-year'] || '',
        }),
    });

    // Certifications  (data model is a flat string array)
    setupEntryForm({
        toggleId: 'toggle-cert-form', iconId: 'toggle-cert-icon',
        formId: 'cert-form',          addBtnId: 'add-cert-btn',
        requiredIds: ['cert-name'],
        fieldIds:    ['cert-name', 'cert-org', 'cert-date'],
        dataKey:     'certifications',
        errorText:   'Certification name is required.',
        buildEntry: (v) => {
            let s = v['cert-name'];
            if (v['cert-org'])  s += ` — ${v['cert-org']}`;
            if (v['cert-date']) s += ` (${v['cert-date']})`;
            return s;
        },
    });

    // ── 7a. LIVE INLINE EDIT SYNC ────────────────────────────────────────────
    // Update currentStructuredData on every keystroke so template switches
    // don't lose in-progress edits.
    resumeDocument.addEventListener('input', (e) => {
        if (!currentStructuredData) return;
        const el = e.target.closest('[data-bind]');
        if (!el) return;
        const path  = el.dataset.bind;
        const type  = el.dataset.bindType;
        const sep   = el.dataset.bindSep || '\n';
        const value = type === 'array'
            ? el.innerText.split(sep).map(s => s.trim()).filter(Boolean)
            : el.innerText.trim();
        setPath(currentStructuredData, path, value);
        scheduleRescore();   // live recompute as the user types
    });

    // ── 7. BLOCK CONTROLS (per-entry delete + contact remove) ────────────────
    resumeDocument.addEventListener('click', (e) => {
        const btn = e.target.closest('.block-ctrl');
        if (!btn || !currentStructuredData) return;
        e.stopPropagation();

        const action = btn.dataset.action;
        const idx    = parseInt(btn.dataset.index, 10);
        const field  = btn.dataset.field;

        if (action === 'remove-exp')     currentStructuredData.experience.splice(idx, 1);
        else if (action === 'remove-proj')  currentStructuredData.projects.splice(idx, 1);
        else if (action === 'remove-cert')  currentStructuredData.certifications.splice(idx, 1);
        else if (action === 'remove-edu')   currentStructuredData.education.splice(idx, 1);
        else if (action === 'remove-contact') {
            currentStructuredData._contact = currentStructuredData._contact || {};
            currentStructuredData._contact[field] = false;
        }

        renderResume(true);
        scheduleRescore(200);
    });

    // ── 6. SECTION TOGGLE PILLS ──────────────────────────────────────────────
    document.querySelectorAll('.sec-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            const sec = btn.dataset.section;
            activeSections[sec] = !activeSections[sec];
            btn.classList.toggle('sec-pill--off', !activeSections[sec]);
            renderResume();
        });
    });

    // ── 8. PDF GENERATION ────────────────────────────────────────────────────
    downloadPdfBtn.addEventListener('click', async () => {
        if (controllers.pdf) {
            controllers.pdf.abort();
            controllers.pdf = null;
        }
        controllers.pdf = new AbortController();
        const signal = controllers.pdf.signal;
        const requestId = ++latestRequestIds.pdf;
        
        downloadPdfBtn.textContent = 'Generating PDF...';

        const resumeWrapper = resumeDocument.querySelector('.resume-wrapper');
        const clone = resumeWrapper.cloneNode(true);

        // ── Strip interactive elements ────────────────────────────────────────
        clone.querySelectorAll('[contenteditable]').forEach(el => el.removeAttribute('contenteditable'));
        clone.querySelectorAll('.block-ctrl').forEach(el => el.remove());

        // ── Remove transform scaling — Playwright renders at native 794×1123px ─
        const scaler = clone.querySelector('.resume-scale-target');
        if (scaler) {
            scaler.style.transform       = '';
            scaler.style.transformOrigin = '';
        }

        // ── Lock A4 dimensions on the wrapper ────────────────────────────────
        clone.style.margin    = '0';
        clone.style.boxShadow = 'none';
        clone.style.width     = '794px';
        clone.style.height    = '1123px';

        // ── Template 4: force critical layout styles inline on the clone ─────
        // CSS classes will be injected below, but inlining these as well makes
        // the sidebar layout robust against any Playwright class-loading quirks.
        const t4Layout  = clone.querySelector('.t4-layout');
        const t4Sidebar = clone.querySelector('.t4-sidebar');
        const t4Main    = clone.querySelector('.t4-main');
        if (t4Layout) {
            t4Layout.style.display        = 'flex';
            t4Layout.style.flexDirection  = 'row';
            t4Layout.style.height         = '1123px';
            t4Layout.style.width          = '794px';
            t4Layout.style.boxSizing      = 'border-box';
        }
        if (t4Sidebar) {
            t4Sidebar.style.width         = '28%';
            t4Sidebar.style.height        = '100%';
            t4Sidebar.style.background    = '#1e293b';
            t4Sidebar.style.color         = '#f8fafc';
            t4Sidebar.style.padding       = '24px 16px';
            t4Sidebar.style.boxSizing     = 'border-box';
            t4Sidebar.style.overflow      = 'hidden';
            t4Sidebar.style.fontFamily    = 'Arial, sans-serif';
            t4Sidebar.style.flexShrink    = '0';
        }
        if (t4Main) {
            t4Main.style.flex             = '1';
            t4Main.style.height           = '100%';
            t4Main.style.padding          = '20px 22px';
            t4Main.style.boxSizing        = 'border-box';
            t4Main.style.overflow         = 'hidden';
            t4Main.style.background       = 'white';
            t4Main.style.fontFamily       = 'Arial, sans-serif';
            t4Main.style.fontSize         = '10pt';
            t4Main.style.color            = '#1e293b';
        }

        // ── Extract all resume CSS rules from the live page ───────────────────
        // This gives Playwright the same class definitions the browser used,
        // covering .resume-scale-target, .t4-*, .r-* and all spacing rules.
        const resumeCss = [...document.styleSheets]
            .flatMap(sheet => {
                try { return [...sheet.cssRules].map(r => r.cssText); }
                catch(e) { return []; }
            })
            .filter(rule => /\.(resume-|t4-|r-section|r-entry|r-sidebar|r-main)/.test(rule))
            .join('\n');

        const finalHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8">
            <style>
                * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; box-sizing: border-box; }
                html, body { margin: 0; padding: 0; background: white; width: 794px; }
                ${resumeCss}
            </style>
            </head><body>${clone.outerHTML}</body></html>`;

        try {
            const res = await fetch(apiUrl('/generate-pdf'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ html: finalHtml }),
                signal
            });
            const blob = await res.blob();
            const url  = window.URL.createObjectURL(blob);
            const a    = document.createElement('a');
            a.href = url; a.download = 'Optimized_ATS_Resume.pdf';
            document.body.appendChild(a); a.click(); a.remove();
        } catch (error) {
            if (error.name === 'AbortError') return;
            alert("Failed to generate PDF.");
        } finally {
            if (requestId === latestRequestIds.pdf) {
                downloadPdfBtn.textContent = '📥 Download ATS PDF';
            }
        }
    });
});

// UX Enhancements
function animateNumber(el, start, end, baseDuration = 800) {
    if (el._animId) cancelAnimationFrame(el._animId);
    const safeEnd = Math.max(0, Math.min(100, Number(end) || 0));
    
    // Respect reduced motion OR no change
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || start === safeEnd) {
        el.textContent = safeEnd;
        return;
    }
    
    const diff = Math.abs(safeEnd - start);
    const duration = Math.min(Math.max(diff * 15, 400), 1200);
    
    let startTime = null;

    function step(timestamp) {
        if (!startTime) startTime = timestamp;
        const progress = Math.min((timestamp - startTime) / duration, 1);
        
        // easeOutExpo for natural deceleration
        const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
        
        el.textContent = Math.floor(ease * (safeEnd - start) + start);
        if (progress < 1) {
            el._animId = requestAnimationFrame(step);
        }
    }

    el._animId = requestAnimationFrame(step);
}

// ── Scorecard: metric icons (inline SVG, PDF-safe) ──────────────────────
const SCORE_METRIC_ICONS = {
    skills:         `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.9 6.5 7.1.7-5.4 4.8 1.6 7-6.2-3.7-6.2 3.7 1.6-7L2 9.2l7.1-.7z"/></svg>`,
    experience:     `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2"/></svg>`,
    projects:       `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/></svg>`,
    education:      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 9l10-5 10 5-10 5L2 9z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/></svg>`,
    certifications: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="9" r="6"/><path d="M9 14l-1 7 4-3 4 3-1-7"/></svg>`,
    structure:      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/></svg>`,
};

// ── Scorecard: metric definitions (mirrors backend CATEGORY_WEIGHTS) ──
const SCORE_METRICS = [
    { key: 'skills',         label: 'Skills Match',          max: 35 },
    { key: 'experience',     label: 'Experience Relevance',  max: 25 },
    { key: 'projects',       label: 'Projects',              max: 15 },
    { key: 'education',      label: 'Education',             max: 10 },
    { key: 'certifications', label: 'Certifications',        max: 10 },
    { key: 'structure',      label: 'ATS Readability',       max: 5  },
];

function setScoreDonut(progressEl, score) {
    if (!progressEl) return;
    const circumference = 2 * Math.PI * 50;
    progressEl.setAttribute('stroke-dasharray', circumference.toFixed(3));
    const offset = circumference * (1 - Math.max(0, Math.min(100, score)) / 100);
    progressEl.setAttribute('stroke-dashoffset', offset.toFixed(3));
}

function renderBreakdown(container, breakdown) {
    if (!container || !breakdown) return;
    container.innerHTML = '';
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    SCORE_METRICS.forEach((metric, index) => {
        const raw = Number(breakdown[metric.key]) || 0;
        const val = Math.max(0, Math.min(metric.max, raw));
        const pct = Math.round((val / metric.max) * 100) || 0;

        const row = document.createElement('div');
        row.className = 'scorecard__metric';
        row.innerHTML = `
            <span class="scorecard__metric-icon">${SCORE_METRIC_ICONS[metric.key] || ''}</span>
            <div class="scorecard__metric-body">
                <div class="scorecard__metric-row">
                    <span class="scorecard__metric-label">${metric.label}</span>
                    <span class="scorecard__metric-value">${val}/${metric.max} pts</span>
                </div>
                <div class="scorecard__metric-bar">
                    <div class="scorecard__metric-bar-fill"></div>
                </div>
            </div>
        `;
        container.appendChild(row);

        const fill = row.querySelector('.scorecard__metric-bar-fill');
        if (!fill) return;
        if (reducedMotion) {
            fill.style.width = pct + '%';
        } else {
            setTimeout(() => { fill.style.width = pct + '%'; }, 150 + index * 80);
        }
    });
}

const INSIGHT_ICON = `<svg class="scorecard__insight-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>`;

function renderInsights(container, insights) {
    if (!container) return;
    container.innerHTML = '';
    (insights || []).forEach(insight => {
        const text = String(insight || '').trim();
        if (!text) return;

        let title = '';
        let body = text;
        const sepIdx = text.indexOf(':');
        if (sepIdx > 0 && sepIdx < 60) {
            title = text.slice(0, sepIdx).trim();
            body = text.slice(sepIdx + 1).trim();
        }

        const li = document.createElement('li');
        li.className = 'scorecard__insight';
        li.innerHTML = `
            ${INSIGHT_ICON}
            <div class="scorecard__insight-body">
                ${title ? `<p class="scorecard__insight-title">${title}</p>` : ''}
                <p class="scorecard__insight-text">${body}</p>
            </div>
        `;
        container.appendChild(li);
    });
}

// Helper for UI Redesign Scorecard
function updateScoreCard(payload) {
    const scoreCard = document.getElementById('scoreCard');
    const emptyState = document.getElementById('empty-state');

    if (emptyState) emptyState.style.display = 'none';
    if (!scoreCard) return;

    const isHidden = scoreCard.classList.contains('hidden');
    scoreCard.classList.remove('hidden');

    if (isHidden) {
        scoreCard.classList.remove('fade-in');
        void scoreCard.offsetWidth;
        scoreCard.classList.add('fade-in');
    }

    const orig = payload.original_score || {};
    const opt = payload.optimized_score || {};

    const safeOrigScore = Math.max(0, Math.min(100, Number(orig.score) || 0));
    const safeOptScore = Math.max(0, Math.min(100, Number(opt.score) || 0));
    const safeConfidence = Math.max(0, Math.min(100, Number(payload.confidence) || 0));

    const animateInto = (id, target) => {
        const el = document.getElementById(id);
        if (!el) return;
        const current = parseInt(el.textContent) || 0;
        animateNumber(el, current, target);
    };

    animateInto('originalScoreValue', safeOrigScore);
    animateInto('scoreValue', safeOptScore);
    animateInto('optimizedScoreValue', safeOptScore);
    animateInto('confidenceValue', safeConfidence);

    const scoreLabel = document.getElementById('scoreLabel');
    if (scoreLabel) scoreLabel.textContent = payload.optimized_label || "Analyzed";

    setScoreDonut(document.getElementById('scoreDonutProgress'), safeOptScore);

    const impEl = document.getElementById('scoreImprovement');
    if (impEl && payload.improvement > 0) {
        impEl.classList.remove('hidden');
        const impVal = document.getElementById('improvementValue');
        if (impVal) impVal.textContent = payload.improvement;
    } else if (impEl) {
        impEl.classList.add('hidden');
    }

    renderInsights(document.getElementById('insightList'), payload.insights);
    renderBreakdown(document.getElementById('breakdownBars'), opt.breakdown);

    if (scoreCard._pulseTimeout) clearTimeout(scoreCard._pulseTimeout);
    scoreCard.classList.remove('completion-pulse');
    void scoreCard.offsetWidth;
    scoreCard.classList.add('completion-pulse');
    scoreCard._pulseTimeout = setTimeout(() => {
        scoreCard.classList.remove('completion-pulse');
    }, 1200);

    const ariaStatus = document.getElementById('ariaStatus');
    if (ariaStatus) {
        ariaStatus.textContent = `ATS score updated to ${safeOptScore}`;
    }
}

