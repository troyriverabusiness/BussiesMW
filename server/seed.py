from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from models.legal_case import LegalCase, LegalCaseStatus, PriorityRiskLevel
from models.traceability import CaseTraceability, HumanReview, Trace, TraceStep


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

ATTORNEYS = [
    "Mara Stein",
    "Eddie Lake",
    "Jamik Tashpulatov",
    "Priya Nair",
    "Clara Hoffmann",
    "Jonas Weber",
    "Noah Brandt",
    "Leonie Fischer",
]

PLAINTIFFS = [
    "Amelia Grant",
    "Keller Automotive GmbH",
    "Northstar Mobility LLC",
    "Sofia Romano",
    "Helios Components AG",
    "Marcus Reed",
    "Avery Chen",
    "Bavaria Fleet Services",
]

LAW_FIRMS = [
    "No external firm",
    "Rosenfeld & Kepler LLP",
    "Bruckner Legal Partners",
    "Hale, Novak & Singh",
    "Meyer Thomas Rechtsanwälte",
]

COURTS = [
    "No court filing",
    "Munich Regional Court I",
    "District Court of Berlin-Mitte",
    "High Court of Justice, London",
    "Superior Court of California, Santa Clara",
]

JURISDICTIONS = ["Germany", "European Union", "United States", "United Kingdom", "France"]

