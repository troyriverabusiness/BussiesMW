import json
from collections.abc import Callable, Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from services.chat_agent_service import AgentSpec, ChatAgentService
from services.internal_contact_service import InternalContactService
from services.legal_data_hub_service import LegalDataHubService
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
        legal_data_hub_service: LegalDataHubService,
        internal_contact_service: InternalContactService,
        external_contact_service: InternalContactService,
        legal_document_service: LegalDocumentService,
    ) -> None:
        self._legal_case_service = legal_case_service
        self._trace_service = trace_service
        self._legal_data_hub_service = legal_data_hub_service
        self._internal_contact_service = internal_contact_service
        self._external_contact_service = external_contact_service
        self._legal_document_service = legal_document_service
        self._chat_agent_service: ChatAgentService | None = None
        self._approval_required_tools = {"contact_external_person"}
        self._handlers: dict[str, ToolHandler] = {
            "list_cases": self._list_cases,
            "get_case": self._get_case,
            "list_case_traces": self._list_case_traces,
            "legal_data_hub_search": self._legal_data_hub_search,
            "analyze_case": lambda args: self._run_specialized_agent("analyze_case", args),
            "review_traceability": lambda args: self._run_specialized_agent("review_traceability", args),
            "draft_legal_document": lambda args: self._run_specialized_agent("draft_legal_document", args),
            "prepare_contact_message": lambda args: self._run_specialized_agent("prepare_contact_message", args),
            "contact_internal_employee": self._contact_internal_employee,
            "contact_external_person": self._contact_external_person,
            "generate_legal_document_pdf": self._generate_legal_document_pdf,
        }

    def set_chat_agent_service(self, chat_agent_service: ChatAgentService) -> None:
        self._chat_agent_service = chat_agent_service

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
                    "name": "legal_data_hub_search",
                    "description": (
                        "Search external German legal sources through Legal Data Hub for the current case. "
                        "Use this before answering German legal questions, case-law questions, statutes, "
                        "product liability, defect, Rücktritt, Sachmangel, or litigation argument questions."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_id": {
                                "type": "string",
                                "description": "The UUID of the current case.",
                            },
                            "user_question": {
                                "type": "string",
                                "description": "The user's legal research question.",
                            },
                        },
                        "required": ["case_id", "user_question"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_case",
                    "description": (
                        "Spawn the case_analysis_agent to analyze case metadata, parties, facts, risks, "
                        "information gaps, status, priority, and recommended next actions."
                    ),
                    "parameters": self._specialized_agent_parameters(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "review_traceability",
                    "description": (
                        "Spawn the traceability_agent to review trace steps, evidence, confidence, "
                        "reasoning, auditability, and human-review needs."
                    ),
                    "parameters": self._specialized_agent_parameters(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "draft_legal_document",
                    "description": (
                        "Spawn the document_drafting_agent to draft legal document content and generate "
                        "a PDF when a downloadable legal document is requested. This does not require "
                        "user approval."
                    ),
                    "parameters": self._specialized_agent_parameters(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "prepare_contact_message",
                    "description": (
                        "Spawn the contact_planning_agent to prepare internal or external contact messages "
                        "and escalation recommendations. External sending still requires explicit approval."
                    ),
                    "parameters": self._specialized_agent_parameters(),
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

    def tools_for(self, names: Sequence[str]) -> list[dict[str, Any]]:
        requested_names = set(names)
        return [tool for tool in self.tools if tool["function"]["name"] in requested_names]

    def requires_approval(self, name: str) -> bool:
        return name in self._approval_required_tools

    def agent_for_tool(self, name: str) -> AgentSpec | None:
        if self._chat_agent_service is None:
            return None
        return self._chat_agent_service.agent_for_tool(name)

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

    def _legal_data_hub_search(self, args: dict[str, Any]) -> dict[str, Any]:
        case_id = self._parse_case_id(args)
        user_question = str(args.get("user_question") or args.get("userQuestion") or "").strip()
        if not user_question:
            raise ValueError("user_question is required")
        return self._legal_data_hub_service.search_for_chat(case_id=case_id, user_question=user_question)

    def _run_specialized_agent(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if self._chat_agent_service is None:
            raise ValueError("Chat agent service is not configured.")

        agent = self._chat_agent_service.agent_for_tool(tool_name)
        if agent is None:
            raise ValueError(f"Unknown specialized agent tool: {tool_name}")

        task = str(args.get("task") or "").strip()
        if not task:
            raise ValueError("task is required")

        return self._chat_agent_service.run_agent(
            agent_name=agent.name,
            task=task,
            case_id=self._parse_optional_case_id(args),
        )

    def _contact_internal_employee(self, args: dict[str, Any]) -> dict[str, Any]:
        message = str(args.get("message") or "").strip()
        return self._internal_contact_service.send_message(message)

    def _contact_external_person(self, args: dict[str, Any]) -> dict[str, Any]:
        message = str(args.get("message") or "").strip()
        return self._external_contact_service.send_message(message)

    def _generate_legal_document_pdf(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._legal_document_service.generate_document(args)

    def _specialized_agent_parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Specific task for the specialized agent to complete.",
                },
                "case_id": {
                    "type": "string",
                    "description": "Current case UUID, when the task relates to a case.",
                },
            },
            "required": ["task"],
        }

    def _parse_optional_case_id(self, args: dict[str, Any]) -> UUID | None:
        case_id = args.get("case_id") or args.get("caseId")
        return UUID(str(case_id)) if case_id else None

    def _parse_case_id(self, args: dict[str, Any]) -> UUID:
        case_id = args.get("case_id") or args.get("caseId")
        if not case_id:
            raise ValueError("case_id is required")

        return UUID(str(case_id))
