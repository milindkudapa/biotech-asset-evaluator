import os
from typing import List, Dict, Any, Optional
import httpx
import ssl
import certifi
from Bio import Entrez
from tavily import TavilyClient
from exa_py import Exa
from dotenv import load_dotenv
import urllib3
import json
import asyncio
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

# Create a custom SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class ClinicalTrialsClient:
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
    
    def __init__(self):
        self.headers = {
            "Accept": "application/json",
            "User-Agent": f"BiotechEvaluator/1.0 (Contact: {os.getenv('CLINICAL_TRIALS_CONTACT_EMAIL')})",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache"
        }
        # Create SSL context with system certificates
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        
    async def search_trials(self, drug_name: str) -> List[Dict[str, Any]]:
        params = {
            "query.term": drug_name,
            "pageSize": 3,
            "format": "json"
        }
        
        try:
            transport = httpx.AsyncHTTPTransport(verify=self.ssl_context)
            async with httpx.AsyncClient(transport=transport, follow_redirects=True, headers=self.headers, timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                
                if response.status_code == 403:
                    logger.error("Received 403 Forbidden - This may be due to rate limiting or invalid credentials")
                    return []
                    
                response.raise_for_status()
                
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    return []
                
                studies = data.get("studies", [])
                
                results = [
                    {
                        "nct_id": study.get("protocolSection", {}).get("identificationModule", {}).get("nctId"),
                        "title": study.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle"),
                        "phase": study.get("protocolSection", {}).get("designModule", {}).get("phases", []),
                        "status": study.get("protocolSection", {}).get("statusModule", {}).get("overallStatus"),
                        "conditions": study.get("protocolSection", {}).get("conditionsModule", {}).get("conditions", []),
                        "description": study.get("protocolSection", {}).get("descriptionModule", {}).get("briefSummary", "")
                    }
                    for study in studies
                ]
                return results
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred while fetching clinical trials: {str(e)}")
            logger.error(f"Request URL: {e.request.url if e.request else 'unknown'}")
            logger.error(f"Request headers: {e.request.headers if e.request else 'unknown'}")
            return []
        except Exception as e:
            logger.error(f"Error occurred while fetching clinical trials: {str(e)}", exc_info=True)
            return []

class PubMedClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    API_KEY = os.getenv("PUBMED_API_KEY")

    async def search_articles(self, drug_name: str) -> List[Dict[str, Any]]:
        """Search for PubMed articles related to a drug."""
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                # First get article IDs
                search_params = {
                    "db": "pubmed",
                    "term": f"{drug_name}[Title/Abstract]",
                    "retmode": "json",
                    "retmax": 20,
                    "api_key": self.API_KEY
                }
                
                response = await client.get(self.BASE_URL, params=search_params)
                response.raise_for_status()
                search_data = response.json()
                
                if not search_data.get("esearchresult", {}).get("idlist"):
                    return []
                
                # Then fetch article details
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(search_data["esearchresult"]["idlist"]),
                    "retmode": "xml",
                    "api_key": self.API_KEY
                }
                
                response = await client.get(self.FETCH_URL, params=fetch_params)
                response.raise_for_status()
                return [{"id": id, "content": response.text} for id in search_data["esearchresult"]["idlist"]]
        except httpx.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            return []
        except Exception as e:
            print(f"Error searching articles: {e}")
            return []

class ExaClient:
    def __init__(self):
        self.client = Exa(api_key=os.getenv("EXA_API_KEY"))
    
    async def search_company_info(self, company_name: str) -> Dict[str, Any]:
        """Search for company information using Exa.ai."""
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                # Implement company info search
                return {"company_name": company_name, "info": "Sample company info"}
        except Exception as e:
            print(f"Error searching company info: {e}")
            return {}

class TavilySearchClient:
    def __init__(self):
        self.client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    async def search_licensing_deals(self, company_name: str, drug_name: str) -> List[Dict[str, Any]]:
        """Search for licensing deals and investments using Tavily."""
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                # Implement licensing deals search
                return [{"deal": "Sample licensing deal"}]
        except Exception as e:
            print(f"Error searching licensing deals: {e}")
            return [] 