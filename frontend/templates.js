// ── SVG icons (inline, PDF-safe) ─────────────────────────────────────────
const ICONS = {
    email:    `<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>`,
    phone:    `<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>`,
    linkedin: `<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>`,
    github:   `<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>`,
};

// ── Contact block ─────────────────────────────────────────────────────────
function contactBlock(data, style) {
    const c = data._contact || {};
    const fields = [
        { key:'email',    val:data.email,    icon:ICONS.email    },
        { key:'phone',    val:data.phone,    icon:ICONS.phone    },
        { key:'linkedin', val:data.linkedin, icon:ICONS.linkedin },
        { key:'github',   val:data.github,   icon:ICONS.github   },
    ].filter(f => c[f.key] !== false && f.val && String(f.val).trim() !== '');
    if (!fields.length) return '';

    if (style === 'sidebar') {
        return fields.map(f => `
            <div style="display:flex;align-items:flex-start;gap:5px;margin-bottom:4px;">
                <span style="opacity:0.65;flex-shrink:0;margin-top:1px;">${f.icon}</span>
                <span style="flex:1;overflow-wrap:break-word;font-size:9pt;">${f.val}</span>
            </div>`).join('');
    }

    const fSize   = style === 'ats' ? '9.5pt' : '9pt';
    const color   = style === 'ats' ? 'color:#111;' : 'color:#64748b;';
    const justify = style === 'ats' ? 'center' : 'flex-start';
    return `<div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:${justify};gap:8px;font-size:${fSize};${color}margin-top:3px;">
        ${fields.map(f => `<span style="display:inline-flex;align-items:center;gap:3px;">
            <span style="opacity:0.6;display:flex;align-items:center;">${f.icon}</span>
            <span>${f.val}</span>
        </span>`).join('')}
    </div>`;
}


// ── Skill sections ────────────────────────────────────────────────────────
function skillSections(data, style, S) {
    S = S || {};
    const technical = S.technical !== false ? (data.technical_skills || data.skills || []) : [];
    const soft      = S.soft      !== false ? (data.soft_skills || []) : [];
    const languages = S.languages !== false ? (data.languages || []) : [];
    const groups    = S.technical !== false ? (data.skill_groups || null) : null;
    const hasGroups = groups && Object.keys(groups).length > 0;

    if (!technical.length && !soft.length && !languages.length) return '';

    const grpLabels = { programming:'Programming', frameworks:'Frameworks', databases:'Databases', tools:'Tools' };

    if (style === 'sidebar') {
        const h4 = 'text-transform:uppercase;font-size:10pt;border-bottom:1px solid #334155;margin:0 0 7px;padding:10px 0 2px;color:#cbd5e1;';
        return `
            ${technical.length ? `
            <h4 style="${h4}">Technical Skills</h4>
            ${hasGroups ? `
            <div style="margin:0 0 18px;">
                ${Object.entries(groups).map(([k,items]) =>
                    `<p style="font-size:9pt;margin:0 0 3px;line-height:1.4;"><span style="color:#94a3b8;text-transform:uppercase;font-size:8pt;letter-spacing:0.3px;">${grpLabels[k]||k}: </span>${items.join(', ')}</p>`
                ).join('')}
            </div>` : `
            <ul style="list-style:none;padding:0;margin:0 0 18px;font-size:9.5pt;">
                ${technical.map(s => `<li style="margin-bottom:3px;">${s}</li>`).join('')}
            </ul>`}` : ''}
            ${soft.length ? `
            <h4 style="${h4}">Soft Skills</h4>
            <ul style="list-style:none;padding:0;margin:0 0 18px;font-size:9.5pt;">
                ${soft.map(s => `<li style="margin-bottom:3px;">${s}</li>`).join('')}
            </ul>` : ''}
            ${languages.length ? `
            <h4 style="${h4}">Languages</h4>
            <ul style="list-style:none;padding:0;margin:0 0 18px;font-size:9.5pt;">
                ${languages.map(s => `<li style="margin-bottom:3px;">${s}</li>`).join('')}
            </ul>` : ''}`;
    }

    const hStyle = style === 'ats'  ? 'text-transform:uppercase;font-size:11pt;border-bottom:1px solid #111;margin:0 0 5px;'
                 : style === 'exec' ? 'font-size:11pt;color:#1e293b;border-bottom:2px solid #e2e8f0;margin:0 0 5px;padding-bottom:2px;text-transform:uppercase;'
                 :                   'color:#10b981;text-transform:uppercase;font-size:10pt;border-bottom:1px solid #e2e8f0;padding-bottom:2px;margin:0 0 5px;';
    const pStyle = style === 'ats'  ? 'margin:0;font-size:10pt;line-height:1.3;'
                 : style === 'exec' ? 'margin:0;font-size:9.5pt;color:#334155;line-height:1.3;'
                 :                   'margin:0;font-size:9.5pt;line-height:1.3;';
    const sep = style === 'ats' ? ' • ' : ', ';
    const w   = 'margin-bottom:8px;break-inside:avoid;';

    return `
        ${technical.length ? `
        <div style="${w}">
            <h4 style="${hStyle}">Technical Skills</h4>
            ${hasGroups
                ? Object.entries(groups).map(([k,items]) =>
                    `<p style="${pStyle}margin-bottom:1px;"><strong>${grpLabels[k]||k}:</strong> ${items.join(sep)}</p>`
                  ).join('')
                : `<p style="${pStyle}">${technical.join(sep)}</p>`
            }
        </div>` : ''}
        ${soft.length      ? `<div style="${w}"><h4 style="${hStyle}">Soft Skills</h4><p style="${pStyle}">${soft.join(sep)}</p></div>` : ''}
        ${languages.length ? `<div style="${w}"><h4 style="${hStyle}">Languages</h4><p style="${pStyle}">${languages.join(sep)}</p></div>` : ''}`;
}


