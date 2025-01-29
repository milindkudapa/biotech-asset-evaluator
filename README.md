# Biotech Asset Evaluator

A comprehensive AI-powered system for evaluating biotech assets through analysis of clinical trials, scientific literature, and financial data. The system uses LangGraph for workflow orchestration and integrates multiple data sources to provide detailed insights.

## Features

- Clinical trial data analysis
- Scientific literature review
- Financial and market analysis
- Regulatory update tracking
- Mechanism of action analysis
- Company financial status evaluation

## Architecture

The system uses a state-based workflow architecture powered by LangGraph:
- FastAPI for RESTful endpoints
- LangGraph for workflow orchestration
- OpenAI GPT-4 for analysis
- Multiple data sources integration (ClinicalTrials.gov, PubMed, Exa.ai, Tavily)

## Installation

1. Clone the repository
```bash
git clone https://github.com/milindkudapa/biotech-asset-evaluator.git
cd biotech-asset-evaluator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file with the following API keys:
```
OPENAI_API_KEY=your_key_here
EXA_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
PUBMED_API_KEY=your_key_here
CLINICAL_TRIALS_CONTACT_EMAIL=your_email_here
```

## Data Models

### Clinical Trial
```python
ClinicalTrial:
    - nct_id: str          # Clinical trial identifier
    - title: str           # Trial title
    - phase: str           # Trial phase
    - status: str          # Current status
    - conditions: List[str] # Medical conditions
    - description: str     # Trial description
```

### Regulatory Update
```python
RegulatoryUpdate:
    - date: str           # YYYY-MM-DD format
    - agency: str         # Regulatory agency
    - type: str           # Update type
    - description: str    # Update details
```

### Licensing Deal
```python
LicensingDeal:
    - date: str           # Deal date
    - parties: List[str]  # Involved parties
    - description: str    # Deal details
    - value: float       # Deal value in USD
```

### Investment
```python
Investment:
    - date: str          # Investment date
    - amount: float      # Amount in USD
    - type: str          # Investment type
    - investor: str      # Investor name
```

### Complete Report Structure
```python
BiotechAssetReport:
    - drug_name: str
    - developer_organization: str
    - overview: Overview
    - mechanism_of_action: MechanismOfAction
    - clinical_activity: ClinicalActivity
    - developer_financial_status: DeveloperFinancialStatus
```

## API Endpoints

### Analysis Endpoints

#### POST /analyze/moa
Analyze mechanism of action for a drug
```json
{
    "drug_name": "string"
}
```

#### POST /analyze/clinical
Analyze clinical trial activity
```json
{
    "drug_name": "string"
}
```

#### POST /analyze/financial
Analyze company financial status
```json
{
    "company_name": "string"
}
```

#### POST /analyze/overview
Generate comprehensive drug overview
```json
{
    "drug_name": "string"
}
```

### Data Endpoints

#### POST /data/trials
Get raw clinical trial data
```json
{
    "drug_name": "string"
}
```

#### POST /data/pubmed
Get raw PubMed article data
```json
{
    "drug_name": "string"
}
```

### Evaluation Endpoint

#### POST /evaluate
Comprehensive asset evaluation
```json
{
    "drug_name": "string",
    "company_name": "string"
}
```

## Testing

Run tests with coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

## Data Sources

- Clinical Trials: ClinicalTrials.gov API
- Scientific Literature: PubMed API
- Company Information: Exa.ai API
- Licensing Deals: Tavily Search API

## Error Handling

The system includes comprehensive error handling with informative default values:
- Missing trial data: "No trial data available"
- Unknown phases: "Phase unknown"
- Missing financial data: "Information not available"
- Empty regulatory updates: Returns current date with "No updates found"

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

## Authors

- Milind Kudapa 
