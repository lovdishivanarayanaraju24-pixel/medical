import pytest
import os
import sys

# Add backend directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ocr.extractor import clean_ocr_text
from app.llm.extractor import validate_json_schema
from app.analysis.flag_detector import detect_abnormal_flag

def test_ocr_text_cleaning():
    raw_text = "The glucose level was 98 mg / dl, TSH was 2.5 u iu / ml, Hemoglobin 14.5 rng/dl"
    cleaned = clean_ocr_text(raw_text)
    
    assert "mg/dL" in cleaned
    assert "uIU/mL" in cleaned
    assert "mg/dL" in cleaned
    assert " / " not in cleaned

def test_json_schema_validation():
    valid_data = {
        "patient": {
            "name": "Jane Doe",
            "dob": "1990-01-01",
            "gender": "Female",
            "contact_info": None
        },
        "report_type": "lab",
        "hospital": "City Hospital",
        "doctor": "Dr. Smith",
        "report_date": "2026-06-28",
        "results": [
            {
                "test_name": "Glucose",
                "value": 95.0,
                "unit": "mg/dL",
                "reference_range_low": 70.0,
                "reference_range_high": 100.0
            }
        ],
        "medications": []
    }
    
    invalid_data = {
        "patient": {
            "dob": "1990-01-01"
        },
        "report_type": "invalid_type",
        "results": []
    }
    
    assert validate_json_schema(valid_data) is True
    assert validate_json_schema(invalid_data) is False

def test_flag_detection():
    # Test high
    res_high = detect_abnormal_flag("glucose", 110.0, 70.0, 100.0)
    assert res_high["flag"] == "high"
    
    # Test critical high (value >= 100 * 1.3)
    res_crit_high = detect_abnormal_flag("glucose", 135.0, 70.0, 100.0)
    assert res_crit_high["flag"] == "critical"
    
    # Test low
    res_low = detect_abnormal_flag("glucose", 65.0, 70.0, 100.0)
    assert res_low["flag"] == "low"
    
    # Test critical low (value <= 70 * 0.7)
    res_crit_low = detect_abnormal_flag("glucose", 45.0, 70.0, 100.0)
    assert res_crit_low["flag"] == "critical"
    
    # Test normal
    res_normal = detect_abnormal_flag("glucose", 85.0, 70.0, 100.0)
    assert res_normal["flag"] == "normal"

def test_reference_range_fallback():
    # Test standard glucose check
    res = detect_abnormal_flag("Blood Glucose Level", 110.0)
    assert res["reference_range_low"] == 70.0
    assert res["reference_range_high"] == 100.0
    assert res["category"] == "glucose"
    assert res["flag"] == "high"
    
    # Test default fallback for completely unknown test
    res_unknown = detect_abnormal_flag("SuperUnknownTestX", 50.0)
    assert res_unknown["reference_range_low"] == 0.0
    assert res_unknown["reference_range_high"] == 100.0
    assert res_unknown["flag"] == "normal"
