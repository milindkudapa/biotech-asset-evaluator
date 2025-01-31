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
import multiprocessing
import subprocess
import sys
import time
from pathlib import Path
from utils.logging_config import setup_logging

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
        state = {"drug_name": request.drug_name, "company_name": None}
        raw_data = await workflow.retrieve_data(state)
        moa_data = await workflow.analyze_mechanism_of_action(raw_data)
        return MechanismOfAction(**moa_data["moa_analysis"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing mechanism of action: {str(e)}")

@app.post("/analyze/clinical", response_model=ClinicalActivity, tags=["Analysis"])
async def analyze_clinical_activity(request: DrugRequest):
    """Analyze clinical trial data for a drug."""
    try:
        state = {"drug_name": request.drug_name, "company_name": None}
        raw_data = await workflow.retrieve_data(state)
        clinical_data = await workflow.analyze_clinical_activity(raw_data)
        return ClinicalActivity(**clinical_data["clinical_analysis"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing clinical activity: {str(e)}")

@app.post("/analyze/financial", response_model=DeveloperFinancialStatus, tags=["Analysis"])
async def analyze_financial_status(request: CompanyRequest):
    """Analyze financial status of a company."""
    try:
        state = {
            "drug_name": "",
            "company_name": request.company_name,
            "raw_data": None,
            "financial_analysis": None
        }
        
        # Get raw data
        raw_data = await workflow.retrieve_data(state)
        state.update(raw_data)
        
        # Check if we have the required data
        if not state["raw_data"]["company_info"] or not state["raw_data"]["licensing_deals"]:
            return DeveloperFinancialStatus()
        
        # Analyze financial data using the state
        financial_data = await workflow.analyze_financial_status(state)
        return DeveloperFinancialStatus(**financial_data["financial_analysis"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing financial status: {str(e)}")

@app.post("/analyze/overview", response_model=Overview, tags=["Analysis"])
async def generate_drug_overview(request: DrugRequest):
    """Generate an overview for a drug."""
    try:
        state = {
            "drug_name": request.drug_name,
            "company_name": None,
            "moa_analysis": None,
            "clinical_analysis": None,
            "overview": None
        }
        
        # Get raw data
        raw_data = await workflow.retrieve_data(state)
        state.update(raw_data)
        
        # Get mechanism of action analysis
        moa_result = await workflow.analyze_mechanism_of_action(state)
        state.update(moa_result)
        
        # Get clinical activity analysis
        clinical_result = await workflow.analyze_clinical_activity(state)
        state.update(clinical_result)
        
        # Generate overview using the updated state
        overview_data = await workflow.generate_overview(state)
        return Overview(**overview_data["overview"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating overview: {str(e)}")

@app.post("/data/trials", response_model=List[Dict[str, Any]], tags=["Data"])
async def get_clinical_trials(request: DrugRequest):
    """Get raw clinical trial data for a drug."""
    try:
        state = {"drug_name": request.drug_name, "company_name": None}
        raw_data = await workflow.retrieve_data(state)
        return raw_data["raw_data"]["clinical_trials"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving clinical trials: {str(e)}")

@app.post("/data/pubmed", response_model=List[Dict[str, Any]], tags=["Data"])
async def get_pubmed_articles(request: DrugRequest):
    """Get raw PubMed article data for a drug."""
    try:
        state = {"drug_name": request.drug_name, "company_name": None}
        raw_data = await workflow.retrieve_data(state)
        return raw_data["raw_data"]["pubmed_articles"]
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

def run_fastapi():
    """Run the FastAPI backend server."""
    try:
        logger.info("Starting FastAPI server...")
        subprocess.run(
            ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start FastAPI server: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("FastAPI server stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error starting FastAPI server: {str(e)}")
        sys.exit(1)

def run_streamlit():
    """Run the Streamlit frontend."""
    try:
        logger.info("Starting Streamlit server...")
        subprocess.run(
            ["streamlit", "run", "src/streamlit_app.py", "--server.port", "8501"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Streamlit server: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Streamlit server stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error starting Streamlit server: {str(e)}")
        sys.exit(1)

def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import uvicorn
        import fastapi
        import streamlit
        import httpx
        logger.info("All required dependencies are installed")
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {str(e)}")
        print("Please install required dependencies:")
        print("pip install fastapi uvicorn streamlit httpx")
        return False

def check_environment():
    """Check if environment is properly configured."""
    required_env = [
        "EX_AI_API_KEY",
        "TAVILY_API_KEY"
    ]
    
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        logger.error(f"Missing environment variables: {', '.join(missing_env)}")
        print("Please set the following environment variables:")
        for env in missing_env:
            print(f"- {env}")
        return False
    
    logger.info("Environment variables are properly configured")
    return True

def main():
    """Main function to run both servers."""
    logger.info("Starting Biotech Asset Evaluator...")
    
    # Check dependencies and environment
    if not check_dependencies() or not check_environment():
        sys.exit(1)
    
    # Create processes for each server
    api_process = multiprocessing.Process(target=run_fastapi)
    streamlit_process = multiprocessing.Process(target=run_streamlit)
    
    try:
        # Start both servers
        api_process.start()
        logger.info("FastAPI process started")
        
        # Wait a bit for FastAPI to initialize
        time.sleep(2)
        
        streamlit_process.start()
        logger.info("Streamlit process started")
        
        # Print access information
        print("\n" + "="*50)
        print("Biotech Asset Evaluator is running!")
        print("="*50)
        print("Access the application at:")
        print("- Frontend: http://localhost:8501")
        print("- API docs: http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop the servers")
        print("="*50 + "\n")
        
        # Wait for processes to complete
        api_process.join()
        streamlit_process.join()
        
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
        
        # Terminate processes
        api_process.terminate()
        streamlit_process.terminate()
        
        # Wait for processes to terminate
        api_process.join()
        streamlit_process.join()
        
        logger.info("Servers shut down successfully")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        
        # Ensure processes are terminated
        api_process.terminate()
        streamlit_process.terminate()
        
        sys.exit(1)

if __name__ == "__main__":
    main() 