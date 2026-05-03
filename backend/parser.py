import io
import logging

import PyPDF2

logger = logging.getLogger(__name__)

MAX_PAGES = 2
MAX_TEXT_CHARS = 3000


def extract_text(file):
    try:
        pdf_stream = io.BytesIO(file.read())
        pdf_reader = PyPDF2.PdfReader(pdf_stream)

        text_chunks = []
        total_chars = 0
        max_pages = min(len(pdf_reader.pages), MAX_PAGES)

        for page_index in range(max_pages):
            extracted = pdf_reader.pages[page_index].extract_text() or ""
            if not extracted:
                continue

            remaining = MAX_TEXT_CHARS - total_chars
            if remaining <= 0:
                break

            clipped = extracted[:remaining]
            text_chunks.append(clipped)
            total_chars += len(clipped)

            if total_chars >= MAX_TEXT_CHARS:
                logger.info("Stopped PDF parsing after reaching %s characters.", MAX_TEXT_CHARS)
                break

        return "\n".join(text_chunks)[:MAX_TEXT_CHARS]
    except Exception as exc:
        logger.error("Error reading PDF: %s", exc, exc_info=True)
        return f"Error reading PDF: {exc}"
