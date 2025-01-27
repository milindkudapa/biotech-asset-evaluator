# Lunartree Biotech Asset Evaluation

A comprehensive system for evaluating biotech assets using AI-powered analysis of clinical trials, scientific literature, and financial data.

## Features

- Clinical trial data analysis
- Scientific literature review
- Financial and market analysis
- Regulatory update tracking
- Mechanism of action analysis
- Company financial status evaluation

## Installation

1. Clone the repository
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

### GET /health
Health check endpoint

### POST /analyze/asset
Analyze a biotech asset
```json
{
    "drug_name": "string",
    "developer_organization": "string"
}
```

### POST /analyze/moa
Analyze mechanism of action
```json
{
    "drug_name": "string"
}
```

### POST /analyze/clinical
Analyze clinical trial activity
```json
{
    "drug_name": "string"
}
```

### POST /analyze/financial
Analyze developer financial status
```json
{
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
