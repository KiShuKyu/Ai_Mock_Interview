import os
import pdfplumber

# ── Set your resume PDF filename here ─────────────────────────────────────────
_PDF_FILENAME = "VishalJha.pdf"

# Resolves to new_ai/image/VishalJha.pdf regardless of where you run from
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PDF_PATH = os.path.join(_THIS_DIR, "image", _PDF_FILENAME)
# ──────────────────────────────────────────────────────────────────────────────


def extract_text_from_pdf(pdf_path: str = DEFAULT_PDF_PATH) -> str:
    """Extract raw text from a PDF file using pdfplumber."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}\n"
            f"Make sure '{_PDF_FILENAME}' is inside the 'image/' folder "
            f"next to extractor.py"
        )
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()