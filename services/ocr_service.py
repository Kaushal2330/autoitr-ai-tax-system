import os
import platform
import shutil
import logging

import pytesseract
from PIL import Image
import pdfplumber
import fitz  # PyMuPDF
import cv2
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# If Tesseract is not in PATH, set it manually (Windows example):
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class OCRService:
    def __init__(self):
        # Auto-detect Tesseract on Windows if not in PATH
        self.tesseract_available = False
        if platform.system().lower().startswith("win"):
            if not shutil.which("tesseract"):
                common_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
                ]
                for candidate in common_paths:
                    if os.path.exists(candidate):
                        pytesseract.pytesseract.tesseract_cmd = candidate
                        logger.info(f"Using Tesseract at: {candidate}")
                        self.tesseract_available = True
                        break
            else:
                self.tesseract_available = True
        
        # Test Tesseract availability
        try:
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
            self.tesseract_available = False

    def extract_text(self, file_path):
        """
        Extract text from a PDF or image file.
        Handles:
        - PDFs with text layers
        - Scanned PDFs (OCR fallback)
        - Image files (OCR with preprocessing)
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return ""
                
            if file_path.lower().endswith('.pdf'):
                return self._extract_from_pdf(file_path)
            else:
                return self._extract_from_image(file_path)
        except Exception as e:
            logger.error(f"OCR failed for {file_path}: {e}")
            return ""

    def _extract_from_pdf(self, pdf_path):
        """Extract text from PDF. Use text layer, then OCR fallback via rasterization."""
        try:
            extracted_text_parts = []

            # Pass 1: Try text layer via pdfplumber
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_number, page in enumerate(pdf.pages, start=1):
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            logger.info(f"Extracted text from page {page_number} using text layer.")
                            extracted_text_parts.append(page_text)
                        else:
                            logger.info(f"No text layer on page {page_number}")
            except Exception as e:
                logger.warning(f"pdfplumber failed reading text: {e}")

            # If some text found already and seems sufficient, return it
            prelim_text = "\n".join(extracted_text_parts).strip()
            if len(prelim_text) >= 20:
                return prelim_text

            # Pass 2: Try vector text extraction via PyMuPDF as another non-OCR attempt
            try:
                doc = fitz.open(pdf_path)
                pymupdf_text_parts = []
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    t = page.get_text("text")
                    if t and t.strip():
                        pymupdf_text_parts.append(t)
                doc.close()
                if pymupdf_text_parts:
                    combined = "\n".join(pymupdf_text_parts).strip()
                    if len(combined) >= 20:
                        logger.info("Extracted text via PyMuPDF text layer.")
                        return combined
            except Exception as e:
                logger.warning(f"PyMuPDF text extraction failed: {e}")

            # Pass 3: OCR fallback by rasterizing pages with PyMuPDF at high DPI
            if not self.tesseract_available:
                logger.warning("Tesseract not available, skipping OCR fallback")
                return ""
                
            try:
                doc = fitz.open(pdf_path)
                ocr_text_parts = []
                # Limit to first 5 pages to prevent hanging
                max_pages = min(len(doc), 5)
                for page_index in range(max_pages):
                    page = doc[page_index]
                    zoom = 200 / 72.0  # Reduced DPI for performance
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)

                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    processed = self._preprocess_pil_for_ocr(img)

                    ocr_text = self._run_best_ocr(processed)
                    if ocr_text.strip():
                        ocr_text_parts.append(ocr_text)
                doc.close()

                combined_ocr = "\n".join(ocr_text_parts).strip()
                return combined_ocr
            except Exception as e:
                logger.error(f"OCR fallback failed for {pdf_path}: {e}")
                return ""
        except Exception as e:
            logger.error(f"PDF extraction failed for {pdf_path}: {e}")
            return ""

    def _extract_from_image(self, image_path):
        """Extract text from image with robust preprocessing before OCR."""
        try:
            if not self.tesseract_available:
                logger.warning("Tesseract not available, cannot process image")
                return ""
                
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Could not read image: {image_path}")
                return ""

            # Resize large images to prevent memory issues
            height, width = img.shape[:2]
            if width > 2000 or height > 2000:
                scale = min(2000/width, 2000/height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height))

            # Grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Noise reduction
            denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

            # Adaptive thresholding (more robust for uneven lighting)
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
            )

            # Deskew before resizing
            deskewed = self._deskew(thresh)

            # Resize for small fonts
            scale_percent = 150  # Reduced for performance
            width = int(deskewed.shape[1] * scale_percent / 100)
            height = int(deskewed.shape[0] * scale_percent / 100)
            resized = cv2.resize(deskewed, (width, height), interpolation=cv2.INTER_LINEAR)

            pil_img = Image.fromarray(resized)
            text = self._run_best_ocr(pil_img)
            return text.strip()
        except Exception as e:
            logger.error(f"Image OCR failed for {image_path}: {e}")
            return ""

    def _preprocess_pil_for_ocr(self, pil_image: Image.Image) -> Image.Image:
        """Convert PIL Image to high-contrast binarized image for OCR."""
        cv_img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
        )
        # Deskew before resizing
        deskewed = self._deskew(thresh)
        scale_percent = 170
        width = int(deskewed.shape[1] * scale_percent / 100)
        height = int(deskewed.shape[0] * scale_percent / 100)
        resized = cv2.resize(deskewed, (width, height), interpolation=cv2.INTER_LINEAR)
        return Image.fromarray(resized)

    def _deskew(self, bin_img: np.ndarray) -> np.ndarray:
        """Estimate skew angle using Hough transform and correct it."""
        try:
            edges = cv2.Canny(bin_img, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=200)
            if lines is None:
                return bin_img
            angles = []
            for rho_theta in lines[:50]:
                rho, theta = rho_theta[0]
                angle = (theta * 180 / np.pi) - 90
                if -45 < angle < 45:
                    angles.append(angle)
            if not angles:
                return bin_img
            median_angle = float(np.median(angles))
            if abs(median_angle) < 0.5:
                return bin_img
            h, w = bin_img.shape[:2]
            center = (w // 2, h // 2)
            rot_mat = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(bin_img, rot_mat, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            return rotated
        except Exception:
            return bin_img

    def _run_best_ocr(self, pil_img: Image.Image) -> str:
        """Run OCR with multiple PSMs and return text from the best-confidence run."""
        if not self.tesseract_available:
            return ""
            
        psm_values = [6, 4]  # Reduced to prevent hanging
        best_text = ""
        best_conf = -1.0
        
        for psm in psm_values:
            config = f"--oem 3 --psm {psm}"
            try:
                # Try simple string extraction first (faster)
                text = pytesseract.image_to_string(pil_img, lang="eng", config=config)
                if text.strip():
                    # Simple scoring based on length and content
                    score = len(text.strip())
                    if score > best_conf:
                        best_conf = score
                        best_text = text
            except Exception as e:
                logger.warning(f"OCR failed for PSM {psm}: {e}")
                continue
                
        return best_text
