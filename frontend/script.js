// ── Display fallback (slim) ─────────────────────────────────────────────
// Backend is the source of truth for canonical names. This formatter only
// runs against (a) raw user input from "add skill", and (b) any string the
// backend hasn't already canonicalized. It mirrors the rules in
// backend/intelligence/normalizer.py + display.py at a high level only —
// no giant alias maps.
const BRAND_EXCEPTIONS = {
    javascript:'JavaScript', typescript:'TypeScript',
    node:'Node.js', express:'Express.js', next:'Next.js', nuxt:'Nuxt.js',
    vue:'Vue.js', nest:'Nest.js', fastapi:'FastAPI',
    github:'GitHub', gitlab:'GitLab', bitbucket:'Bitbucket',
    mongodb:'MongoDB', postgresql:'PostgreSQL', mysql:'MySQL', sqlite:'SQLite',
    mariadb:'MariaDB', dynamodb:'DynamoDB', graphql:'GraphQL',
    'scikit-learn':'scikit-learn', pytorch:'PyTorch', tensorflow:'TensorFlow',
    numpy:'NumPy', scipy:'SciPy', jquery:'jQuery',
    macos:'macOS', ios:'iOS', openai:'OpenAI', huggingface:'Hugging Face',
};
const UPPERCASE_TOKENS = new Set([
    'aws','gcp','sql','html','css','nlp','etl','api','apis','ai','ml','ui','ux',
    'cdn','cors','jwt','rpc','tcp','udp','ssh','ssl','tls','json','xml','yaml',
    'csv','pdf','url','uri','http','https','rest','graphql','orm','ide','sdk',
    'cli','gui','saas','paas','iaas','k8s','ci','cd','qa','dns','vpc','ec2',
    's3','rds','iam','gpu','cpu','ram','os','io','db',
]);

