from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.legal_case import LegalCaseStatus, PriorityRiskLevel


class LegalCaseResponse(BaseModel):
    id: UUID
    case_number: str = Field(alias="caseNumber")
    case_type: str = Field(alias="type")
    issue_summary: str = Field(alias="issueSummary")
    status: LegalCaseStatus
    last_updated: datetime = Field(alias="lastUpdated")
    recent: bool

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class LegalCaseDetailResponse(LegalCaseResponse):
    case_type: str = Field(alias="caseType")
    assigned_attorney: str = Field(alias="assignedAttorney")
    created_date: datetime = Field(alias="createdDate")
    last_updated_date: datetime = Field(alias="lastUpdatedDate")
    tags: list[str]
    short_summary: str = Field(alias="shortSummary")
    plaintiff_name: str = Field(alias="plaintiffName")
    compensation_amount: float = Field(alias="compensationAmount")
    next_due_date: datetime = Field(alias="nextDueDate")
    external_law_firm_involved: str = Field(alias="externalLawFirmInvolved")
    court_involved: str = Field(alias="courtInvolved")
    jurisdiction: str
    priority_risk_level: PriorityRiskLevel = Field(alias="priorityRiskLevel")
    last_correspondence: str = Field(alias="lastCorrespondence")
    waiting_for: str = Field(alias="waitingFor")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
