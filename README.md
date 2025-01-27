# Biotech Asset Evaluation Agent

An intelligent agent that evaluates biotech drug assets and their developer companies, providing structured reports with insights about mechanism of action, clinical activity, and financial status.

## Features

- Automated evaluation of drug assets and biotech companies
- Data aggregation from multiple sources:
  - ClinicalTrials.gov for trial data
  - PubMed for scientific literature
  - Exa.ai for company information
  - Tavily for licensing deals and investments
- LLM-powered analysis using OpenAI GPT-4
- Structured JSON reports with comprehensive insights
- FastAPI-based REST API

## Project Structure

```
.
├── src/
│   ├── clients/
│   │   └── api_clients.py      # API client implementations
│   ├── models/
│   │   └── schemas.py          # Pydantic models and schemas
│   ├── workflow/
│   │   └── evaluation_workflow.py  # LangGraph workflow
│   └── main.py                 # FastAPI application
├── requirements.txt            # Project dependencies
├── .env                       # Environment variables (not tracked in git)
└── README.md                  # Project documentation
```

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/milindkudapa/lunartree-agent.git
   cd lunartree-agent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_key_here
   PUBMED_API_KEY=your_key_here
   PUBMED_EMAIL=your_email_here
   EXA_API_KEY=your_key_here
   TAVILY_API_KEY=your_key_here
   ```

## Dependencies

Key dependencies include:
- httpx==0.27.2 (for API requests)
- openai>=1.10.0 (OpenAI API client)
- langchain>=0.1.0 (LLM framework)
- langgraph>=0.0.10 (Workflow orchestration)
- tavily-python>=0.2.0 (Tavily API client)
- exa-py>=1.0.0 (Exa.ai API client)
- biopython>=1.83 (PubMed access)
- fastapi>=0.109.0 (API framework)
- pydantic>=2.6.0 (Data validation)

## Usage

1. Start the API server:
   ```bash
   python -m src.main
   ```

2. The API will be available at `http://localhost:8000`

3. Use the `/evaluate` endpoint to evaluate a drug asset:
   ```bash
   curl -X POST "http://localhost:8000/evaluate" \
        -H "Content-Type: application/json" \
        -d '{"drug_name": "example_drug", "company_name": "example_biotech"}'
   ```

4. Access the API documentation at `http://localhost:8000/docs`

## API Response Format

The API returns a structured JSON report with the following sections:

```json
{
  "drug_name": "string",
  "developer_organization": "string",
  "overview": {
    "description": "string"
  },
  "mechanism_of_action": {
    "target_pathways": "string",
    "biology": "string"
  },
  "clinical_activity": {
    "ongoing_trials": [],
    "completed_trials": [],
    "regulatory_updates": []
  },
  "developer_financial_status": {
    "ownership_type": "string",
    "funding": "string",
    "revenue": "string",
    "licensing_deals": [],
    "disclosed_investments": []
  }
}
```

## Required API Keys

The following API keys should be set in your `.env` file:
- OpenAI API key
- PubMed API key and email
- Exa.ai API key
- Tavily API key

## License

MIT License 