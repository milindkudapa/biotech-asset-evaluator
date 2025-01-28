from typing import Dict, Any, List, Annotated, TypedDict, Literal
import asyncio
from langgraph.graph import Graph, StateGraph, END
from langgraph.prebuilt.tool_executor import ToolExecutor
from langgraph.checkpoint.memory import MemorySaver
from openai import AsyncOpenAI
import json
import os
from dotenv import load_dotenv
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel
import networkx as nx
import matplotlib.pyplot as plt

from ..clients.api_clients import (
    ClinicalTrialsClient,
    PubMedClient,
    ExaClient,
    TavilySearchClient
)
from ..models.schemas import (
    BiotechAssetReport,
    Overview,
    MechanismOfAction,
    ClinicalActivity,
    DeveloperFinancialStatus,
    ClinicalTrial,
    RegulatoryUpdate,
    LicensingDeal,
    Investment
)

load_dotenv()

class WorkflowState(TypedDict):
    """State management for the biotech evaluation workflow."""
    drug_name: str
    company_name: str | None
    raw_data: Dict[str, Any]
    moa_analysis: Dict[str, str]
    clinical_analysis: Dict[str, List]
    financial_analysis: Dict[str, Any]
    overview: Dict[str, str]
    final_report: Dict[str, Any] | None

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
        
        # Initialize memory saver for state persistence
        self.checkpointer = MemorySaver()
        
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
            model="gpt-4o-2024-11-20",
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

    async def retrieve_data(self, state: Dict) -> Dict[str, Any]:
        """Retrieve data from all sources concurrently."""
        drug_name = state["drug_name"]
        company_name = state["company_name"]
        
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
        
        return {"raw_data": processed_results}

    async def analyze_mechanism_of_action(self, state: Dict) -> Dict[str, Any]:
        """Analyze mechanism of action using LLM."""
        pubmed_data = state["raw_data"]["pubmed_articles"]
        
        system_prompt = """You are a biotech expert specializing in drug mechanism analysis. 
        Analyze scientific literature to understand drug mechanisms of action.
        Focus on molecular pathways, targets, and biological processes.
        Format your response as JSON with 'target_pathways' and 'biology' fields."""
        
        # Extract content from pubmed_data
        if not pubmed_data or not isinstance(pubmed_data, list):
            return {"moa_analysis": {
                "target_pathways": "Not available",
                "biology": "Not available"
            }}
            
        # Get the content from the first (and only) item
        content = pubmed_data[0].get("content", "") if pubmed_data else ""
        if not content:
            return {"moa_analysis": {
                "target_pathways": "Not available",
                "biology": "Not available"
            }}
            
        # Split content into manageable chunks
        chunks = self._chunk_text(content)
        chunk_results = await self._process_chunks(chunks, system_prompt)
        
        # Initialize lists for collecting results
        target_pathways = []
        biology = []
        
        # Process each chunk result
        for result in chunk_results:
            if isinstance(result, dict):
                if "target_pathways" in result:
                    if isinstance(result["target_pathways"], str):
                        target_pathways.append(result["target_pathways"])
                    elif isinstance(result["target_pathways"], list):
                        target_pathways.extend(str(item) for item in result["target_pathways"])
                    elif result["target_pathways"] is not None:
                        target_pathways.append(str(result["target_pathways"]))
                
                if "biology" in result:
                    if isinstance(result["biology"], str):
                        biology.append(result["biology"])
                    elif isinstance(result["biology"], list):
                        biology.extend(str(item) for item in result["biology"])
                    elif result["biology"] is not None:
                        biology.append(str(result["biology"]))
        
        return {"moa_analysis": {
            "target_pathways": "; ".join(target_pathways) if target_pathways else "Not available",
            "biology": "; ".join(biology) if biology else "Not available"
        }}

    async def analyze_clinical_activity(self, state: Dict) -> Dict[str, Any]:
        """Analyze clinical trial data using LLM."""
        trials_data = state["raw_data"]["clinical_trials"]
        
        system_prompt = """You are a clinical trial analyst with expertise in biotech.
        Focus on trial phases, outcomes, and regulatory implications.
        Format your response as JSON with 'ongoing_trials', 'completed_trials', and 'regulatory_updates' fields."""
        
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
                        if isinstance(item, dict):
                            if key in ["ongoing_trials", "completed_trials"]:
                                processed_item = {
                                    "nct_id": str(item.get("nct_id", "Not available")),
                                    "title": str(item.get("title", "Not available")),
                                    "phase": str(item.get("phase", "NA")),
                                    "status": str(item.get("status", "Not available")).upper(),
                                    "conditions": [str(c) for c in item.get("conditions", [])] if isinstance(item.get("conditions"), list) else [],
                                    "description": str(item.get("description", "Not available"))
                                }
                                merged_result[key].append(processed_item)
                            elif key == "regulatory_updates":
                                date_str = item.get("date", "2024-01-01")
                                if not isinstance(date_str, str) or not date_str.count("-") == 2:
                                    date_str = "2024-01-01"
                                
                                agency = str(item.get("agency", "FDA")).upper()
                                if agency not in ["FDA", "EMA", "MHRA"]:
                                    agency = "OTHER"
                                    
                                update_type = str(item.get("type", "UPDATE")).upper()
                                if update_type not in ["APPROVAL", "REJECTION", "HOLD"]:
                                    update_type = "UPDATE"
                                    
                                processed_item = {
                                    "date": date_str,
                                    "agency": agency,
                                    "type": update_type,
                                    "description": str(item.get("description", "Not available"))
                                }
                                merged_result["regulatory_updates"].append(processed_item)
        
        return {"clinical_analysis": merged_result}

    async def analyze_financial_status(self, state: Dict) -> Dict[str, Any]:
        """Analyze company financial data using LLM."""
        company_data = state["raw_data"].get("company_info")
        deals_data = state["raw_data"].get("licensing_deals")
        
        # Create default financial data when not available
        default_financial_data = {
            "ownership_type": "Not available",
            "funding": "Not available",
            "revenue": "Not available",
            "licensing_deals": [],
            "disclosed_investments": []
        }
        
        if not company_data or not deals_data:
            return {"financial_analysis": default_financial_data}
            
        system_prompt = """You are a financial analyst specializing in biotech companies.
        Analyze company financial data and licensing deals.
        Format your response as JSON with fields for ownership_type, funding, revenue, licensing_deals, and disclosed_investments."""
        
        data_str = json.dumps({"company": company_data, "deals": deals_data})
        chunks = self._chunk_text(data_str)
        chunk_results = await self._process_chunks(chunks, system_prompt)
        
        # Process and merge results
        merged_result = {
            "ownership_type": "Not available",
            "funding": "Not available",
            "revenue": "Not available",
            "licensing_deals": [],
            "disclosed_investments": []
        }
        
        for result in chunk_results:
            if isinstance(result, dict):
                for key in merged_result:
                    if key in result:
                        if key in ["licensing_deals", "disclosed_investments"]:
                            items = result[key] if isinstance(result[key], list) else [result[key]]
                            for item in items:
                                if isinstance(item, dict):
                                    merged_result[key].append(item)
                        else:
                            merged_result[key] = str(result[key])
        
        return {"financial_analysis": merged_result}

    async def generate_overview(self, state: Dict) -> Dict[str, Any]:
        """Generate overview using LLM based on analyzed data."""
        drug_name = state["drug_name"]
        moa_data = state["moa_analysis"]
        clinical_data = state["clinical_analysis"]
        
        system_prompt = """You are a biotech analyst specializing in drug development.
        Generate a comprehensive overview of the drug based on mechanism of action and clinical data.
        Format your response as JSON with 'description' field."""
        
        data = {
            "drug_name": drug_name,
            "mechanism_of_action": moa_data,
            "clinical_data": clinical_data
        }
        
        data_str = json.dumps(data)
        chunks = self._chunk_text(data_str)
        chunk_results = await self._process_chunks(chunks, system_prompt)
        
        # Process and merge results
        overview = {
            "description": "Not available"
        }
        
        for result in chunk_results:
            if isinstance(result, dict) and "description" in result:
                overview["description"] = str(result["description"])
        
        return {"overview": overview}

    def should_continue(self, state: Dict) -> Literal["analyze_moa", "analyze_clinical", "analyze_financial", "generate_overview", END]:
        """Determine the next node based on state."""
        # Check if we're coming from retrieve_data
        if state.get("raw_data") and not state.get("moa_analysis"):
            return "analyze_moa"
        # Check if we're coming from analyze_moa
        elif state.get("moa_analysis") and not state.get("clinical_analysis"):
            return "analyze_clinical"
        # Check if we're coming from analyze_clinical
        elif state.get("clinical_analysis") and not state.get("financial_analysis"):
            return "analyze_financial"
        # Check if we're coming from analyze_financial
        elif state.get("financial_analysis") and not state.get("overview"):
            return "generate_overview"
        # If we have everything, we're done
        return END

    def visualize_workflow(self) -> None:
        """Visualize the workflow graph using NetworkX."""
        # Create a new directed graph
        graph = nx.DiGraph()
        
        # Add nodes
        nodes = ["retrieve_data", "analyze_moa", "analyze_clinical", "analyze_financial", "generate_overview", "END"]
        graph.add_nodes_from(nodes)
        
        # Add edges with conditions
        edges = [
            ("retrieve_data", "analyze_moa", "has_raw_data"),
            ("analyze_moa", "analyze_clinical", "has_moa"),
            ("analyze_clinical", "analyze_financial", "has_clinical"),
            ("analyze_financial", "generate_overview", "has_financial"),
            ("generate_overview", "END", "complete"),
            # Add possible early termination edges
            ("retrieve_data", "END", "error"),
            ("analyze_moa", "END", "error"),
            ("analyze_clinical", "END", "error"),
            ("analyze_financial", "END", "error"),
            ("generate_overview", "END", "error")
        ]
        
        # Add edges with their conditions
        for source, target, condition in edges:
            graph.add_edge(source, target, condition=condition)
        
        # Create a new figure
        plt.figure(figsize=(12, 8))
        
        # Define node positions using hierarchical layout
        pos = nx.spring_layout(graph, k=1, iterations=50)
        
        # Draw nodes
        nx.draw_networkx_nodes(graph, pos, 
                             node_color=['lightblue' if node != 'END' else 'lightgreen' for node in graph.nodes()],
                             node_size=2000, alpha=0.7)
        
        # Draw edges
        nx.draw_networkx_edges(graph, pos, edge_color='gray', arrows=True, arrowsize=20)
        
        # Add labels
        nx.draw_networkx_labels(graph, pos)
        
        # Add edge labels
        edge_labels = nx.get_edge_attributes(graph, 'condition')
        nx.draw_networkx_edge_labels(graph, pos, edge_labels)
        
        plt.title("Biotech Asset Evaluation Workflow")
        plt.axis('off')
        plt.tight_layout()
        
        # Save the visualization
        plt.savefig('workflow_graph.png', dpi=300, bbox_inches='tight')
        plt.close()

    def create_workflow(self) -> StateGraph:
        """Create a LangGraph workflow for biotech asset evaluation."""
        # Initialize the graph with state management
        workflow = StateGraph(WorkflowState)
        
        # Define the nodes
        workflow.add_node("retrieve_data", self.retrieve_data)
        workflow.add_node("analyze_moa", self.analyze_mechanism_of_action)
        workflow.add_node("analyze_clinical", self.analyze_clinical_activity)
        workflow.add_node("analyze_financial", self.analyze_financial_status)
        workflow.add_node("generate_overview", self.generate_overview)
        
        # Set retrieve_data as the first node
        workflow.set_entry_point("retrieve_data")
        
        # Add conditional edges for workflow progression with labels
        workflow.add_conditional_edges(
            "retrieve_data",
            self.should_continue,
            {
                "analyze_moa": "analyze_moa",
                END: END
            }
        )
        
        # Add conditional edges for each analysis step
        workflow.add_conditional_edges(
            "analyze_moa",
            self.should_continue,
            {
                "analyze_clinical": "analyze_clinical",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "analyze_clinical",
            self.should_continue,
            {
                "analyze_financial": "analyze_financial",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "analyze_financial",
            self.should_continue,
            {
                "generate_overview": "generate_overview",
                END: END
            }
        )
        
        # Add final conditional edge from overview generation
        workflow.add_conditional_edges(
            "generate_overview",
            self.should_continue,
            {END: END}
        )
        
        # Compile the graph
        return workflow.compile()

    async def evaluate_asset(self, drug_name: str, company_name: str = None) -> BiotechAssetReport:
        """Execute the biotech asset evaluation workflow."""
        # Initialize workflow state
        initial_state = {
            "drug_name": drug_name,
            "company_name": company_name,
            "raw_data": {},
            "moa_analysis": {},
            "clinical_analysis": {},
            "financial_analysis": {},
            "overview": {},
            "final_report": None
        }
        
        # Create and execute the workflow with checkpointing
        workflow = self.create_workflow()
        final_state = await workflow.ainvoke(
            initial_state,
            {"configurable": {
                "checkpointer": self.checkpointer,
                "recursion_limit": 10
            }}
        )
        
        # Convert state back to Pydantic models
        overview = Overview(description=final_state["overview"].get("description", "Not available"))
        
        moa = MechanismOfAction(
            target_pathways=final_state["moa_analysis"].get("target_pathways", "Not available"),
            biology=final_state["moa_analysis"].get("biology", "Not available")
        )
        
        clinical = ClinicalActivity(
            ongoing_trials=[ClinicalTrial(**trial) for trial in final_state["clinical_analysis"].get("ongoing_trials", [])],
            completed_trials=[ClinicalTrial(**trial) for trial in final_state["clinical_analysis"].get("completed_trials", [])],
            regulatory_updates=[RegulatoryUpdate(**update) for update in final_state["clinical_analysis"].get("regulatory_updates", [])]
        )
        
        financial = DeveloperFinancialStatus(
            ownership_type=final_state["financial_analysis"].get("ownership_type", "Not available"),
            funding=final_state["financial_analysis"].get("funding", "Not available"),
            revenue=final_state["financial_analysis"].get("revenue", "Not available"),
            licensing_deals=[LicensingDeal(**deal) for deal in final_state["financial_analysis"].get("licensing_deals", [])],
            disclosed_investments=[Investment(**inv) for inv in final_state["financial_analysis"].get("disclosed_investments", [])]
        )
        
        # Construct the final report
        report = BiotechAssetReport(
            drug_name=drug_name,
            developer_organization=company_name if company_name else "Not available",
            overview=overview,
            mechanism_of_action=moa,
            clinical_activity=clinical,
            developer_financial_status=financial
        )
        
        return report 