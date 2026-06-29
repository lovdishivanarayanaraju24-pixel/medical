import os
import json
import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Schema definition for validation
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "patient": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "dob": {"type": ["string", "null"]},
                "gender": {"type": ["string", "null"]},
                "contact_info": {"type": ["string", "null"]}
            },
            "required": ["name"]
        },
        "report_type": {"type": "string", "enum": ["lab", "prescription", "discharge", "other"]},
        "hospital": {"type": ["string", "null"]},
        "doctor": {"type": ["string", "null"]},
        "report_date": {"type": ["string", "null"]},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "test_name": {"type": "string"},
                    "value": {"type": "number"},
                    "unit": {"type": ["string", "null"]},
                    "reference_range_low": {"type": ["number", "null"]},
                    "reference_range_high": {"type": ["number", "null"]}
                },
                "required": ["test_name", "value"]
            }
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "medicine_name": {"type": "string"},
                    "dosage": {"type": ["string", "null"]},
                    "frequency": {"type": ["string", "null"]},
                    "duration": {"type": ["string", "null"]},
                    "instructions": {"type": ["string", "null"]}
                },
                "required": ["medicine_name"]
            }
        }
    },
    "required": ["patient", "report_type", "results", "medications"]
}

# Simple manual validation helper to avoid external dependencies issues
def validate_json_schema(data: Any) -> bool:
    try:
        if not isinstance(data, dict):
            return False
        if "patient" not in data or not isinstance(data["patient"], dict):
            return False
        if "results" not in data or not isinstance(data["results"], list):
            return False
        if "medications" not in data or not isinstance(data["medications"], list):
            return False
        if "report_type" not in data or data["report_type"] not in ["lab", "prescription", "discharge", "other"]:
            return False
        
        # Validate patient name exists
        if "name" not in data["patient"]:
            return False
            
        # Validate result objects
        for r in data["results"]:
            if not isinstance(r, dict) or "test_name" not in r or "value" not in r:
                return False
            if not isinstance(r["value"], (int, float)):
                return False
                
        # Validate medication objects
        for m in data["medications"]:
            if not isinstance(m, dict) or "medicine_name" not in m:
                return False
        return True
    except Exception:
        return False

