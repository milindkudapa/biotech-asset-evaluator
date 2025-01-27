import os
import ssl
import certifi
import httpx
import urllib3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import json
import logging

# Disable SSL verification globally
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure httpx to not verify SSL
httpx.DEFAULT_CERTS_FILE = None

from .workflow.evaluation_workflow import BiotechEvaluationWorkflow
from .models.schemas import (
    BiotechAssetReport,
    Overview,
    MechanismOfAction,
    ClinicalActivity,
    DeveloperFinancialStatus
)
from .clients.api_clients import ClinicalTrialsClient, PubMedClient, ExaClient, TavilySearchClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Biotech Asset Evaluation API",
    description="API for evaluating biotech drug assets and their developers",
    version="1.0.0"
)

# Initialize workflow
workflow = BiotechEvaluationWorkflow()

class DrugRequest(BaseModel):
    """Request model for drug-related endpoints."""
    drug_name: str

class CompanyRequest(BaseModel):
    """Request model for company-related endpoints."""
    company_name: str

class EvaluationRequest(BaseModel):
    """Request model for full evaluation."""
    drug_name: str
    company_name: Optional[str] = None

@app.post("/analyze/moa", response_model=MechanismOfAction, tags=["Analysis"])
async def analyze_mechanism_of_action(request: DrugRequest):
    """Analyze the mechanism of action for a drug."""
    try:
        raw_data = await workflow.retrieve_data(request.drug_name)
        moa_data = await workflow.analyze_mechanism_of_action(raw_data["pubmed_articles"])
        return MechanismOfAction(**moa_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing mechanism of action: {str(e)}")

@app.post("/analyze/clinical", response_model=ClinicalActivity, tags=["Analysis"])
async def analyze_clinical_activity(request: DrugRequest):
    """Analyze clinical trial data for a drug."""
    try:
        raw_data = await workflow.retrieve_data(request.drug_name)
        clinical_data = await workflow.analyze_clinical_activity(raw_data["clinical_trials"])
        return ClinicalActivity(**clinical_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing clinical activity: {str(e)}")

@app.post("/analyze/financial", response_model=DeveloperFinancialStatus, tags=["Analysis"])
async def analyze_financial_status(request: CompanyRequest):
    """Analyze financial status of a company."""
    try:
        raw_data = await workflow.retrieve_data(drug_name="", company_name=request.company_name)
        if not raw_data["company_info"] or not raw_data["licensing_deals"]:
            return DeveloperFinancialStatus()
        
        financial_data = await workflow.analyze_financial_status(
            raw_data["company_info"],
            raw_data["licensing_deals"]
        )
        return DeveloperFinancialStatus(**financial_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing financial status: {str(e)}")

@app.post("/analyze/overview", response_model=Overview, tags=["Analysis"])
async def generate_drug_overview(request: DrugRequest):
    """Generate an overview for a drug."""
    try:
        # Get mechanism of action and clinical data first
        raw_data = await workflow.retrieve_data(request.drug_name)
        moa_data = await workflow.analyze_mechanism_of_action(raw_data["pubmed_articles"])
        clinical_data = await workflow.analyze_clinical_activity(raw_data["clinical_trials"])
        
        # Generate overview
        overview_data = await workflow.generate_overview(request.drug_name, moa_data, clinical_data)
        return Overview(**overview_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating overview: {str(e)}")

@app.post("/data/trials", response_model=List[Dict[str, Any]], tags=["Data"])
async def get_clinical_trials(request: DrugRequest):
    """Get raw clinical trial data for a drug."""
    try:
        raw_data = await workflow.retrieve_data(request.drug_name)
        return raw_data["clinical_trials"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving clinical trials: {str(e)}")

@app.post("/data/pubmed", response_model=List[Dict[str, Any]], tags=["Data"])
async def get_pubmed_articles(request: DrugRequest):
    """Get raw PubMed article data for a drug."""
    try:
        raw_data = await workflow.retrieve_data(request.drug_name)
        return raw_data["pubmed_articles"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving PubMed articles: {str(e)}")

@app.post("/evaluate", response_model=BiotechAssetReport, tags=["Evaluation"])
async def evaluate_asset(request: EvaluationRequest):
    """
    Comprehensive evaluation of a drug asset and its developer.
    This endpoint combines all analyses into a single report.
    """
    try:
        report = await workflow.evaluate_asset(request.drug_name, request.company_name)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating asset: {str(e)}")

@app.get("/health", tags=["System"])
async def health_check():
    """Check if the API is running."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 