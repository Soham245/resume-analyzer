from playwright.sync_api import sync_playwright

def generate_pdf_from_html(html_content):
    """Renders HTML to a pixel-perfect PDF using Headless Chromium."""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        page = browser.new_page()

        page.set_content(
            html_content,
            wait_until="networkidle"
        )

        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={
                "top": "0",
                "right": "0",
                "bottom": "0",
                "left": "0"
            }
        )

        browser.close()

        return pdf_bytes