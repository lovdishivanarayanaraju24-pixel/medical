import sqlite3
import os
import json

def generate_mock_data():
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../medvault.db")
    print(f"Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Patient check or creation
    patient_name = "Arjun Mehta"
    cursor.execute("SELECT id FROM patients WHERE name = ?", (patient_name,))
    p_row = cursor.fetchone()
    if p_row:
        patient_id = p_row["id"]
        print(f"Patient {patient_name} already exists with ID: {patient_id}")
    else:
        cursor.execute(
            "INSERT INTO patients (name, dob, gender, contact_info) VALUES (?, ?, ?, ?)",
            (patient_name, "1981-03-12", "Male", "+91 98765 43210")
        )
        patient_id = cursor.lastrowid
        print(f"Created patient {patient_name} with ID: {patient_id}")

    # Delete existing reports for this patient to prevent duplication
    cursor.execute("DELETE FROM reports WHERE patient_id = ?", (patient_id,))
    
    # 5 Mock reports with dates: 2026-01-10, 2026-02-15, 2026-03-20, 2026-04-25, 2026-05-30
    # Parameters: Hemoglobin, Glucose, Cholesterol, WBC, RBC, Platelets, Creatinine, Vitamin D
    reports_data = [
        {
            "date": "2026-01-10",
            "hospital": "Max Health Center",
            "doctor": "Dr. Vivek Sharma",
            "results": [
                {"test_name": "Hemoglobin", "value": 11.2, "unit": "g/dL", "low": 13.8, "high": 17.2, "flag": "low", "category": "blood"},
                {"test_name": "Glucose", "value": 145.0, "unit": "mg/dL", "low": 70.0, "high": 100.0, "flag": "high", "category": "glucose"},
                {"test_name": "Cholesterol", "value": 240.0, "unit": "mg/dL", "low": 125.0, "high": 200.0, "flag": "high", "category": "lipid"},
                {"test_name": "WBC", "value": 11500.0, "unit": "/uL", "low": 4000.0, "high": 11000.0, "flag": "high", "category": "blood"},
                {"test_name": "RBC", "value": 4.1, "unit": "million/uL", "low": 4.5, "high": 5.9, "flag": "low", "category": "blood"},
                {"test_name": "Platelets", "value": 140000.0, "unit": "/uL", "low": 150000.0, "high": 450000.0, "flag": "low", "category": "blood"},
                {"test_name": "Creatinine", "value": 1.4, "unit": "mg/dL", "low": 0.6, "high": 1.2, "flag": "high", "category": "kidney"},
                {"test_name": "Vitamin D", "value": 18.0, "unit": "ng/mL", "low": 30.0, "high": 100.0, "flag": "low", "category": "general"},
            ]
        },
        {
            "date": "2026-02-15",
            "hospital": "Max Health Center",
            "doctor": "Dr. Vivek Sharma",
            "results": [
                {"test_name": "Hemoglobin", "value": 12.0, "unit": "g/dL", "low": 13.8, "high": 17.2, "flag": "low", "category": "blood"},
                {"test_name": "Glucose", "value": 130.0, "unit": "mg/dL", "low": 70.0, "high": 100.0, "flag": "high", "category": "glucose"},
                {"test_name": "Cholesterol", "value": 225.0, "unit": "mg/dL", "low": 125.0, "high": 200.0, "flag": "high", "category": "lipid"},
                {"test_name": "WBC", "value": 10200.0, "unit": "/uL", "low": 4000.0, "high": 11000.0, "flag": "normal", "category": "blood"},
                {"test_name": "RBC", "value": 4.3, "unit": "million/uL", "low": 4.5, "high": 5.9, "flag": "low", "category": "blood"},
                {"test_name": "Platelets", "value": 165000.0, "unit": "/uL", "low": 150000.0, "high": 450000.0, "flag": "normal", "category": "blood"},
                {"test_name": "Creatinine", "value": 1.3, "unit": "mg/dL", "low": 0.6, "high": 1.2, "flag": "high", "category": "kidney"},
                {"test_name": "Vitamin D", "value": 22.0, "unit": "ng/mL", "low": 30.0, "high": 100.0, "flag": "low", "category": "general"},
            ]
        },
        {
            "date": "2026-03-20",
            "hospital": "City Diagnostics",
            "doctor": "Dr. Vivek Sharma",
            "results": [
                {"test_name": "Hemoglobin", "value": 13.1, "unit": "g/dL", "low": 13.8, "high": 17.2, "flag": "low", "category": "blood"},
                {"test_name": "Glucose", "value": 112.0, "unit": "mg/dL", "low": 70.0, "high": 100.0, "flag": "high", "category": "glucose"},
                {"test_name": "Cholesterol", "value": 208.0, "unit": "mg/dL", "low": 125.0, "high": 200.0, "flag": "high", "category": "lipid"},
                {"test_name": "WBC", "value": 8500.0, "unit": "/uL", "low": 4000.0, "high": 11000.0, "flag": "normal", "category": "blood"},
                {"test_name": "RBC", "value": 4.5, "unit": "million/uL", "low": 4.5, "high": 5.9, "flag": "normal", "category": "blood"},
                {"test_name": "Platelets", "value": 190000.0, "unit": "/uL", "low": 150000.0, "high": 450000.0, "flag": "normal", "category": "blood"},
                {"test_name": "Creatinine", "value": 1.1, "unit": "mg/dL", "low": 0.6, "high": 1.2, "flag": "normal", "category": "kidney"},
                {"test_name": "Vitamin D", "value": 28.0, "unit": "ng/mL", "low": 30.0, "high": 100.0, "flag": "low", "category": "general"},
            ]
        },
        {
            "date": "2026-04-25",
            "hospital": "City Diagnostics",
            "doctor": "Dr. Vivek Sharma",
            "results": [
                {"test_name": "Hemoglobin", "value": 14.0, "unit": "g/dL", "low": 13.8, "high": 17.2, "flag": "normal", "category": "blood"},
                {"test_name": "Glucose", "value": 98.0, "unit": "mg/dL", "low": 70.0, "high": 100.0, "flag": "normal", "category": "glucose"},
                {"test_name": "Cholesterol", "value": 195.0, "unit": "mg/dL", "low": 125.0, "high": 200.0, "flag": "normal", "category": "lipid"},
                {"test_name": "WBC", "value": 6800.0, "unit": "/uL", "low": 4000.0, "high": 11000.0, "flag": "normal", "category": "blood"},
                {"test_name": "RBC", "value": 4.8, "unit": "million/uL", "low": 4.5, "high": 5.9, "flag": "normal", "category": "blood"},
                {"test_name": "Platelets", "value": 220000.0, "unit": "/uL", "low": 150000.0, "high": 450000.0, "flag": "normal", "category": "blood"},
                {"test_name": "Creatinine", "value": 0.95, "unit": "mg/dL", "low": 0.6, "high": 1.2, "flag": "normal", "category": "kidney"},
                {"test_name": "Vitamin D", "value": 35.0, "unit": "ng/mL", "low": 30.0, "high": 100.0, "flag": "normal", "category": "general"},
            ]
        },
        {
            "date": "2026-05-30",
            "hospital": "Max Health Center",
            "doctor": "Dr. Vivek Sharma",
            "results": [
                {"test_name": "Hemoglobin", "value": 14.5, "unit": "g/dL", "low": 13.8, "high": 17.2, "flag": "normal", "category": "blood"},
                {"test_name": "Glucose", "value": 92.0, "unit": "mg/dL", "low": 70.0, "high": 100.0, "flag": "normal", "category": "glucose"},
                {"test_name": "Cholesterol", "value": 185.0, "unit": "mg/dL", "low": 125.0, "high": 200.0, "flag": "normal", "category": "lipid"},
                {"test_name": "WBC", "value": 5900.0, "unit": "/uL", "low": 4000.0, "high": 11000.0, "flag": "normal", "category": "blood"},
                {"test_name": "RBC", "value": 5.0, "unit": "million/uL", "low": 4.5, "high": 5.9, "flag": "normal", "category": "blood"},
                {"test_name": "Platelets", "value": 245000.0, "unit": "/uL", "low": 150000.0, "high": 450000.0, "flag": "normal", "category": "blood"},
                {"test_name": "Creatinine", "value": 0.88, "unit": "mg/dL", "low": 0.6, "high": 1.2, "flag": "normal", "category": "kidney"},
                {"test_name": "Vitamin D", "value": 42.0, "unit": "ng/mL", "low": 30.0, "high": 100.0, "flag": "normal", "category": "general"},
            ]
        }
    ]

    for rep in reports_data:
        # Create report record
        raw_txt = f"Patient: {patient_name}\nHospital: {rep['hospital']}\nDoctor: {rep['doctor']}\nDate: {rep['date']}\n"
        for res in rep["results"]:
            raw_txt += f"{res['test_name']}: {res['value']} {res['unit']} ({res['low']}-{res['high']})\n"
            
        cursor.execute(
            """INSERT INTO reports (patient_id, report_type, hospital, doctor, report_date, source_file_path, raw_ocr_text)
               VALUES (?, 'lab', ?, ?, ?, '', ?)""",
            (patient_id, rep["hospital"], rep["doctor"], rep["date"], raw_txt)
        )
        report_id = cursor.lastrowid
        
        # Create test results
        for res in rep["results"]:
            cursor.execute(
                """INSERT INTO test_results (report_id, test_name, value, unit, reference_range_low, reference_range_high, flag, category)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (report_id, res["test_name"], res["value"], res["unit"], res["low"], res["high"], res["flag"], res["category"])
            )
            
        # Create FTS content
        fts_content = f"{patient_name} {rep['hospital']} {rep['doctor']} {raw_txt}"
        cursor.execute("INSERT INTO reports_fts (report_id, content) VALUES (?, ?)", (report_id, fts_content))

    conn.commit()
    conn.close()
    print("5 mock reports generated successfully for Arjun Mehta!")

if __name__ == "__main__":
    generate_mock_data()
