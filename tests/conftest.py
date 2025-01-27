import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import os
import json

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.main import app
from src.workflow.evaluation_workflow import BiotechEvaluationWorkflow

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)

@pytest.fixture
def mock_workflow():
    """Create a mock workflow for testing."""
    with patch("src.main.workflow") as mock:
        # Mock retrieve_data
        mock.retrieve_data = AsyncMock(return_value={
            "clinical_trials": [{"id": "NCT123", "title": "Test Trial"}],
            "pubmed_articles": [{"id": "123", "content": "Test article"}],
            "company_info": {"name": "Test Company", "status": "Public"},
            "licensing_deals": [{"deal": "Test Deal"}]
        })
        
        # Mock analyze_mechanism_of_action
        mock.analyze_mechanism_of_action = AsyncMock(return_value={
            "target_pathways": "Test pathway",
            "biology": "Test biology"
        })
        
        # Mock analyze_clinical_activity
        mock.analyze_clinical_activity = AsyncMock(return_value={
            "ongoing_trials": [
                {
                    "nct_id": "NCT123",
                    "title": "Test Trial",
                    "phase": "PHASE1",
                    "status": "ONGOING",
                    "conditions": ["Test Condition"],
                    "description": "Test Description"
                }
            ],
            "completed_trials": [],
            "regulatory_updates": [
                {
                    "date": "2024-01-01",
                    "agency": "FDA",
                    "type": "UPDATE",
                    "description": "Test Update"
                }
            ]
        })
        
        # Mock analyze_financial_status
        mock.analyze_financial_status = AsyncMock(return_value={
            "ownership_type": "PUBLIC",
            "funding": "Test funding",
            "revenue": "Test revenue",
            "licensing_deals": [
                {
                    "date": "2024-01-01",
                    "parties": ["Company A", "Company B"],
                    "description": "Test Deal",
                    "value": 1000000.0
                }
            ],
            "disclosed_investments": [
                {
                    "date": "2024-01-01",
                    "amount": 1000000.0,
                    "type": "Series A",
                    "investor": "Test Investor"
                }
            ]
        })
        
        # Mock generate_overview
        mock.generate_overview = AsyncMock(return_value={
            "description": "Test overview description"
        })
        
        # Mock evaluate_asset
        mock.evaluate_asset = AsyncMock(return_value={
            "drug_name": "Test Drug",
            "developer_organization": "Test Company",
            "overview": {"description": "Test overview"},
            "mechanism_of_action": {
                "target_pathways": "Test pathway",
                "biology": "Test biology"
            },
            "clinical_activity": {
                "ongoing_trials": [],
                "completed_trials": [],
                "regulatory_updates": []
            },
            "developer_financial_status": {
                "ownership_type": "PUBLIC",
                "funding": "Test funding",
                "revenue": "Test revenue",
                "licensing_deals": [],
                "disclosed_investments": []
            }
        })
        
        yield mock 