TAG_SETS = [
    ["consumer", "refund", "pre-litigation"],
    ["litigation", "outside-counsel", "deadline"],
    ["compliance", "regulatory", "evidence"],
    ["contract", "vendor", "indemnity"],
    ["employment", "confidential", "settlement"],
    ["privacy", "gdpr", "cross-border"],
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

RISK_SEQUENCE = [
    PriorityRiskLevel.HIGH,
    PriorityRiskLevel.MEDIUM,
    PriorityRiskLevel.CRITICAL,
    PriorityRiskLevel.LOW,
]


def build_demo_legal_cases() -> list[dict[str, object]]:
    base_time = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    cases: list[dict[str, object]] = []

    for index, issue_summary in enumerate(ISSUE_SUMMARIES):
        status = STATUS_SEQUENCE[index % len(STATUS_SEQUENCE)]
        case_type = CASE_TYPES[index % len(CASE_TYPES)]
        created_date = base_time - timedelta(days=14 + index * 2, hours=index % 7)
        last_updated = base_time - timedelta(hours=index * 5 + (index % 4))
        next_due_date = base_time + timedelta(days=(index % 12) + 1, hours=index % 5)
        attorney = ATTORNEYS[index % len(ATTORNEYS)]
        plaintiff = PLAINTIFFS[index % len(PLAINTIFFS)]
        law_firm = LAW_FIRMS[index % len(LAW_FIRMS)]
        court = COURTS[index % len(COURTS)]
        risk_level = RISK_SEQUENCE[index % len(RISK_SEQUENCE)]
        case_number = f"BMW-LGL-2026-{index + 1:04d}"
        compensation_amount = 4800 + (index * 1375) + ((index % 6) * 2400)
        last_correspondence = (
            f"{law_firm if law_firm != 'No external firm' else 'The business owner'} sent an update on "
            f"{issue_summary.lower()} and requested legal confirmation before the next response."
        )
        waiting_for = (
            f"{attorney} to review the latest record set and confirm the next action before "
            f"{next_due_date.strftime('%B %-d, %Y')}."
        )
        cases.append(
            {
                "id": uuid5(NAMESPACE_URL, f"bussies-legal-case-{index + 1}"),
                "case_number": case_number,
                "case_type": case_type,
                "issue_summary": issue_summary,
                "status": status,
                "assigned_attorney": attorney,
                "created_date": created_date,
                "last_updated": last_updated,
                "last_updated_date": last_updated,
                "tags": TAG_SETS[index % len(TAG_SETS)],
                "short_summary": (
                    f"{case_number} concerns a {case_type.lower()} matter for {plaintiff}. "
                    f"The team is tracking exposure, correspondence, and next-step approvals."
                ),
                "plaintiff_name": plaintiff,
                "compensation_amount": compensation_amount,
                "next_due_date": next_due_date,
                "external_law_firm_involved": law_firm,
                "court_involved": court,
                "jurisdiction": JURISDICTIONS[index % len(JURISDICTIONS)],
                "priority_risk_level": risk_level,
                "recent": index < 8 or index in {12, 18, 27, 36, 44},
                "last_correspondence": last_correspondence,
                "waiting_for": waiting_for,
            }
        )

    return cases


DEMO_LEGAL_CASES = build_demo_legal_cases()


TRACE_BLUEPRINTS = [
    ("Email intake classification", "classified_intake", "n8n.email_classifier"),
    ("Plaintiff claim extraction", "extracted_claim", "legal.claim_extractor"),
    ("Compensation evaluation", "evaluated_exposure", "finance.compensation_model"),
    ("Court and jurisdiction check", "checked_jurisdiction", "legal.jurisdiction_lookup"),
    ("External law firm routing", "routed_counsel", "ops.counsel_router"),
    ("Risk scoring", "scored_risk", "risk.priority_model"),
    ("Draft response recommendation", "drafted_response", "doc.response_recommender"),
]


def seed_traceability(db: Session) -> None:
    traceability_count = db.scalar(select(func.count()).select_from(CaseTraceability)) or 0
    if traceability_count == len(DEMO_LEGAL_CASES):
        return

    db.execute(delete(HumanReview))
    db.execute(delete(TraceStep))
    db.execute(delete(Trace))
    db.execute(delete(CaseTraceability))

    base_time = datetime(2026, 4, 25, 8, 30, tzinfo=UTC)
    traceability_records: list[CaseTraceability] = []
    traces: list[Trace] = []
    trace_steps: list[TraceStep] = []

    for case_index, case_data in enumerate(DEMO_LEGAL_CASES):
        case_id = case_data["id"]
        received_at = base_time - timedelta(hours=case_index * 3)
        traceability_id = uuid5(NAMESPACE_URL, f"traceability-{case_id}")
        traceability_records.append(
            CaseTraceability(
                id=traceability_id,
                case_id=case_id,
                email_subject=f"Legal intake: {case_data['issue_summary']} / {case_data['case_number']}",
                email_sender=f"legal.intake+{case_index + 1}@example-corp.com",
                received_at=received_at,
                started_at=received_at + timedelta(minutes=2),
                completed_at=received_at + timedelta(minutes=18 + (case_index % 7)),
                status="Completed with review" if case_index % 5 == 0 else "Completed",
            )
        )

        for trace_index, trace_name in enumerate(["Intake orchestration", "Legal analysis", "Action recommendation"]):
            trace_id = uuid5(NAMESPACE_URL, f"trace-{case_id}-{trace_index}")
            human_required = case_index % 5 == 0 and trace_index == 2
            traces.append(
                Trace(
                    id=trace_id,
                    case_traceability_id=traceability_id,
                    status="Review required" if human_required else "Completed",
                    confidence=round(0.78 + ((case_index + trace_index) % 14) / 100, 2),
                    human_in_loop_required=human_required,
                    created_at=received_at + timedelta(minutes=4 + trace_index * 5),
                )
            )

            step_slice = TRACE_BLUEPRINTS[trace_index * 2 : trace_index * 2 + 3]
            for step_index, (step, output_key, tool_name) in enumerate(step_slice):
                step_human_required = human_required and step_index == len(step_slice) - 1
                confidence = round(0.74 + ((case_index + trace_index + step_index) % 18) / 100, 2)
                trace_steps.append(
                    TraceStep(
                        id=uuid5(NAMESPACE_URL, f"trace-step-{case_id}-{trace_index}-{step_index}"),
                        trace_id=trace_id,
                        step=step,
                        input={
                            "caseNumber": case_data["case_number"],
                            "issueSummary": case_data["issue_summary"],
                            "emailSubject": f"Legal intake: {case_data['issue_summary']}",
                            "jurisdiction": case_data["jurisdiction"],
                        },
                        output={
                            output_key: True,
                            "status": case_data["status"].value,
                            "assignedAttorney": case_data["assigned_attorney"],
                            "priorityRiskLevel": case_data["priority_risk_level"].value,
                            "nextDueDate": case_data["next_due_date"].isoformat(),
                        },
                        reasoning=(
                            f"The agent compared the email intake, case metadata, and stored legal operations "
                            f"rules. It treated {case_data['issue_summary'].lower()} as a "
                            f"{case_data['case_type'].lower()} matter in {case_data['jurisdiction']} and "
                            f"selected a conservative workflow because the tracked risk level is "
                            f"{case_data['priority_risk_level'].value.lower()}."
                        ),
                        confidence=confidence,
                        tool_calls=[
                            {
                                "tool": tool_name,
                                "status": "success",
                                "latencyMs": 420 + case_index * 3 + step_index * 40,
                            },
                            {
                                "tool": "postgres.case_registry",
                                "status": "success",
                                "fieldsRead": ["status", "lastCorrespondence", "waitingFor"],
                            },
                        ],
                        human_in_loop_required=step_human_required,
                        created_at=received_at + timedelta(minutes=5 + trace_index * 5 + step_index),
                    )
                )

    db.add_all(traceability_records)
    db.add_all(traces)
    db.add_all(trace_steps)
    db.commit()


def seed_legal_cases(db: Session) -> None:
    case_count = db.scalar(select(func.count()).select_from(LegalCase)) or 0
    detailed_count = (
        db.scalar(
            select(func.count())
            .select_from(LegalCase)
            .where(LegalCase.case_number.is_not(None), LegalCase.short_summary.is_not(None))
        )
        or 0
    )
    if case_count == len(DEMO_LEGAL_CASES) and detailed_count == len(DEMO_LEGAL_CASES):
        seed_traceability(db)
        return

    db.execute(delete(LegalCase))
    db.add_all(LegalCase(**case_data) for case_data in DEMO_LEGAL_CASES)
    db.commit()
    seed_traceability(db)
