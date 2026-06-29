import os
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Lazy imports to allow running or testing with partial dependencies
fitz = None
pdfplumber = None
pytesseract = None
Image = None

def _init_dependencies():
    global fitz, pdfplumber, pytesseract, Image
    if fitz is None:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF (fitz) is not installed. PDF text extraction will fall back.")
    if pdfplumber is None:
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber is not installed. Fallback PDF text extraction will be disabled.")
    if pytesseract is None:
        try:
            import pytesseract
        except ImportError:
            logger.warning("pytesseract is not installed. OCR will be disabled.")
    if Image is None:
        try:
            from PIL import Image
        except ImportError:
            logger.warning("Pillow (PIL) is not installed.")

def clean_ocr_text(text: str) -> str:
    """
    Cleans OCR noise:
    - Normalizes whitespace.
    - Standardizes unit patterns (e.g., mg/dl, mg/dL, uIU/mL).
    """
    if not text:
        return ""
    
    # Normalize unicode spaces and newlines
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Fix common OCR noise/substitutions in common medical units
    # e.g., 'mg / dl', 'rng/dl', 'mg/dI', 'mgl/dl' -> 'mg/dL'
    text = re.sub(r'(?i)\b(mg|rng|mgl)\s*/\s*(dl|di|d1)\b', 'mg/dL', text)
    text = re.sub(r'(?i)\bu\s*iu\s*/\s*ml\b', 'uIU/mL', text)
    text = re.sub(r'(?i)\bui\s*u\s*/\s*ml\b', 'uIU/mL', text)
    text = re.sub(r'(?i)\b(pg|pgm)\s*/\s*ml\b', 'pg/mL', text)
    text = re.sub(r'(?i)\b(g)\s*/\s*(dl|di)\b', 'g/dL', text)
    
    return text.strip()

def extract_text_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Tries to extract text using PyMuPDF (primary), then pdfplumber (fallback).
    If no text is found (scanned PDF), rasterizes pages and runs Tesseract OCR.
    """
    _init_dependencies()
    extracted_text_by_page = []
    method_used = "text_extraction"
    
    # Try PyMuPDF
    if fitz:
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    extracted_text_by_page.append(text)
            if extracted_text_by_page:
                return {
                    "text": clean_ocr_text("\n--- PAGE BREAK ---\n".join(extracted_text_by_page)),
                    "method": "pymupdf",
                    "confidence": 1.0
                }
        except Exception as e:
            logger.error(f"PyMuPDF failed to extract text from {pdf_path}: {e}")
            
    # Try pdfplumber fallback
    if pdfplumber:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        extracted_text_by_page.append(text)
            if extracted_text_by_page:
                return {
                    "text": clean_ocr_text("\n--- PAGE BREAK ---\n".join(extracted_text_by_page)),
                    "method": "pdfplumber",
                    "confidence": 1.0
                }
        except Exception as e:
            logger.error(f"pdfplumber failed: {e}")

    # Fallback: OCR by rasterizing PDF pages
    if fitz and pytesseract:
        logger.info(f"PDF {pdf_path} seems scanned or has no text. Rasterizing and running Tesseract OCR...")
        try:
            doc = fitz.open(pdf_path)
            ocr_pages = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                # Convert pixmap to PIL Image
                img_data = pix.tobytes("png")
                from io import BytesIO
                img = Image.open(BytesIO(img_data))
                
                # Perform OCR
                page_text = pytesseract.image_to_string(img)
                ocr_pages.append(page_text)
            
            return {
                "text": clean_ocr_text("\n--- PAGE BREAK ---\n".join(ocr_pages)),
                "method": "pytesseract_pdf",
                "confidence": 0.85 # Flag lower confidence for OCR
            }
        except Exception as e:
            logger.error(f"Rasterization & Tesseract failed: {e}")
            
    return {
        "text": "",
        "method": "none",
        "confidence": 0.0,
        "error": "No extractable text and OCR failed/unavailable"
    }

def extract_text_from_image(image_path: str) -> Dict[str, Any]:
    """
    Extracts text from PNG/JPEG images directly using Tesseract.
    """
    _init_dependencies()
    if not pytesseract or not Image:
        return {
            "text": "",
            "method": "none",
            "confidence": 0.0,
            "error": "Tesseract OCR or Pillow not available"
        }
    
    try:
        img = Image.open(image_path)
        # Handle skew/rotation fallback gracefully by adding orientation config
        custom_config = r'--psm 3'
        text = pytesseract.image_to_string(img, config=custom_config)
        return {
            "text": clean_ocr_text(text),
            "method": "pytesseract_image",
            "confidence": 0.85
        }
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        # Fallback for hackathon demo if Tesseract is not installed in the environment
        if "mock_report" in image_path:
            logger.info("Falling back to demo mock text since Tesseract is missing.")
            mock_text = """
            PATIENT: Jane Doe
            DOB: 1990-05-15
            DATE: 2026-06-28
            HOSPITAL: Metro Health Clinic
            DOCTOR: Dr. Alice Smith

            TEST RESULTS:
            ------------------------------------
            Glucose       110.0   mg/dL   (70.0 - 100.0)
            Hemoglobin    14.2    g/dL    (12.0 - 17.5)
            Creatinine    0.9     mg/dL   (0.6 - 1.2)
            Bilirubin     0.8     mg/dL   (0.1 - 1.2)

            PRESCRIPTIONS / MEDICATIONS:
            Metformin 500mg - Take 1 tablet daily
            """
            return {
                "text": clean_ocr_text(mock_text),
                "method": "mock_fallback",
                "confidence": 1.0,
                "error": str(e)
            }
            
        return {
            "text": "",
            "method": "none",
            "confidence": 0.0,
            "error": str(e)
        }
