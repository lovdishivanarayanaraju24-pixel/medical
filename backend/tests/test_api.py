from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)

def test_api_dashboard_stats():
    response = client.get("/api/dashboard-stats")
    assert response.status_code == 200
    json_data = response.json()
    assert "health_score" in json_data
    assert "total_reports" in json_data
    assert "abnormal_count" in json_data
    assert "category_stats" in json_data

def test_api_patients():
    response = client.get("/api/patients")
    assert response.status_code == 200
    patients = response.json()
    assert isinstance(patients, list)
    if len(patients) > 0:
        assert "id" in patients[0]
        assert "name" in patients[0]

def test_api_search_structured_queries():
    response = client.get("/api/search?q=low+hemoglobin")
    assert response.status_code == 200
    search_data = response.json()
    assert "keyword_results" in search_data
    assert "semantic_results" in search_data

def test_api_report_summary():
    # Fetch first report if exists
    rep_response = client.get("/api/reports")
    assert rep_response.status_code == 200
    reports = rep_response.json()
    if len(reports) > 0:
        report_id = reports[0]["id"]
        summary_response = client.get(f"/api/reports/{report_id}/summary")
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        assert "abnormal_findings" in summary_data
        assert "normal_findings" in summary_data
        assert "historical_trends" in summary_data
        assert "clinical_disclaimer" in summary_data
