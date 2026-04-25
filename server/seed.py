from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from models.legal_case import LegalCase, LegalCaseStatus


CASE_TYPES = [
    "Consumer Refund",
    "Litigation",
    "Compliance Review",
    "Vendor Contract",
    "Employment Matter",
    "Data Privacy",
    "Regulatory Complaint",
    "Insurance Claim",
    "Settlement Review",
    "Intellectual Property",
]

ISSUE_SUMMARIES = [
    "Money back issue",
    "Refund issue",
    "Lawsuit issue",
    "Vendor indemnity review",
    "Closed settlement archive",
    "Regulatory complaint intake",
    "Breach of contract assessment",
    "Data processing addendum review",
    "Employment termination dispute",
    "Insurance coverage denial",
    "Product liability notice",
    "Consumer protection inquiry",
    "Supplier payment escalation",
    "Trademark usage conflict",
    "Compliance evidence request",
    "Cross-border privacy complaint",
    "Commercial lease disagreement",
    "Warranty reimbursement claim",
    "Pre-litigation demand letter",
    "Outside counsel budget review",
    "Contract renewal exception",
    "Board governance question",
    "Procurement policy deviation",
    "Customer chargeback dispute",
    "Regulatory audit response",
    "Settlement payment confirmation",
    "Employee confidentiality concern",
    "Marketing claims review",
    "Discovery hold request",
    "Service-level penalty claim",
    "Consumer cancellation complaint",
    "Records retention exception",
    "Franchise disclosure review",
    "Software licensing dispute",
    "Antitrust information request",
    "Whistleblower intake review",
    "Product recall legal assessment",
    "Third-party subpoena response",
    "Warranty terms clarification",
    "Class action monitoring",
    "Debt collection complaint",
    "Mediation preparation request",
    "E-discovery vendor issue",
    "Policy exception approval",
    "Customer fraud allegation",
    "Accessibility compliance review",
    "Partner termination notice",
    "Document privilege review",
    "Tax authority correspondence",
    "Executive employment amendment",
]

STATUS_SEQUENCE = [
    LegalCaseStatus.ACTION_REQUIRED,
    LegalCaseStatus.PENDING,
    LegalCaseStatus.CLOSED,
    LegalCaseStatus.PENDING,
]


def build_demo_legal_cases() -> list[dict[str, object]]:
    base_time = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    cases: list[dict[str, object]] = []

    for index, issue_summary in enumerate(ISSUE_SUMMARIES):
        cases.append(
            {
                "id": uuid5(NAMESPACE_URL, f"bussies-legal-case-{index + 1}"),
                "case_type": CASE_TYPES[index % len(CASE_TYPES)],
                "issue_summary": issue_summary,
                "status": STATUS_SEQUENCE[index % len(STATUS_SEQUENCE)],
                "last_updated": base_time - timedelta(hours=index * 5 + (index % 4)),
            }
        )

    return cases


DEMO_LEGAL_CASES = build_demo_legal_cases()


def seed_legal_cases(db: Session) -> None:
    case_count = db.scalar(select(func.count()).select_from(LegalCase)) or 0
    if case_count == len(DEMO_LEGAL_CASES):
        return

    db.execute(delete(LegalCase))
    db.add_all(LegalCase(**case_data) for case_data in DEMO_LEGAL_CASES)
    db.commit()