class LocalLLMExtractor:
    def __init__(self, model_name: str = "Phi-3-mini-4k-instruct-Q4_K_M.gguf"):
        self.model_name = model_name
        self.models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../models")
        self.model_path = os.path.join(self.models_dir, model_name)
        self.llm = None
        
    def _load_model(self):
        if self.llm is not None:
            return
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model file not found at {self.model_path}. Please download it using the setup script."
            )
            
        try:
            from llama_cpp import Llama
            logger.info(f"Loading local LLM model from {self.model_path}...")
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=4096,
                n_threads=4,
                verbose=False
            )
            logger.info("Local LLM model loaded successfully.")
        except ImportError:
            logger.error("llama-cpp-python is not installed. Running in mock/simulation mode.")
            raise ImportError("llama-cpp-python is not installed.")

    def extract_structured_data(self, cleaned_text: str) -> Dict[str, Any]:
        """
        Runs local LLM to perform entity extraction with strict JSON enforcement and retry validation loops.
        """
        try:
            self._load_model()
        except (FileNotFoundError, ImportError, Exception) as e:
            logger.warning(f"Using fallback heuristic extractor due to LLM load failure: {e}")
            return self._fallback_extraction_heuristic(cleaned_text)
        
        prompt = self._generate_prompt(cleaned_text)
        
        retries = 2
        last_error = ""
        
        while retries >= 0:
            try:
                # Call model
                logger.info(f"Invoking local LLM (Attempts remaining: {retries})...")
                output = self.llm(
                    prompt,
                    max_tokens=1024,
                    temperature=0.1,
                    stop=["<|end|>", "###"]
                )
                response_text = output["choices"][0]["text"]
                
                # Parse JSON
                extracted_json = self._clean_and_parse_json(response_text)
                
                # Validate schema
                if validate_json_schema(extracted_json):
                    logger.info("JSON schema validated successfully.")
                    return extracted_json
                else:
                    raise ValueError("JSON parsed successfully but failed schema validation.")
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Extraction attempt failed: {last_error}")
                retries -= 1
                if retries >= 0:
                    # Provide correction prompt feedback
                    prompt = self._generate_correction_prompt(prompt, response_text if 'response_text' in locals() else "", last_error)
        
        # If all retries fail, return the best effort structured data or fallback
        logger.error(f"LLM extraction failed after retries. Last error: {last_error}")
        return self._fallback_extraction_heuristic(cleaned_text)

    def _generate_prompt(self, text: str) -> str:
        schema_str = json.dumps(EXTRACTION_SCHEMA, indent=2)
        return f"""<|system|>
You are a medical intelligence extractor. Analyze the clinical document below and output a strict JSON document following this schema:
{schema_str}
Do not output any text other than valid JSON. Do not include markdown codeblocks or comments.
<|user|>
Extract structured details from this clinical text:
\"\"\"
{text}
\"\"\"
<|assistant|>
"""

    def _generate_correction_prompt(self, original_prompt: str, bad_output: str, error_msg: str) -> str:
        return f"""{original_prompt}{bad_output}
<|user|>
The output was invalid: {error_msg}.
Please output valid JSON matching the schema exactly. Correct the formatting.
<|assistant|>
"""

    def _clean_and_parse_json(self, text: str) -> Dict[str, Any]:
        # Extract markdown json block if model wrapped it
        match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.DOTALL)
        if match:
            text = match.group(1)
        
        # Strip potential garbage before first { and after last }
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx+1]
            
        return json.loads(text)

    def _fallback_extraction_heuristic(self, text: str) -> Dict[str, Any]:
        """
        Pure Python backup regex extractor for when LLM is unavailable or repeatedly errors.
        """
        logger.info("Running heuristic regex-based clinical parser fallback.")
        patient_name = "Unknown Patient"
        # Try to find common patient indicators
        name_match = re.search(r'(?i)\b(?:patient name)\b[\s:]*([A-Za-z]+(?: [A-Za-z]+){0,3})', text)
        if not name_match:
            name_match = re.search(r'(?i)\b(?:patient|name)\b[\s:]*([A-Za-z]+(?: [A-Za-z]+){0,3})', text)
        if name_match:
            extracted_name = name_match.group(1).strip()
            if extracted_name.lower() not in ["information", "id", "age", "name", "patient", "field"]:
                patient_name = extracted_name

        # Try to extract Hospital (removed 'laboratory' and 'lab' to avoid catching 'Lab Ref No')
        hospital = None
        hosp_match = re.search(r'(?i)\b(?:hospital|clinic|center|centre)\b[\s:]*([A-Za-z]+(?: [A-Za-z]+){0,3})', text)
        if hosp_match:
            hospital = hosp_match.group(1).strip()

        # Try to extract Doctor
        doctor = None
        doc_match = re.search(r'(?i)\b(?:doctor|physician|consultant)\b[\s:]*([A-Za-z\.]+(?: [A-Za-z\.]+){0,3})', text)
        if doc_match:
            doctor = doc_match.group(1).strip()

        # Try to extract Date (DD-Mon-YYYY or YYYY-MM-DD)
        report_date = None
        date_match = re.search(r'(?i)\bdate\b[\s:]*(\d{1,2}[\s\-]+[A-Za-z]+[\s\-]+\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})', text)
        if date_match:
            report_date = date_match.group(1).strip()
        else:
            any_date = re.search(r'(?i)(\d{1,2}[\s\-]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-]+\d{2,4}|\b\d{4}[-/]\d{2}[-/]\d{2}\b|\b\d{2}[-/]\d{2}[-/]\d{4}\b)', text)
            if any_date:
                report_date = any_date.group(1).strip()
            
        results = []
        # Find common lab patterns: name value unit reference
        matches = re.finditer(
            r'(?i)\b([a-zA-Z ]+)\b\s+(\d+(?:\.\d+)?)\s*(mg/dL|g/dL|uIU/mL|pg/mL|%)\s*(?:[\(\[]\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*[\)\]])?',
            text
        )
        for m in matches:
            name = m.group(1).strip()
            if len(name) < 3 or name.lower() in ["range", "value", "level", "result", "normal", "high", "low"]:
                continue
            val = float(m.group(2))
            unit = m.group(3)
            low = float(m.group(4)) if m.group(4) else None
            high = float(m.group(5)) if m.group(5) else None
            
            results.append({
                "test_name": name,
                "value": val,
                "unit": unit,
                "reference_range_low": low,
                "reference_range_high": high
            })
            
        # Parse medications
        meds = []
        med_matches = re.finditer(r'(?i)\b(?:rx|medication|tablet|capsule|take)\b\s*([A-Za-z ]+)\s+(\d+\s*(?:mg|ml|mcg|tab))', text)
        for mm in med_matches:
            meds.append({
                "medicine_name": mm.group(1).strip(),
                "dosage": mm.group(2).strip(),
                "frequency": "Once daily",
                "duration": None,
                "instructions": None
            })
            
        return {
            "patient": {
                "name": patient_name,
                "dob": None,
                "gender": None,
                "contact_info": None
            },
            "report_type": "lab" if results else "prescription",
            "hospital": hospital,
            "doctor": doctor,
            "report_date": report_date,
            "results": results,
            "medications": meds
        }
