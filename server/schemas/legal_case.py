from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CaseStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    ACTION_REQUIRED = "Action Required"
    AWAITING_COUNTERPARTY = "Awaiting Counterparty"
    AWAITING_INTERNAL = "Awaiting Internal"


class CasePriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class LegalCaseResponse(BaseModel):
    id: UUID
    title: str | None = None
    department: str | None = None
    status: CaseStatus
    priority: CasePriority
    next_due_date: date | None = Field(default=None, alias="nextDueDate")
    internal: bool
    plaintiff: str | None = None
    defendant: str | None = None
    court_authority: str | None = Field(default=None, alias="courtAuthority")
    jurisdiction: str | None = None
    claim_amount: float | None = Field(default=None, alias="claimAmount")
    legal_issue: str | None = Field(default=None, alias="legalIssue")
    case_facts: list[str] | None = Field(default=None, alias="caseFacts")
    information_gaps: list[str] | None = Field(default=None, alias="informationGaps")
    suggestion_action_items: list[str] | None = Field(default=None, alias="suggestionActionItems")
    last_update_date: datetime = Field(alias="lastUpdateDate")
    source_documents: str | None = Field(default=None, alias="sourceDocuments")
    case_summary: str | None = Field(default=None, alias="caseSummary")

    model_config = ConfigDict(populate_by_name=True)


class LegalCaseDetailResponse(LegalCaseResponse):
    pass
