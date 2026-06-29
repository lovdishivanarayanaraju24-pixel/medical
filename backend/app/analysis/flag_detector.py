import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Standard healthy reference ranges bundled for fallbacks
STANDARD_REFERENCE_RANGES = {
    "glucose": {"low": 70.0, "high": 100.0, "unit": "mg/dL", "category": "glucose"},
    "cholesterol": {"low": 0.0, "high": 200.0, "unit": "mg/dL", "category": "lipid"},
    "hemoglobin": {"low": 12.0, "high": 17.5, "unit": "g/dL", "category": "blood"},
    "creatinine": {"low": 0.6, "high": 1.2, "unit": "mg/dL", "category": "kidney"},
    "tsh": {"low": 0.4, "high": 4.5, "unit": "uIU/mL", "category": "thyroid"},
    "bilirubin": {"low": 0.1, "high": 1.2, "unit": "mg/dL", "category": "liver"}
}

# Configuration for critical margin thresholds (clinical multipliers)
# E.g., value > high * (1 + high_critical_margin) OR value < low * (1 - low_critical_margin)
DEFAULT_CLINICAL_CONFIG = {
    "high_critical_multiplier": 1.3, # 30% above high limit is critical
    "low_critical_multiplier": 0.7   # 30% below low limit is critical
}

def detect_abnormal_flag(
    test_name: str,
    value: float,
    range_low: Optional[float] = None,
    range_high: Optional[float] = None,
    config: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Compares a numerical result against a reference range.
    Returns:
        {
            "flag": "normal" | "high" | "low" | "critical",
            "category": str,
            "range_low": float,
            "range_high": float
        }
    """
    cfg = config or DEFAULT_CLINICAL_CONFIG
    test_key = test_name.lower().strip()
    
    # Fallback to standard reference range if none provided
    category = "general"
    resolved_low = range_low
    resolved_high = range_high
    
    # Look for partial matches in bundled list
    for key, spec in STANDARD_REFERENCE_RANGES.items():
        if key in test_key:
            category = spec["category"]
            if resolved_low is None:
                resolved_low = spec["low"]
            if resolved_high is None:
                resolved_high = spec["high"]
            break
            
    # Default range fallback if absolutely nothing is specified
    if resolved_low is None:
        resolved_low = 0.0
    if resolved_high is None:
        resolved_high = 100.0 # Standard safety boundary
        
    flag = "normal"
    
    # Detect high bounds
    if value > resolved_high:
        crit_high_boundary = resolved_high * cfg.get("high_critical_multiplier", 1.3)
        if value >= crit_high_boundary:
            flag = "critical"
        else:
            flag = "high"
            
    # Detect low bounds
    elif value < resolved_low:
        crit_low_boundary = resolved_low * cfg.get("low_critical_multiplier", 0.7)
        if value <= crit_low_boundary:
            flag = "critical"
        else:
            flag = "low"
            
    return {
        "flag": flag,
        "category": category,
        "reference_range_low": resolved_low,
        "reference_range_high": resolved_high
    }
