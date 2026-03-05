import pdfplumber
import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class PDFProcessor:
    def is_encrypted(self, pdf_path: str) -> bool:
        try:
            with fitz.open(pdf_path) as doc:
                return doc.needs_pass
        except Exception:
            return False

    def unlock_pdf(self, pdf_path: str, password: str) -> str:
        """Attempt to unlock an encrypted PDF and save a temporary decrypted copy. Returns new path."""
        try:
            doc = fitz.open(pdf_path)
            if not doc.needs_pass:
                return pdf_path
            ok = doc.authenticate(password)
            if not ok:
                raise ValueError("Invalid password for PDF")
            # Save a decrypted temporary file alongside original
            unlocked_path = pdf_path.replace('.pdf', '_unlocked.pdf')
            doc.save(unlocked_path)
            doc.close()
            return unlocked_path
        except Exception as e:
            logging.getLogger(__name__).error(f"Unlock PDF failed: {e}")
            raise
    def extract_text_direct(self, pdf_path):
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            return ""
