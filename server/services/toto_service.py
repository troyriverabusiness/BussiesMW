from schemas.toto import TotoChatRequest, TotoChatResponse


class TotoService:
    def get_case_update(self, payload: TotoChatRequest) -> TotoChatResponse:
        if payload.case_id:
            return TotoChatResponse(
                status="Pending",
                lastCorrespondence="Outside counsel sent a draft response packet this morning.",
                waitingFor="Client approval on settlement authority and supporting exhibits.",
                summary=(
                    "Toto reviewed the matter context and found one active dependency. "
                    "The next useful action is to confirm authority and release the response packet."
                ),
            )

        return TotoChatResponse(
            status="Action Required",
            lastCorrespondence="Legal operations received a new intake note from the business owner.",
            waitingFor="Matter owner assignment and initial risk triage.",
            summary=(
                "Toto can prepare a concise update once a case is selected. "
                "For now, the request appears to need ownership, status confirmation, and next-step routing."
            ),
        )
