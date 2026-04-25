from datetime import datetime
from enum import Enum
from uuid import UUID
from uuid import uuid4

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime, Uuid

from database import Base


class LegalCaseStatus(str, Enum):
    ACTION_REQUIRED = "Action Required"
    PENDING = "Pending"
    CLOSED = "Closed"


class LegalCase(Base):
    __tablename__ = "legal_cases"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    case_type: Mapped[str] = mapped_column("type", String(120), nullable=False)
    issue_summary: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[LegalCaseStatus] = mapped_column(
        SqlEnum(
            LegalCaseStatus,
            values_callable=lambda enum_values: [item.value for item in enum_values],
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