// ── Projects block ────────────────────────────────────────────────────────
function projectsBlock(projects, style) {
    if (!projects || !projects.length) return '';

    if (style === 'ats') return `
        <section data-role="projects" style="margin-bottom:8px;">
            <h4 style="text-transform:uppercase;font-size:11pt;border-bottom:1px solid #111;margin:0 0 5px;">Projects</h4>
            ${projects.map((p,i) => `
                <div style="margin-bottom:8px;break-inside:avoid;">
                    <div style="display:flex;justify-content:space-between;align-items:center;font-weight:bold;font-size:10pt;">
                        <span>${p.title}</span>
                        <span style="display:flex;align-items:center;">
                            <span style="font-weight:normal;font-style:italic;font-size:9pt;">${(p.tech_stack||[]).join(', ')}</span>
                        </span>
                    </div>
                    <ul style="margin:0;padding-left:15px;font-size:9pt;">
                        ${(p.points||[]).slice(0,3).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                    </ul>
                </div>`).join('')}
        </section>`;

    if (style === 'exec') return `
        <section data-role="projects" style="margin-bottom:8px;">
            <h4 style="font-size:11pt;color:#1e293b;border-bottom:2px solid #e2e8f0;margin:0 0 5px;padding-bottom:2px;text-transform:uppercase;">Projects</h4>
            ${projects.map((p,i) => `
                <div style="margin-bottom:8px;break-inside:avoid;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-weight:bold;font-size:10.5pt;">${p.title}</span>
                        <span style="display:flex;align-items:center;">
                            <span style="color:#2563eb;font-size:9pt;">${(p.tech_stack||[]).join(', ')}</span>
                        </span>
                    </div>
                    <ul style="margin:0;padding-left:15px;font-size:9.5pt;color:#334155;">
                        ${(p.points||[]).slice(0,3).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                    </ul>
                </div>`).join('')}
        </section>`;

    if (style === 'tech') return `
        <div data-role="projects" style="margin-bottom:8px;">
            <h4 style="color:#10b981;text-transform:uppercase;font-size:10pt;border-bottom:1px solid #e2e8f0;padding-bottom:2px;margin:0 0 5px;">Projects</h4>
            ${projects.map((p,i) => `
                <div style="margin-bottom:8px;break-inside:avoid;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong style="font-size:10.5pt;">${p.title}</strong>
                        <span style="display:flex;align-items:center;">
                            <span style="color:#64748b;font-size:9pt;">${(p.tech_stack||[]).join(' · ')}</span>
                        </span>
                    </div>
                    <ul style="margin:0;padding-left:15px;font-size:9.5pt;">
                        ${(p.points||[]).slice(0,3).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                    </ul>
                </div>`).join('')}
        </div>`;

    if (style === 'sidebar') return `
        <div data-role="projects" style="margin-bottom:13px;">
            <h4 style="text-transform:uppercase;font-size:10pt;color:#0f172a;border-bottom:2px solid #e2e8f0;margin:0 0 7px;padding-bottom:3px;">Projects</h4>
            ${projects.map((p,i) => `
                <div style="margin-bottom:11px;break-inside:avoid;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong style="font-size:10pt;">${p.title}</strong>
                        <span style="display:flex;align-items:center;">
                            <span style="color:#64748b;font-size:9pt;">${(p.tech_stack||[]).join(' · ')}</span>
                        </span>
                    </div>
                    <ul style="margin:0;padding-left:15px;font-size:9.5pt;">
                        ${(p.points||[]).slice(0,3).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                    </ul>
                </div>`).join('')}
        </div>`;

    return '';
}

// ── A4 constants (px at 96dpi) ────────────────────────────────────────────
// 794 × 1123 px  =  210mm × 297mm  @96dpi
// The outer .resume-wrapper is ALWAYS these exact pixels — never grows.
// Content scaling (if overflow) is handled via transform:scale on .resume-scale-target.

const ResumeTemplates = {

    // 1. Classic ATS ──────────────────────────────────────────────────────
    ats_classic: (data, S) => {
        S = S || {};
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;background:white;box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target" style="width:794px;padding:40px;box-sizing:border-box;font-family:'Times New Roman',serif;color:#111;line-height:1.25;transform-origin:top left;">

                <div data-section="profile">
                    <header style="text-align:center;border-bottom:1.5px solid #111;padding-bottom:6px;margin-bottom:8px;flex-shrink:0;">
                        <h1 style="margin:0;font-size:23pt;text-transform:uppercase;line-height:1.1;">${data.name}</h1>
                        <h3 style="margin:2px 0 0;font-size:12pt;font-weight:normal;line-height:1.2;">${data.title}</h3>
                        ${contactBlock(data, 'ats')}
                    </header>
                    <section data-role="summary" style="margin-bottom:6px;">
                        <p style="margin:0;text-align:justify;font-size:9.5pt;">${data.summary}</p>
                    </section>
                </div>

                <div data-section="skills">${skillSections(data, 'ats', S)}</div>

                ${S.experience !== false ? `
                <section data-role="experience" style="margin-bottom:8px;">
                    <h4 style="text-transform:uppercase;font-size:11pt;border-bottom:1px solid #111;margin:0 0 5px;">Professional Experience</h4>
                    ${(data.experience||[]).map((exp,i) => `
                        <div style="margin-bottom:8px;break-inside:avoid;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;font-weight:bold;font-size:10pt;">
                                <span>${exp.role}</span>
                                <span style="display:flex;align-items:center;">
                                    <span style="font-weight:normal;font-size:9pt;">${exp.duration}</span>
                                        </span>
                            </div>
                            <div style="font-style:italic;font-size:9pt;margin-bottom:1px;">${exp.company}</div>
                            <ul style="margin:0;padding-left:14px;font-size:9pt;">
                                ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                            </ul>
                        </div>`).join('')}
                </section>` : ''}

                ${S.projects !== false ? projectsBlock(data.projects,'ats') : ''}

                ${S.education !== false ? `
                <section data-section="education-cert" style="margin-bottom:8px;break-inside:avoid;">
                    <h4 style="text-transform:uppercase;font-size:11pt;border-bottom:1px solid #111;margin:0 0 5px;">Education</h4>
                    ${(data.education||[]).map((ed,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:9.5pt;margin-bottom:1px;">
                            <strong>${ed.degree}</strong>
                            <span style="display:flex;align-items:center;">
                                <span>${ed.institution} | ${ed.year}</span>
                                </span>
                        </div>`).join('')}
                </section>` : ''}

                ${S.certifications !== false && (data.certifications||[]).length ? `
                <section data-section="education-cert" style="break-inside:avoid;">
                    <h4 style="text-transform:uppercase;font-size:11pt;border-bottom:1px solid #111;margin:0 0 5px;">Certifications & Achievements</h4>
                    ${(data.certifications||[]).map((c,i) => `
                        <div style="display:flex;align-items:center;font-size:9pt;margin-bottom:1px;gap:3px;">
                            <span style="flex:1;display:flex;align-items:baseline;gap:3px;"><span style="flex-shrink:0;">•</span><span>${c}</span></span>
                        </div>`).join('')}
                </section>` : ''}

            </div>
        </div>`;
    },

    // 2. Executive — Boardroom elegant: charcoal tones, thin top accent band,
    //    wide name with refined serif, muted palette, clean horizontal rules
    executive: (data, S) => {
        S = S || {};
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;background:white;box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target" style="width:794px;padding:0;box-sizing:border-box;font-family:'Cambria','Georgia',serif;color:#2d2d2d;line-height:1.3;transform-origin:top left;">

                <!-- Thin charcoal accent band -->
                <div style="height:6px;background:#2d2d2d;"></div>

                <div style="padding:32px 48px 30px;">

                    <div data-section="profile">
                        <header style="text-align:center;margin-bottom:14px;flex-shrink:0;">
                            <h1 style="margin:0;font-size:28pt;font-weight:400;letter-spacing:3px;text-transform:uppercase;color:#2d2d2d;line-height:1.1;">${data.name}</h1>
                            <div style="width:60px;height:1px;background:#999;margin:8px auto;"></div>
                            <h3 style="margin:0;font-size:11pt;font-weight:400;color:#666;letter-spacing:1.5px;text-transform:uppercase;line-height:1.3;">${data.title}</h3>
                            <div style="margin-top:8px;display:flex;flex-wrap:wrap;justify-content:center;gap:14px;font-size:9pt;color:#555;">
                                ${(data._contact||{}).email !== false && data.email ? `<span style="display:inline-flex;align-items:center;gap:3px;"><span style="opacity:0.5;">${ICONS.email}</span>${data.email}</span>` : ''}
                                ${(data._contact||{}).phone !== false && data.phone ? `<span style="display:inline-flex;align-items:center;gap:3px;"><span style="opacity:0.5;">${ICONS.phone}</span>${data.phone}</span>` : ''}
                                ${(data._contact||{}).linkedin !== false && data.linkedin ? `<span style="display:inline-flex;align-items:center;gap:3px;"><span style="opacity:0.5;">${ICONS.linkedin}</span>${data.linkedin}</span>` : ''}
                                ${(data._contact||{}).github !== false && data.github ? `<span style="display:inline-flex;align-items:center;gap:3px;"><span style="opacity:0.5;">${ICONS.github}</span>${data.github}</span>` : ''}
                            </div>
                        </header>
                        <hr style="border:none;border-top:1px solid #d0d0d0;margin:0 0 10px;">
                        <p data-role="summary" style="margin:0 0 12px;text-align:justify;font-size:9.5pt;color:#444;line-height:1.5;">${data.summary}</p>
                    </div>

                    ${S.experience !== false ? `
                    <section data-role="experience" style="margin-bottom:10px;">
                        <h4 style="font-size:9.5pt;text-transform:uppercase;letter-spacing:2px;color:#2d2d2d;margin:0 0 6px;padding-bottom:3px;border-bottom:1px solid #d0d0d0;font-weight:600;">Professional Experience</h4>
                        ${(data.experience||[]).map((exp,i) => `
                            <div style="margin-bottom:10px;break-inside:avoid;">
                                <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                    <strong style="font-size:10.5pt;color:#2d2d2d;">${exp.role}</strong>
                                    <span style="font-size:9pt;color:#888;font-style:italic;">${exp.duration}</span>
                                </div>
                                <div style="font-size:9pt;color:#666;margin-bottom:2px;">${exp.company}</div>
                                <ul style="margin:0;padding-left:14px;font-size:9pt;color:#444;">
                                    ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;line-height:1.4;">${pt}</li>`).join('')}
                                </ul>
                            </div>`).join('')}
                    </section>` : ''}

                    ${S.projects !== false ? projectsBlock(data.projects,'exec') : ''}

                    <div data-section="skills">${skillSections(data,'exec',S)}</div>

                    ${S.education !== false ? `
                    <section data-section="education-cert" style="margin-bottom:8px;break-inside:avoid;">
                        <h4 style="font-size:9.5pt;text-transform:uppercase;letter-spacing:2px;color:#2d2d2d;margin:0 0 5px;padding-bottom:3px;border-bottom:1px solid #d0d0d0;font-weight:600;">Education</h4>
                        ${(data.education||[]).map((ed,i) => `
                            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;font-size:9.5pt;">
                                <strong>${ed.degree}</strong>
                                <span style="color:#888;font-style:italic;">${ed.institution}, ${ed.year}</span>
                            </div>`).join('')}
                    </section>` : ''}

                    ${S.certifications !== false && (data.certifications||[]).length ? `
                    <section data-section="education-cert" style="break-inside:avoid;">
                        <h4 style="font-size:9.5pt;text-transform:uppercase;letter-spacing:2px;color:#2d2d2d;margin:0 0 5px;padding-bottom:3px;border-bottom:1px solid #d0d0d0;font-weight:600;">Certifications</h4>
                        ${(data.certifications||[]).map((c,i) => `
                            <div style="font-size:9pt;margin-bottom:2px;color:#444;padding-left:10px;border-left:2px solid #d0d0d0;">
                                ${c}
                            </div>`).join('')}
                    </section>` : ''}

                </div>
            </div>
        </div>`;
    },

    // 3. Bold Modern — Startup/creative: two-column header with accent block,
    //    bold sans-serif, coral-orange accent, pill-shaped skill tags, geometric feel
    tech_modern: (data, S) => {
        S = S || {};
        const accent = '#e8553d';
        const accentLight = '#fef2f0';
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;background:white;box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target" style="width:794px;padding:0;box-sizing:border-box;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;color:#1a1a1a;line-height:1.3;transform-origin:top left;">

                <!-- Split header: name block + contact -->
                <div data-section="profile">
                    <header style="display:flex;flex-shrink:0;">
                        <div style="background:${accent};color:#fff;padding:28px 24px;width:55%;box-sizing:border-box;">
                            <h1 style="margin:0;font-size:24pt;font-weight:800;line-height:1.1;letter-spacing:-0.5px;">${data.name}</h1>
                            <h3 style="margin:4px 0 0;font-size:11pt;font-weight:400;color:rgba(255,255,255,0.85);text-transform:uppercase;letter-spacing:1px;line-height:1.2;">${data.title}</h3>
                        </div>
                        <div style="background:#fafafa;padding:28px 20px;width:45%;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;gap:4px;font-size:9pt;color:#555;border-bottom:1px solid #eee;">
                            ${(data._contact||{}).email !== false && data.email ? `<span style="display:inline-flex;align-items:center;gap:4px;"><span style="opacity:0.5;">${ICONS.email}</span>${data.email}</span>` : ''}
                            ${(data._contact||{}).phone !== false && data.phone ? `<span style="display:inline-flex;align-items:center;gap:4px;"><span style="opacity:0.5;">${ICONS.phone}</span>${data.phone}</span>` : ''}
                            ${(data._contact||{}).linkedin !== false && data.linkedin ? `<span style="display:inline-flex;align-items:center;gap:4px;"><span style="opacity:0.5;">${ICONS.linkedin}</span>${data.linkedin}</span>` : ''}
                            ${(data._contact||{}).github !== false && data.github ? `<span style="display:inline-flex;align-items:center;gap:4px;"><span style="opacity:0.5;">${ICONS.github}</span>${data.github}</span>` : ''}
                        </div>
                    </header>
                    <div style="padding:16px 32px 0;">
                        <p data-role="summary" style="margin:0 0 12px;font-size:9.5pt;text-align:justify;color:#444;line-height:1.5;">${data.summary}</p>
                    </div>
                </div>

                <div style="padding:0 32px 30px;">

                    ${S.experience !== false ? `
                    <div data-role="experience" style="margin-bottom:10px;">
                        <h4 style="font-size:10pt;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:${accent};margin:0 0 6px;padding-bottom:3px;border-bottom:2px solid ${accent};">Experience</h4>
                        ${(data.experience||[]).map((exp,i) => `
                            <div style="margin-bottom:9px;break-inside:avoid;padding-left:10px;border-left:3px solid ${accentLight};">
                                <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                    <strong style="font-size:10.5pt;">${exp.role}</strong>
                                    <span style="font-size:8.5pt;color:#888;">${exp.duration}</span>
                                </div>
                                <div style="font-size:9pt;color:${accent};font-weight:600;margin-bottom:2px;">${exp.company}</div>
                                <ul style="margin:0;padding-left:14px;font-size:9pt;color:#444;">
                                    ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;line-height:1.4;">${pt}</li>`).join('')}
                                </ul>
                            </div>`).join('')}
                    </div>` : ''}

                    ${S.projects !== false ? projectsBlock(data.projects,'tech') : ''}

                    <div data-section="skills">${skillSections(data,'tech',S)}</div>

                    ${S.education !== false ? `
                    <div data-section="education-cert" style="margin-bottom:7px;">
                        <h4 style="font-size:10pt;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:${accent};margin:0 0 5px;padding-bottom:3px;border-bottom:2px solid ${accent};">Education</h4>
                        ${(data.education||[]).map((ed,i) => `
                            <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:9.5pt;margin-bottom:2px;">
                                <strong>${ed.degree}</strong>
                                <span style="color:#888;font-size:9pt;">${ed.institution} &middot; ${ed.year}</span>
                            </div>`).join('')}
                    </div>` : ''}

                    ${S.certifications !== false && (data.certifications||[]).length ? `
                    <section data-section="education-cert" style="break-inside:avoid;">
                        <h4 style="font-size:10pt;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:${accent};margin:0 0 5px;padding-bottom:3px;border-bottom:2px solid ${accent};">Certifications</h4>
                        ${(data.certifications||[]).map((c,i) => `
                            <div style="font-size:9pt;margin-bottom:3px;color:#444;display:flex;align-items:center;gap:5px;">
                                <span style="width:5px;height:5px;border-radius:50%;background:${accent};flex-shrink:0;"></span>
                                ${c}
                            </div>`).join('')}
                    </section>` : ''}

                </div>
            </div>
        </div>`;
    },

    // 4. Sidebar Pro ──────────────────────────────────────────────────────
    sidebar_pro: (data, S) => {
        S = S || {};
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target t4-layout" style="transform-origin:top left;">

                <!-- Sidebar (28%) -->
                <div class="t4-sidebar">
                    <div data-section="profile">
                        <h1 style="font-size:25pt;font-weight:700;line-height:1.15;margin:0 0 4px;color:#f8fafc;">${data.name}</h1>
                        <p style="font-size:10.5pt;color:#94a3b8;font-weight:400;margin:0 0 14px;line-height:1.3;">${data.title}</p>

                        <div class="t4-sb-section">
                            <h4 style="text-transform:uppercase;font-size:9pt;letter-spacing:0.5px;color:#cbd5e1;border-bottom:1px solid #334155;margin:0 0 6px;padding-bottom:3px;">Contact</h4>
                            <div style="font-size:9.5pt;color:#94a3b8;">
                                ${contactBlock(data,'sidebar')}
                            </div>
                        </div>
                    </div>

                    <div data-section="skills">${skillSections(data,'sidebar',S)}</div>
                </div>

                <!-- Main content (72%) -->
                <div class="t4-main">

                    <div data-role="summary" data-section="profile" class="t4-section">
                        <h4 class="t4-section-head">Profile</h4>
                        <p style="margin:0;font-size:10.5pt;line-height:1.45;text-align:justify;">${data.summary}</p>
                    </div>

                    ${S.experience !== false ? `
                    <div data-role="experience" class="t4-section">
                        <h4 class="t4-section-head">Experience</h4>
                        ${(data.experience||[]).map((exp,i) => `
                        <div style="margin-bottom:8px;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                <strong style="font-size:11pt;">${exp.role}</strong>
                                </div>
                            <div style="font-size:10pt;color:#64748b;margin-bottom:3px;">
                                <span>${exp.company}</span>
                                <span> · </span>
                                <span>${exp.duration}</span>
                            </div>
                            <ul style="margin:0;padding-left:14px;font-size:10pt;">
                                ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                            </ul>
                        </div>`).join('')}
                    </div>` : ''}

                    ${S.projects !== false ? projectsBlock(data.projects,'sidebar') : ''}

                    ${S.education !== false && (data.education||[]).length ? `
                    <div class="t4-section" data-section="education-cert">
                        <h4 class="t4-section-head">Education</h4>
                        ${(data.education||[]).map((ed,i) => `
                        <div style="margin-bottom:6px;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                <strong style="font-size:10.5pt;">${ed.degree}</strong>
                                </div>
                            <div style="font-size:10pt;color:#64748b;">
                                <span>${ed.institution}</span><span> · ${ed.year}</span>
                            </div>
                        </div>`).join('')}
                    </div>` : ''}

                    ${S.certifications !== false && (data.certifications||[]).length ? `
                    <div class="t4-section" data-section="education-cert">
                        <h4 class="t4-section-head">Certifications & Achievements</h4>
                        ${(data.certifications||[]).map((c,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;font-size:10pt;">
                            <span>${c}</span>
                        </div>`).join('')}
                    </div>` : ''}

                </div>

            </div>
        </div>`;
    },

    // 5. Corporate — Consulting/structured: teal accent, grid-style contact bar,
    //    two-column skills layout, metric-focused entries, clean professional feel
    modern_corporate: (data, S) => {
        S = S || {};
        const accent = '#0d7377';
        const accentBg = '#f0fafa';
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;background:white;box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target" style="width:794px;padding:0;box-sizing:border-box;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;color:#1a1a1a;line-height:1.3;transform-origin:top left;">

                <div data-section="profile">
                    <!-- Structured header: name left, contact right, teal bar bottom -->
                    <header style="padding:30px 40px 0;flex-shrink:0;">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                            <div>
                                <h1 style="margin:0;font-size:24pt;font-weight:700;color:#1a1a1a;line-height:1.1;">${data.name}</h1>
                                <h3 style="margin:3px 0 0;font-size:11pt;font-weight:500;color:${accent};line-height:1.2;">${data.title}</h3>
                            </div>
                            <div style="text-align:right;font-size:9pt;color:#555;line-height:1.6;">
                                ${(data._contact||{}).email !== false && data.email ? `<div style="display:flex;align-items:center;justify-content:flex-end;gap:4px;"><span>${data.email}</span><span style="opacity:0.5;">${ICONS.email}</span></div>` : ''}
                                ${(data._contact||{}).phone !== false && data.phone ? `<div style="display:flex;align-items:center;justify-content:flex-end;gap:4px;"><span>${data.phone}</span><span style="opacity:0.5;">${ICONS.phone}</span></div>` : ''}
                                ${(data._contact||{}).linkedin !== false && data.linkedin ? `<div style="display:flex;align-items:center;justify-content:flex-end;gap:4px;"><span>${data.linkedin}</span><span style="opacity:0.5;">${ICONS.linkedin}</span></div>` : ''}
                                ${(data._contact||{}).github !== false && data.github ? `<div style="display:flex;align-items:center;justify-content:flex-end;gap:4px;"><span>${data.github}</span><span style="opacity:0.5;">${ICONS.github}</span></div>` : ''}
                            </div>
                        </div>
                        <div style="height:3px;background:${accent};margin-top:12px;"></div>
                    </header>
                    <div style="padding:12px 40px 0;">
                        <p data-role="summary" style="margin:0 0 12px;font-size:9.5pt;text-align:justify;color:#444;line-height:1.5;">${data.summary}</p>
                    </div>
                </div>

                <div style="padding:0 40px 30px;">

                    ${S.experience !== false ? `
                    <section data-role="experience" style="margin-bottom:10px;">
                        <h4 style="font-size:10pt;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:${accent};margin:0 0 6px;padding-bottom:3px;border-bottom:2px solid ${accent};">Experience</h4>
                        ${(data.experience||[]).map((exp,i) => `
                            <div style="margin-bottom:9px;break-inside:avoid;">
                                <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                    <strong style="font-size:10.5pt;">${exp.role}</strong>
                                    <span style="font-size:9pt;color:#888;">${exp.duration}</span>
                                </div>
                                <div style="font-size:9pt;color:${accent};font-weight:600;margin-bottom:2px;">${exp.company}</div>
                                <ul style="margin:0;padding-left:14px;font-size:9pt;color:#444;">
                                    ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;line-height:1.4;">${pt}</li>`).join('')}
                                </ul>
                            </div>`).join('')}
                    </section>` : ''}

                    ${S.projects !== false ? projectsBlock(data.projects,'exec') : ''}

                    <div data-section="skills">${skillSections(data,'exec',S)}</div>

                    ${S.education !== false ? `
                    <section data-section="education-cert" style="margin-bottom:8px;break-inside:avoid;">
                        <h4 style="font-size:10pt;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:${accent};margin:0 0 5px;padding-bottom:3px;border-bottom:2px solid ${accent};">Education</h4>
                        ${(data.education||[]).map((ed,i) => `
                            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;font-size:9.5pt;">
                                <strong>${ed.degree}</strong>
                                <span style="color:#888;font-size:9pt;">${ed.institution} &middot; ${ed.year}</span>
                            </div>`).join('')}
                    </section>` : ''}

                    ${S.certifications !== false && (data.certifications||[]).length ? `
                    <section data-section="education-cert" style="break-inside:avoid;">
                        <h4 style="font-size:10pt;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:${accent};margin:0 0 5px;padding-bottom:3px;border-bottom:2px solid ${accent};">Certifications</h4>
                        ${(data.certifications||[]).map((c,i) => `
                            <div style="font-size:9pt;margin-bottom:3px;color:#444;padding:3px 8px;background:${accentBg};border-radius:3px;">
                                ${c}
                            </div>`).join('')}
                    </section>` : ''}
                </div>

            </div>
        </div>`;
    },

    // 6. Minimal Professional ────────────────────────────────────────────
    minimal_pro: (data, S) => {
        S = S || {};
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;background:white;box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target" style="width:794px;padding:44px 48px;box-sizing:border-box;font-family:'Georgia',serif;color:#222;line-height:1.3;transform-origin:top left;">

                <div data-section="profile">
                    <header style="margin-bottom:12px;flex-shrink:0;">
                        <h1 style="margin:0;font-size:26pt;font-weight:600;letter-spacing:-0.5px;line-height:1.1;">${data.name}</h1>
                        <h3 style="margin:2px 0 0;font-size:11pt;font-weight:400;color:#888;letter-spacing:2px;text-transform:uppercase;line-height:1.2;">${data.title}</h3>
                        ${contactBlock(data, 'ats')}
                        <hr style="border:none;border-top:1px solid #ccc;margin:8px 0 0;">
                    </header>
                    <p data-role="summary" style="margin:0 0 10px;font-size:9.5pt;text-align:justify;color:#444;font-style:italic;">${data.summary}</p>
                </div>

                ${S.experience !== false ? `
                <section data-role="experience" style="margin-bottom:10px;">
                    <h4 style="font-size:10pt;text-transform:uppercase;letter-spacing:2px;color:#888;margin:0 0 6px;font-weight:400;">Experience</h4>
                    ${(data.experience||[]).map((exp,i) => `
                        <div style="margin-bottom:8px;break-inside:avoid;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:10pt;">
                                <strong>${exp.role}</strong>
                                <span style="display:flex;align-items:center;">
                                    <span style="font-size:9pt;color:#888;">${exp.duration}</span>
                                        </span>
                            </div>
                            <div style="font-size:9pt;color:#666;margin-bottom:1px;">${exp.company}</div>
                            <ul style="margin:0;padding-left:14px;font-size:9pt;color:#444;">
                                ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                            </ul>
                        </div>`).join('')}
                </section>` : ''}

                ${S.projects !== false ? projectsBlock(data.projects,'exec') : ''}

                <div data-section="skills">${skillSections(data,'ats',S)}</div>

                ${S.education !== false ? `
                <section data-section="education-cert" style="margin-bottom:7px;break-inside:avoid;">
                    <h4 style="font-size:10pt;text-transform:uppercase;letter-spacing:2px;color:#888;margin:0 0 5px;font-weight:400;">Education</h4>
                    ${(data.education||[]).map((ed,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:1px;font-size:9.5pt;">
                            <strong>${ed.degree}</strong>
                            <span style="display:flex;align-items:center;">
                                <span>${ed.institution} · ${ed.year}</span>
                                </span>
                        </div>`).join('')}
                </section>` : ''}

                ${S.certifications !== false && (data.certifications||[]).length ? `
                <section data-section="education-cert" style="break-inside:avoid;">
                    <h4 style="font-size:10pt;text-transform:uppercase;letter-spacing:2px;color:#888;margin:0 0 5px;font-weight:400;">Certifications</h4>
                    ${(data.certifications||[]).map((c,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1px;font-size:9pt;">
                            <span>${c}</span>
                        </div>`).join('')}
                </section>` : ''}

            </div>
        </div>`;
    },

    // 7. Tech Professional ───────────────────────────────────────────────
    tech_pro: (data, S) => {
        S = S || {};
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;background:white;box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target" style="width:794px;padding:36px 40px;box-sizing:border-box;font-family:'Consolas','Courier New',monospace;color:#1e1e1e;line-height:1.25;transform-origin:top left;">

                <div data-section="profile">
                    <header style="margin-bottom:10px;flex-shrink:0;">
                        <div style="display:flex;align-items:baseline;gap:10px;">
                            <h1 style="margin:0;font-size:22pt;font-weight:700;line-height:1.1;">${data.name}</h1>
                            <span style="font-size:9pt;color:#0ea5e9;font-family:sans-serif;">// ${data.title}</span>
                        </div>
                        ${contactBlock(data, 'tech')}
                        <div style="border-top:2px dashed #0ea5e9;margin-top:6px;"></div>
                    </header>
                    <p data-role="summary" style="margin:0 0 8px;font-size:9pt;font-family:sans-serif;color:#475569;background:#f8fafc;padding:6px 10px;border-left:3px solid #0ea5e9;">${data.summary}</p>
                </div>

                ${S.experience !== false ? `
                <section data-role="experience" style="margin-bottom:8px;">
                    <h4 style="font-size:10pt;color:#0ea5e9;margin:0 0 5px;font-family:sans-serif;"><span style="color:#888;">&gt;</span> Experience</h4>
                    ${(data.experience||[]).map((exp,i) => `
                        <div style="margin-bottom:8px;break-inside:avoid;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:10pt;">
                                <strong style="font-family:sans-serif;">${exp.role}</strong>
                                <span style="display:flex;align-items:center;">
                                    <span style="font-size:8.5pt;color:#64748b;font-family:sans-serif;">${exp.company} | ${exp.duration}</span>
                                        </span>
                            </div>
                            <ul style="margin:0;padding-left:14px;font-size:8.5pt;font-family:sans-serif;color:#334155;">
                                ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                            </ul>
                        </div>`).join('')}
                </section>` : ''}

                ${S.projects !== false ? projectsBlock(data.projects,'tech') : ''}

                <div data-section="skills">${skillSections(data,'tech',S)}</div>

                ${S.education !== false ? `
                <section data-section="education-cert" style="margin-bottom:7px;break-inside:avoid;">
                    <h4 style="font-size:10pt;color:#0ea5e9;margin:0 0 5px;font-family:sans-serif;"><span style="color:#888;">&gt;</span> Education</h4>
                    ${(data.education||[]).map((ed,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:9pt;margin-bottom:1px;font-family:sans-serif;">
                            <strong>${ed.degree}</strong>
                            <span style="display:flex;align-items:center;">
                                <span style="color:#64748b;">${ed.institution} · ${ed.year}</span>
                                </span>
                        </div>`).join('')}
                </section>` : ''}

                ${S.certifications !== false && (data.certifications||[]).length ? `
                <section data-section="education-cert" style="break-inside:avoid;">
                    <h4 style="font-size:10pt;color:#0ea5e9;margin:0 0 5px;font-family:sans-serif;"><span style="color:#888;">&gt;</span> Certifications</h4>
                    ${(data.certifications||[]).map((c,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1px;font-size:8.5pt;font-family:sans-serif;">
                            <span>${c}</span>
                        </div>`).join('')}
                </section>` : ''}

            </div>
        </div>`;
    },

    // 8. Editorial — Magazine-inspired luxury: display serif, warm cream tones,
    //    full-width name band, gold accent line, elegant whitespace, italic details
    premium_exec: (data, S) => {
        S = S || {};
        const gold = '#b8860b';
        const cream = '#fdfcf8';
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;background:${cream};box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target" style="width:794px;padding:0;box-sizing:border-box;font-family:'Palatino Linotype','Book Antiqua','Georgia',serif;color:#2a2a2a;line-height:1.35;transform-origin:top left;">

                <div data-section="profile">
                    <!-- Elegant centered name with gold rule -->
                    <header style="text-align:center;padding:40px 50px 0;flex-shrink:0;">
                        <h1 style="margin:0;font-size:30pt;font-weight:400;letter-spacing:4px;text-transform:uppercase;color:#2a2a2a;line-height:1.1;">${data.name}</h1>
                        <div style="width:80px;height:2px;background:${gold};margin:10px auto;"></div>
                        <h3 style="margin:0;font-size:11pt;font-weight:400;color:#777;letter-spacing:2px;text-transform:uppercase;line-height:1.3;">${data.title}</h3>
                        <div style="margin-top:10px;display:flex;flex-wrap:wrap;justify-content:center;gap:14px;font-size:9pt;color:#888;">
                            ${(data._contact||{}).email !== false && data.email ? `<span style="display:inline-flex;align-items:center;gap:3px;"><span style="opacity:0.5;">${ICONS.email}</span>${data.email}</span>` : ''}
                            ${(data._contact||{}).phone !== false && data.phone ? `<span style="display:inline-flex;align-items:center;gap:3px;"><span style="opacity:0.5;">${ICONS.phone}</span>${data.phone}</span>` : ''}
                            ${(data._contact||{}).linkedin !== false && data.linkedin ? `<span style="display:inline-flex;align-items:center;gap:3px;"><span style="opacity:0.5;">${ICONS.linkedin}</span>${data.linkedin}</span>` : ''}
                            ${(data._contact||{}).github !== false && data.github ? `<span style="display:inline-flex;align-items:center;gap:3px;"><span style="opacity:0.5;">${ICONS.github}</span>${data.github}</span>` : ''}
                        </div>
                    </header>
                    <div style="padding:14px 50px 0;">
                        <p data-role="summary" style="margin:0 0 12px;font-size:9.5pt;text-align:center;color:#555;font-style:italic;line-height:1.6;max-width:600px;margin-left:auto;margin-right:auto;">${data.summary}</p>
                        <hr style="border:none;border-top:1px solid #e0ddd5;margin:0;">
                    </div>
                </div>

                <div style="padding:14px 50px 30px;">

                    ${S.experience !== false ? `
                    <section data-role="experience" style="margin-bottom:12px;">
                        <h4 style="font-size:10pt;text-transform:uppercase;letter-spacing:3px;color:${gold};margin:0 0 8px;font-weight:400;">Experience</h4>
                        ${(data.experience||[]).map((exp,i) => `
                            <div style="margin-bottom:10px;break-inside:avoid;">
                                <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                    <strong style="font-size:10.5pt;font-weight:700;">${exp.role}</strong>
                                    <span style="font-size:9pt;color:#999;font-style:italic;">${exp.duration}</span>
                                </div>
                                <div style="font-size:9pt;color:${gold};margin-bottom:2px;">${exp.company}</div>
                                <ul style="margin:0;padding-left:14px;font-size:9pt;color:#444;list-style-type:none;">
                                    ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;line-height:1.45;padding-left:8px;border-left:1px solid #e0ddd5;">${pt}</li>`).join('')}
                                </ul>
                            </div>`).join('')}
                    </section>` : ''}

                    ${S.projects !== false ? projectsBlock(data.projects,'exec') : ''}

                    <div data-section="skills">${skillSections(data,'exec',S)}</div>

                    ${S.education !== false ? `
                    <section data-section="education-cert" style="margin-bottom:8px;break-inside:avoid;">
                        <h4 style="font-size:10pt;text-transform:uppercase;letter-spacing:3px;color:${gold};margin:0 0 6px;font-weight:400;">Education</h4>
                        ${(data.education||[]).map((ed,i) => `
                            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;font-size:9.5pt;">
                                <strong>${ed.degree}</strong>
                                <span style="color:#999;font-style:italic;">${ed.institution}, ${ed.year}</span>
                            </div>`).join('')}
                    </section>` : ''}

                    ${S.certifications !== false && (data.certifications||[]).length ? `
                    <section data-section="education-cert" style="break-inside:avoid;">
                        <h4 style="font-size:10pt;text-transform:uppercase;letter-spacing:3px;color:${gold};margin:0 0 6px;font-weight:400;">Certifications</h4>
                        ${(data.certifications||[]).map((c,i) => `
                            <div style="font-size:9pt;margin-bottom:3px;color:#555;padding-left:10px;border-left:1px solid ${gold};">
                                ${c}
                            </div>`).join('')}
                    </section>` : ''}
                </div>

            </div>
        </div>`;
    },
};
