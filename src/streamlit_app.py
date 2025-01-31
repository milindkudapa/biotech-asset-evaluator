import streamlit as st
import httpx
import json
from typing import Dict, Any, List
import asyncio
from dotenv import load_dotenv
import os
import logging
from utils.logging_config import setup_logging

# Set up logging
loggers = setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

logger.info("Starting Biotech Asset Evaluator application")

# Configure page
st.set_page_config(
    page_title="Biotech Asset Evaluator",
    page_icon="🧬",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_analysis" not in st.session_state:
    st.session_state.current_analysis = None
if "analysis_type" not in st.session_state:
    st.session_state.analysis_type = None

# Custom CSS
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background: #e3f2fd;
        border-left: 5px solid #2196f3;
    }
    .assistant-message {
        background: #f5f5f5;
        border-left: 5px solid #4caf50;
    }
    .stButton button {
        background-color: #4CAF50;
        color: white;
        border-radius: 20px;
        padding: 10px 20px;
        border: none;
    }
    .stButton button:hover {
        background-color: #45a049;
    }
    h1 {
        color: #1a237e;
        padding-bottom: 20px;
        border-bottom: 2px solid #e0e0e0;
    }
    h2 {
        color: #283593;
        padding: 10px 0;
        margin-top: 20px;
    }
    h3 {
        color: #303f9f;
        padding: 8px 0;
    }
    h4 {
        color: #3949ab;
        padding: 5px 0;
    }
    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .row-widget.stButton {
        text-align: center;
        padding: 10px 0;
    }
    .data-label {
        font-weight: bold;
        color: #424242;
    }
    .data-value {
        color: #212121;
        padding-left: 10px;
    }
    .section-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .metric-container {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
async def make_api_request(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Make an async request to the FastAPI backend."""
    api_url = f"http://localhost:8000{endpoint}"
    api_logger = logging.getLogger('api')
    api_logger.info(f"Making request to {endpoint} with data: {data}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:  # Increased timeout to 5 minutes
        try:
            # First check if the API is reachable
            try:
                await client.get("http://localhost:8000/health", timeout=5.0)
            except httpx.ConnectError as e:
                api_logger.error(f"API server not reachable: {str(e)}")
                return {
                    "error": "Cannot connect to the API server. Please ensure the backend server is running and try again."
                }
            
            # Make the actual request
            try:
                api_logger.debug(f"Sending POST request to {api_url}")
                
                # For complete evaluation, use longer timeout
                if endpoint == "/evaluate":
                    timeout = httpx.Timeout(300.0, connect=5.0)  # 5 minutes for complete eval
                else:
                    timeout = httpx.Timeout(120.0, connect=5.0)  # 2 minutes for other endpoints
                
                response = await client.post(
                    api_url,
                    json=data,
                    timeout=timeout
                )
                response.raise_for_status()
                result = response.json()
                api_logger.info(f"Successfully received response from {endpoint}")
                api_logger.debug(f"Response data: {result}")
                return result
            except httpx.TimeoutException as e:
                api_logger.error(f"Request to {endpoint} timed out: {str(e)}")
                return {
                    "error": "The analysis is taking longer than expected. Please try again or use a more specific analysis type."
                }
            except httpx.HTTPStatusError as e:
                api_logger.error(f"HTTP error for {endpoint}: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 404:
                    return {
                        "error": f"The requested endpoint {endpoint} was not found. Please check your request."
                    }
                elif e.response.status_code == 422:
                    return {
                        "error": "Invalid input data provided. Please check your request parameters."
                    }
                else:
                    return {
                        "error": f"Server error occurred: {e.response.status_code}"
                    }
            except httpx.RequestError as e:
                api_logger.error(f"Request error for {endpoint}: {str(e)}")
                return {
                    "error": "Failed to make the request. Please check your connection and try again."
                }
        except Exception as e:
            api_logger.error(f"Unexpected error for {endpoint}: {str(e)}", exc_info=True)
            return {
                "error": "An unexpected error occurred. Please try again later."
            }

def format_json_content(content: Any) -> str:
    """Format JSON content for better display."""
    if isinstance(content, list):
        if not content:
            return "Not available"
        return "\n".join(f"• {item}" for item in content)
    elif isinstance(content, dict):
        if not content:
            return "Not available"
        formatted = []
        for key, value in content.items():
            formatted.append(f"**{key.replace('_', ' ').title()}**: {value}")
        return "\n".join(formatted)
    elif content is None:
        return "Not available"
    return str(content)

def format_data_row(label: str, value: Any, is_markdown: bool = False) -> str:
    """Format a data row with consistent styling."""
    formatted_value = format_json_content(value) if not is_markdown else value
    return f'<div><span class="data-label">{label}:</span><span class="data-value">{formatted_value}</span></div>'

def display_analysis_results(result: Dict[str, Any], analysis_type: str):
    """Display analysis results in a structured format."""
    if "error" in result:
        logger.error(f"Error in {analysis_type} analysis: {result['error']}")
        st.error(result["error"])
        return

    logger.info(f"Displaying {analysis_type} analysis results")
    
    if analysis_type == "Complete":
        # Drug name and organization header
        st.title(f"🔬 {result.get('drug_name', 'Unknown Drug')} Analysis")
        st.subheader(f"by {result.get('developer_organization', 'Unknown Organization')}")
        
        # Overview Section
        if result.get("overview"):
            with st.container():
                st.markdown('<div class="section-container">', unsafe_allow_html=True)
                st.markdown("### 📋 Overview")
                overview_text = result["overview"].get("description", "No overview available")
                st.markdown(overview_text)
                
                if result["overview"].get("key_points"):
                    st.markdown("#### Key Points")
                    for point in result["overview"]["key_points"]:
                        st.markdown(f"• {point}")
                st.markdown('</div>', unsafe_allow_html=True)
            
        # Mechanism of Action Section
        with st.container():
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown("### 🧬 Mechanism of Action")
            moa = result.get("mechanism_of_action", {})
            
            col1, col2 = st.columns(2)
            with col1:
                with st.container():
                    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                    st.markdown("#### Target Pathways")
                    pathways = moa.get("target_pathways", [])
                    if isinstance(pathways, list):
                        for pathway in pathways:
                            st.markdown(f"• {pathway}")
                    else:
                        st.markdown(pathways)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                with st.container():
                    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                    st.markdown("#### Biology")
                    biology = moa.get("biology", {})
                    if isinstance(biology, dict):
                        for key, value in biology.items():
                            st.markdown(f"**{key.replace('_', ' ').title()}**")
                            st.markdown(format_json_content(value))
                    else:
                        st.markdown(biology)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if moa.get("detailed_description"):
                st.markdown("#### Detailed Description")
                st.markdown(moa["detailed_description"])
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Clinical Activity Section
        with st.container():
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown("### 🏥 Clinical Activity")
            clinical = result.get("clinical_activity", {})
            
            # Summary metrics if available
            if clinical.get("summary"):
                cols = st.columns(4)
                metrics = {
                    "Total Trials": clinical["summary"].get("total_trials", 0),
                    "Ongoing": clinical["summary"].get("ongoing_count", 0),
                    "Completed": clinical["summary"].get("completed_count", 0),
                    "Success Rate": f"{clinical['summary'].get('success_rate', 0)}%"
                }
                for col, (label, value) in zip(cols, metrics.items()):
                    with col:
                        st.metric(label, value)
            
            tabs = st.tabs(["Ongoing Trials", "Completed Trials"])
            
            with tabs[0]:
                if clinical.get("ongoing_trials"):
                    for trial in clinical["ongoing_trials"]:
                        with st.expander(trial.get("title", "Unknown Trial")):
                            st.markdown(format_data_row("NCT ID", trial.get("nct_id", "Not available")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Phase", trial.get("phase", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Status", trial.get("status", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Start Date", trial.get("start_date", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Estimated Completion", trial.get("estimated_completion", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Conditions", format_json_content(trial.get("conditions", []))), unsafe_allow_html=True)
                            
                            if trial.get('description'):
                                st.markdown("##### Study Description")
                                st.markdown(trial['description'])
                            
                            if trial.get('endpoints'):
                                st.markdown("##### Endpoints")
                                for endpoint in trial['endpoints']:
                                    st.markdown(f"• {endpoint}")
                else:
                    st.info("No ongoing trials found")
            
            with tabs[1]:
                if clinical.get("completed_trials"):
                    for trial in clinical["completed_trials"]:
                        with st.expander(trial.get("title", "Unknown Trial")):
                            st.markdown(format_data_row("NCT ID", trial.get("nct_id", "Not available")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Phase", trial.get("phase", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Status", trial.get("status", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Completion Date", trial.get("completion_date", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Conditions", format_json_content(trial.get("conditions", []))), unsafe_allow_html=True)
                            
                            if trial.get('results'):
                                st.markdown("##### Results")
                                st.markdown(trial['results'])
                            
                            if trial.get('publications'):
                                st.markdown("##### Related Publications")
                                for pub in trial['publications']:
                                    st.markdown(f"• [{pub['title']}]({pub['url']})")
                else:
                    st.info("No completed trials found")
            st.markdown('</div>', unsafe_allow_html=True)
                    
        # Financial Status Section
        with st.container():
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown("### 💰 Developer Financial Status")
            financial = result.get("developer_financial_status", {})
            
            # Financial metrics
            if financial.get("metrics"):
                metrics = financial["metrics"]
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Market Cap", f"${metrics.get('market_cap', 0):,.2f}M")
                with cols[1]:
                    st.metric("Cash Position", f"${metrics.get('cash_position', 0):,.2f}M")
                with cols[2]:
                    st.metric("Burn Rate", f"${metrics.get('burn_rate', 0):,.2f}M/month")
            
            col1, col2 = st.columns(2)
            with col1:
                with st.container():
                    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                    st.markdown("#### Company Overview")
                    st.markdown(format_data_row("Ownership Type", financial.get("ownership_type", "Not available")), unsafe_allow_html=True)
                    st.markdown(format_data_row("Funding Status", financial.get("funding", "Not available")), unsafe_allow_html=True)
                    if financial.get("funding_rounds"):
                        st.markdown("##### Funding Rounds")
                        for round in financial["funding_rounds"]:
                            st.markdown(f"• {round['date']}: ${round['amount']:,.2f}M ({round['type']})")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                with st.container():
                    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                    st.markdown("#### Financial Details")
                    st.markdown(format_data_row("Revenue", financial.get("revenue", "Not available")), unsafe_allow_html=True)
                    if financial.get("financial_highlights"):
                        st.markdown("##### Highlights")
                        for highlight in financial["financial_highlights"]:
                            st.markdown(f"• {highlight}")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if financial.get("licensing_deals"):
                st.markdown("#### 🤝 Licensing Deals")
                for deal in financial["licensing_deals"]:
                    with st.expander(f"Deal on {deal.get('date', 'Unknown Date')}"):
                        st.markdown(format_data_row("Parties", format_json_content(deal.get("parties", []))), unsafe_allow_html=True)
                        value = deal.get('value')
                        if value is None:
                            st.markdown(format_data_row("Value", "Not disclosed"), unsafe_allow_html=True)
                        else:
                            st.markdown(format_data_row("Value", f"${value:,.2f}M"), unsafe_allow_html=True)
                        
                        if deal.get('terms'):
                            st.markdown("##### Deal Terms")
                            for term in deal['terms']:
                                st.markdown(f"• {term}")
                        
                        st.markdown(format_data_row("Description", deal.get("description", "No description available")), unsafe_allow_html=True)
            
            if financial.get("disclosed_investments"):
                st.markdown("#### 💸 Investments")
                for investment in financial["disclosed_investments"]:
                    with st.expander(f"Investment on {investment.get('date', 'Unknown Date')}"):
                        st.markdown(format_data_row("Investor", investment.get("investor", "Unknown")), unsafe_allow_html=True)
                        st.markdown(format_data_row("Type", investment.get("type", "Not specified")), unsafe_allow_html=True)
                        amount = investment.get('amount')
                        if amount:
                            st.markdown(format_data_row("Amount", f"${amount:,.2f}M"), unsafe_allow_html=True)
                        else:
                            st.markdown(format_data_row("Amount", "Not disclosed"), unsafe_allow_html=True)
                        
                        if investment.get('details'):
                            st.markdown("##### Investment Details")
                            for detail in investment['details']:
                                st.markdown(f"• {detail}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    elif analysis_type == "Moa":
        with st.container():
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown("### 🧬 Mechanism of Action Analysis")
            
            # Target Pathways
            st.markdown("#### Target Pathways")
            pathways = result.get("target_pathways", [])
            if isinstance(pathways, list):
                for pathway in pathways:
                    st.markdown(f"• {pathway}")
            else:
                st.markdown(pathways)
            
            # Biology
            st.markdown("#### Biological Mechanism")
            biology = result.get("biology", {})
            if isinstance(biology, dict):
                for key, value in biology.items():
                    st.markdown(f"**{key.replace('_', ' ').title()}**")
                    st.markdown(format_json_content(value))
            else:
                st.markdown(biology)
            
            # Additional MOA details if available
            if result.get("detailed_description"):
                st.markdown("#### Detailed Description")
                st.markdown(result["detailed_description"])
            
            if result.get("references"):
                st.markdown("#### References")
                for ref in result["references"]:
                    st.markdown(f"• {ref}")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    elif analysis_type == "Clinical":
        with st.container():
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown("### 🏥 Clinical Trials Analysis")
            
            # Summary metrics if available
            if result.get("summary"):
                cols = st.columns(4)
                metrics = {
                    "Total Trials": result["summary"].get("total_trials", 0),
                    "Ongoing": result["summary"].get("ongoing_count", 0),
                    "Completed": result["summary"].get("completed_count", 0),
                    "Success Rate": f"{result['summary'].get('success_rate', 0)}%"
                }
                for col, (label, value) in zip(cols, metrics.items()):
                    with col:
                        st.metric(label, value)
            
            if not result.get("ongoing_trials") and not result.get("completed_trials"):
                st.info("No clinical trials found.")
                return
            
            tabs = st.tabs(["Ongoing Trials", "Completed Trials"])
            
            with tabs[0]:
                if result.get("ongoing_trials"):
                    for trial in result["ongoing_trials"]:
                        with st.expander(trial.get("title", "Unknown Trial")):
                            st.markdown(format_data_row("NCT ID", trial.get("nct_id", "Not available")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Phase", trial.get("phase", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Status", trial.get("status", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Start Date", trial.get("start_date", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Estimated Completion", trial.get("estimated_completion", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Conditions", format_json_content(trial.get("conditions", []))), unsafe_allow_html=True)
                            
                            if trial.get('description'):
                                st.markdown("##### Study Description")
                                st.markdown(trial['description'])
                            
                            if trial.get('endpoints'):
                                st.markdown("##### Endpoints")
                                for endpoint in trial['endpoints']:
                                    st.markdown(f"• {endpoint}")
                else:
                    st.info("No ongoing trials found")
            
            with tabs[1]:
                if result.get("completed_trials"):
                    for trial in result["completed_trials"]:
                        with st.expander(trial.get("title", "Unknown Trial")):
                            st.markdown(format_data_row("NCT ID", trial.get("nct_id", "Not available")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Phase", trial.get("phase", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Status", trial.get("status", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Completion Date", trial.get("completion_date", "Unknown")), unsafe_allow_html=True)
                            st.markdown(format_data_row("Conditions", format_json_content(trial.get("conditions", []))), unsafe_allow_html=True)
                            
                            if trial.get('results'):
                                st.markdown("##### Results")
                                st.markdown(trial['results'])
                            
                            if trial.get('publications'):
                                st.markdown("##### Related Publications")
                                for pub in trial['publications']:
                                    st.markdown(f"• [{pub['title']}]({pub['url']})")
                else:
                    st.info("No completed trials found")
            st.markdown('</div>', unsafe_allow_html=True)
    
    elif analysis_type == "Financial":
        with st.container():
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown("### 💰 Financial Analysis")
            
            # Financial metrics
            if result.get("metrics"):
                metrics = result["metrics"]
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Market Cap", f"${metrics.get('market_cap', 0):,.2f}M")
                with cols[1]:
                    st.metric("Cash Position", f"${metrics.get('cash_position', 0):,.2f}M")
                with cols[2]:
                    st.metric("Burn Rate", f"${metrics.get('burn_rate', 0):,.2f}M/month")
            
            col1, col2 = st.columns(2)
            with col1:
                with st.container():
                    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                    st.markdown("#### Company Overview")
                    st.markdown(format_data_row("Ownership Type", result.get("ownership_type", "Not available")), unsafe_allow_html=True)
                    st.markdown(format_data_row("Funding Status", result.get("funding", "Not available")), unsafe_allow_html=True)
                    if result.get("funding_rounds"):
                        st.markdown("##### Funding Rounds")
                        for round in result["funding_rounds"]:
                            st.markdown(f"• {round['date']}: ${round['amount']:,.2f}M ({round['type']})")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                with st.container():
                    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                    st.markdown("#### Financial Details")
                    st.markdown(format_data_row("Revenue", result.get("revenue", "Not available")), unsafe_allow_html=True)
                    if result.get("financial_highlights"):
                        st.markdown("##### Highlights")
                        for highlight in result["financial_highlights"]:
                            st.markdown(f"• {highlight}")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if result.get("licensing_deals"):
                st.markdown("#### 🤝 Licensing Deals")
                for deal in result["licensing_deals"]:
                    with st.expander(f"Deal on {deal.get('date', 'Unknown Date')}"):
                        st.markdown(format_data_row("Parties", format_json_content(deal.get("parties", []))), unsafe_allow_html=True)
                        value = deal.get('value')
                        if value is None:
                            st.markdown(format_data_row("Value", "Not disclosed"), unsafe_allow_html=True)
                        else:
                            st.markdown(format_data_row("Value", f"${value:,.2f}M"), unsafe_allow_html=True)
                        
                        if deal.get('terms'):
                            st.markdown("##### Deal Terms")
                            for term in deal['terms']:
                                st.markdown(f"• {term}")
                        
                        st.markdown(format_data_row("Description", deal.get("description", "No description available")), unsafe_allow_html=True)
            else:
                st.info("No licensing deals found.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    elif analysis_type == "Overview":
        with st.container():
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown("### 📋 Drug Overview")
            
            if "description" in result:
                st.markdown(result["description"])
            
            if result.get("key_points"):
                st.markdown("#### Key Points")
                for point in result["key_points"]:
                    st.markdown(f"• {point}")
            
            if result.get("development_status"):
                st.markdown("#### Development Status")
                st.markdown(result["development_status"])
            
            if result.get("indications"):
                st.markdown("#### Indications")
                for indication in result["indications"]:
                    st.markdown(f"• {indication}")
            
            if not any(key in result for key in ["description", "key_points", "development_status", "indications"]):
                st.info("No overview information available.")
            
            st.markdown('</div>', unsafe_allow_html=True)

def process_user_input(user_input: str) -> Dict[str, Any]:
    """Process user input to determine the type of analysis needed."""
    logger.info(f"Processing user input: {user_input}")
    input_lower = user_input.lower()
    
    # Extract drug or company name first
    drug_name = extract_drug_name(user_input)
    company_name = extract_company_name(user_input)
    
    if not drug_name and not company_name:
        # If no specific name found, use the word after the analysis type
        words = input_lower.split()
        for i, word in enumerate(words):
            if i + 1 < len(words):
                if "mechanism" in word or "moa" in word:
                    drug_name = words[i + 1]
                elif "clinical" in word or "trials" in word:
                    drug_name = words[i + 1]
                elif "financial" in word or "company" in word:
                    company_name = words[i + 1]
                elif "overview" in word or "complete" in word or "evaluate" in word:
                    drug_name = words[i + 1]
    
    # Log only when no valid input is found
    if not drug_name and not company_name:
        logger.warning(f"Could not extract drug or company name from input: {user_input}")
    else:
        logger.info(f"Extracted drug_name: {drug_name}, company_name: {company_name}")
    
    if "complete" in input_lower or "evaluate" in input_lower:
        logger.info("Processing complete evaluation request")
        return {
            "type": "complete",
            "endpoint": "/evaluate",
            "data": {"drug_name": drug_name, "company_name": company_name}
        }
    elif "mechanism" in input_lower or "moa" in input_lower:
        logger.info("Processing mechanism of action request")
        return {
            "type": "moa",
            "endpoint": "/analyze/moa",
            "data": {"drug_name": drug_name}
        }
    elif "clinical" in input_lower or "trials" in input_lower:
        logger.info("Processing clinical trials request")
        return {
            "type": "clinical",
            "endpoint": "/analyze/clinical",
            "data": {"drug_name": drug_name}
        }
    elif "financial" in input_lower or "company" in input_lower:
        logger.info("Processing financial status request")
        return {
            "type": "financial",
            "endpoint": "/analyze/financial",
            "data": {"company_name": company_name}
        }
    elif "overview" in input_lower:
        logger.info("Processing overview request")
        return {
            "type": "overview",
            "endpoint": "/analyze/overview",
            "data": {"drug_name": drug_name}
        }
    else:
        logger.warning(f"Unknown analysis type requested: {user_input}")
        return {
            "type": "unknown",
            "error": "I'm not sure what analysis you're looking for. Please specify if you want to analyze mechanism of action, clinical trials, financial status, get an overview, or perform a complete evaluation."
        }

def extract_drug_name(text: str) -> str:
    """Extract drug name from user input."""
    words = text.split()
    for i, word in enumerate(words):
        if word.lower() in ["drug", "for", "about", "of"]:
            if i + 1 < len(words):
                return words[i + 1]
    return ""

def extract_company_name(text: str) -> str:
    """Extract company name from user input."""
    words = text.split()
    for i, word in enumerate(words):
        if word.lower() in ["company", "for", "about", "of"]:
            if i + 1 < len(words):
                return words[i + 1]
    return ""

# Main interface
logger.info("Initializing main interface")

# Sidebar for analysis type selection
with st.sidebar:
    st.markdown("### Analysis Type")
    analysis_options = {
        "complete": "🔍 Complete Evaluation",
        "moa": "🧬 Mechanism of Action",
        "clinical": "🏥 Clinical Trials",
        "financial": "💰 Financial Status",
        "overview": "📋 Overview"
    }
    
    for key, label in analysis_options.items():
        if st.button(label, key=f"btn_{key}", use_container_width=True):
            st.session_state.analysis_type = key
            st.session_state.current_analysis = None
    
    st.markdown("---")
    
    if st.button("Clear Analysis", use_container_width=True):
        st.session_state.analysis_type = None
        st.session_state.current_analysis = None
        st.session_state.messages = []
        st.rerun()

# Main content area
if st.session_state.analysis_type:
    st.markdown(f"### {analysis_options[st.session_state.analysis_type]}")
    
    # Input form based on analysis type
    with st.form(key="analysis_form"):
        if st.session_state.analysis_type == "complete":
            drug_name = st.text_input("Drug Name*", key="drug_name")
            company_name = st.text_input("Company Name", key="company_name")
            submit = st.form_submit_button("Analyze", use_container_width=True)
            
            if submit and drug_name:
                analysis_request = {
                    "type": "complete",
                    "endpoint": "/evaluate",
                    "data": {"drug_name": drug_name, "company_name": company_name if company_name else None}
                }
                st.session_state.current_analysis = analysis_request
        
        elif st.session_state.analysis_type == "moa":
            drug_name = st.text_input("Drug Name*", key="drug_name")
            submit = st.form_submit_button("Analyze Mechanism of Action", use_container_width=True)
            
            if submit and drug_name:
                analysis_request = {
                    "type": "moa",
                    "endpoint": "/analyze/moa",
                    "data": {"drug_name": drug_name}
                }
                st.session_state.current_analysis = analysis_request
        
        elif st.session_state.analysis_type == "clinical":
            drug_name = st.text_input("Drug Name*", key="drug_name")
            phase_filter = st.multiselect(
                "Trial Phase Filter",
                options=["Phase 1", "Phase 2", "Phase 3", "Phase 4"],
                default=None
            )
            status_filter = st.multiselect(
                "Trial Status Filter",
                options=["Recruiting", "Completed", "Active", "Terminated"],
                default=None
            )
            submit = st.form_submit_button("Analyze Clinical Trials", use_container_width=True)
            
            if submit and drug_name:
                analysis_request = {
                    "type": "clinical",
                    "endpoint": "/analyze/clinical",
                    "data": {
                        "drug_name": drug_name,
                        "phase_filter": phase_filter if phase_filter else None,
                        "status_filter": status_filter if status_filter else None
                    }
                }
                st.session_state.current_analysis = analysis_request
        
        elif st.session_state.analysis_type == "financial":
            company_name = st.text_input("Company Name*", key="company_name")
            include_deals = st.checkbox("Include Licensing Deals", value=True)
            include_investments = st.checkbox("Include Investments", value=True)
            submit = st.form_submit_button("Analyze Financial Status", use_container_width=True)
            
            if submit and company_name:
                analysis_request = {
                    "type": "financial",
                    "endpoint": "/analyze/financial",
                    "data": {
                        "company_name": company_name,
                        "include_deals": include_deals,
                        "include_investments": include_investments
                    }
                }
                st.session_state.current_analysis = analysis_request
        
        elif st.session_state.analysis_type == "overview":
            drug_name = st.text_input("Drug Name*", key="drug_name")
            submit = st.form_submit_button("Get Overview", use_container_width=True)
            
            if submit and drug_name:
                analysis_request = {
                    "type": "overview",
                    "endpoint": "/analyze/overview",
                    "data": {"drug_name": drug_name}
                }
                st.session_state.current_analysis = analysis_request

    # Process analysis request if exists
    if st.session_state.current_analysis:
        with st.spinner("Analyzing... This may take a few minutes for comprehensive evaluations..."):
            logger.info(f"Making API request for {st.session_state.current_analysis['type']} analysis")
            
            # Add progress message for complete evaluations
            if st.session_state.current_analysis['type'] == 'complete':
                st.info("Performing comprehensive evaluation. This may take up to 5 minutes...")
            
            result = asyncio.run(make_api_request(
                st.session_state.current_analysis["endpoint"],
                st.session_state.current_analysis["data"]
            ))
            
            if "error" not in result:
                logger.info(f"Successfully completed {st.session_state.current_analysis['type']} analysis")
                display_analysis_results(result, st.session_state.current_analysis["type"].title())
            else:
                logger.error(f"Error in API response: {result['error']}")
                if "timeout" in result["error"].lower():
                    st.error(
                        "The analysis is taking longer than expected. You can try:\n"
                        "- Breaking down the analysis into specific parts (MOA, Clinical, etc.)\n"
                        "- Checking if the API server is under heavy load\n"
                        "- Trying again in a few minutes"
                    )
                else:
                    st.error(f"Error: {result['error']}")

else:
    # Welcome message when no analysis type is selected
    st.markdown("""
    Welcome to the Biotech Asset Evaluator! Select an analysis type from the sidebar to begin:
    
    - 🔍 **Complete Evaluation**: Comprehensive analysis of a drug and its developer
    - 🧬 **Mechanism of Action**: Detailed analysis of how a drug works
    - 🏥 **Clinical Trials**: Information about ongoing and completed trials
    - 💰 **Financial Status**: Company financial analysis and deals
    - 📋 **Overview**: Quick summary of a drug
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <small>Powered by AI - Analyzing biotech assets using clinical trials, scientific literature, and market data</small>
</div>
""", unsafe_allow_html=True)

logger.info("Application ready for user interaction")

# Sidebar with additional information
with st.sidebar:
    st.markdown("### How to Use")
    st.markdown("""
    Try asking questions like:
    - "What's the mechanism of action for [drug name]?"
    - "Show me clinical trials for [drug name]"
    - "What's the financial status of [company name]?"
    - "Give me an overview of [drug name]"
    - "Evaluate [drug name] by [company name]"
    """) 