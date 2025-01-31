from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field, constr, confloat, field_validator

class ClinicalTrial(BaseModel):
    """Model for a clinical trial."""
    nct_id: str = Field(default="No trial ID available")
    title: str = Field(default="No trial title available")
    phase: str = Field(default="Phase unknown")
    status: str = Field(default="Status unknown")
    conditions: List[str] = Field(default_factory=lambda: ["No conditions specified"])
    description: str = Field(default="No trial description available")

class RegulatoryUpdate(BaseModel):
    """Model for a regulatory update."""
    date: str = Field(
        default=date.today().strftime("%Y-%m-%d"),
        pattern=r"^\d{4}-\d{2}-\d{2}$"  # Enforce YYYY-MM-DD format
    )
    agency: str = Field(default="No regulatory agency specified")
    type: str = Field(default="No update type specified")
    description: str = Field(default="No regulatory updates found for this asset")

class LicensingDeal(BaseModel):
    """Model for a licensing deal."""
    date: str = Field(default="Date not disclosed")
    parties: List[str] = Field(default_factory=lambda: ["Parties not disclosed"])
    description: str = Field(default="No licensing deal details available")
    value: Optional[float] = Field(default=None, description="Deal value in USD, None if not disclosed")

    @field_validator('value', mode='before')
    @classmethod
    def validate_value(cls, v):
        """Handle undisclosed or invalid values."""
        if v is None or isinstance(v, float):
            return v
        if isinstance(v, str) and v.lower() in ['not disclosed', 'undisclosed', 'n/a', '', 'none']:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    class Config:
        """Model configuration."""
        validate_assignment = True
        arbitrary_types_allowed = True

class Investment(BaseModel):
    """Model for an investment."""
    date: str = Field(default="Date not disclosed")
    amount: float = Field(default=0.0, description="Investment amount in USD")
    type: str = Field(default="Investment type not specified")
    investor: str = Field(default="Investor not disclosed")

class Overview(BaseModel):
    """Model for the drug overview."""
    description: str = Field(default="No overview available for this asset")

class MechanismOfAction(BaseModel):
    """Model for mechanism of action details."""
    target_pathways: str = Field(default="Target pathways not identified")
    biology: str = Field(default="Biological mechanism not described")

class ClinicalActivity(BaseModel):
    """Model for clinical trial activity."""
    ongoing_trials: List[ClinicalTrial] = Field(default_factory=list, description="List of active clinical trials")
    completed_trials: List[ClinicalTrial] = Field(default_factory=list, description="List of completed clinical trials")
    regulatory_updates: List[RegulatoryUpdate] = Field(default_factory=list, description="List of regulatory milestones")

class DeveloperFinancialStatus(BaseModel):
    """Model for company financial status."""
    ownership_type: str = Field(default="Company ownership type not available")
    funding: str = Field(default="Funding information not available")
    revenue: str = Field(default="Revenue information not available")
    licensing_deals: List[LicensingDeal] = Field(default_factory=list, description="List of licensing agreements")
    disclosed_investments: List[Investment] = Field(default_factory=list, description="List of known investments")

    @field_validator('licensing_deals', mode='before')
    @classmethod
    def validate_licensing_deals(cls, v):
        """Pre-process licensing deals to handle undisclosed values."""
        if not v:
            return []
        processed_deals = []
        for deal in v:
            if isinstance(deal, dict):
                # Handle the value field specifically
                if 'value' in deal:
                    value = deal['value']
                    if isinstance(value, str) and value.lower() in ['not disclosed', 'undisclosed', 'n/a', '', 'none']:
                        deal['value'] = None
                    elif not isinstance(value, (float, type(None))):
                        try:
                            deal['value'] = float(value)
                        except (ValueError, TypeError):
                            deal['value'] = None
                processed_deals.append(deal)
            else:
                processed_deals.append(deal)
        return processed_deals

    class Config:
        """Model configuration."""
        validate_assignment = True
        arbitrary_types_allowed = True

class BiotechAssetReport(BaseModel):
    """Complete report model."""
    drug_name: str
    developer_organization: str = Field(default="Developer organization not specified")
    overview: Overview
    mechanism_of_action: MechanismOfAction
    clinical_activity: ClinicalActivity
    developer_financial_status: DeveloperFinancialStatus

    class Config:
        """Model configuration."""
        validate_assignment = True
        extra = "forbid"
        str_strip_whitespace = True 