from datetime import datetime
from enum import Enum
from uuid import UUID
from uuid import uuid4

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Boolean, DateTime, Uuid

from database import Base


class LegalCaseStatus(str, Enum):
    ACTION_REQUIRED = "Action Required"
    PENDING = "Pending"
    CLOSED = "Closed"


class PriorityRiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class LegalCase(Base):
    __tablename__ = "legal_cases"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    case_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
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
    assigned_attorney: Mapped[str] = mapped_column(String(120), nullable=False)
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    short_summary: Mapped[str] = mapped_column(Text, nullable=False)
    plaintiff_name: Mapped[str] = mapped_column(String(160), nullable=False)
    compensation_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    next_due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    external_law_firm_involved: Mapped[str] = mapped_column(String(160), nullable=False)
    court_involved: Mapped[str] = mapped_column(String(160), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(120), nullable=False)
    priority_risk_level: Mapped[PriorityRiskLevel] = mapped_column(
        SqlEnum(
            PriorityRiskLevel,
            values_callable=lambda enum_values: [item.value for item in enum_values],
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    recent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_correspondence: Mapped[str] = mapped_column(Text, nullable=False)
    waiting_for: Mapped[str] = mapped_column(Text, nullable=False)
