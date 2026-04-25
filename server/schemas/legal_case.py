from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.legal_case import LegalCaseStatus


class LegalCaseResponse(BaseModel):
    id: UUID
    case_type: str = Field(alias="type")
    issue_summary: str = Field(alias="issueSummary")
    status: LegalCaseStatus
    last_updated: datetime = Field(alias="lastUpdated")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