function _normalizeKey(skill) {
    if (!skill || typeof skill !== 'string') return '';
    let s = skill.trim().toLowerCase();
    if (!s) return '';
    s = s.replace(/^[\s\-_/,.;:|()\[\]{}]+|[\s\-_/,.;:|()\[\]{}]+$/g, '');
    s = s.replace(/(?<=[a-z0-9])-(?=[a-z0-9])/g, ' ');
    s = s.replace(/[\s/_]+/g, ' ').trim();
    s = s.replace(/\.{2,}/g, '.');
    const jsStripped = s.replace(/(?:\s*\.|\s+|(?<=[a-z]))js$/i, '');
    if (jsStripped.length >= 2) s = jsStripped;
    s = s.replace(/\bapis\b/g, 'api');
    const verStripped = s.replace(/(?<=[a-z+#])\s*\d{1,4}(?:\.\d+)*$/i, '');
    if (verStripped.length >= 2) s = verStripped;
    return s.trim();
}

function _formatToken(token) {
    if (!token) return token;
    const lower = token.toLowerCase();
    if (UPPERCASE_TOKENS.has(lower)) return lower.toUpperCase();
    if (token.includes('.')) {
        const [head, ...rest] = token.split('.');
        return _formatToken(head) + '.' + rest.join('.').toLowerCase();
    }
    const trailing = (token.match(/[.+#]+$/) || [''])[0];
    if (trailing) {
        const head = token.slice(0, -trailing.length);
        return head ? _formatToken(head) + trailing : token;
    }
    return token.charAt(0).toUpperCase() + token.slice(1).toLowerCase();
}

function canonicalizeSkill(skill) {
    const key = _normalizeKey(skill);
    if (!key) return '';
    if (BRAND_EXCEPTIONS[key]) return BRAND_EXCEPTIONS[key];
    return key.split(' ').filter(Boolean).map(_formatToken).join(' ');
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

// ── Slim local skill grouper ────────────────────────────────────────────
// Backend's filter_and_group_skills is the source of truth (uses the full
// heuristic categorizer + registry). This function only runs as a fallback
// when the backend response is missing skill_groups, so it uses a small
// pattern-based bucket assignment rather than maintaining giant lists.
const _BUCKET_RULES = [
    { bucket: 'programming', test: k => /^(python|javascript|typescript|java|c\+\+|c#|c|go|rust|ruby|php|swift|kotlin|scala|perl|r|matlab|bash|shell|html|css|sql|dart)$/.test(k) },
    { bucket: 'databases',   test: k => /sql|^postgres|^mongo|(?<=[a-z])db$|\borm\b|redis|cassandra|elasticsearch|firebase|supabase|neo4j/.test(k) },
    { bucket: 'frameworks',  test: k => /^(react|vue|angular|svelte|astro|remix|next|nuxt|nest|fastify|node|express|django|flask|spring|rails|laravel|fastapi|bootstrap|tailwind)$/.test(k) || /\.js$/.test(k) },
];

function filterAndGroupSkills(technicalList) {
    const seen = new Set();
    const groups = { programming: [], frameworks: [], databases: [], tools: [] };

    for (const raw of (technicalList || [])) {
        if (!raw || !raw.trim()) continue;
        const display = canonicalizeSkill(raw);
        if (!display) continue;
        const lower = display.toLowerCase();
        if (seen.has(lower)) continue;
        seen.add(lower);

        const key = _normalizeKey(raw);
        const rule = _BUCKET_RULES.find(r => r.test(key));
        const bucket = rule ? rule.bucket : 'tools';
        if (groups[bucket].length < 4) groups[bucket].push(display);
    }
    return Object.fromEntries(Object.entries(groups).filter(([, v]) => v.length));
}

document.addEventListener('DOMContentLoaded', () => {
    const controllers = { analyze: null, optimize: null, manual: null, builder: null, pdf: null };
    const latestRequestIds = { analyze: 0, optimize: 0, manual: 0, builder: 0, pdf: 0 };
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    // Local development hits Flask on :5000; production hits the deployed
    // service. Detection: any hostname that looks local routes to localhost.
    const _isLocalHost = /^(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])$/i.test(window.location.hostname);
    const API_BASE_URL = _isLocalHost
        ? `http://${window.location.hostname || 'localhost'}:5000`
        : 'https://resume-analyzer-c5s7.onrender.com';
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
        // Manual mode panel. Backend already returns canonical display forms
        // (registry-resolved), so we render the strings as-is — re-formatting
        // them here would downgrade "REST APIs" -> "REST API", "GitHub Actions"
        // -> "Github Actions", etc.
        if (manualSkillsMissing && manualSkillsMatched) {
            const matchedStyle = { bg:'rgba(16,185,129,0.12)', color:'#6ee7b7', border:'rgba(16,185,129,0.25)' };
            const missingStyle = { bg:'rgba(239,68,68,0.10)',  color:'#fca5a5', border:'rgba(239,68,68,0.20)' };
            manualSkillsMatched.innerHTML = '';
            manualSkillsMissing.innerHTML = '';
            (matched || []).forEach(s => manualSkillsMatched.appendChild(makeBadge(s, matchedStyle, null)));
            (missing || []).forEach(s => manualSkillsMissing.appendChild(makeBadge(s, missingStyle, null)));
        }
    }

    // ── Single setter: always computes skill_groups so templates always show grouped skills ──
    function setCurrentData(data) {
        currentStructuredData = data;
        // Backend response is the canonical source for display forms; do not
        // re-canonicalize here (the slim frontend formatter doesn't know
        // about registry-seeded multi-token brands).
        currentStructuredData.technical_skills = currentStructuredData.technical_skills || [];
        currentStructuredData.soft_skills      = currentStructuredData.soft_skills      || [];
        currentStructuredData.languages        = currentStructuredData.languages        || [];
        // Always compute groups client-side as a fallback; backend value takes precedence if present.
        if (!currentStructuredData.skill_groups || !Object.keys(currentStructuredData.skill_groups).length) {
            currentStructuredData.skill_groups = filterAndGroupSkills(currentStructuredData.technical_skills);
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
        // currentSkills holds canonical display forms from the backend (or
        // the "add skill" path, which canonicalizes on entry). Render as-is.
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
        // Backend already canonicalized these via the intelligence pipeline.
        ['technical', 'soft', 'languages'].forEach(cat => {
            const container = jdContainers[cat];
            container.innerHTML = '';
            (jdSkills[cat] || []).forEach(skill => {
                container.appendChild(makeBadge(skill, jdBadgeStyle[cat], null));
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
        // All inputs here are backend-supplied display forms; render as-is.
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

        const matchedStyle = { bg:'rgba(16,185,129,0.12)',  color:'#6ee7b7', border:'rgba(16,185,129,0.25)' };
        const missingStyle = { bg:'rgba(239,68,68,0.10)',   color:'#fca5a5', border:'rgba(239,68,68,0.20)' };

        manualSkillsMatched.innerHTML = '';
        manualSkillsMissing.innerHTML = '';
        // Backend matched/missing are computed against the full resume content
        // (not just the flat "Your Skills" list) and are already canonical.
        (matchedSkills || []).forEach(s =>
            manualSkillsMatched.appendChild(makeBadge(s, matchedStyle, null)));
        (missingSkills || []).forEach(s =>
            manualSkillsMissing.appendChild(makeBadge(s, missingStyle, null)));
    }

    function renderManualSuggestions(suggestions) {
        renderTipList(manualSuggestionsList, suggestions);
    }

    // ── Utility: parse comma-separated skill string → array ──────────────────
    function parseCommaList(str) {
        return str ? str.split(',').map(s => s.trim()).filter(Boolean) : [];
    }

    // ── Render helper ────────────────────────────────────────────────────────
    function renderResume() {
        if (!currentStructuredData) return;
        const tpl = templateSelect.value || 'ats_classic';
        resumeDocument.style.cssText = 'display:flex;flex-direction:column;align-items:center;width:100%;padding:0;background:transparent;';
        resumeDocument.innerHTML = ResumeTemplates[tpl](currentStructuredData, activeSections);
        decorateEditableSections();
        autoFitPage();
        updateRecommendation();
    }

    // ── Editor drawer + hover-edit affordances ──────────────────────────────
    // Drawer body is populated by per-section panel renderers (Phase 2+).
    // Phase 1 ships only the open/close plumbing and the hover pencil icon.
    const editorDrawer       = document.getElementById('editor-drawer');
    const editorDrawerBody   = document.getElementById('editor-drawer-body');
    const editorDrawerTitle  = document.getElementById('editor-drawer-title');
    const editorDrawerClose  = document.getElementById('editor-drawer-close');
    const drawerBackdrop     = document.getElementById('drawer-backdrop');
    const builderPreview     = document.getElementById('builder-preview');

    const SECTION_LABELS = {
        profile:          'Profile',
        experience:       'Experience',
        projects:         'Projects',
        skills:           'Skills',
        'education-cert': 'Education & Certifications',
    };
    // Sections that have a real editor panel registered. Anything else still
    // opens the drawer but renders the Phase-1 placeholder.
    const sectionPanels = {};

    const PENCIL_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>';

    // Map an element's data-* attributes to a canonical section key.
    function sectionKeyFor(el) {
        if (!el) return null;
        if (el.dataset.section) return el.dataset.section;
        const role = el.dataset.role;
        if (role === 'experience' || role === 'projects') return role;
        if (role === 'summary') return 'profile';
        return null;
    }

    // After every render, find each top-level editable section and bolt on a
    // hover-revealed pencil icon. Dedupes by checking for an existing button
    // so re-renders don't accumulate.
    function decorateEditableSections() {
        const targets = resumeDocument.querySelectorAll('[data-section], [data-role="experience"], [data-role="projects"]');
        targets.forEach(el => {
            const key = sectionKeyFor(el);
            if (!key || !SECTION_LABELS[key]) return;
            // Only decorate the outermost match for each key — avoid stacking
            // pencils on nested data-section duplicates (e.g., summary inside profile group).
            if (el.closest(`[data-edit-decorated="${key}"]`)) return;
            el.setAttribute('data-edit-decorated', key);
            el.classList.add('resume-section-hoverable');
            if (el.querySelector(':scope > .section-edit-btn')) return;
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'section-edit-btn';
            btn.setAttribute('aria-label', `Edit ${SECTION_LABELS[key]}`);
            btn.dataset.editSection = key;
            btn.innerHTML = PENCIL_SVG;
            el.appendChild(btn);
        });
    }

    function openDrawer(sectionKey) {
        const label = SECTION_LABELS[sectionKey] || 'Edit section';
        editorDrawerTitle.textContent = label;
        // If a panel is registered for this section, let it own the body.
        // Otherwise show a friendly placeholder (Phase 1 state).
        if (typeof sectionPanels[sectionKey] === 'function') {
            sectionPanels[sectionKey](editorDrawerBody);
        } else {
            editorDrawerBody.innerHTML =
                `<p style="color:var(--color-text-muted);font-size:0.85rem;margin:0;">` +
                `The <strong>${label}</strong> editor will open here in the next phase.</p>`;
        }
        editorDrawer.classList.add('is-open');
        editorDrawer.setAttribute('aria-hidden', 'false');
        drawerBackdrop.classList.add('is-visible');
        drawerBackdrop.setAttribute('aria-hidden', 'false');
    }

    function closeDrawer() {
        editorDrawer.classList.remove('is-open');
        editorDrawer.setAttribute('aria-hidden', 'true');
        drawerBackdrop.classList.remove('is-visible');
        drawerBackdrop.setAttribute('aria-hidden', 'true');
    }

    // Delegate hover-icon clicks.
    resumeDocument.addEventListener('click', (e) => {
        const btn = e.target.closest('.section-edit-btn');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        openDrawer(btn.dataset.editSection);
    }, true);

    editorDrawerClose.addEventListener('click', closeDrawer);
    drawerBackdrop.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && editorDrawer.classList.contains('is-open')) closeDrawer();
    });

    // ── Phase 2: Section panel renderers ────────────────────────────────────
    // Each panel renderer receives the drawer body element and populates it.
    // Mutations go through currentStructuredData → renderResume() → scheduleRescore().

    // Shared: render an entry list with edit/delete/reorder + add form.
    function renderEntryList(container, opts) {
        const { dataKey, titleFn, subtitleFn, formFields, requiredFields, buildEntry, populateForm } = opts;
        if (!currentStructuredData) {
            container.innerHTML = '<p style="color:var(--color-text-muted);font-size:0.85rem;">Generate or analyze a resume first.</p>';
            return;
        }
        const entries = currentStructuredData[dataKey] || [];
        container.innerHTML = '';
        let editingIndex = -1; // tracks which entry is being edited

        function rerender() {
            renderResume();
            scheduleRescore(200);
            renderEntryList(container, opts);
        }

        // Entry cards
        entries.forEach((entry, idx) => {
            const card = document.createElement('div');
            card.className = 'editor-entry-card';
            card.innerHTML = `
                <div class="editor-entry-card__header">
                    <div style="min-width:0;">
                        <div class="editor-entry-card__title">${titleFn(entry)}</div>
                        ${subtitleFn ? `<div class="editor-entry-card__subtitle">${subtitleFn(entry)}</div>` : ''}
                    </div>
                    <div class="editor-entry-card__actions">
                        <button type="button" class="editor-entry-btn" data-act="edit" data-idx="${idx}" title="Edit">✎</button>
                        ${idx > 0 ? `<button type="button" class="editor-entry-btn" data-act="up" data-idx="${idx}" title="Move up">↑</button>` : ''}
                        ${idx < entries.length - 1 ? `<button type="button" class="editor-entry-btn" data-act="down" data-idx="${idx}" title="Move down">↓</button>` : ''}
                        <button type="button" class="editor-entry-btn editor-entry-btn--danger" data-act="delete" data-idx="${idx}" title="Delete">×</button>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });

        // Wire card actions via delegation
        container.addEventListener('click', function handler(e) {
            const btn = e.target.closest('[data-act]');
            if (!btn) return;
            const act = btn.dataset.act;
            const idx = parseInt(btn.dataset.idx, 10);
            const arr = currentStructuredData[dataKey];
            if (!arr) return;
            if (act === 'delete') {
                arr.splice(idx, 1);
                rerender();
            } else if (act === 'up' && idx > 0) {
                [arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]];
                rerender();
            } else if (act === 'down' && idx < arr.length - 1) {
                [arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]];
                rerender();
            } else if (act === 'edit') {
                editingIndex = idx;
                // Populate form with existing entry data and show it
                if (populateForm) populateForm(arr[idx], form);
                form.classList.add('is-active');
                addBtn.style.display = 'none';
                saveBtn.textContent = 'Update';
            }
        });

        // Add-new / edit form
        const addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'editor-add-btn';
        addBtn.innerHTML = `<span>+</span> Add ${SECTION_LABELS[dataKey] || 'entry'}`;
        container.appendChild(addBtn);

        const form = document.createElement('div');
        form.className = 'editor-inline-form';
        form.innerHTML = formFields.map(f => {
            if (f.type === 'textarea') {
                return `<div class="editor-field-group">
                    <label class="editor-field-label">${f.label}</label>
                    <textarea class="editor-field-input" data-fid="${f.id}" rows="${f.rows || 3}" placeholder="${f.placeholder || ''}"></textarea>
                </div>`;
            }
            return `<div class="editor-field-group">
                <label class="editor-field-label">${f.label}</label>
                <input type="text" class="editor-field-input" data-fid="${f.id}" placeholder="${f.placeholder || ''}">
            </div>`;
        }).join('') + `
            <div class="editor-inline-form__actions">
                <button type="button" class="editor-inline-form__cancel">Cancel</button>
                <button type="button" class="editor-inline-form__save">Save</button>
            </div>`;
        container.appendChild(form);

        const saveBtn = form.querySelector('.editor-inline-form__save');

        addBtn.addEventListener('click', () => {
            editingIndex = -1;
            saveBtn.textContent = 'Save';
            form.querySelectorAll('.editor-field-input').forEach(el => el.value = '');
            form.classList.add('is-active');
            addBtn.style.display = 'none';
        });

        form.querySelector('.editor-inline-form__cancel').addEventListener('click', () => {
            editingIndex = -1;
            form.classList.remove('is-active');
            addBtn.style.display = '';
            form.querySelectorAll('.editor-field-input').forEach(el => el.value = '');
        });

        saveBtn.addEventListener('click', () => {
            const vals = {};
            let missing = false;
            form.querySelectorAll('.editor-field-input').forEach(el => {
                vals[el.dataset.fid] = el.value.trim();
            });
            for (const rId of (requiredFields || [])) {
                if (!vals[rId]) { missing = true; break; }
            }
            if (missing) return;

            currentStructuredData[dataKey] = currentStructuredData[dataKey] || [];
            if (editingIndex >= 0) {
                // Update existing entry
                currentStructuredData[dataKey][editingIndex] = buildEntry(vals);
            } else {
                // Add new entry
                currentStructuredData[dataKey].push(buildEntry(vals));
            }

            editingIndex = -1;
            form.classList.remove('is-active');
            addBtn.style.display = '';
            form.querySelectorAll('.editor-field-input').forEach(el => el.value = '');
            rerender();
        });
    }

    // ── Profile panel ───────────────────────────────────────────────────────
    sectionPanels['profile'] = (body) => {
        if (!currentStructuredData) {
            body.innerHTML = '<p style="color:var(--color-text-muted);font-size:0.85rem;">Generate or analyze a resume first.</p>';
            return;
        }
        const d = currentStructuredData;
        body.innerHTML = `
            <div class="editor-field-group">
                <label class="editor-field-label">Name</label>
                <input type="text" class="editor-field-input" data-profile="name" value="${d.name || ''}">
            </div>
            <div class="editor-field-group">
                <label class="editor-field-label">Professional Title</label>
                <input type="text" class="editor-field-input" data-profile="title" value="${d.title || ''}">
            </div>
            <div class="editor-field-group">
                <label class="editor-field-label">Summary / About</label>
                <textarea class="editor-field-input" data-profile="summary" rows="4">${d.summary || ''}</textarea>
            </div>
            <div class="editor-section-divider"></div>
            <h3 class="editor-sub-header">Contact Information</h3>
            <div class="editor-field-row editor-field-row--2">
                <div class="editor-field-group">
                    <label class="editor-field-label">Email</label>
                    <input type="email" class="editor-field-input" data-profile="email" value="${d.email || ''}">
                </div>
                <div class="editor-field-group">
                    <label class="editor-field-label">Phone</label>
                    <input type="tel" class="editor-field-input" data-profile="phone" value="${d.phone || ''}">
                </div>
            </div>
            <div class="editor-field-row editor-field-row--2">
                <div class="editor-field-group">
                    <label class="editor-field-label">LinkedIn</label>
                    <input type="text" class="editor-field-input" data-profile="linkedin" value="${d.linkedin || ''}">
                </div>
                <div class="editor-field-group">
                    <label class="editor-field-label">GitHub</label>
                    <input type="text" class="editor-field-input" data-profile="github" value="${d.github || ''}">
                </div>
            </div>
        `;

        body.querySelectorAll('[data-profile]').forEach(el => {
            el.addEventListener('input', () => {
                const key = el.dataset.profile;
                currentStructuredData[key] = el.value.trim();
                renderResume();
                scheduleRescore();
            });
        });
    };

    // ── Experience panel ────────────────────────────────────────────────────
    sectionPanels['experience'] = (body) => {
        renderEntryList(body, {
            dataKey: 'experience',
            titleFn: e => e.role || 'Untitled',
            subtitleFn: e => [e.company, e.duration].filter(Boolean).join(' · '),
            requiredFields: ['role', 'company'],
            formFields: [
                { id: 'role', label: 'Role / Job Title', placeholder: 'e.g. Senior Software Engineer' },
                { id: 'company', label: 'Company', placeholder: 'e.g. Acme Corp' },
                { id: 'duration', label: 'Duration', placeholder: 'e.g. Jan 2023 – Present' },
                { id: 'desc', label: 'Bullet Points (one per line)', placeholder: 'Led backend migration, reducing API latency by 40%', type: 'textarea', rows: 3 },
            ],
            buildEntry: v => ({
                role: v.role,
                company: v.company,
                duration: v.duration || '',
                points: v.desc ? v.desc.split('\n').map(l => l.replace(/^[-•*]\s*/, '').trim()).filter(Boolean) : [],
            }),
            populateForm: (e, form) => {
                form.querySelector('[data-fid="role"]').value = e.role || '';
                form.querySelector('[data-fid="company"]').value = e.company || '';
                form.querySelector('[data-fid="duration"]').value = e.duration || '';
                form.querySelector('[data-fid="desc"]').value = (e.points || e.details || []).join('\n');
            },
        });
    };

    // ── Projects panel ──────────────────────────────────────────────────────
    sectionPanels['projects'] = (body) => {
        renderEntryList(body, {
            dataKey: 'projects',
            titleFn: p => p.title || 'Untitled',
            subtitleFn: p => (p.tech_stack || []).join(', '),
            requiredFields: ['title'],
            formFields: [
                { id: 'title', label: 'Project Title', placeholder: 'e.g. E-Commerce Platform' },
                { id: 'stack', label: 'Tech Stack (comma-separated)', placeholder: 'React, Node.js, MongoDB' },
                { id: 'desc', label: 'Bullet Points (one per line)', placeholder: 'Built cart + checkout, integrated Stripe', type: 'textarea', rows: 3 },
            ],
            buildEntry: v => ({
                title: v.title,
                tech_stack: v.stack ? v.stack.split(',').map(s => s.trim()).filter(Boolean) : [],
                points: v.desc ? v.desc.split('\n').map(l => l.replace(/^[-•*]\s*/, '').trim()).filter(Boolean) : [],
            }),
            populateForm: (p, form) => {
                form.querySelector('[data-fid="title"]').value = p.title || '';
                form.querySelector('[data-fid="stack"]').value = (p.tech_stack || []).join(', ');
                form.querySelector('[data-fid="desc"]').value = (p.points || []).join('\n');
            },
        });
    };

    // ── Education & Certifications panel ────────────────────────────────────
    sectionPanels['education-cert'] = (body) => {
        if (!currentStructuredData) {
            body.innerHTML = '<p style="color:var(--color-text-muted);font-size:0.85rem;">Generate or analyze a resume first.</p>';
            return;
        }
        body.innerHTML = '';

        // Education sub-section
        const eduHeader = document.createElement('h3');
        eduHeader.className = 'editor-sub-header';
        eduHeader.textContent = 'Education';
        body.appendChild(eduHeader);

        const eduContainer = document.createElement('div');
        eduContainer.style.cssText = 'display:flex;flex-direction:column;gap:10px;margin-bottom:16px;';
        body.appendChild(eduContainer);

        renderEntryList(eduContainer, {
            dataKey: 'education',
            titleFn: e => e.degree || 'Untitled',
            subtitleFn: e => [e.institution, e.year].filter(Boolean).join(' · '),
            requiredFields: ['degree', 'institution'],
            formFields: [
                { id: 'degree', label: 'Degree', placeholder: 'e.g. B.Tech Computer Science' },
                { id: 'institution', label: 'Institution', placeholder: 'e.g. MIT' },
                { id: 'year', label: 'Year / Duration', placeholder: 'e.g. 2019–2023' },
                { id: 'gpa', label: 'GPA / Score (optional)', placeholder: 'e.g. 3.8/4.0' },
            ],
            buildEntry: v => ({
                degree: v.gpa ? `${v.degree} (${v.gpa})` : v.degree,
                institution: v.institution,
                year: v.year || '',
            }),
            populateForm: (e, form) => {
                // Reverse the buildEntry GPA merge: "B.Tech CS (3.8/4.0)" → degree="B.Tech CS", gpa="3.8/4.0"
                let deg = e.degree || '';
                let gpa = '';
                const gpaMatch = deg.match(/^(.*?)\s*\(([^)]+)\)\s*$/);
                if (gpaMatch) { deg = gpaMatch[1]; gpa = gpaMatch[2]; }
                form.querySelector('[data-fid="degree"]').value = deg;
                form.querySelector('[data-fid="institution"]').value = e.institution || '';
                form.querySelector('[data-fid="year"]').value = e.year || '';
                form.querySelector('[data-fid="gpa"]').value = gpa;
            },
        });

        // Certifications sub-section
        const certHeader = document.createElement('h3');
        certHeader.className = 'editor-sub-header';
        certHeader.textContent = 'Certifications';
        body.appendChild(certHeader);

        const certContainer = document.createElement('div');
        certContainer.style.cssText = 'display:flex;flex-direction:column;gap:10px;';
        body.appendChild(certContainer);

        renderEntryList(certContainer, {
            dataKey: 'certifications',
            titleFn: c => typeof c === 'string' ? c : (c.name || 'Untitled'),
            requiredFields: ['name'],
            formFields: [
                { id: 'name', label: 'Certification Name', placeholder: 'e.g. AWS Solutions Architect' },
                { id: 'org', label: 'Issuing Organization', placeholder: 'e.g. Amazon' },
                { id: 'date', label: 'Date / Validity', placeholder: 'e.g. Jan 2024' },
            ],
            buildEntry: v => {
                let s = v.name;
                if (v.org) s += ` — ${v.org}`;
                if (v.date) s += ` (${v.date})`;
                return s;
            },
            populateForm: (c, form) => {
                // Parse "Name — Org (Date)" string back into fields
                let name = '', org = '', date = '';
                if (typeof c === 'string') {
                    let rest = c;
                    // Extract trailing (date)
                    const dateMatch = rest.match(/\s*\(([^)]+)\)\s*$/);
                    if (dateMatch) { date = dateMatch[1]; rest = rest.slice(0, dateMatch.index); }
                    // Split on " — " for name vs org
                    const dashIdx = rest.indexOf(' — ');
                    if (dashIdx !== -1) { name = rest.slice(0, dashIdx); org = rest.slice(dashIdx + 3); }
                    else { name = rest; }
                } else {
                    name = c.name || '';
                    org = c.org || '';
                    date = c.date || '';
                }
                form.querySelector('[data-fid="name"]').value = name.trim();
                form.querySelector('[data-fid="org"]').value = org.trim();
                form.querySelector('[data-fid="date"]').value = date.trim();
            },
        });
    };

    // ── Phase 3: Skills panel ─────────────────────────────────────────────────
    sectionPanels['skills'] = (body) => {
        if (!currentStructuredData) {
            body.innerHTML = '<p style="color:var(--color-text-muted);font-size:0.85rem;">Generate or analyze a resume first.</p>';
            return;
        }
        body.innerHTML = '';

        const CATEGORIES = [
            { key: 'technical', stateKey: 'technical_skills', label: 'Technical Skills' },
            { key: 'soft',      stateKey: 'soft_skills',      label: 'Soft Skills' },
            { key: 'languages', stateKey: 'languages',        label: 'Languages' },
        ];

        function syncAndRender() {
            // Mirror currentSkills → currentStructuredData, recompute groups, re-render resume
            CATEGORIES.forEach(({ key, stateKey }) => {
                currentStructuredData[stateKey] = [...currentSkills[key]];
            });
            currentStructuredData.skill_groups = filterAndGroupSkills(currentStructuredData.technical_skills || []);
            renderResume();
            scheduleRescore(200);
        }

        function renderChips() {
            CATEGORIES.forEach(({ key, label }) => {
                const section = body.querySelector(`[data-skill-cat="${key}"]`);
                if (!section) return;
                const chipsEl = section.querySelector('.editor-skill-chips');
                chipsEl.innerHTML = '';
                currentSkills[key].forEach((skill, idx) => {
                    const chip = document.createElement('span');
                    chip.className = 'editor-skill-chip';
                    chip.innerHTML = `${skill}<button type="button" aria-label="Remove ${skill}">×</button>`;
                    chip.querySelector('button').addEventListener('click', () => {
                        currentSkills[key].splice(idx, 1);
                        syncAndRender();
                        renderChips();
                    });
                    chipsEl.appendChild(chip);
                });
            });
        }

        CATEGORIES.forEach(({ key, label }) => {
            const section = document.createElement('div');
            section.dataset.skillCat = key;
            section.style.cssText = 'margin-bottom:16px;';

            const header = document.createElement('h3');
            header.className = 'editor-sub-header';
            header.textContent = label;
            section.appendChild(header);

            const chips = document.createElement('div');
            chips.className = 'editor-skill-chips';
            chips.style.marginBottom = '8px';
            section.appendChild(chips);

            // Add row
            const addRow = document.createElement('div');
            addRow.className = 'editor-skill-add-row';
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'editor-field-input';
            input.placeholder = `Add ${label.toLowerCase().replace(' skills', '')} skill…`;
            const addBtn = document.createElement('button');
            addBtn.type = 'button';
            addBtn.className = 'editor-add-btn';
            addBtn.style.cssText = 'padding:6px 12px;';
            addBtn.textContent = '+ Add';

            function doAdd() {
                const val = input.value.trim();
                if (!val) return;
                const canon = canonicalizeSkill(val);
                if (currentSkills[key].map(s => s.toLowerCase()).includes(canon.toLowerCase())) {
                    input.value = '';
                    return;
                }
                currentSkills[key].push(canon);
                input.value = '';
                syncAndRender();
                renderChips();
            }

            addBtn.addEventListener('click', doAdd);
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') { e.preventDefault(); doAdd(); }
            });

            addRow.appendChild(input);
            addRow.appendChild(addBtn);
            section.appendChild(addRow);

            body.appendChild(section);
        });

        renderChips();
    };

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
            // Backend's intelligence pipeline returns canonical display forms;
            // store them verbatim.
            savedJdSkillsFlat = data.jd_skills_flat || [];
            currentSkills = {
                technical: data.resume_skills?.technical || [],
                soft:      data.resume_skills?.soft      || [],
                languages: data.resume_skills?.languages || [],
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
                savedJdSkillsFlat = payload.jd_skills_flat;
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

    // ── 3. TEMPLATE SWITCHING + VISUAL GALLERY ─────────────────────────────
    templateSelect.addEventListener('change', () => renderResume());

    // Phase 4: visual template gallery
    const TEMPLATE_META = [
        { id: 'ats_classic',  name: 'Classic ATS',   tag: 'Best for portals',
          mini: `<div style="padding:6px 8px;font-family:sans-serif;">
            <div style="text-align:center;margin-bottom:4px;">
              <div style="background:#333;height:5px;width:60%;margin:0 auto 2px;border-radius:1px;"></div>
              <div style="background:#888;height:3px;width:40%;margin:0 auto;border-radius:1px;"></div>
            </div>
            <div style="border-top:1px solid #bfa;margin-bottom:3px;"></div>
            <div style="background:#e8e0d4;height:3px;width:90%;margin-bottom:2px;border-radius:1px;"></div>
            <div style="background:#e8e0d4;height:3px;width:75%;margin-bottom:4px;border-radius:1px;"></div>
            <div style="background:#8b6f47;height:2px;width:50%;margin-bottom:2px;border-radius:1px;"></div>
            <div style="background:#ddd;height:2px;width:85%;margin-bottom:1px;border-radius:1px;"></div>
            <div style="background:#ddd;height:2px;width:70%;border-radius:1px;"></div>
          </div>` },
        { id: 'executive',    name: 'Executive',     tag: 'Sleek & Professional',
          mini: `<div style="padding:6px 8px;font-family:sans-serif;">
            <div style="background:#1a1a1a;padding:4px;margin-bottom:4px;border-radius:1px;">
              <div style="background:#fff;height:4px;width:55%;margin-bottom:2px;border-radius:1px;"></div>
              <div style="background:rgba(255,255,255,.5);height:2px;width:35%;border-radius:1px;"></div>
            </div>
            <div style="background:#8b6f47;height:2px;width:45%;margin-bottom:3px;border-radius:1px;"></div>
            <div style="background:#ddd;height:2px;width:90%;margin-bottom:1px;border-radius:1px;"></div>
            <div style="background:#ddd;height:2px;width:80%;margin-bottom:3px;border-radius:1px;"></div>
            <div style="background:#8b6f47;height:2px;width:40%;margin-bottom:2px;border-radius:1px;"></div>
            <div style="background:#ddd;height:2px;width:85%;border-radius:1px;"></div>
          </div>` },
        { id: 'tech_modern',  name: 'Tech Modern',   tag: 'Clean & Grid-based',
          mini: `<div style="padding:6px 8px;font-family:sans-serif;">
            <div style="text-align:center;margin-bottom:3px;">
              <div style="background:#2c3e50;height:4px;width:50%;margin:0 auto 2px;border-radius:1px;"></div>
              <div style="background:#7f8c8d;height:2px;width:65%;margin:0 auto;border-radius:1px;"></div>
            </div>
            <div style="display:flex;gap:3px;margin-bottom:3px;">
              <div style="background:#3498db;height:2px;flex:1;border-radius:1px;"></div>
              <div style="background:#2ecc71;height:2px;flex:1;border-radius:1px;"></div>
              <div style="background:#e67e22;height:2px;flex:1;border-radius:1px;"></div>
            </div>
            <div style="background:#ddd;height:2px;width:90%;margin-bottom:1px;border-radius:1px;"></div>
            <div style="background:#ddd;height:2px;width:75%;margin-bottom:3px;border-radius:1px;"></div>
            <div style="background:#2c3e50;height:2px;width:40%;margin-bottom:2px;border-radius:1px;"></div>
            <div style="background:#ddd;height:2px;width:80%;border-radius:1px;"></div>
          </div>` },
        { id: 'sidebar_pro',  name: 'Sidebar Pro',   tag: 'Two-Column Creative',
          mini: `<div style="display:flex;height:100%;font-family:sans-serif;">
            <div style="width:35%;background:#2c3e50;padding:5px;">
              <div style="background:rgba(255,255,255,.7);height:4px;width:80%;margin-bottom:3px;border-radius:1px;"></div>
              <div style="background:rgba(255,255,255,.4);height:2px;width:60%;margin-bottom:4px;border-radius:1px;"></div>
              <div style="background:rgba(255,255,255,.3);height:2px;width:70%;margin-bottom:1px;border-radius:1px;"></div>
              <div style="background:rgba(255,255,255,.3);height:2px;width:55%;border-radius:1px;"></div>
            </div>
            <div style="flex:1;padding:5px;">
              <div style="background:#333;height:4px;width:70%;margin-bottom:2px;border-radius:1px;"></div>
              <div style="background:#ddd;height:2px;width:90%;margin-bottom:1px;border-radius:1px;"></div>
              <div style="background:#ddd;height:2px;width:75%;margin-bottom:3px;border-radius:1px;"></div>
              <div style="background:#8b6f47;height:2px;width:45%;margin-bottom:2px;border-radius:1px;"></div>
              <div style="background:#ddd;height:2px;width:80%;border-radius:1px;"></div>
            </div>
          </div>` },
    ];

    const templateGallery = document.getElementById('template-gallery');
    if (templateGallery) {
        TEMPLATE_META.forEach(tpl => {
            const card = document.createElement('button');
            card.type = 'button';
            card.className = 'template-card' + (templateSelect.value === tpl.id ? ' template-card--active' : '');
            card.dataset.templateId = tpl.id;
            card.setAttribute('role', 'radio');
            card.setAttribute('aria-checked', templateSelect.value === tpl.id ? 'true' : 'false');
            card.innerHTML = `
                <div class="template-card__preview">
                    <div class="template-card__preview-mini">${tpl.mini}</div>
                </div>
                <div class="template-card__info">
                    <span class="template-card__name">${tpl.name}</span>
                    <span class="template-card__tag">${tpl.tag}</span>
                </div>`;
            card.addEventListener('click', () => {
                templateSelect.value = tpl.id;
                templateSelect.dispatchEvent(new Event('change'));
                // Update active state
                templateGallery.querySelectorAll('.template-card').forEach(c => {
                    c.classList.remove('template-card--active');
                    c.setAttribute('aria-checked', 'false');
                });
                card.classList.add('template-card--active');
                card.setAttribute('aria-checked', 'true');
            });
            templateGallery.appendChild(card);
        });
    }

    // ── Phase 5: Experience-vs-Project recommendation banner ──────────────
    const recBanner = document.getElementById('recommendation-banner');
    const recText   = document.getElementById('recommendation-text');

    function updateRecommendation() {
        if (!recBanner || !recText || !currentStructuredData) {
            if (recBanner) recBanner.classList.remove('is-visible');
            return;
        }
        const exp  = (currentStructuredData.experience || []).length;
        const proj = (currentStructuredData.projects    || []).length;
        const hasBullets = (currentStructuredData.experience || []).some(
            e => (e.bullets || e.details || []).length > 0
        );

        let msg = '';
        if (exp === 0 && proj === 0) {
            msg = `<strong>Add your experience or projects</strong>
                   Resumes with at least one experience entry or project score significantly higher with ATS systems. Click the ✏️ pencil on the Experience or Projects section to get started.`;
        } else if (exp > 0 && !hasBullets) {
            msg = `<strong>Strengthen your experience bullets</strong>
                   Your experience entries don't have bullet points yet. Quantified achievements (e.g. "Improved latency by 40%") make a big ATS difference.`;
        } else if (exp === 0 && proj > 0) {
            msg = `<strong>Consider adding work experience</strong>
                   You have ${proj} project${proj > 1 ? 's' : ''} but no professional experience. Even internships or freelance work can boost your resume's ATS score.`;
        } else if (proj === 0 && exp > 0 && exp <= 2) {
            msg = `<strong>Add a project to stand out</strong>
                   With ${exp} experience entr${exp > 1 ? 'ies' : 'y'}, adding a personal or open-source project can showcase technical breadth and initiative.`;
        }

        if (msg) {
            recText.innerHTML = msg;
            recBanner.classList.add('is-visible');
        } else {
            recBanner.classList.remove('is-visible');
        }
    }

    // ── 4. ADD EXPERIENCE — moved to drawer-based editor (Phase 2) ────────

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

        // Raw user input — apply the slim frontend canonicalizer so chips and
        // the structured resume show consistent display forms before the
        // backend round-trip. (Backend re-canonicalizes anyway; this keeps
        // the UI honest while we wait for the response.)
        const technical = canonicalizeSkillList(parseCommaList(document.getElementById('m-technical').value));
        const soft      = canonicalizeSkillList(parseCommaList(document.getElementById('m-soft').value));
        const languages = canonicalizeSkillList(parseCommaList(document.getElementById('m-languages').value));

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
                // Backend's /optimize re-runs the user skills through the
                // intelligence pipeline (which knows the registry aliases),
                // so its resume.* fields are authoritative for display.
                // Adopt them before rendering so chips show "TypeScript"
                // instead of "Ts", "PostgreSQL" instead of "Postgres", etc.
                const optResume = optimizePayload.resume || {};
                if (Array.isArray(optResume.technical_skills)) currentSkills.technical = optResume.technical_skills;
                if (Array.isArray(optResume.soft_skills))      currentSkills.soft      = optResume.soft_skills;
                if (Array.isArray(optResume.languages))        currentSkills.languages = optResume.languages;

                renderManualAnalysis(
                    currentSkills,
                    analysisData.jd_skills || {},
                    analysisData.matched_skills || [],
                    analysisData.missing_skills || []
                );
                savedJdSkillsFlat = analysisData.jd_skills_flat || [];
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
                    savedJdSkillsFlat = optimizePayload.jd_skills_flat;
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

    // ── 5b. BUILDER — OPTIMIZE FOR JD (removed from builder UI, Fix #9) ────

    // ── 5c. Collapsible ATS score card toggle ────────────────────────────────
    const scorecardToggle = document.getElementById('scorecard-toggle');
    if (scorecardToggle) {
        scorecardToggle.addEventListener('click', () => {
            const card = document.getElementById('scoreCard');
            if (!card) return;
            const collapsed = card.classList.toggle('scorecard--collapsed');
            scorecardToggle.setAttribute('aria-expanded', !collapsed);
        });
    }

    // ── 6. ENTRY FORMS — moved to drawer-based editors (Phase 2) ──────────

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

        renderResume();
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
        clone.querySelectorAll('.block-ctrl').forEach(el => el.remove());
        clone.querySelectorAll('.section-edit-btn').forEach(el => el.remove());

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

    // Update collapsed mini-donut and toggle value
    const miniProg = document.getElementById('scoreMiniProgress');
    if (miniProg) {
        const pct = 100 - safeOptScore;
        miniProg.setAttribute('stroke-dashoffset', pct);
    }
    const toggleVal = document.getElementById('scoreToggleValue');
    if (toggleVal) toggleVal.innerHTML = `${safeOptScore}<small>/100</small>`;

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

