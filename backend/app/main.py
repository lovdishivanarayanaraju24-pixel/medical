import os
import shutil
import sqlite3
import csv
import re
from io import StringIO
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.db.migrations import run_migrations, get_connection
from app.ocr.extractor import extract_text_from_pdf, extract_text_from_image
from app.llm.extractor import LocalLLMExtractor
from app.analysis.flag_detector import detect_abnormal_flag

# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "../../uploads")
DB_PATH = os.path.join(BASE_DIR, "../../medvault.db")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Run DB Migrations at Startup
run_migrations(DB_PATH)

app = FastAPI(title="MedVault AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Semantic search models helper (lazy loading)
sentence_transformer_model = None

def get_embedding(text: str) -> List[float]:
    global sentence_transformer_model
    if sentence_transformer_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            sentence_transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            # Fallback mock embedding if library not present or loading fails
            print(f"Embedding model fallback: {e}")
            import hashlib
            h = hashlib.md5(text.encode('utf-8')).digest()
            # return mock 384 dimensional list
            return [float(b) / 255.0 for b in h] * 24
            
    return sentence_transformer_model.encode(text).tolist()

def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    try:
        import numpy as np
        v1, v2 = np.array(vec1), np.array(vec2)
        dot = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return float(dot / (norm_v1 * norm_v2))
    except Exception:
        # manual calculation fallback
        dot = sum(a*b for a, b in zip(vec1, vec2))
        norm_a = sum(a*a for a in vec1) ** 0.5
        norm_b = sum(b*b for b in vec2) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

# --- Endpoints ---

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # OCR Extractor
        ext = os.path.splitext(file.filename)[1].lower()
        if ext == ".pdf":
            ocr_result = extract_text_from_pdf(temp_path)
        elif ext in [".png", ".jpg", ".jpeg"]:
            ocr_result = extract_text_from_image(temp_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")
            
        raw_text = ocr_result.get("text", "")
        if not raw_text.strip():
            error_msg = ocr_result.get("error", "No extractable text found. Ensure Tesseract OCR is installed for images.")
            raise HTTPException(status_code=400, detail=f"Text extraction failed: {error_msg}")
            
        # LLM Entity Extractor
        llm_extractor = LocalLLMExtractor()
        extracted_data = llm_extractor.extract_structured_data(raw_text)
        
        # Store to DB
        conn = get_connection(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Patient check or creation
        patient = extracted_data.get("patient", {})
        patient_name = patient.get("name") or "Unknown Patient"
        cursor.execute("SELECT id FROM patients WHERE name = ?", (patient_name,))
        p_row = cursor.fetchone()
        if p_row:
            patient_id = p_row["id"]
        else:
            cursor.execute(
                "INSERT INTO patients (name, dob, gender, contact_info) VALUES (?, ?, ?, ?)",
                (patient_name, patient.get("dob"), patient.get("gender"), patient.get("contact_info"))
            )
            patient_id = cursor.lastrowid
            
        # 2. Report creation
        cursor.execute(
            """INSERT INTO reports (patient_id, report_type, hospital, doctor, report_date, source_file_path, raw_ocr_text) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                patient_id,
                extracted_data.get("report_type", "lab"),
                extracted_data.get("hospital"),
                extracted_data.get("doctor"),
                extracted_data.get("report_date"),
                temp_path,
                raw_text
            )
        )
        report_id = cursor.lastrowid
        
        # 3. Test results
        results = extracted_data.get("results", [])
        for res in results:
            t_name = res.get("test_name", "Unknown Test")
            t_val = res.get("value")
            t_unit = res.get("unit")
            r_low = res.get("reference_range_low")
            r_high = res.get("reference_range_high")
            
            # Detect flag and category
            analysis = detect_abnormal_flag(t_name, t_val, r_low, r_high)
            
            cursor.execute(
                """INSERT INTO test_results (report_id, test_name, value, unit, reference_range_low, reference_range_high, flag, category)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report_id,
                    t_name,
                    t_val,
                    t_unit,
                    analysis["reference_range_low"],
                    analysis["reference_range_high"],
                    analysis["flag"],
                    analysis["category"]
                )
            )
            
        # 4. Medications
        medications = extracted_data.get("medications", [])
        for med in medications:
            cursor.execute(
                """INSERT INTO medications (report_id, medicine_name, dosage, frequency, duration, instructions)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    report_id,
                    med.get("medicine_name"),
                    med.get("dosage"),
                    med.get("frequency"),
                    med.get("duration"),
                    med.get("instructions")
                )
            )
            
        # 5. FTS5 Indexing
        fts_content = f"{patient_name} {extracted_data.get('hospital', '')} {extracted_data.get('doctor', '')} {raw_text}"
        cursor.execute("INSERT INTO reports_fts (report_id, content) VALUES (?, ?)", (report_id, fts_content))
        
        # 6. Embeddings semantic mapping
        vector = get_embedding(fts_content)
        import json
        vector_blob = json.dumps(vector).encode('utf-8')
        cursor.execute(
            "INSERT INTO embeddings (report_id, vector_blob, model_name) VALUES (?, ?, ?)",
            (report_id, vector_blob, "all-MiniLM-L6-v2")
        )
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "report_id": report_id,
            "patient_id": patient_id,
            "extracted_data": extracted_data
        }
        
    except Exception as e:
        logger.exception("Error processing document upload")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@app.get("/api/reports")
def list_reports(
    patient_id: Optional[int] = None,
    report_type: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT r.*, p.name as patient_name 
        FROM reports r 
        JOIN patients p ON r.patient_id = p.id
        WHERE 1=1
    """
    params = []
    if patient_id:
        query += " AND r.patient_id = ?"
        params.append(patient_id)
    if report_type:
        query += " AND r.report_type = ?"
        params.append(report_type)
        
    query += " ORDER BY r.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/reports/{id}")
def get_report_detail(id: int):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT r.*, p.name as patient_name FROM reports r JOIN patients p ON r.patient_id = p.id WHERE r.id = ?", (id,))
    report = cursor.fetchone()
    if not report:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found")
        
    cursor.execute("SELECT * FROM test_results WHERE report_id = ?", (id,))
    results = cursor.fetchall()
    
    cursor.execute("SELECT * FROM medications WHERE report_id = ?", (id,))
    medications = cursor.fetchall()
    
    conn.close()
    return {
        "report": dict(report),
        "results": [dict(r) for r in results],
        "medications": [dict(m) for m in medications]
    }

@app.get("/api/trends")
def get_health_trends(
    test_name: str = Query(..., description="Name of test to track trends"),
    patient_id: Optional[int] = Query(None, description="Optional patient ID to filter")
):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    
    query = """
        SELECT tr.value, tr.unit, tr.reference_range_low, tr.reference_range_high, tr.flag, r.report_date, r.hospital, r.id as report_id, r.patient_id
        FROM test_results tr
        JOIN reports r ON tr.report_id = r.id
        WHERE tr.test_name LIKE ?
    """
    params = [f"%{test_name}%"]
    
    if patient_id:
        query += " AND r.patient_id = ?"
        params.append(patient_id)
        
    query += " ORDER BY r.report_date ASC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/patients")
def get_patients():
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM patients ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/tests/unique")
def get_unique_tests(patient_id: Optional[int] = Query(None, description="Optional patient ID to filter unique tests")):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    if patient_id:
        cursor.execute(
            """SELECT DISTINCT tr.test_name 
               FROM test_results tr
               JOIN reports r ON tr.report_id = r.id
               WHERE r.patient_id = ?
               ORDER BY tr.test_name ASC""",
            (patient_id,)
        )
    else:
        cursor.execute("SELECT DISTINCT test_name FROM test_results ORDER BY test_name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [r["test_name"] for r in rows if r["test_name"]]

@app.get("/api/dashboard-stats")
def get_dashboard_stats(patient_id: Optional[int] = Query(None, description="Optional patient ID to filter stats")):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    
    # Base query filters
    where_clause = ""
    params = []
    if patient_id:
        where_clause = " WHERE patient_id = ?"
        params.append(patient_id)
        
    cursor.execute(f"SELECT count(*) as total_reports FROM reports{where_clause}", params)
    total_reports = cursor.fetchone()["total_reports"]
    
    # Get latest report date
    cursor.execute(f"SELECT max(report_date) as latest_date FROM reports{where_clause}", params)
    latest_report_date = cursor.fetchone()["latest_date"] or "N/A"
    
    # Get abnormal count and category statistics
    abnormal_query = """
        SELECT count(*) as abnormal_count 
        FROM test_results tr
        JOIN reports r ON tr.report_id = r.id
        WHERE tr.flag != 'normal'
    """
    category_query = """
        SELECT tr.category, count(*) as count
        FROM test_results tr
        JOIN reports r ON tr.report_id = r.id
    """
    if patient_id:
        abnormal_query += " AND r.patient_id = ?"
        category_query += " WHERE r.patient_id = ?"
        
    category_query += " GROUP BY tr.category"
    
    cursor.execute(abnormal_query, [patient_id] if patient_id else [])
    abnormal_count = cursor.fetchone()["abnormal_count"] or 0
    
    cursor.execute(category_query, [patient_id] if patient_id else [])
    cat_rows = cursor.fetchall()
    category_stats = {row["category"]: row["count"] for row in cat_rows if row["category"]}
    
    conn.close()
    
    # Health score calculation: start from 100, deduct 8 for each abnormal parameter (min 20)
    health_score = max(20, 100 - (abnormal_count * 8))
    risk_level = "Normal"
    if health_score < 50:
        risk_level = "Critical"
    elif health_score < 80:
        risk_level = "Elevated"
        
    return {
        "health_score": health_score,
        "abnormal_count": abnormal_count,
        "risk_level": risk_level,
        "total_reports": total_reports,
        "latest_report_date": latest_report_date,
        "category_stats": category_stats
    }

@app.get("/api/search")
def hybrid_search(q: str = Query(..., description="Search query string")):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    
    q_clean = q.lower().strip()
    
    # Enhanced rule-based/regex query intent parsing (100% offline intelligence)
    intent_results = []
    
    # Parse queries like "low hemoglobin reports" or "find reports with high cholesterol"
    # Match patterns: (low|high|abnormal) (metric_name)
    match_status = re.search(r'\b(low|high|abnormal|elevated|critical)\b', q_clean)
    match_test = re.search(r'\b(hemoglobin|hb|glucose|sugar|cholesterol|lipid|wbc|rbc|platelets|creatinine|vitamin d|kidney|liver)\b', q_clean)
    
    # Parse queries like "compare my glucose over time" or "compare glucose"
    match_compare = re.search(r'\b(compare|trend|over time|history|timeline|chart)\b', q_clean)
    
    # Parse queries like "show latest cbc report" or "latest report"
    match_latest = re.search(r'\b(latest|recent|newest|last)\b', q_clean)
    
    if match_status or match_test or match_compare or match_latest:
        filter_clauses = ["1=1"]
        filter_params = []
        
        # Test parameter resolution
        test_param = None
        if match_test:
            test_param = match_test.group(1)
            # Normalization mapping
            if test_param in ["hb", "hemoglobin"]:
                test_param = "Hemoglobin"
            elif test_param in ["sugar", "glucose"]:
                test_param = "Glucose"
            elif test_param in ["lipid", "cholesterol"]:
                test_param = "Cholesterol"
            elif test_param == "vitamin d":
                test_param = "Vitamin D"
            elif test_param == "creatinine":
                test_param = "Creatinine"
            elif test_param == "wbc":
                test_param = "WBC"
            elif test_param == "rbc":
                test_param = "RBC"
            elif test_param == "platelets":
                test_param = "Platelets"
            
            if test_param:
                if test_param.lower() in ["kidney", "liver"]:
                    filter_clauses.append("tr.category = ?")
                    filter_params.append("kidney" if test_param.lower() == "kidney" else "liver")
                else:
                    filter_clauses.append("tr.test_name LIKE ?")
                    filter_params.append(f"%{test_param}%")
        
        # Flag/Status resolution
        if match_status:
            status_val = match_status.group(1)
            if status_val == "abnormal":
                filter_clauses.append("tr.flag != 'normal'")
            elif status_val in ["low", "high", "critical"]:
                filter_clauses.append("tr.flag = ?")
                filter_params.append(status_val)
                
        # Handle report type
        if "cbc" in q_clean or "blood count" in q_clean:
            filter_clauses.append("r.report_type = 'lab'")
            
        sql_query = f"""
            SELECT DISTINCT r.id, r.report_type, r.hospital, r.doctor, r.report_date, p.name as patient_name,
                   'Found matching parameter: ' || tr.test_name || ' (' || tr.value || ' ' || tr.unit || ', status: ' || tr.flag || ')' as snippet,
                   1.0 as relevance
            FROM reports r
            JOIN patients p ON r.patient_id = p.id
            JOIN test_results tr ON tr.report_id = r.id
            WHERE {" AND ".join(filter_clauses)}
        """
        
        if match_latest:
            sql_query += " ORDER BY r.report_date DESC LIMIT 1"
        else:
            sql_query += " ORDER BY r.report_date DESC"
            
        cursor.execute(sql_query, filter_params)
        intent_results = [dict(r) for r in cursor.fetchall()]
        
    # Standard keyword & FTS5 search
    cursor.execute(
        """SELECT r.id, r.report_type, r.hospital, r.doctor, r.report_date, p.name as patient_name, SUBSTR(r.raw_ocr_text, 1, 150) as snippet
           FROM reports r
           JOIN patients p ON r.patient_id = p.id
           JOIN reports_fts fts ON r.id = fts.report_id
           WHERE fts.content MATCH ?""",
        (q,)
    )
    fts_rows = cursor.fetchall()
    fts_results = [dict(r) for r in fts_rows]
    
    # Semantic search (vector comparison)
    query_vector = get_embedding(q)
    cursor.execute(
        """SELECT e.report_id, e.vector_blob, r.report_type, r.hospital, r.doctor, r.report_date, p.name as patient_name, SUBSTR(r.raw_ocr_text, 1, 150) as snippet
           FROM embeddings e
           JOIN reports r ON e.report_id = r.id
           JOIN patients p ON e.report_id = r.id OR r.patient_id = p.id""" # Robust join
    )
    all_embeddings = cursor.fetchall()
    
    semantic_results = []
    import json
    for row in all_embeddings:
        try:
            stored_vector = json.loads(row["vector_blob"].decode('utf-8'))
            similarity = compute_cosine_similarity(query_vector, stored_vector)
            # Elevate similarity score if query intents matched this report
            matched_intent = any(x["id"] == row["report_id"] for x in intent_results)
            boost = 0.25 if matched_intent else 0.0
            score = min(1.0, similarity + boost)
            if score > 0.35:
                semantic_results.append({
                    "id": row["report_id"],
                    "report_type": row["report_type"],
                    "hospital": row["hospital"],
                    "doctor": row["doctor"],
                    "report_date": row["report_date"],
                    "patient_name": row["patient_name"],
                    "snippet": row["snippet"],
                    "similarity": score
                })
        except Exception:
            continue
            
    semantic_results.sort(key=lambda x: x["similarity"], reverse=True)
    
    # Merge intent results into keyword/FTS results to ensure maximum match accuracy offline
    for r in intent_results:
        if not any(x["id"] == r["id"] for x in fts_results):
            fts_results.insert(0, r)
            
    conn.close()
    return {
        "keyword_results": fts_results,
        "semantic_results": semantic_results
    }

@app.get("/api/reports/{id}/summary")
def get_offline_report_summary(id: int):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    
    # Load report detail
    cursor.execute("""
        SELECT r.*, p.name as patient_name, p.dob, p.gender
        FROM reports r
        JOIN patients p ON r.patient_id = p.id
        WHERE r.id = ?
    """, (id,))
    report = cursor.fetchone()
    if not report:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found")
        
    patient_id = report["patient_id"]
    report_date = report["report_date"]
    
    # Load results
    cursor.execute("SELECT * FROM test_results WHERE report_id = ?", (id,))
    results = [dict(r) for r in cursor.fetchall()]
    
    # Find previous report for trend comparison
    cursor.execute("""
        SELECT id, report_date FROM reports 
        WHERE patient_id = ? AND report_date < ? 
        ORDER BY report_date DESC LIMIT 1
    """, (patient_id, report_date))
    prev_report = cursor.fetchone()
    
    prev_results = {}
    if prev_report:
        cursor.execute("SELECT test_name, value FROM test_results WHERE report_id = ?", (prev_report["id"],))
        prev_results = {r["test_name"].lower(): r["value"] for r in cursor.fetchall()}
        
    conn.close()
    
    # Generate Offline Heuristic Summary
    abnormals = [r for r in results if r["flag"] != "normal"]
    normals = [r for r in results if r["flag"] == "normal"]
    
    abnormal_text = "None. All parameters are within normal physiological bounds."
    if abnormals:
        abnormal_text = ", ".join([f"{r['test_name']} ({r['value']} {r['unit']}: {r['flag'].upper()})" for r in abnormals])
        
    normal_text = "None."
    if normals:
        normal_text = ", ".join([f"{r['test_name']} ({r['value']} {r['unit']})" for r in normals])
        
    # Analyze trends
    trends = []
    for r in results:
        t_name_lower = r["test_name"].lower()
        if t_name_lower in prev_results:
            prev_val = prev_results[t_name_lower]
            curr_val = r["value"]
            diff = curr_val - prev_val
            pct = ((diff / prev_val) * 100) if prev_val != 0 else 0
            direction = "increased" if diff > 0 else "decreased"
            if abs(pct) > 2.0: # Only log significant changes
                trends.append(f"{r['test_name']} has {direction} by {abs(pct):.1f}% (from {prev_val} to {curr_val} {r['unit']})")
                
    trend_text = "No previous report found for comparison."
    if prev_report:
        trend_text = "; ".join(trends) if trends else "All parameters remained stable since the previous report."
        
    disclaimer = "INFORMATIONAL NOTE ONLY: This summary is generated offline by MedVault AI and does not constitute a formal diagnosis. Please consult a qualified healthcare professional to discuss these test values and coordinate appropriate medical care."
    
    return {
        "abnormal_findings": abnormal_text,
        "normal_findings": normal_text,
        "historical_trends": trend_text,
        "clinical_disclaimer": disclaimer
    }

@app.get("/api/export")
def export_reports(format: str = "json"):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT r.id, p.name as patient_name, r.report_type, r.hospital, r.doctor, r.report_date, r.raw_ocr_text
           FROM reports r
           JOIN patients p ON r.patient_id = p.id"""
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if format.lower() == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Patient Name", "Report Type", "Hospital", "Doctor", "Report Date", "Raw Text"])
        for r in rows:
            writer.writerow([r["id"], r["patient_name"], r["report_type"], r["hospital"], r["doctor"], r["report_date"], r["raw_ocr_text"][:200]])
        output.seek(0)
        return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=reports_export.csv"})
        
    return JSONResponse(content=rows)

# Serve build assets of the React frontend if built
FRONTEND_STATIC = os.path.join(BASE_DIR, "../../frontend/static")
if os.path.exists(FRONTEND_STATIC):
    app.mount("/static", StaticFiles(directory=FRONTEND_STATIC), name="static")

FRONTEND_DIST = os.path.join(BASE_DIR, "../../frontend/dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
