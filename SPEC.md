# Specification: Lab Report Structured Extractor (MVP)

## 1. Problem Statement & Scope

### Problem Statement
Clinical lab reports are delivered in inconsistent layouts, tabulations, and terminologies across different providers. Patients cannot track their physiological metrics across time without manually compiling data into spreadsheets. Existing digital solutions require uploading highly sensitive personal health information (PHI) to third-party cloud engines. 

### Scope
To deliver a robust offline MVP under hackathon constraints, scope boundaries are defined as follows:

*   **In-Scope:**
    *   Printed or digitally generated lab reports in PDF or image format (PNG, JPEG).
    *   Standard tabular lab panels with columns representing: Test Name, Result/Value, Unit, Reference Range, and Abnormal Flag.
    *   Standard panels in English (e.g., Complete Blood Count (CBC), Lipid Panel, Thyroid Panel, Basic Metabolic Panel).
    *   Single-page or multi-page documents where tables have standard boundaries.
*   **Out-of-Scope:**
    *   Handwritten reports or handwriting annotations.
    *   Non-tabular reports (e.g., narrative diagnostic scans, genomic sequencing reports, imaging summaries).
    *   Non-English reports.
    *   Active integration with live electronic health record (EHR) systems (e.g., FHIR).

---

## 2. Data Schema (JSON Output)

Every parsed lab record is structured and validated against the following schema before storage.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LabReport",
  "type": "object",
  "properties": {
    "report_date": {
      "type": "string",
      "format": "date",
      "description": "Date of lab report (YYYY-MM-DD)"
    },
    "source_lab": {
      "type": ["string", "null"],
      "description": "Name of the issuing laboratory (optional)"
    },
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "test_name": {
            "type": "string",
            "description": "Cleaned, standardized name of the test"
          },
          "value": {
            "type": "number",
            "description": "Numerical measurement result"
          },
          "unit": {
            "type": "string",
            "description": "Unit of measurement (e.g., mg/dL, g/dL, mIU/L)"
          },
          "reference_range": {
            "type": "string",
            "description": "The expected healthy reference range as printed (e.g., 4.0 - 11.0, <100)"
          },
          "flag": {
            "type": "string",
            "enum": ["Normal", "H", "L"],
            "description": "Abnormal flag: H (High), L (Low), or Normal"
          }
        },
        "required": ["test_name", "value", "unit", "reference_range", "flag"]
      }
    },
    "summary": {
      "type": ["string", "null"],
      "description": "Optional local-LLM generated plain English summary of doctor notes/impressions"
    }
  },
  "required": ["report_date", "results"]
}
```

---

## 3. Functional Requirements

*   **FR1: Document Upload & Preprocessing**
    *   The user must be able to upload PDF or image files (PNG/JPEG) through a Streamlit drag-and-drop interface.
    *   PDF files must be converted to images locally at 300 DPI for optimal OCR resolution.
*   **FR2: Offline OCR Extraction**
    *   System must extract text blocks and layout parameters locally using Tesseract OCR via `pytesseract`.
    *   No external OCR services (e.g., Google Cloud Vision, AWS Textract) shall be reached.
*   **FR3: Deterministic Tabular Parsing**
    *   System must parse OCR text outputs into structured fields using regular expressions targeting column positions and keyword rules.
    *   System must extract: `test_name`, raw `value`, `unit`, and `reference_range`.
*   **FR4: Normalization & Automatic Flag Detection**
    *   System must automatically extract or compute the abnormal flag (`H` or `L`) by parsing the `reference_range` (e.g., `4.5 - 11.0` or `< 130`) and checking if the numerical `value` falls outside these bounds.
    *   If the source document explicitly lists an abnormal flag (e.g., a separate column with `*` or `H`/`L`), the parser should match and verify this.
*   **FR5: SQLite Storage & Persistence**
    *   Extracted reports must be saved to a local SQLite database (`lab_history.db`).
    *   Database must store the report metadata, individual parsed measurements, and path references to the uploaded files.
*   **FR6: Local Streamlit Trends Dashboard**
    *   The UI must provide an interactive trend chart showing historical values for a selected test (e.g., TSH levels over the last 3 visits).
    *   Users must be able to filter by test name and view visual indicators when values cross reference bounds.
*   **FR7: Optional LLM Note Summarizer**
    *   The UI must include an input field for free-text doctor remarks.
    *   When requested, the application must run a local quantized model (Qwen2.5-1.5B/Llama-3.2-3B) via `llama.cpp` wrapper to translate clinical jargon into plain English.

---

## 4. Non-Functional Requirements

*   **NFR1: Strict Privacy / 100% Offline operation**
    *   The application must function completely with network cards/Wi-Fi disabled. There must be zero HTTP requests to external domains during processing.
*   **NFR2: CPU-Only Target**
    *   All parsing, database transaction, OCR, and optional LLM inference must run on standard x86/ARM CPUs. No GPU acceleration or CUDA runtime is required.
*   **NFR3: Performance Boundaries**
    *   OCR and Regex extraction for a single-page document must complete within 8 seconds on a standard modern CPU.
    *   Optional LLM summarization (using a 1.5B or 3B model at Q4 quantization) must complete within 25 seconds on a CPU (minimum speed: 5 tokens/sec).
*   **NFR4: Extensibility**
    *   The parser rules must be modularized so that new lab layouts can be added as simple regex dictionaries.

---

## 5. Success Criteria for the MVP Demo (Phase 2 Validation)

To declare the Phase 2 MVP successful, the following sequence must run end-to-end:
1.  **Environment Preparation:** Turn off Wi-Fi/unplug network interfaces.
2.  **Ingestion:** Upload a sample de-identified multi-column CBC lab report PDF.
3.  **OCR & Parse:** Hit "Extract" in the Streamlit UI. Under 10 seconds, the screen must display a fully filled, editable data grid containing the correct test names, numeric values, and units.
4.  **Verification:** The computed flags (`H`/`L`) in the database matches the printed boundaries of the input test sheet.
5.  **Analytics:** The UI successfully plots the newly uploaded value alongside mock historical values in a clean line graph.
