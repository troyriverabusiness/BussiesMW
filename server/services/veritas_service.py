from data_access.legal_case_repository import LegalCaseRepository
from schemas.veritas import VeritasChatRequest, VeritasChatResponse


def _format_case_text(value: object, fallback: str) -> str:
    if isinstance(value, list):
        formatted_items = [str(item).strip() for item in value if str(item).strip()]
        if formatted_items:
            return "; ".join(formatted_items)

    if value:
        return str(value)

    return fallback


class VeritasService:
    def __init__(self, repository: LegalCaseRepository) -> None:
        self._repository = repository

    def get_case_update(self, payload: VeritasChatRequest) -> VeritasChatResponse:
        if payload.case_id:
            legal_case = self._repository.get_by_id(payload.case_id)
            if legal_case is None:
                return VeritasChatResponse(
                    status="Case not found",
                    lastCorrespondence="No case record was available for the provided identifier.",
                    waitingFor="Verify the case link and try again.",
                    summary="I could not find that case in the legal case registry.",
                )

            status = str(legal_case.get("status") or "Unknown")
            title = str(legal_case.get("title") or "Selected case")
            priority = str(legal_case.get("priority") or "unknown")
            next_due_date = legal_case.get("next_due_date") or "not scheduled"
            action_items = _format_case_text(
                legal_case.get("suggestion_action_items"),
                "Review the Supabase case record and confirm the next action.",
            )
            case_summary = _format_case_text(
                legal_case.get("case_summary") or legal_case.get("case_facts"),
                title,
            )

            return VeritasChatResponse(
                status=status,
                lastCorrespondence=str(
                    legal_case.get("source_documents")
                    or legal_case.get("last_update_date")
                    or "No source document is attached to this case."
                ),
                waitingFor=action_items,
                summary=(
                    f"{title} is currently {status.lower()} with {priority.lower()} priority. "
                    f"The next due date is {next_due_date}. {case_summary}"
                ),
            )

        return VeritasChatResponse(
            status="Action Required",
            lastCorrespondence="Legal operations received a new intake note from the business owner.",
            waitingFor="Matter owner assignment and initial risk triage.",
            summary=(
                "Veritas can prepare a concise update once a case is selected. "
                "For now, the request appears to need ownership, status confirmation, and next-step routing."
            ),
        )
