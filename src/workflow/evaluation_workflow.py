from typing import Dict, Any, List
import asyncio
from langgraph.graph import Graph
from openai import AsyncOpenAI
import json
import os
from dotenv import load_dotenv
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..clients.api_clients import (
    ClinicalTrialsClient,
    PubMedClient,
    ExaClient,
    TavilySearchClient
)
from ..models.schemas import BiotechAssetReport, Overview, MechanismOfAction, ClinicalActivity, DeveloperFinancialStatus

load_dotenv()

class BiotechEvaluationWorkflow:
    def __init__(self):
        # Initialize OpenAI API client with latest configuration
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://api.openai.com/v1",
            max_retries=3,
            timeout=60.0
        )
        self.clinical_trials_client = ClinicalTrialsClient()
        self.pubmed_client = PubMedClient()
        self.exa_client = ExaClient()
        self.tavily_client = TavilySearchClient()
        
    def _chunk_text(self, text: str, chunk_size: int = 4000) -> List[str]:
        """Split text into chunks to manage token limits."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word.split())
            if current_size + word_size > chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """Helper method to generate response from OpenAI API with retry logic."""
        messages = [
            {"role": "system", "content": system_prompt or "You are a biotech analysis expert. Format your response as valid JSON."},
            {"role": "user", "content": f"{prompt}\n\nProvide your response in JSON format."}
        ]
        
        # Calculate approximate token count
        total_tokens = sum(len(m["content"].split()) * 1.3 for m in messages)
        
        # If estimated tokens are too high, truncate the content
        if total_tokens > 4000:
            reduction_factor = 4000 / total_tokens
            messages[1]["content"] = messages[1]["content"][:int(len(messages[1]["content"]) * reduction_factor)]
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            seed=42,
            max_tokens=1000,
            presence_penalty=0,
            frequency_penalty=0,
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content

    async def _process_chunks(self, chunks: List[str], system_prompt: str) -> List[Dict]:
        """Process text chunks with rate limiting."""
        results = []
        for chunk in chunks:
            response = await self._generate_response(chunk, system_prompt)
            chunk_result = json.loads(response)
            results.append(chunk_result)
            await asyncio.sleep(2)  # Rate limiting
        return results

    async def retrieve_data(self, drug_name: str, company_name: str = None) -> Dict[str, Any]:
        """Retrieve data from all sources concurrently."""
        # Treat empty string as None
        if not company_name:
            company_name = None
            
        tasks = [
            self.clinical_trials_client.search_trials(drug_name),
            self.pubmed_client.search_articles(drug_name)
        ]
        
        if company_name:
            tasks.extend([
                self.exa_client.search_company_info(company_name),
                self.tavily_client.search_licensing_deals(company_name, drug_name)
            ])
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = {
            "clinical_trials": results[0] if not isinstance(results[0], Exception) else [],
            "pubmed_articles": results[1] if not isinstance(results[1], Exception) else [],
            "company_info": results[2] if len(results) > 2 and not isinstance(results[2], Exception) else None,
            "licensing_deals": results[3] if len(results) > 3 and not isinstance(results[3], Exception) else None
        }
        
        # Limit data to reduce token usage
        if processed_results["clinical_trials"]:
            processed_results["clinical_trials"] = processed_results["clinical_trials"][:2]
        if processed_results["pubmed_articles"]:
            processed_results["pubmed_articles"] = processed_results["pubmed_articles"][:2]
            
        # Truncate article content
        if processed_results["pubmed_articles"]:
            for article in processed_results["pubmed_articles"]:
                if "content" in article:
                    article["content"] = article["content"][:1500]
        
        return processed_results

    async def analyze_mechanism_of_action(self, pubmed_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Analyze mechanism of action using LLM."""
        system_prompt = """You are a biotech expert specializing in drug mechanism analysis. 
        Analyze scientific literature to understand drug mechanisms of action.
        Focus on molecular pathways, targets, and biological processes.
        Format your response as JSON with 'target_pathways' and 'biology' fields."""
        
        # Extract content from pubmed_data
        if not pubmed_data or not isinstance(pubmed_data, list):
            return {
                "target_pathways": "Not available",
                "biology": "Not available"
            }
            
        # Get the content from the first (and only) item
        content = pubmed_data[0].get("content", "") if pubmed_data else ""
        if not content:
            return {
                "target_pathways": "Not available",
                "biology": "Not available"
            }
            
        # Split content into manageable chunks
        chunks = self._chunk_text(content)
        chunk_results = await self._process_chunks(chunks, system_prompt)
        
        # Initialize lists for collecting results
        target_pathways = []
        biology = []
        
        # Process each chunk result
        for result in chunk_results:
            if isinstance(result, dict):
                # Handle target_pathways
                if "target_pathways" in result:
                    if isinstance(result["target_pathways"], str):
                        target_pathways.append(result["target_pathways"])
                    elif isinstance(result["target_pathways"], list):
                        target_pathways.extend(str(item) for item in result["target_pathways"])
                    elif result["target_pathways"] is not None:
                        target_pathways.append(str(result["target_pathways"]))
                
                # Handle biology
                if "biology" in result:
                    if isinstance(result["biology"], str):
                        biology.append(result["biology"])
                    elif isinstance(result["biology"], list):
                        biology.extend(str(item) for item in result["biology"])
                    elif result["biology"] is not None:
                        biology.append(str(result["biology"]))
        
        # Return the merged results
        return {
            "target_pathways": "; ".join(target_pathways) if target_pathways else "Not available",
            "biology": "; ".join(biology) if biology else "Not available"
        }
        
    async def analyze_clinical_activity(self, trials_data: List[Dict[str, Any]]) -> Dict[str, List]:
        """Analyze clinical trial data using LLM."""
        system_prompt = """You are a clinical trial analyst with expertise in biotech.
        Focus on trial phases, outcomes, and regulatory implications.
        Format your response as JSON with 'ongoing_trials', 'completed_trials', and 'regulatory_updates' fields.
        For each trial, include a 'phase' field as a string (e.g. 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', or 'NA')."""
        
        data_str = json.dumps(trials_data)
        chunks = self._chunk_text(data_str)
        chunk_results = await self._process_chunks(chunks, system_prompt)
        
        merged_result = {
            "ongoing_trials": [],
            "completed_trials": [],
            "regulatory_updates": []
        }
        
        for result in chunk_results:
            for key in merged_result:
                if key in result:
                    items = result[key] if isinstance(result[key], list) else [result[key]]
                    for item in items:
                        if isinstance(item, dict) and 'phase' in item:
                            # Convert phase to string if it's a list
                            if isinstance(item['phase'], list):
                                item['phase'] = item['phase'][0] if item['phase'] else 'NA'
                    merged_result[key].extend(items)
        
        return merged_result
        
    async def analyze_financial_status(self, company_data: Dict[str, Any], deals_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze company financial data using LLM."""
        system_prompt = """You are a financial analyst specializing in biotech companies.
        Focus on company valuation, funding rounds, and market position.
        Format your response as JSON with the following structure:
        {
            "ownership_type": "string",
            "funding": "string",
            "revenue": "string",
            "licensing_deals": [
                {
                    "date": "YYYY-MM-DD",
                    "parties": ["company1", "company2"],
                    "description": "string",
                    "value": float or null  # Must be a number or null, not a string
                }
            ],
            "disclosed_investments": [
                {
                    "date": "YYYY-MM-DD",
                    "amount": float,  # Must be a number, not a string
                    "type": "string",
                    "investor": "string"  # Single investor string, not a list
                }
            ]
        }"""
        
        combined_data = {
            "company_info": company_data,
            "licensing_deals": deals_data
        }
        
        response = await self._generate_response(
            json.dumps(combined_data),
            system_prompt=system_prompt
        )
        result = json.loads(response)
        
        # Process licensing deals
        if "licensing_deals" in result:
            if not isinstance(result["licensing_deals"], list):
                result["licensing_deals"] = []
            else:
                processed_deals = []
                for deal in result["licensing_deals"]:
                    if not isinstance(deal, dict):
                        continue
                    # Convert string values to numbers or null
                    try:
                        if "value" in deal:
                            value_str = deal["value"]
                            if isinstance(value_str, str):
                                # Extract numeric value from string
                                value_str = value_str.replace("$", "").replace(",", "")
                                if "million" in value_str.lower():
                                    value_str = value_str.lower().replace("million", "").strip()
                                    value = float(value_str) * 1_000_000
                                elif "billion" in value_str.lower():
                                    value_str = value_str.lower().replace("billion", "").strip()
                                    value = float(value_str) * 1_000_000_000
                                else:
                                    value = float(value_str)
                                deal["value"] = value
                            elif not isinstance(value_str, (int, float)):
                                deal["value"] = None
                    except (ValueError, TypeError):
                        deal["value"] = None
                    
                    # Ensure required fields
                    deal["date"] = deal.get("date", "Not specified")
                    deal["parties"] = deal.get("parties", ["Unknown"])
                    deal["description"] = deal.get("description", "Not available")
                    processed_deals.append(deal)
                result["licensing_deals"] = processed_deals
        else:
            result["licensing_deals"] = []
            
        # Process disclosed investments
        if "disclosed_investments" in result:
            if not isinstance(result["disclosed_investments"], list):
                result["disclosed_investments"] = []
            else:
                processed_investments = []
                for inv in result["disclosed_investments"]:
                    if not isinstance(inv, dict):
                        continue
                    try:
                        # Convert amount to float
                        if "amount" in inv:
                            amount_str = inv["amount"]
                            if isinstance(amount_str, str):
                                # Extract numeric value from string
                                amount_str = amount_str.replace("$", "").replace(",", "")
                                if "million" in amount_str.lower():
                                    amount_str = amount_str.lower().replace("million", "").strip()
                                    amount = float(amount_str) * 1_000_000
                                elif "billion" in amount_str.lower():
                                    amount_str = amount_str.lower().replace("billion", "").strip()
                                    amount = float(amount_str) * 1_000_000_000
                                else:
                                    amount = float(amount_str)
                                inv["amount"] = amount
                        
                        # Convert investors list to single investor string
                        if "investors" in inv:
                            inv["investor"] = inv["investors"][0] if inv["investors"] else "Unknown"
                            del inv["investors"]
                        elif "investor" not in inv:
                            inv["investor"] = "Unknown"
                            
                        # Ensure required fields
                        inv["date"] = inv.get("date", "Not specified")
                        inv["type"] = inv.get("type", "Not specified")
                        processed_investments.append(inv)
                    except (ValueError, TypeError, IndexError):
                        continue
                result["disclosed_investments"] = processed_investments
        else:
            result["disclosed_investments"] = []
            
        return result
        
    async def generate_overview(self, drug_name: str, moa_data: Dict[str, str], clinical_data: Dict[str, List]) -> Dict[str, str]:
        """Generate overview using LLM."""
        system_prompt = """You are a senior biotech analyst creating executive summaries.
        Focus on key value drivers and market potential.
        Format your response as JSON with a 'description' field."""
        
        data = {
            "drug_name": drug_name,
            "mechanism_of_action": moa_data,
            "clinical_data": clinical_data
        }
        
        response = await self._generate_response(
            json.dumps(data),
            system_prompt=system_prompt
        )
        return json.loads(response)
        
    def create_workflow(self) -> Graph:
        """Create the LangGraph workflow."""
        workflow = Graph()
        
        # Define nodes
        workflow.add_node("retrieve_data", self.retrieve_data)
        workflow.add_node("analyze_moa", self.analyze_mechanism_of_action)
        workflow.add_node("analyze_clinical", self.analyze_clinical_activity)
        workflow.add_node("analyze_financial", self.analyze_financial_status)
        workflow.add_node("generate_overview", self.generate_overview)
        
        # Define edges
        workflow.add_edge("retrieve_data", "analyze_moa")
        workflow.add_edge("retrieve_data", "analyze_clinical")
        workflow.add_edge("retrieve_data", "analyze_financial")
        workflow.add_edge("analyze_moa", "generate_overview")
        workflow.add_edge("analyze_clinical", "generate_overview")
        
        return workflow
        
    async def evaluate_asset(self, drug_name: str, company_name: str = None) -> BiotechAssetReport:
        """Run the evaluation workflow and generate report."""
        # Treat empty string as None
        if not company_name:
            company_name = None
            
        # Retrieve and analyze data
        raw_data = await self.retrieve_data(drug_name, company_name)
        
        moa_data = await self.analyze_mechanism_of_action(raw_data["pubmed_articles"])
        clinical_data = await self.analyze_clinical_activity(raw_data["clinical_trials"])
        overview_data = await self.generate_overview(drug_name, moa_data, clinical_data)
        
        # Create default financial data when not available
        default_financial_data = {
            "ownership_type": "Not available",
            "funding": "Not available",
            "revenue": "Not available",
            "licensing_deals": [],
            "disclosed_investments": []
        }
        
        financial_data = None
        if company_name and raw_data["company_info"] and raw_data["licensing_deals"]:
            financial_data = await self.analyze_financial_status(
                raw_data["company_info"],
                raw_data["licensing_deals"]
            )
        
        # Compile report
        report = BiotechAssetReport(
            drug_name=drug_name,
            developer_organization=company_name if company_name else "Not available",
            overview=Overview(**overview_data),
            mechanism_of_action=MechanismOfAction(**moa_data),
            clinical_activity=ClinicalActivity(**clinical_data),
            developer_financial_status=DeveloperFinancialStatus(**(financial_data or default_financial_data))
        )
        
        return report 