"""Stage 0.5 verification suite — automates the Stage 0 validation matrix.

One command:

    python tools/verify_suite.py            # full matrix (app + all PDF exports)
    python tools/verify_suite.py --skip-pdf # fast app-level checks only

Architecture
────────────
The suite drives the REAL application, not a reimplementation:

  1. Serves frontend/ on an ephemeral local port.
  2. Opens it in headless Chromium (Playwright, already a backend dep).
  3. Stubs ONLY the AI endpoint (/generate-from-inputs) via route
     interception — everything downstream (response handling, render,
     autofit, sticky header, mobile fit, export payload construction)
     is production code.
  4. Clicks the real Download button per template; intercepts the real
     /generate-pdf request to capture the exact payload the frontend
     built, and answers the page with a tiny fake PDF so the UI flow
     completes.
  5. After the browser closes, converts every captured payload with the
     real backend generate_pdf_from_html() and validates the PDFs.

Validated per template (x2 page modes):
  - PDF generated, %PDF magic, non-trivial size
  - Expected page count (1-page mode -> 1; overflow 2-page mode -> >=2;
    sidebar templates are single-page by design -> 1)
  - Text extractability (ATS): content probes present across all pages
  - Section-heading ORDER parity: headings captured from the rendered
    DOM appear in the same order in the extracted PDF text
    (presence-only for the two-column sidebar template, where PDF
    text-extraction column order is not guaranteed)

Data-preservation guard (S0-2 regression):
  - The REAL backend fallback path (AI forced to fail via invalid key)
    must preserve every populated input section — experience, projects,
    education, certifications, skills. Any populated section coming
    back empty fails the suite.
  - Rendered-UI check: a sentinel from every section of the stub
    profile (incl. summary) must appear in the rendered document.

App-level checks:
  - Manual-entry -> generate -> builder opens with content
  - Render integrity (A4 wrapper, scale target, non-empty text)
  - Sticky header: zero height delta between normal/stuck (the Stage 0
    jitter root cause), no autonomous flips parked at the threshold
  - No unexpected nested vertical scroll containers in the builder
  - Mobile 390px: zoom mode pans, fit mode fully fits, no horizontal
    body overflow
  - Zero console errors / pageerrors / [app-error] lines during the run

Exit code 0 = all pass; 1 = failures (summary table printed either way).
"""

import argparse
import functools
import io
import re
import socket
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import PyPDF2

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

# ── Profiles served by the AI-endpoint stub ─────────────────────────────────
_BASE = {
    "name": "Priya Sharma", "title": "Full Stack Developer",
    "email": "priya.sharma@email.com", "phone": "+91 98765 43210",
    "linkedin": "linkedin.com/in/priyasharma", "github": "github.com/priyasharma",
    "technical_skills": ["JavaScript", "TypeScript", "React", "Node.js",
                         "PostgreSQL", "Redis", "AWS", "Docker"],
    "soft_skills": ["Leadership", "Communication", "Mentoring"],
    "languages": ["English", "Hindi"],
    "skill_groups": {"programming": ["JavaScript", "TypeScript"],
                     "frameworks": ["React", "Node.js"],
                     "databases": ["PostgreSQL", "Redis"],
                     "tools": ["AWS", "Docker"]},
    "education": [{"degree": "B.Tech Computer Science",
                   "institution": "IIT Delhi", "year": "2019-2023"}],
    "certifications": ["AWS Solutions Architect Associate (2024)", "CKA (2023)"],
    "_generation_ok": True,
    "_generation_meta": {"ok": True, "model_used": "stub", "attempts": 1,
                         "fallback_model_used": False, "duration_ms": 1},
}

STANDARD_PROFILE = dict(_BASE, summary=(
    "Full stack developer with 3+ years building high-scale commerce systems."),
    experience=[
        {"role": "Software Engineer", "company": "Flipkart", "duration": "2023-Present",
         "points": ["Built checkout microservices handling 2M daily transactions",
                    "Designed idempotent payment retry pipeline"]},
        {"role": "SDE Intern", "company": "Amazon", "duration": "Summer 2022",
         "points": ["Shipped inventory reconciliation tool used by 40 teams"]},
    ],
    projects=[
        {"title": "PayTrack", "tech_stack": ["React", "Node.js", "PostgreSQL"],
         "points": ["Real-time expense tracker with 5k users"]},
        {"title": "DevDash", "tech_stack": ["Next.js", "Redis"],
         "points": ["CI/CD analytics dashboard, 200+ GitHub stars"]},
    ])

