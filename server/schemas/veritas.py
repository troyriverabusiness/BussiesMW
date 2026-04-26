from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VeritasChatRequest(BaseModel):
    request: str | None = None
    message: str | None = None
    case_id: UUID | None = Field(default=None, alias="caseId")

    model_config = ConfigDict(populate_by_name=True)


class VeritasChatResponse(BaseModel):
    status: str
    last_correspondence: str = Field(alias="lastCorrespondence")
    waiting_for: str = Field(alias="waitingFor")
    summary: str

    model_config = ConfigDict(populate_by_name=True)
