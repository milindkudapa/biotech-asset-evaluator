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
import re

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
        if not os.getenv("EXA_API_KEY"):
            logger.error("EXA_API_KEY not found in environment variables")
    
    async def search_company_info(self, company_name: str) -> Dict[str, Any]:
        """Search for company information using Exa.ai."""
        try:
            if not self.client:
                logger.error("Exa client not properly initialized")
                return {
                    "company_name": company_name,
                    "info": "Error: Exa client not initialized",
                    "sources": []
                }
            
            # Create search query for company information
            query = f"""
            Find detailed information about {company_name}, including:
            - Company type (public/private)
            - Funding history
            - Revenue information
            - Recent company news and developments
            - Market position in biotech/pharma
            Focus on financial and business aspects.
            """
            
            # Perform the search and get SearchResponse object
            search_response = self.client.search(
                query,
                num_results=5,
                use_autoprompt=True
            )
            
            # Initialize response structure
            processed_info = {
                "company_name": company_name,
                "info": "No information found",
                "sources": [],
                "recent_developments": []
            }
            
            # Check if search_response exists and has results attribute
            if not search_response or not hasattr(search_response, 'results'):
                return processed_info
            
            # Get results from the SearchResponse object
            results = search_response.results
            if not results:
                return processed_info
                
            # Process each result
            for result in results:
                if not result:
                    continue
                    
                # Add source information
                source_info = {}
                
                # Safely get attributes
                source_info["title"] = getattr(result, 'title', 'No title')
                source_info["url"] = getattr(result, 'url', '')
                
                if hasattr(result, 'published_date'):
                    source_info["date"] = result.published_date
                
                processed_info["sources"].append(source_info)
                
                # Get text content if available
                text_content = getattr(result, 'text', '')
                if text_content:
                    processed_info["recent_developments"].append(text_content[:500])
            
            # Create summary from developments
            if processed_info["recent_developments"]:
                processed_info["info"] = "\n\n".join([
                    f"Source: {source['title']}\n{dev[:200]}..."
                    for source, dev in zip(
                        processed_info["sources"][:3],
                        processed_info["recent_developments"][:3]
                    )
                ])
            
            return processed_info
            
        except Exception as e:
            logger.error(f"Error searching company info via Exa.ai: {str(e)}")
            return {
                "company_name": company_name,
                "info": "Error retrieving company information",
                "sources": []
            }

class TavilySearchClient:
    def __init__(self):
        self.client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    async def search_licensing_deals(self, company_name: str, drug_name: str) -> List[Dict[str, Any]]:
        """Search for licensing deals and investments using Tavily."""
        try:
            # Create specific queries for different aspects
            queries = [
                f"{company_name} {drug_name} licensing deal announcement",
                f"{company_name} {drug_name} partnership agreement",
                f"{company_name} funding round investment biotech"
            ]
            
            all_results = []
            for query in queries:
                # Use Tavily's search API with correct parameters according to docs
                response = self.client.search(  # Removed await since it's synchronous
                    query=query,
                    search_depth="advanced",
                    include_domains=[
                        "fiercebiotech.com",
                        "biospace.com",
                        "evaluate.com",
                        "bloomberg.com",
                        "reuters.com"
                    ],
                    max_results=3,
                    include_answer=True,
                    include_raw_content=True
                )
                
                if response and "results" in response:
                    all_results.extend(response["results"])
            
            # Process and structure the results
            processed_deals = []
            seen_urls = set()  # To avoid duplicates
            
            for result in all_results:
                # Skip if we've seen this URL before
                if result["url"] in seen_urls:
                    continue
                seen_urls.add(result["url"])
                
                # Extract date from the result
                date = result.get("published_date", "Not specified")
                
                # Create a structured deal entry
                deal = {
                    "date": date,
                    "title": result.get("title", ""),
                    "description": result.get("content", "")[:500],  # Changed from snippet to content
                    "url": result["url"],
                    "source": result.get("source", "Unknown source"),
                    "type": "licensing_deal" if "licensing" in result.get("content", "").lower() 
                           else "investment" if "investment" in result.get("content", "").lower()
                           else "partnership"
                }
                
                # Try to extract financial values using regex
                value_match = re.search(r'\$\s*(\d+(?:\.\d+)?)\s*(million|billion|M|B)?', 
                                      result.get("content", ""))
                if value_match:
                    amount = float(value_match.group(1))
                    multiplier = {
                        'billion': 1e9, 'B': 1e9,
                        'million': 1e6, 'M': 1e6
                    }.get(value_match.group(2), 1)
                    deal["value"] = amount * multiplier
                
                processed_deals.append(deal)
            
            return processed_deals[:5]  # Return top 5 most relevant deals
            
        except Exception as e:
            logger.error(f"Error searching licensing deals via Tavily: {str(e)}")
            return [] 