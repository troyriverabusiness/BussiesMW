import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from services.internal_contact_service import InternalContactService
from services.legal_case_service import LegalCaseService
from services.legal_document_service import LegalDocumentService
from services.trace_service import TraceService


ToolHandler = Callable[[dict[str, Any]], Any]


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


class ChatToolRegistry:
    def __init__(
        self,
        legal_case_service: LegalCaseService,
        trace_service: TraceService,
        internal_contact_service: InternalContactService,
        external_contact_service: InternalContactService,
        legal_document_service: LegalDocumentService,
    ) -> None:
        self._legal_case_service = legal_case_service
        self._trace_service = trace_service
        self._internal_contact_service = internal_contact_service
        self._external_contact_service = external_contact_service
        self._legal_document_service = legal_document_service
        self._approval_required_tools = {"contact_external_person"}
        self._handlers: dict[str, ToolHandler] = {
            "list_cases": self._list_cases,
            "get_case": self._get_case,
            "list_case_traces": self._list_case_traces,
            "contact_internal_employee": self._contact_internal_employee,
            "contact_external_person": self._contact_external_person,
            "generate_legal_document_pdf": self._generate_legal_document_pdf,
        }

    @property
    def tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_cases",
                    "description": "List legal cases available in the local case registry.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_case",
                    "description": "Fetch detailed local project data for one legal case.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_id": {
                                "type": "string",
                                "description": "The UUID of the case to fetch.",
                            },
                        },
                        "required": ["case_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_case_traces",
                    "description": "List traceability records and trace steps for one legal case.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_id": {
                                "type": "string",
                                "description": "The UUID of the case whose traces should be fetched.",
                            },
                        },
                        "required": ["case_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "contact_internal_employee",
                    "description": (
                        "Contact internal employee by sending a Telegram message to the configured internal recipient. "
                        "Use this when the user asks to notify, message, escalate to, or contact an internal employee."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Plain-text message to send to the configured internal employee.",
                            },
                        },
                        "required": ["message"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "contact_external_person",
                    "description": (
                        "Contact an external person by sending a Telegram message to the configured external recipient. "
                        "This tool requires explicit user approval before execution."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Plain-text message to send to the configured external person.",
                            },
                        },
                        "required": ["message"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_legal_document_pdf",
                    "description": (
                        "Generate a professional PDF for a requested legal document, such as a court order, "
                        "contract, agreement, letter, notice, or filing draft. Use this when the user asks to "
                        "create, draft, generate, download, or prepare a legal document as a PDF."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "documentType": {
                                "type": "string",
                                "description": "The legal document category, for example Court Order or Service Agreement.",
                            },
                            "title": {
                                "type": "string",
                                "description": "Formal title to display at the top of the document.",
                            },
                            "caseId": {
                                "type": "string",
                                "description": "Current case UUID, when the document relates to a case.",
                            },
                            "court": {
                                "type": "string",
                                "description": "Court, tribunal, authority, or recipient organization, when relevant.",
                            },
                            "recipient": {
                                "type": "string",
                                "description": "Person or organization receiving the document, when relevant.",
                            },
                            "jurisdiction": {
                                "type": "string",
                                "description": "Applicable jurisdiction or governing law, when known.",
                            },
                            "reference": {
                                "type": "string",
                                "description": "Matter, filing, claim, or contract reference, when known.",
                            },
                            "parties": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Parties named in the document.",
                            },
                            "sections": {
                                "type": "array",
                                "description": "Ordered formal sections containing the drafted legal text.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "heading": {"type": "string"},
                                        "body": {"type": "string"},
                                        "pageBreakBefore": {"type": "boolean"},
                                    },
                                    "required": ["heading", "body"],
                                },
                            },
                            "signatureBlocks": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Signature or approval labels to include at the end of the document.",
                            },
                        },
                        "required": ["documentType", "title", "sections"],
                    },
                },
            },
        ]

    def requires_approval(self, name: str) -> bool:
        return name in self._approval_required_tools

    def dispatch_json(self, name: str, args: dict[str, Any]) -> str:
        handler = self._handlers.get(name)
        if handler is None:
            result = {"error": f"Unknown tool: {name}"}
        else:
            result = handler(args)

        return json.dumps(_jsonable(result), ensure_ascii=False, default=str)

    def _list_cases(self, _: dict[str, Any]) -> dict[str, Any]:
        return {"cases": self._legal_case_service.list_cases()}

    def _get_case(self, args: dict[str, Any]) -> dict[str, Any]:
        case_id = self._parse_case_id(args)
        legal_case = self._legal_case_service.get_case(case_id)
        return {"case": legal_case}

    def _list_case_traces(self, args: dict[str, Any]) -> dict[str, Any]:
        case_id = self._parse_case_id(args)
        traces = self._trace_service.list_case_traces(case_id)
        return {"traces": traces or [], "caseFound": traces is not None}

    def _contact_internal_employee(self, args: dict[str, Any]) -> dict[str, Any]:
        message = str(args.get("message") or "").strip()
        return self._internal_contact_service.send_message(message)

    def _contact_external_person(self, args: dict[str, Any]) -> dict[str, Any]:
        message = str(args.get("message") or "").strip()
        return self._external_contact_service.send_message(message)

    def _generate_legal_document_pdf(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._legal_document_service.generate_document(args)

    def _parse_case_id(self, args: dict[str, Any]) -> UUID:
        case_id = args.get("case_id") or args.get("caseId")
        if not case_id:
            raise ValueError("case_id is required")

        return UUID(str(case_id))