OVERFLOW_PROFILE = dict(_BASE, summary=(
    "Full stack developer with 3+ years building high-scale commerce systems "
    "across payments, logistics, and analytics platforms."),
    experience=[
        {"role": f"Software Engineer {i+1}",
         "company": ["Flipkart", "Amazon", "Google", "Stripe", "Razorpay", "Swiggy"][i],
         "duration": f"{2018+i}-{2019+i}",
         "points": ["Built checkout microservices handling 2M daily transactions",
                    "Designed idempotent payment retry pipeline that cut failures 18%",
                    "Mentored 3 junior engineers; added contract testing to 6 services"]}
        for i in range(6)],
    projects=[
        {"title": f"Project {i+1}", "tech_stack": ["React", "Node.js", "PostgreSQL"],
         "points": ["Real-time system with 5k users", "Sub-100ms websocket sync"]}
        for i in range(6)])

TEXT_PROBES = ["Priya Sharma", "Flipkart", "IIT Delhi", "CKA (2023)"]

# ── Data-preservation guard (S0-2 regression) ───────────────────────────────
# Raw manual-entry inputs with a distinct sentinel value per section. Fed to
# the REAL backend generate_resume_from_inputs() with AI forced to fail
# (invalid key), which exercises the fallback path where S0-2 silently
# discarded experience/projects/education/certifications. Any populated
# source section coming back empty is a regression and fails the suite.
# (The manual form has no summary input, so summary is asserted on the
# UI-render check below instead — there is nothing to preserve here.)
PRESERVATION_INPUTS = {
    "name": "Guard Tester", "title": "Preservation Engineer",
    "email": "guard@example.com", "phone": "+1 555 0100",
    "linkedin": "linkedin.com/in/guard", "github": "github.com/guard",
    "experience_text": ("Platform Engineer, SentinelCorp, 2020-Present\n"
                        "Kept the sentinel dataset intact across 4 releases"),
    "projects_text": "GuardRail | Python, Flask | Regression tripwire project",
    "education_text": "M.Sc Data Systems, Sentinel University, 2015-2017",
    "certifications_text": "Certified Sentinel Keeper (2021)",
    "technical_skills": ["Python", "Flask"],
    "soft_skills": ["Vigilance"],
    "languages": ["English"],
}
PRESERVATION_EXPECT = {
    "experience": "SentinelCorp",
    "projects": "GuardRail",
    "education": "Sentinel University",
    "certifications": "Certified Sentinel Keeper (2021)",
    "technical_skills": "Python",
    "soft_skills": "Vigilance",
    "languages": "English",
}

# Rendered-UI preservation: one sentinel per section from STANDARD_PROFILE
# must appear in the rendered resume text after a (stubbed) generation.
UI_SECTION_SENTINELS = {
    "summary": "high-scale commerce systems",
    "experience": "Flipkart",
    "projects": "PayTrack",
    "education": "IIT Delhi",
    "certifications": "CKA (2023)",
    "skills": "PostgreSQL",
}

# ── Check bookkeeping ───────────────────────────────────────────────────────
CHECKS = []


def record(name, ok, ms, detail=""):
    CHECKS.append({"name": name, "ok": bool(ok), "ms": int(ms), "detail": detail})
    mark = "PASS" if ok else "FAIL"
    line = f"  [{mark}] {name}  ({int(ms)} ms)"
    if detail and not ok:
        line += f"  -- {detail}"
    print(line, flush=True)


class _Timer:
    def __enter__(self):
        self.t0 = time.monotonic()
        return self

    def __exit__(self, *a):
        self.ms = (time.monotonic() - self.t0) * 1000


# ── Local static server ─────────────────────────────────────────────────────
class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs):  # silence per-request noise
        pass


def start_frontend_server():
    handler = functools.partial(_QuietHandler, directory=str(FRONTEND_DIR))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{port}/"


