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
    let currentSkills = { technical: [], soft: [], languages: [] };
    let currentStructuredData = null;
    let activeSections = {
        experience: true, projects: true, certifications: true, education: true,
        technical: true,  soft: true,     languages: true,
    };

    // ── Single setter: always computes skill_groups so templates always show grouped skills ──
    function setCurrentData(data) {
        currentStructuredData = data;
        // Always compute groups client-side; backend value takes precedence if present
        if (!currentStructuredData.skill_groups || !Object.keys(currentStructuredData.skill_groups).length) {
            currentStructuredData.skill_groups = filterAndGroupSkills(currentStructuredData.technical_skills || []);
        }
        console.log('[setCurrentData] skill_groups:', JSON.stringify(currentStructuredData.skill_groups));
    }

    // ── Badge style configs ──────────────────────────────────────────────────
    const userBadgeStyle = {
        technical: { bg: 'rgba(99,102,241,0.12)', color: '#a5b4fc', border: 'rgba(99,102,241,0.25)' },
        soft:      { bg: 'rgba(139,92,246,0.12)',  color: '#c4b5fd', border: 'rgba(139,92,246,0.25)' },
        languages: { bg: 'rgba(14,165,233,0.12)',  color: '#7dd3fc', border: 'rgba(14,165,233,0.25)' },
    };
    const jdBadgeStyle = {
        technical: { bg: 'rgba(245,158,11,0.10)',  color: '#fbbf24', border: 'rgba(245,158,11,0.20)' },
        soft:      { bg: 'rgba(249,115,22,0.10)',   color: '#fb923c', border: 'rgba(249,115,22,0.20)' },
        languages: { bg: 'rgba(20,184,166,0.10)',   color: '#2dd4bf', border: 'rgba(20,184,166,0.20)' },
    };

    // ── Render helpers ───────────────────────────────────────────────────────
    function makeBadge(text, style, onRemove) {
        const badge = document.createElement('div');
        badge.style.cssText = `display:inline-flex;align-items:center;gap:5px;padding:3px 9px;
            border-radius:5px;font-size:11px;font-weight:600;
            background:${style.bg};color:${style.color};border:1px solid ${style.border};`;

        const label = document.createElement('span');
        label.textContent = text;
        badge.appendChild(label);

        if (onRemove) {
            const x = document.createElement('button');
            x.textContent = '×';
            x.style.cssText = 'background:none;border:none;cursor:pointer;padding:0;font-size:13px;line-height:1;color:#94a3b8;';
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
                container.appendChild(makeBadge(skill, userBadgeStyle[cat], () => {
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
                container.appendChild(makeBadge(skill, jdBadgeStyle[cat], null));
            });
        });
    }

    function renderSuggestions(suggestions) {
        suggestionsList.innerHTML = '';
        suggestions.forEach(tip => {
            const li = document.createElement('li');
            li.style.cssText = 'display:flex;align-items:flex-start;gap:8px;font-size:12px;color:#cbd5e1;line-height:1.4;';
            li.innerHTML = `<span style="color:#f59e0b;flex-shrink:0;margin-top:1px;">›</span><span>${tip}</span>`;
            suggestionsList.appendChild(li);
        });
    }

    // ── Manual analysis render helpers ──────────────────────────────────────
    function renderManualAnalysis(userSkills, jdSkills) {
        ['technical', 'soft', 'languages'].forEach(cat => {
            manualSkillContainers[cat].innerHTML = '';
            (userSkills[cat] || []).forEach(skill => {
                manualSkillContainers[cat].appendChild(makeBadge(skill, userBadgeStyle[cat], null));
            });
            manualJdContainers[cat].innerHTML = '';
            (jdSkills[cat] || []).forEach(skill => {
                manualJdContainers[cat].appendChild(makeBadge(skill, jdBadgeStyle[cat], null));
            });
        });

        const userFlat = new Set(
            [...(userSkills.technical||[]), ...(userSkills.soft||[]), ...(userSkills.languages||[])]
            .map(s => s.toLowerCase())
        );
        const jdFlat = [
            ...(jdSkills.technical||[]), ...(jdSkills.soft||[]), ...(jdSkills.languages||[])
        ];

        const matchedStyle = { bg:'rgba(16,185,129,0.12)',  color:'#6ee7b7', border:'rgba(16,185,129,0.25)' };
        const missingStyle = { bg:'rgba(239,68,68,0.10)',   color:'#fca5a5', border:'rgba(239,68,68,0.20)' };

        manualSkillsMatched.innerHTML = '';
        manualSkillsMissing.innerHTML = '';
        jdFlat.forEach(skill => {
            const target = userFlat.has(skill.toLowerCase()) ? manualSkillsMatched : manualSkillsMissing;
            const style  = userFlat.has(skill.toLowerCase()) ? matchedStyle : missingStyle;
            target.appendChild(makeBadge(skill, style, null));
        });
    }

    function renderManualSuggestions(suggestions) {
        manualSuggestionsList.innerHTML = '';
        suggestions.forEach(tip => {
            const li = document.createElement('li');
            li.style.cssText = 'display:flex;align-items:flex-start;gap:8px;font-size:12px;color:#cbd5e1;line-height:1.4;';
            li.innerHTML = `<span style="color:#f59e0b;flex-shrink:0;margin-top:1px;">›</span><span>${tip}</span>`;
            manualSuggestionsList.appendChild(li);
        });
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
        resumeDocument.style.cssText = 'display:flex;flex-direction:column;align-items:center;width:100%;padding:40px 0;background:#0f172a;';
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
        if (val && !currentSkills[cat].map(s => s.toLowerCase()).includes(val.toLowerCase())) {
            currentSkills[cat].push(val);
            newSkillInput.value = '';
            renderUserSkills();
        }
    });

    newSkillInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); addSkillBtn.click(); }
    });

    // ── 1. ANALYSIS FLOW ─────────────────────────────────────────────────────
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMessage.classList.add('hidden');
        resultsSection.classList.add('hidden');
        builderSection.classList.add('hidden');

        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-75', 'cursor-not-allowed');
        btnText.textContent = 'Processing...';
        spinner.classList.remove('hidden');

        const resumeFile = document.getElementById('resume-file').files[0];
        savedJdText = document.getElementById('jd-text').value;

        pdfViewer.src = URL.createObjectURL(resumeFile) + "#toolbar=0&navpanes=0&view=Fit";

        const formData = new FormData();
        formData.append('resume', resumeFile);
        formData.append('jd', savedJdText);

        try {
            const response = await fetch('https://resume-analyzer-23x0.onrender.com/analyze', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) throw new Error("Analysis Failed");

            const data = await response.json();

            savedRawText  = data.raw_text;
            currentSkills = {
                technical: data.resume_skills?.technical || [],
                soft:      data.resume_skills?.soft      || [],
                languages: data.resume_skills?.languages || [],
            };

            renderUserSkills();
            renderJdSkills(data.jd_skills || {});
            renderSuggestions(data.suggestions || []);

            resultsSection.classList.remove('hidden');
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (error) {
            errorMessage.textContent = `Backend Error: ${error.message}`;
            errorMessage.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-75', 'cursor-not-allowed');
            btnText.textContent = 'Analyze Resume';
            spinner.classList.add('hidden');
        }
    });

    // ── 2. OPTIMIZE FLOW ─────────────────────────────────────────────────────
    startRewriteBtn.addEventListener('click', async () => {
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
        startRewriteBtn.textContent = 'Optimizing...';
        startRewriteBtn.disabled = true;

        try {
            const res = await fetch('https://resume-analyzer-23x0.onrender.com/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    raw_text: savedRawText,
                    jd_text:  savedJdText,
                    skills:   currentSkills
                })
            });

            const payload = await res.json();

            if (!res.ok) {
                // Show the actual backend error message, not a generic one
                throw new Error(payload.error || `Server error ${res.status}`);
            }

            setCurrentData(payload);
            builderSection.classList.remove('hidden');
            renderResume();
            requestAnimationFrame(() => autoFitPage()); // re-measure now section is visible
            builderSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (error) {
            // Surface the real error to the user — not just a generic alert
            errorMessage.textContent = `Optimize failed: ${error.message}`;
            errorMessage.classList.remove('hidden');
            console.error('[optimize]', error);
        } finally {
            startRewriteBtn.textContent = 'Optimize Resume for Job Description';
            startRewriteBtn.disabled = false;
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

        try {
            if (jdText) {
                // ── JD path: analyze → show skill panel → optimize ────────────
                genBtnText.textContent = 'Analyzing skills...';
                const analysisRes = await fetch('https://resume-analyzer-23x0.onrender.com/analyze-manual', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        jd_text:         jdText,
                        user_skills_flat: [...technical, ...soft, ...languages],
                    }),
                });
                const analysisData = await analysisRes.json();
                if (!analysisRes.ok) throw new Error(analysisData.error || `Analysis error ${analysisRes.status}`);

                renderManualAnalysis(currentSkills, analysisData.jd_skills || {});
                renderManualSuggestions(analysisData.suggestions || []);
                manualAnalysisSection.classList.remove('hidden');
                manualAnalysisSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

                // Optimize resume for JD (same pipeline as upload mode)
                genBtnText.textContent = 'Optimizing for JD...';
                const optimizeRes = await fetch('https://resume-analyzer-23x0.onrender.com/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        raw_text: savedRawText,
                        jd_text:  jdText,
                        skills:   currentSkills,
                    }),
                });
                const optimizePayload = await optimizeRes.json();
                if (!optimizeRes.ok) throw new Error(optimizePayload.error || `Optimize error ${optimizeRes.status}`);

                setCurrentData(optimizePayload);

            } else {
                // ── No JD: generate plain resume from inputs ──────────────────
                const res = await fetch('https://resume-analyzer-23x0.onrender.com/generate-from-inputs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ inputs }),
                });
                const payload = await res.json();
                if (!res.ok) throw new Error(payload.error || `Server error ${res.status}`);

                setCurrentData(payload);
                currentSkills = {
                    technical: payload.technical_skills || [],
                    soft:      payload.soft_skills      || [],
                    languages: payload.languages        || [],
                };
            }

            builderSection.classList.remove('hidden');
            renderResume();
            requestAnimationFrame(() => autoFitPage()); // section now visible → zoom can measure
            builderSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (error) {
            errorMessage.textContent = `Generation failed: ${error.message}`;
            errorMessage.classList.remove('hidden');
            console.error('[generate-from-inputs]', error);
        } finally {
            genBtnText.textContent = '✨ Generate Resume from Inputs';
            genSpinner.classList.add('hidden');
            generateManualBtn.disabled = false;
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

        try {
            const res = await fetch('https://resume-analyzer-23x0.onrender.com/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    raw_text: savedRawText,
                    jd_text:  savedJdText,
                    skills:   currentSkills,
                }),
            });
            const payload = await res.json();
            if (!res.ok) throw new Error(payload.error || `Server error ${res.status}`);

            setCurrentData(payload);
            renderResume();

            // Collapse the JD panel after success
            builderJdForm.classList.add('hidden');
            builderJdIcon.textContent = '+';

        } catch (error) {
            errorMessage.textContent = `Optimization failed: ${error.message}`;
            errorMessage.classList.remove('hidden');
            console.error('[builder-optimize]', error);
        } finally {
            builderOptText.textContent = 'Optimize Resume';
            builderOptSpin.classList.add('hidden');
            builderOptBtn.disabled = false;
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
            const res = await fetch('https://resume-analyzer-23x0.onrender.com/generate-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ html: finalHtml })
            });
            const blob = await res.blob();
            const url  = window.URL.createObjectURL(blob);
            const a    = document.createElement('a');
            a.href = url; a.download = 'Optimized_ATS_Resume.pdf';
            document.body.appendChild(a); a.click(); a.remove();
        } catch {
            alert("Failed to generate PDF.");
        } finally {
            downloadPdfBtn.textContent = '📥 Download ATS PDF';
        }
    });
});
