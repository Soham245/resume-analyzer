import PyPDF2
import io
import logging

logger = logging.getLogger(__name__)

def extract_text(file):
    try:
        # 1. SAFE FILE HANDLING
        # Read the file directly into a BytesIO stream to prevent reading limits
        # and duplicate operations later
        file_bytes = file.read()
        pdf_stream = io.BytesIO(file_bytes)
        
        pdf_reader = PyPDF2.PdfReader(pdf_stream)
        
        # 2. CONTROL PDF PARSING
        # Limit to 5 pages max to avoid hanging on massive documents
        max_pages = min(len(pdf_reader.pages), 5)
        
        text_chunks = []
        for i in range(max_pages):
            page = pdf_reader.pages[i]
            extracted = page.extract_text()
            if extracted:
                text_chunks.append(extracted)
        
        # 4. OPTIMIZE STRING BUILDING
        text = "\n".join(text_chunks)
        
        # 3. LIMIT TEXT SIZE
        # Cap text payload length to 6000 characters
        if len(text) > 6000:
            logger.info("Truncating PDF text to 6000 characters.")
            text = text[:6000]
            
        return text
    except Exception as e:
        logger.error(f"Error reading PDF: {e}", exc_info=True)
        return f"Error reading PDF: {e}"