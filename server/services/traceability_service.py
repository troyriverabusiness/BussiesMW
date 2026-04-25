from uuid import UUID

from data_access.traceability_repository import TraceabilityRepository
from schemas.traceability import CaseTraceabilityResponse, HumanReviewCreate, HumanReviewResponse


class TraceabilityService:
    def __init__(self, repository: TraceabilityRepository) -> None:
        self._repository = repository

    def get_case_traceability(self, case_id: UUID) -> CaseTraceabilityResponse | None:
        legal_case = self._repository.get_case(case_id)
        traceability = self._repository.get_case_traceability(case_id)
        if legal_case is None or traceability is None:
            return None

        traces = []
        for trace in self._repository.list_traces(traceability.id):
            traces.append(
                {
                    "id": trace.id,
                    "status": trace.status,
                    "confidence": trace.confidence,
                    "humanInLoopRequired": trace.human_in_loop_required,
                    "createdAt": trace.created_at,
                    "steps": self._repository.list_steps(trace.id),
                    "reviews": self._repository.list_reviews(trace.id),
                }
            )

        return CaseTraceabilityResponse(
            id=traceability.id,
            caseId=traceability.case_id,
            caseNumber=legal_case.case_number,
            issueSummary=legal_case.issue_summary,
            emailSubject=traceability.email_subject,
            emailSender=traceability.email_sender,
            receivedAt=traceability.received_at,
            startedAt=traceability.started_at,
            completedAt=traceability.completed_at,
            status=traceability.status,
            traces=traces,
        )

    def create_review(self, payload: HumanReviewCreate) -> HumanReviewResponse:
        return self._repository.create_review(payload)
