# Biotech Asset Evaluation Agent

An intelligent agent that evaluates biotech drug assets and their developer companies, providing structured reports with insights about mechanism of action, clinical activity, and financial status.

## Features

- Automated evaluation of drug assets and biotech companies
- Data aggregation from multiple sources:
  - ClinicalTrials.gov for trial data
  - PubMed for scientific literature
  - Exa.ai for company information
  - Tavily for licensing deals and investments
- LLM-powered analysis using Azure OpenAI
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
├── .env.example               # Example environment variables
└── README.md                  # Project documentation
```

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd biotech-asset-evaluation
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

4. Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

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

- Azure OpenAI API key and endpoint
- PubMed API key and email
- Exa.ai API key
- Tavily API key

## License

MIT License 