# ── Browser phase ───────────────────────────────────────────────────────────
def run_browser_phase(url, skip_pdf):
    """Drives the real UI. Returns (captured_exports, template_headings)."""
    captured = []            # {template, page_mode, html}
    headings = {}            # template -> [heading, ...] from live DOM
    console_faults = []
    stub_profile = {"data": STANDARD_PROFILE}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1400, "height": 900},
                                  accept_downloads=True)
        page = ctx.new_page()

        page.on("pageerror", lambda e: console_faults.append(f"pageerror: {e}"))
        page.on("console", lambda m: console_faults.append(f"console.{m.type}: {m.text}")
                if m.type == "error" or "[app-error]" in m.text else None)

        import json as _json

        def stub_generate(route):
            route.fulfill(status=200, content_type="application/json",
                          body=_json.dumps(stub_profile["data"]))

        def capture_pdf(route):
            body = route.request.post_data_json or {}
            captured.append({"template": body.get("template", "?"),
                             "page_mode": body.get("page_mode", "?"),
                             "html": body.get("html", "")})
            route.fulfill(status=200, content_type="application/pdf",
                          body=b"%PDF-1.4\n%%EOF")

        page.route("**/generate-from-inputs", stub_generate)
        page.route("**/generate-pdf", capture_pdf)

        page.goto(url, wait_until="networkidle")

        # ── Generate through the real manual-entry flow ────────────────────
        with _Timer() as t:
            page.click("#mode-manual")
            page.fill("#m-name", "Priya Sharma")
            page.fill("#m-title", "Full Stack Developer")
            page.click("#m-jd-gate-no")
            page.click("#generate-manual-btn")
            page.wait_for_selector("#resume-document .resume-wrapper", timeout=15000)
        ok = page.eval_on_selector("#resume-document", "el => el.innerText.includes('Flipkart')")
        record("app: manual entry -> generate -> builder renders", ok, t.ms)

        # ── Rendered-UI preservation: every section reaches the document ────
        with _Timer() as t:
            rendered = page.eval_on_selector(
                "#resume-document", "el => el.innerText.toLowerCase()")
            missing = [f"{sec} (sentinel '{sent}')"
                       for sec, sent in UI_SECTION_SENTINELS.items()
                       if sent.lower() not in rendered]
        record("preservation: all sections render in UI", not missing, t.ms,
               "; ".join(missing))

        # ── Render integrity ────────────────────────────────────────────────
        with _Timer() as t:
            integrity = page.evaluate("""() => {
                const w = document.querySelector('#resume-document .resume-wrapper');
                const s = document.querySelector('#resume-document .resume-scale-target');
                return { wrapper: !!w, scaler: !!s,
                         wrapperH: w ? w.offsetHeight : 0,
                         text: document.getElementById('resume-document').innerText.length };
            }""")
        record("app: render integrity (wrapper/scaler/A4 height/text)",
               integrity["wrapper"] and integrity["scaler"]
               and integrity["wrapperH"] >= 1000 and integrity["text"] > 300,
               t.ms, str(integrity))

        # ── Sticky header invariants ────────────────────────────────────────
        with _Timer() as t:
            sticky = page.evaluate("""() => {
                const h = document.getElementById('workspace-header');
                const was = h.classList.contains('workspace-header--stuck');
                h.classList.remove('workspace-header--stuck');
                const a = h.offsetHeight;
                h.classList.add('workspace-header--stuck');
                const b = h.offsetHeight;
                h.classList.toggle('workspace-header--stuck', was);
                return { delta: a - b };
            }""")
        record("app: sticky toggle causes zero reflow (height delta 0)",
               sticky["delta"] == 0, t.ms, f"delta={sticky['delta']}px")

        with _Timer() as t:
            flips = page.evaluate("""async () => {
                const sent = document.getElementById('workspace-header-sentinel');
                const thr = Math.round(sent.getBoundingClientRect().top + scrollY);
                scrollTo({ top: thr + 1, behavior: 'instant' });
                await new Promise(r => setTimeout(r, 250));
                let n = 0;
                const mo = new MutationObserver(ms => ms.forEach(m => {
                    if (m.attributeName === 'class') n++; }));
                mo.observe(document.getElementById('workspace-header'), { attributes: true });
                await new Promise(r => setTimeout(r, 1200));
                mo.disconnect();
                scrollTo({ top: 0, behavior: 'instant' });
                return n;
            }""")
        record("app: no autonomous sticky flips parked at threshold",
               flips == 0, t.ms, f"flips={flips}")

        with _Timer() as t:
            scrollers = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('#builder-section *').forEach(el => {
                    const cs = getComputedStyle(el);
                    if ((cs.overflowY === 'auto' || cs.overflowY === 'scroll')
                        && el.scrollHeight > el.clientHeight + 1)
                        out.push(el.className || el.id);
                });
                return out;
            }""")
        unexpected = [s for s in scrollers if "template-drawer__body" not in str(s)]
        record("app: single scroll container (no unexpected nested scrollers)",
               not unexpected, t.ms, f"unexpected={unexpected}")

        # ── Mobile preview ──────────────────────────────────────────────────
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        with _Timer() as t:
            mob = page.evaluate("""() => {
                const w = document.querySelector('#resume-document .resume-wrapper');
                const f = document.querySelector('.resume-frame');
                return { transform: w.style.transform,
                         pans: f.scrollWidth > f.clientWidth,
                         bodyOverflow: document.documentElement.scrollWidth > innerWidth };
            }""")
        record("mobile: zoom mode active and pannable, no body overflow",
               "scale" in mob["transform"] and mob["pans"] and not mob["bodyOverflow"],
               t.ms, str(mob))

        with _Timer() as t:
            page.click("#preview-zoom-btn")
            page.wait_for_timeout(350)
            fit = page.evaluate("""() => {
                const w = document.querySelector('#resume-document .resume-wrapper');
                const f = document.querySelector('.resume-frame');
                return { fits: w.getBoundingClientRect().width <= f.clientWidth + 1,
                         pan: f.scrollWidth - f.clientWidth };
            }""")
            page.click("#preview-zoom-btn")  # restore zoom default
        record("mobile: fit mode fully fits (zero pan)", fit["fits"] and fit["pan"] == 0,
               t.ms, str(fit))
        page.set_viewport_size({"width": 1400, "height": 900})
        page.wait_for_timeout(300)

        # ── Export payload capture per template x page mode ────────────────
        if not skip_pdf:
            template_ids = page.evaluate("() => Object.keys(ResumeTemplates)")

            def export_all(page_mode_label, profile):
                stub_profile["data"] = profile
                # The app is in the builder view after any prior generation —
                # navigate back to the (persisted) manual form to regenerate.
                if page.is_visible("#back-to-upload-btn"):
                    page.click("#back-to-upload-btn")
                    page.wait_for_timeout(500)
                page.click("#mode-manual")
                page.fill("#m-name", "Priya Sharma")
                page.fill("#m-title", "Full Stack Developer")
                if page.is_visible("#m-jd-gate-no"):
                    page.click("#m-jd-gate-no")
                page.click("#generate-manual-btn")
                page.wait_for_selector("#resume-document .resume-wrapper", timeout=15000)
                page.wait_for_timeout(700)
                pill = page.locator(".length-pill", has_text=page_mode_label).first
                pill.click()
                page.wait_for_timeout(300)
                cards = page.locator("#template-drawer .template-card")
                count = cards.count()
                for i in range(count):
                    cards.nth(i).click()
                    page.wait_for_timeout(400)
                    tpl_headings = page.evaluate("""() => {
                        const sel = '#resume-document h1,#resume-document h2,'
                                  + '#resume-document h3,#resume-document h4,'
                                  + '#resume-document .r-section-title';
                        return [...document.querySelectorAll(sel)]
                            .map(h => h.textContent.trim()).filter(Boolean);
                    }""")
                    n_before = len(captured)
                    page.click("#download-pdf-btn")
                    for _ in range(100):
                        if len(captured) > n_before:
                            break
                        page.wait_for_timeout(100)
                    if len(captured) > n_before:
                        headings[captured[-1]["template"]] = tpl_headings

            with _Timer() as t:
                export_all("1 Page", STANDARD_PROFILE)
            for c in captured:
                c.setdefault("profile", "standard")
            record(f"export: captured 1-page payloads ({len(captured)} templates)",
                   len(captured) == len(template_ids), t.ms,
                   f"got {len(captured)}, expected {len(template_ids)}")

            n1 = len(captured)
            with _Timer() as t:
                export_all("2 Pages", OVERFLOW_PROFILE)
            for c in captured:
                c.setdefault("profile", "overflow")
            record(f"export: captured 2-page payloads ({len(captured) - n1} templates)",
                   len(captured) - n1 == len(template_ids), t.ms)

        browser.close()

    faults = [f for f in console_faults]
    record("app: zero console errors / [app-error] lines", not faults, 0,
           "; ".join(faults[:3]))
    return captured, headings


# ── Generation phase (backend, no browser) ─────────────────────────────────
def run_generation_phase():
    """S0-2 regression guard: the fallback path must preserve every populated
    input section. AI is forced to fail with an invalid key, so this runs the
    real generate_resume_from_inputs() end to end without network luck."""
    import json as _json

    from backend.rewriter import generate_resume_from_inputs

    with _Timer() as t:
        result = generate_resume_from_inputs(PRESERVATION_INPUTS,
                                             "invalid-key-forces-fallback")
    ok = result.get("_generation_ok") is False
    record("preservation: fallback path engaged (_generation_ok=false)",
           ok, t.ms, f"_generation_ok={result.get('_generation_ok')}")

    lost = []
    for section, sentinel in PRESERVATION_EXPECT.items():
        value = result.get(section) or []
        if not value:
            lost.append(f"{section} is EMPTY")
        elif sentinel.lower() not in _json.dumps(value).lower():
            lost.append(f"{section} lost sentinel '{sentinel}'")
    record("preservation: all populated sections survive fallback",
           not lost, 0, "; ".join(lost))


# ── PDF phase ───────────────────────────────────────────────────────────────
def run_pdf_phase(captured, headings):
    from backend.pdf_generator import generate_pdf_from_html

    def collapse(s):
        # PDF text extraction is unreliable about spaces (kerned/styled runs can
        # merge or split words) — compare with all whitespace removed.
        return re.sub(r"\s+", "", s.lower())

    for item in captured:
        tpl, mode, html = item["template"], item["page_mode"], item["html"]
        label = f"pdf: {tpl} (page_mode={mode}, {item.get('profile', '?')})"
        # Detect the sidebar layout by its markup (class attribute), NOT a bare
        # substring — the payload embeds all resume CSS rules, so '.t4-layout'
        # appears in the <style> block of every template.
        is_sidebar = re.search(r'class="[^"]*\bt4-layout\b', html) is not None
        try:
            with _Timer() as t:
                pdf = generate_pdf_from_html(html)
            reader = PyPDF2.PdfReader(io.BytesIO(pdf))
            pages = len(reader.pages)
            text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
            flat = collapse(text)

            problems = []
            if not pdf.startswith(b"%PDF-"):
                problems.append("bad magic")
            if len(pdf) < 5000:
                problems.append(f"suspiciously small ({len(pdf)} bytes)")
            if mode == 1 or is_sidebar:
                if pages != 1:
                    problems.append(f"expected 1 page, got {pages}")
            else:
                if pages < 2:
                    problems.append(f"expected >=2 pages, got {pages}")
            # The sidebar template is a fixed single-page layout that truncates
            # overflowing content by design — the preview shows the identical
            # truncation plus the overflow-indicator warning, so export/preview
            # parity holds. Tail-content probes therefore don't apply to the
            # sidebar+overflow combination; core probes always do.
            skip_tail = is_sidebar and item.get("profile") == "overflow"
            for probe in TEXT_PROBES:
                is_tail_probe = probe == TEXT_PROBES[-1]
                if is_tail_probe and skip_tail:
                    continue
                if collapse(probe) not in flat:
                    problems.append(f"missing text probe: {probe}")

            tpl_heads = [h for h in headings.get(tpl, []) if len(h) > 2]
            missing = [h for h in tpl_heads if collapse(h) not in flat]
            if missing:
                problems.append(f"headings missing from PDF: {missing}")
            elif not is_sidebar and tpl_heads:
                pos = [flat.index(collapse(h)) for h in tpl_heads]
                if pos != sorted(pos):
                    problems.append("heading order differs between DOM and PDF")

            record(label, not problems, t.ms,
                   "; ".join(problems) if problems else f"{pages}p {len(pdf)}B")
        except Exception as exc:  # noqa: BLE001 — a failing export must not kill the suite
            record(label, False, 0, f"exception: {exc}")


def main():
    ap = argparse.ArgumentParser(description="Resume Analyzer verification suite")
    ap.add_argument("--skip-pdf", action="store_true",
                    help="app-level checks only (fast)")
    args = ap.parse_args()

    print("Resume Analyzer verification suite")
    print(f"frontend: {FRONTEND_DIR}")
    suite_start = time.monotonic()

    print("-- generation phase (fallback preservation) " + "-" * 14)
    run_generation_phase()

    server, url = start_frontend_server()
    try:
        print(f"serving on {url}\n-- browser phase " + "-" * 40)
        captured, headings = run_browser_phase(url, args.skip_pdf)
        if not args.skip_pdf:
            print(f"\n-- pdf phase ({len(captured)} exports) " + "-" * 28)
            run_pdf_phase(captured, headings)
    finally:
        server.shutdown()

    total_ms = int((time.monotonic() - suite_start) * 1000)
    passed = sum(1 for c in CHECKS if c["ok"])
    failed = [c for c in CHECKS if not c["ok"]]
    print("\n" + "=" * 60)
    print(f"RESULT: {passed}/{len(CHECKS)} checks passed in {total_ms / 1000:.1f}s")
    for c in failed:
        print(f"  FAILED: {c['name']} -- {c['detail']}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
