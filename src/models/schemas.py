from typing import List, Optional
from pydantic import BaseModel, Field

class Overview(BaseModel):
    description: str = Field(..., description="Brief description of the drug asset and its context")

class MechanismOfAction(BaseModel):
    target_pathways: str = Field(..., description="Details of the target pathways")
    biology: str = Field(..., description="Related biological mechanisms")

class ClinicalTrial(BaseModel):
    nct_id: str = Field(..., description="ClinicalTrials.gov identifier")
    phase: str = Field(..., description="Trial phase")
    status: str = Field(..., description="Current status of the trial")
    title: str = Field(..., description="Title of the trial")
    conditions: List[str] = Field(default_factory=list, description="Conditions being studied")
    completion_date: Optional[str] = Field(None, description="Expected or actual completion date")
    results: Optional[str] = Field(None, description="Summary of results if available")

class RegulatoryUpdate(BaseModel):
    date: str = Field(..., description="Date of the update")
    agency: str = Field(..., description="Regulatory agency (e.g., FDA, EMA)")
    type: str = Field(..., description="Type of update (e.g., approval, fast track)")
    description: str = Field(..., description="Details of the regulatory update")

class ClinicalActivity(BaseModel):
    ongoing_trials: List[ClinicalTrial] = Field(default_factory=list)
    completed_trials: List[ClinicalTrial] = Field(default_factory=list)
    regulatory_updates: List[RegulatoryUpdate] = Field(default_factory=list)

class LicensingDeal(BaseModel):
    date: str = Field(..., description="Date of the deal")
    parties: List[str] = Field(..., description="Companies involved in the deal")
    value: Optional[float] = Field(None, description="Total value of the deal in USD")
    description: str = Field(..., description="Details of the licensing deal")

class Investment(BaseModel):
    date: str = Field(..., description="Date of investment")
    investor: str = Field(..., description="Name of investor")
    amount: Optional[float] = Field(None, description="Investment amount in USD")
    type: str = Field(..., description="Type of investment (e.g., Series A, IPO)")

class DeveloperFinancialStatus(BaseModel):
    ownership_type: str = Field(..., description="Public/Private status")
    funding: str = Field(..., description="Details of funding rounds")
    revenue: Optional[str] = Field(None, description="Annual revenue data")
    licensing_deals: List[LicensingDeal] = Field(default_factory=list)
    disclosed_investments: List[Investment] = Field(default_factory=list)

class BiotechAssetReport(BaseModel):
    drug_name: str = Field(..., description="Name of the drug asset")
    developer_organization: Optional[str] = Field(None, description="Name of the developer organization")
    overview: Overview
    mechanism_of_action: MechanismOfAction
    clinical_activity: ClinicalActivity
    developer_financial_status: DeveloperFinancialStatus 