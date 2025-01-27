import os
import ssl
import certifi
import httpx
import urllib3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import json
import logging

# Disable SSL verification globally
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure httpx to not verify SSL
httpx.DEFAULT_CERTS_FILE = None

from .workflow.evaluation_workflow import BiotechEvaluationWorkflow
from .models.schemas import BiotechAssetReport
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

class EvaluationRequest(BaseModel):
    drug_name: str
    company_name: Optional[str] = None

@app.post("/evaluate", response_model=BiotechAssetReport)
async def evaluate_asset(request: EvaluationRequest) -> BiotechAssetReport:
    """
    Evaluate a biotech drug asset and its developer company.
    
    Parameters:
    - drug_name: Name of the drug asset to evaluate
    - company_name: Optional name of the developer company
    
    Returns:
    - A structured report containing the evaluation results
    """
    try:
        workflow = BiotechEvaluationWorkflow()
        report = await workflow.evaluate_asset(
            drug_name=request.drug_name,
            company_name=request.company_name
        )
        return report
    except Exception as e:
        print(f"Error in evaluate_asset: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error evaluating asset: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 