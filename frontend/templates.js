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
                <span contenteditable="true" style="flex:1;overflow-wrap:break-word;font-size:9pt;">${f.val}</span>
                <button class="block-ctrl" data-action="remove-contact" data-field="${f.key}"
                    style="flex-shrink:0;background:none;border:none;cursor:pointer;color:#475569;font-size:10px;line-height:1;padding:0;" title="Remove">×</button>
            </div>`).join('');
    }

    const fSize   = style === 'ats' ? '9.5pt' : '9pt';
    const color   = style === 'ats' ? 'color:#111;' : 'color:#64748b;';
    const justify = style === 'ats' ? 'center' : 'flex-start';
    return `<div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:${justify};gap:8px;font-size:${fSize};${color}margin-top:3px;">
        ${fields.map(f => `<span style="display:inline-flex;align-items:center;gap:3px;">
            <span style="opacity:0.6;display:flex;align-items:center;">${f.icon}</span>
            <span contenteditable="true">${f.val}</span>
            <button class="block-ctrl" data-action="remove-contact" data-field="${f.key}"
                style="background:none;border:none;cursor:pointer;color:#94a3b8;font-size:10px;line-height:1;padding:0 1px;" title="Remove">×</button>
        </span>`).join('')}
    </div>`;
}

// ── Per-entry delete button ───────────────────────────────────────────────
function delBtn(action, idx) {
    return `<button class="block-ctrl" data-action="${action}" data-index="${idx}"
        style="background:none;border:1px solid #d1d5db;border-radius:3px;cursor:pointer;
        color:#94a3b8;font-size:9px;line-height:1;padding:1px 4px;opacity:0.5;margin-left:5px;flex-shrink:0;"
        title="Remove">×</button>`;
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
            <h4 contenteditable="true" style="${h4}">Technical Skills</h4>
            ${hasGroups ? `
            <div style="margin:0 0 18px;">
                ${Object.entries(groups).map(([k,items]) =>
                    `<p style="font-size:9pt;margin:0 0 3px;line-height:1.4;"><span style="color:#94a3b8;text-transform:uppercase;font-size:8pt;letter-spacing:0.3px;">${grpLabels[k]||k}: </span>${items.join(', ')}</p>`
                ).join('')}
            </div>` : `
            <ul contenteditable="true" style="list-style:none;padding:0;margin:0 0 18px;font-size:9.5pt;">
                ${technical.map(s => `<li style="margin-bottom:3px;">${s}</li>`).join('')}
            </ul>`}` : ''}
            ${soft.length ? `
            <h4 contenteditable="true" style="${h4}">Soft Skills</h4>
            <ul contenteditable="true" style="list-style:none;padding:0;margin:0 0 18px;font-size:9.5pt;">
                ${soft.map(s => `<li style="margin-bottom:3px;">${s}</li>`).join('')}
            </ul>` : ''}
            ${languages.length ? `
            <h4 contenteditable="true" style="${h4}">Languages</h4>
            <ul contenteditable="true" style="list-style:none;padding:0;margin:0 0 18px;font-size:9.5pt;">
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
            <h4 contenteditable="true" style="${hStyle}">Technical Skills</h4>
            ${hasGroups
                ? Object.entries(groups).map(([k,items]) =>
                    `<p style="${pStyle}margin-bottom:1px;"><strong>${grpLabels[k]||k}:</strong> ${items.join(sep)}</p>`
                  ).join('')
                : `<p contenteditable="true" style="${pStyle}">${technical.join(sep)}</p>`
            }
        </div>` : ''}
        ${soft.length      ? `<div style="${w}"><h4 contenteditable="true" style="${hStyle}">Soft Skills</h4><p contenteditable="true" style="${pStyle}">${soft.join(sep)}</p></div>` : ''}
        ${languages.length ? `<div style="${w}"><h4 contenteditable="true" style="${hStyle}">Languages</h4><p contenteditable="true" style="${pStyle}">${languages.join(sep)}</p></div>` : ''}`;
}


// ── Projects block ────────────────────────────────────────────────────────
function projectsBlock(projects, style) {
    if (!projects || !projects.length) return '';

    if (style === 'ats') return `
        <section data-role="projects" style="margin-bottom:8px;">
            <h4 contenteditable="true" style="text-transform:uppercase;font-size:11pt;border-bottom:1px solid #111;margin:0 0 5px;">Projects</h4>
            ${projects.map((p,i) => `
                <div style="margin-bottom:8px;break-inside:avoid;">
                    <div style="display:flex;justify-content:space-between;align-items:center;font-weight:bold;font-size:10pt;">
                        <span contenteditable="true" data-bind="projects[${i}].title">${p.title}</span>
                        <span style="display:flex;align-items:center;">
                            <span contenteditable="true" style="font-weight:normal;font-style:italic;font-size:9pt;">${(p.tech_stack||[]).join(', ')}</span>
                            ${delBtn('remove-proj',i)}
                        </span>
                    </div>
                    <ul contenteditable="true" style="margin:0;padding-left:15px;font-size:9pt;" data-bind="projects[${i}].points" data-bind-type="array">
                        ${(p.points||[]).slice(0,3).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                    </ul>
                </div>`).join('')}
        </section>`;

    if (style === 'exec') return `
        <section data-role="projects" style="margin-bottom:8px;">
            <h4 contenteditable="true" style="font-size:11pt;color:#1e293b;border-bottom:2px solid #e2e8f0;margin:0 0 5px;padding-bottom:2px;text-transform:uppercase;">Projects</h4>
            ${projects.map((p,i) => `
                <div style="margin-bottom:8px;break-inside:avoid;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span contenteditable="true" style="font-weight:bold;font-size:10.5pt;" data-bind="projects[${i}].title">${p.title}</span>
                        <span style="display:flex;align-items:center;">
                            <span contenteditable="true" style="color:#2563eb;font-size:9pt;">${(p.tech_stack||[]).join(', ')}</span>
                            ${delBtn('remove-proj',i)}
                        </span>
                    </div>
                    <ul contenteditable="true" style="margin:0;padding-left:15px;font-size:9.5pt;color:#334155;" data-bind="projects[${i}].points" data-bind-type="array">
                        ${(p.points||[]).slice(0,3).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                    </ul>
                </div>`).join('')}
        </section>`;

    if (style === 'tech') return `
        <div data-role="projects" style="margin-bottom:8px;">
            <h4 contenteditable="true" style="color:#10b981;text-transform:uppercase;font-size:10pt;border-bottom:1px solid #e2e8f0;padding-bottom:2px;margin:0 0 5px;">Projects</h4>
            ${projects.map((p,i) => `
                <div style="margin-bottom:8px;break-inside:avoid;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong contenteditable="true" style="font-size:10.5pt;" data-bind="projects[${i}].title">${p.title}</strong>
                        <span style="display:flex;align-items:center;">
                            <span contenteditable="true" style="color:#64748b;font-size:9pt;">${(p.tech_stack||[]).join(' · ')}</span>
                            ${delBtn('remove-proj',i)}
                        </span>
                    </div>
                    <ul contenteditable="true" style="margin:0;padding-left:15px;font-size:9.5pt;" data-bind="projects[${i}].points" data-bind-type="array">
                        ${(p.points||[]).slice(0,3).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                    </ul>
                </div>`).join('')}
        </div>`;

    if (style === 'sidebar') return `
        <div data-role="projects" style="margin-bottom:13px;">
            <h4 contenteditable="true" style="text-transform:uppercase;font-size:10pt;color:#0f172a;border-bottom:2px solid #e2e8f0;margin:0 0 7px;padding-bottom:3px;">Projects</h4>
            ${projects.map((p,i) => `
                <div style="margin-bottom:11px;break-inside:avoid;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong contenteditable="true" style="font-size:10pt;" data-bind="projects[${i}].title">${p.title}</strong>
                        <span style="display:flex;align-items:center;">
                            <span contenteditable="true" style="color:#64748b;font-size:9pt;">${(p.tech_stack||[]).join(' · ')}</span>
                            ${delBtn('remove-proj',i)}
                        </span>
                    </div>
                    <ul contenteditable="true" style="margin:0;padding-left:15px;font-size:9.5pt;" data-bind="projects[${i}].points" data-bind-type="array">
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

                <header style="text-align:center;border-bottom:1.5px solid #111;padding-bottom:6px;margin-bottom:8px;flex-shrink:0;">
                    <h1 contenteditable="true" style="margin:0;font-size:23pt;text-transform:uppercase;line-height:1.1;" data-bind="name">${data.name}</h1>
                    <h3 contenteditable="true" style="margin:2px 0 0;font-size:12pt;font-weight:normal;line-height:1.2;" data-bind="title">${data.title}</h3>
                    ${contactBlock(data, 'ats')}
                </header>

                <section data-role="summary" style="margin-bottom:6px;">
                    <p contenteditable="true" style="margin:0;text-align:justify;font-size:9.5pt;" data-bind="summary">${data.summary}</p>
                </section>

                ${skillSections(data, 'ats', S)}

                ${S.experience !== false ? `
                <section data-role="experience" style="margin-bottom:8px;">
                    <h4 contenteditable="true" style="text-transform:uppercase;font-size:11pt;border-bottom:1px solid #111;margin:0 0 5px;">Professional Experience</h4>
                    ${(data.experience||[]).map((exp,i) => `
                        <div style="margin-bottom:8px;break-inside:avoid;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;font-weight:bold;font-size:10pt;">
                                <span contenteditable="true" data-bind="experience[${i}].role">${exp.role}</span>
                                <span style="display:flex;align-items:center;">
                                    <span contenteditable="true" style="font-weight:normal;font-size:9pt;" data-bind="experience[${i}].duration">${exp.duration}</span>
                                    ${delBtn('remove-exp',i)}
                                </span>
                            </div>
                            <div contenteditable="true" style="font-style:italic;font-size:9pt;margin-bottom:1px;" data-bind="experience[${i}].company">${exp.company}</div>
                            <ul contenteditable="true" style="margin:0;padding-left:14px;font-size:9pt;" data-bind="experience[${i}].points" data-bind-type="array">
                                ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                            </ul>
                        </div>`).join('')}
                </section>` : ''}

                ${S.projects !== false ? projectsBlock(data.projects,'ats') : ''}

                ${S.education !== false ? `
                <section style="margin-bottom:8px;break-inside:avoid;">
                    <h4 contenteditable="true" style="text-transform:uppercase;font-size:11pt;border-bottom:1px solid #111;margin:0 0 5px;">Education</h4>
                    ${(data.education||[]).map((ed,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:9.5pt;margin-bottom:1px;">
                            <strong contenteditable="true" data-bind="education[${i}].degree">${ed.degree}</strong>
                            <span style="display:flex;align-items:center;">
                                <span contenteditable="true">${ed.institution} | ${ed.year}</span>
                                ${delBtn('remove-edu',i)}
                            </span>
                        </div>`).join('')}
                </section>` : ''}

                ${S.certifications !== false && (data.certifications||[]).length ? `
                <section style="break-inside:avoid;">
                    <h4 contenteditable="true" style="text-transform:uppercase;font-size:11pt;border-bottom:1px solid #111;margin:0 0 5px;">Certifications & Achievements</h4>
                    ${(data.certifications||[]).map((c,i) => `
                        <div style="display:flex;align-items:center;font-size:9pt;margin-bottom:1px;gap:3px;">
                            <span style="flex:1;display:flex;align-items:baseline;gap:3px;"><span style="flex-shrink:0;">•</span><span contenteditable="true" data-bind="certifications[${i}]">${c}</span></span>
                            ${delBtn('remove-cert',i)}
                        </div>`).join('')}
                </section>` : ''}

            </div>
        </div>`;
    },

    // 2. Executive ────────────────────────────────────────────────────────
    executive: (data, S) => {
        S = S || {};
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;background:white;box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target" style="width:794px;padding:40px;box-sizing:border-box;font-family:Arial,sans-serif;color:#222;line-height:1.25;transform-origin:top left;">

                <header style="margin-bottom:10px;border-left:5px solid #2563eb;padding-left:12px;flex-shrink:0;">
                    <h1 contenteditable="true" style="margin:0;font-size:23pt;color:#1e293b;line-height:1.1;" data-bind="name">${data.name}</h1>
                    <h3 contenteditable="true" style="margin:1px 0 0;font-size:13pt;color:#2563eb;line-height:1.2;" data-bind="title">${data.title}</h3>
                    ${contactBlock(data, 'exec')}
                </header>

                <p contenteditable="true" data-role="summary" style="margin:0 0 8px;text-align:justify;font-size:9.5pt;color:#334155;" data-bind="summary">${data.summary}</p>

                ${S.experience !== false ? `
                <section data-role="experience" style="margin-bottom:8px;">
                    <h4 contenteditable="true" style="font-size:11pt;color:#1e293b;border-bottom:2px solid #e2e8f0;margin:0 0 5px;padding-bottom:2px;text-transform:uppercase;">Experience</h4>
                    ${(data.experience||[]).map((exp,i) => `
                        <div style="margin-bottom:8px;break-inside:avoid;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;font-weight:bold;font-size:10pt;">
                                <span contenteditable="true" data-bind="experience[${i}].role">${exp.role}</span>
                                <span style="display:flex;align-items:center;">
                                    <span contenteditable="true" style="color:#64748b;font-weight:normal;font-size:9pt;" data-bind="experience[${i}].duration">${exp.duration}</span>
                                    ${delBtn('remove-exp',i)}
                                </span>
                            </div>
                            <div contenteditable="true" style="color:#2563eb;font-size:9pt;font-weight:bold;margin-bottom:1px;" data-bind="experience[${i}].company">${exp.company}</div>
                            <ul contenteditable="true" style="margin:0;padding-left:14px;font-size:9pt;color:#334155;" data-bind="experience[${i}].points" data-bind-type="array">
                                ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                            </ul>
                        </div>`).join('')}
                </section>` : ''}

                ${S.projects !== false ? projectsBlock(data.projects,'exec') : ''}

                ${skillSections(data,'exec',S)}

                ${S.education !== false ? `
                <section style="margin-bottom:7px;break-inside:avoid;">
                    <h4 contenteditable="true" style="font-size:11pt;color:#1e293b;border-bottom:2px solid #e2e8f0;margin:0 0 5px;padding-bottom:2px;text-transform:uppercase;">Education</h4>
                    ${(data.education||[]).map((ed,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:1px;font-size:9.5pt;color:#334155;">
                            <span><strong contenteditable="true" data-bind="education[${i}].degree">${ed.degree}</strong> &bull; <span contenteditable="true">${ed.institution}, ${ed.year}</span></span>
                            ${delBtn('remove-edu',i)}
                        </div>`).join('')}
                </section>` : ''}

                ${S.certifications !== false && (data.certifications||[]).length ? `
                <section style="break-inside:avoid;">
                    <h4 contenteditable="true" style="font-size:11pt;color:#1e293b;border-bottom:2px solid #e2e8f0;margin:0 0 5px;padding-bottom:2px;text-transform:uppercase;">Certifications & Achievements</h4>
                    ${(data.certifications||[]).map((c,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1px;font-size:9pt;color:#334155;">
                            <span contenteditable="true" data-bind="certifications[${i}]">${c}</span>
                            ${delBtn('remove-cert',i)}
                        </div>`).join('')}
                </section>` : ''}

            </div>
        </div>`;
    },

    // 3. Tech Modern ──────────────────────────────────────────────────────
    tech_modern: (data, S) => {
        S = S || {};
        return `
        <div class="resume-wrapper" style="width:794px;height:1123px;overflow:hidden;position:relative;background:white;box-sizing:border-box;margin:0 auto;box-shadow:0 4px 24px rgba(0,0,0,0.18);">
            <div class="resume-scale-target" style="width:794px;padding:40px;box-sizing:border-box;font-family:sans-serif;color:#1e293b;line-height:1.25;transform-origin:top left;">

                <div style="border-left:4px solid #10b981;padding-left:12px;margin-bottom:10px;flex-shrink:0;">
                    <h1 contenteditable="true" style="margin:0;font-size:23pt;font-weight:800;line-height:1.1;" data-bind="name">${data.name}</h1>
                    <h3 contenteditable="true" style="margin:1px 0 0;font-size:12pt;color:#10b981;text-transform:uppercase;letter-spacing:1px;line-height:1.2;" data-bind="title">${data.title}</h3>
                    ${contactBlock(data, 'tech')}
                </div>

                <p contenteditable="true" data-role="summary" style="margin:0 0 8px;font-size:9.5pt;text-align:justify;" data-bind="summary">${data.summary}</p>

                ${S.experience !== false ? `
                <div data-role="experience" style="margin-bottom:8px;">
                    <h4 contenteditable="true" style="color:#10b981;text-transform:uppercase;font-size:10pt;border-bottom:1px solid #e2e8f0;padding-bottom:2px;margin:0 0 5px;">Experience</h4>
                    ${(data.experience||[]).map((exp,i) => `
                        <div style="margin-bottom:8px;break-inside:avoid;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                <strong contenteditable="true" style="font-size:10.5pt;" data-bind="experience[${i}].role">${exp.role}</strong>
                                <span style="display:flex;align-items:center;">
                                    <span contenteditable="true" style="color:#64748b;font-size:9pt;">${exp.company} | ${exp.duration}</span>
                                    ${delBtn('remove-exp',i)}
                                </span>
                            </div>
                            <ul contenteditable="true" style="margin:0;padding-left:14px;font-size:9pt;" data-bind="experience[${i}].points" data-bind-type="array">
                                ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                            </ul>
                        </div>`).join('')}
                </div>` : ''}

                ${S.projects !== false ? projectsBlock(data.projects,'tech') : ''}

                ${skillSections(data,'tech',S)}

                ${S.education !== false ? `
                <div style="margin-bottom:7px;">
                    <h4 contenteditable="true" style="color:#10b981;text-transform:uppercase;font-size:10pt;border-bottom:1px solid #e2e8f0;padding-bottom:2px;margin:0 0 5px;">Education</h4>
                    ${(data.education||[]).map((ed,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:9.5pt;margin-bottom:1px;">
                            <span contenteditable="true"><strong>${ed.degree}</strong> &mdash; ${ed.institution} (${ed.year})</span>
                            ${delBtn('remove-edu',i)}
                        </div>`).join('')}
                </div>` : ''}

                ${S.certifications !== false && (data.certifications||[]).length ? `
                <section style="break-inside:avoid;">
                    <h4 contenteditable="true" style="color:#10b981;text-transform:uppercase;font-size:10pt;border-bottom:1px solid #e2e8f0;padding-bottom:2px;margin:0 0 5px;">Certifications & Achievements</h4>
                    ${(data.certifications||[]).map((c,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1px;font-size:9pt;">
                            <span contenteditable="true" data-bind="certifications[${i}]">${c}</span>
                            ${delBtn('remove-cert',i)}
                        </div>`).join('')}
                </section>` : ''}

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
                    <h1 contenteditable="true" data-bind="name" style="font-size:25pt;font-weight:700;line-height:1.15;margin:0 0 4px;color:#f8fafc;">${data.name}</h1>
                    <p contenteditable="true" data-bind="title" style="font-size:10.5pt;color:#94a3b8;font-weight:400;margin:0 0 14px;line-height:1.3;">${data.title}</p>

                    <div class="t4-sb-section">
                        <h4 style="text-transform:uppercase;font-size:9pt;letter-spacing:0.5px;color:#cbd5e1;border-bottom:1px solid #334155;margin:0 0 6px;padding-bottom:3px;">Contact</h4>
                        <div style="font-size:9.5pt;color:#94a3b8;">
                            ${contactBlock(data,'sidebar')}
                        </div>
                    </div>

                    ${skillSections(data,'sidebar',S)}
                </div>

                <!-- Main content (72%) -->
                <div class="t4-main">

                    <div data-role="summary" class="t4-section">
                        <h4 class="t4-section-head">Profile</h4>
                        <p contenteditable="true" data-bind="summary" style="margin:0;font-size:10.5pt;line-height:1.45;text-align:justify;">${data.summary}</p>
                    </div>

                    ${S.experience !== false ? `
                    <div data-role="experience" class="t4-section">
                        <h4 class="t4-section-head">Experience</h4>
                        ${(data.experience||[]).map((exp,i) => `
                        <div style="margin-bottom:8px;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                <strong contenteditable="true" data-bind="experience[${i}].role" style="font-size:11pt;">${exp.role}</strong>
                                ${delBtn('remove-exp',i)}
                            </div>
                            <div style="font-size:10pt;color:#64748b;margin-bottom:3px;">
                                <span contenteditable="true" data-bind="experience[${i}].company">${exp.company}</span>
                                <span> · </span>
                                <span contenteditable="true" data-bind="experience[${i}].duration">${exp.duration}</span>
                            </div>
                            <ul contenteditable="true" data-bind="experience[${i}].points" data-bind-type="array" style="margin:0;padding-left:14px;font-size:10pt;">
                                ${(exp.points||[]).slice(0,2).map(pt=>`<li style="margin-bottom:3px;">${pt}</li>`).join('')}
                            </ul>
                        </div>`).join('')}
                    </div>` : ''}

                    ${S.projects !== false ? projectsBlock(data.projects,'sidebar') : ''}

                    ${S.education !== false && (data.education||[]).length ? `
                    <div class="t4-section">
                        <h4 class="t4-section-head">Education</h4>
                        ${(data.education||[]).map((ed,i) => `
                        <div style="margin-bottom:6px;">
                            <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                <strong contenteditable="true" data-bind="education[${i}].degree" style="font-size:10.5pt;">${ed.degree}</strong>
                                ${delBtn('remove-edu',i)}
                            </div>
                            <div style="font-size:10pt;color:#64748b;">
                                <span contenteditable="true">${ed.institution}</span><span> · ${ed.year}</span>
                            </div>
                        </div>`).join('')}
                    </div>` : ''}

                    ${S.certifications !== false && (data.certifications||[]).length ? `
                    <div class="t4-section">
                        <h4 class="t4-section-head">Certifications & Achievements</h4>
                        ${(data.certifications||[]).map((c,i) => `
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;font-size:10pt;">
                            <span contenteditable="true" data-bind="certifications[${i}]">${c}</span>
                            ${delBtn('remove-cert',i)}
                        </div>`).join('')}
                    </div>` : ''}

                </div>

            </div>
        </div>`;
    },
};
