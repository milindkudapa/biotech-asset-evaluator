import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_analyze_moa(test_client, mock_workflow):
    """Test the mechanism of action analysis endpoint."""
    response = test_client.post("/analyze/moa", json={"drug_name": "test_drug"})
    assert response.status_code == 200
    data = response.json()
    assert "target_pathways" in data
    assert "biology" in data

def test_analyze_clinical(test_client, mock_workflow):
    """Test the clinical trial analysis endpoint."""
    response = test_client.post("/analyze/clinical", json={"drug_name": "test_drug"})
    assert response.status_code == 200
    data = response.json()
    assert "ongoing_trials" in data
    assert "completed_trials" in data
    assert "regulatory_updates" in data
    
    # Validate trial structure
    if data["ongoing_trials"]:
        trial = data["ongoing_trials"][0]
        assert all(key in trial for key in ["nct_id", "title", "phase", "status", "conditions", "description"])

def test_analyze_financial(test_client, mock_workflow):
    """Test the financial status analysis endpoint."""
    response = test_client.post("/analyze/financial", json={"company_name": "test_company"})
    assert response.status_code == 200
    data = response.json()
    assert "ownership_type" in data
    assert "funding" in data
    assert "revenue" in data
    assert "licensing_deals" in data
    assert "disclosed_investments" in data

def test_analyze_overview(test_client, mock_workflow):
    """Test the drug overview generation endpoint."""
    response = test_client.post("/analyze/overview", json={"drug_name": "test_drug"})
    assert response.status_code == 200
    data = response.json()
    assert "description" in data

def test_get_clinical_trials(test_client, mock_workflow):
    """Test the raw clinical trials data endpoint."""
    response = test_client.post("/data/trials", json={"drug_name": "test_drug"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "id" in data[0]
        assert "title" in data[0]

def test_get_pubmed_articles(test_client, mock_workflow):
    """Test the raw PubMed articles endpoint."""
    response = test_client.post("/data/pubmed", json={"drug_name": "test_drug"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "id" in data[0]
        assert "content" in data[0]

def test_evaluate_asset(test_client, mock_workflow):
    """Test the complete asset evaluation endpoint."""
    response = test_client.post("/evaluate", json={
        "drug_name": "test_drug",
        "company_name": "test_company"
    })
    assert response.status_code == 200
    data = response.json()
    assert "drug_name" in data
    assert "developer_organization" in data
    assert "overview" in data
    assert "mechanism_of_action" in data
    assert "clinical_activity" in data
    assert "developer_financial_status" in data

def test_invalid_drug_name(test_client, mock_workflow):
    """Test error handling for invalid drug name."""
    response = test_client.post("/analyze/moa", json={"drug_name": ""})
    assert response.status_code == 422  # Validation error

def test_invalid_company_name(test_client, mock_workflow):
    """Test error handling for invalid company name."""
    response = test_client.post("/analyze/financial", json={"company_name": ""})
    assert response.status_code == 422  # Validation error

def test_missing_required_field(test_client, mock_workflow):
    """Test error handling for missing required field."""
    response = test_client.post("/analyze/moa", json={})
    assert response.status_code == 422  # Validation error

@pytest.mark.parametrize("endpoint", [
    "/analyze/moa",
    "/analyze/clinical",
    "/analyze/financial",
    "/analyze/overview",
    "/data/trials",
    "/data/pubmed",
    "/evaluate"
])
def test_method_not_allowed(test_client, endpoint):
    """Test that endpoints only accept their defined HTTP methods."""
    response = test_client.get(endpoint)
    assert response.status_code == 405  # Method not allowed 