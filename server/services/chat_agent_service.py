import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from data_access.openai_chat_client import OpenAIChatClient


MAX_SUB_AGENT_TOOL_ITERATIONS = 4


class ChatAgentError(RuntimeError):
    """Raised when a specialized chat agent cannot complete its task."""


class ChatToolProvider(Protocol):
    def tools_for(self, names: Sequence[str]) -> list[dict[str, Any]]:
        """Return OpenAI tool schemas matching the requested tool names."""

    def dispatch_json(self, name: str, args: dict[str, Any]) -> str:
        """Dispatch a tool and return its JSON-encoded result."""


@dataclass(frozen=True)
class AgentSpec:
    name: str
    label: str
    description: str
    system_prompt: str
    allowed_tools: tuple[str, ...]
    max_iterations: int = MAX_SUB_AGENT_TOOL_ITERATIONS


AGENT_SPECS: dict[str, AgentSpec] = {
    "case_analysis_agent": AgentSpec(
        name="case_analysis_agent",
        label="Case analysis agent",
        description="Analyze case status, risks, facts, gaps, and next actions.",
        allowed_tools=("get_case", "list_case_traces", "legal_data_hub_search"),
        system_prompt=(
            "You are the Veritas case analysis agent. Analyze legal case metadata, parties, "
            "facts, legal issue, status, priority, risks, information gaps, and next actions. "
            "For German legal research, case-law, statutes, product liability, defect, "
            "Rücktritt, Sachmangel, litigation, or legal-argument questions, call "
            "legal_data_hub_search before completing the analysis. Use only the provided "
            "tools. Return JSON only with keys: summary, findings, recommendedActions, "
            "confidence, sourcesUsed, requiresHumanReview."
        ),
    ),
    "traceability_agent": AgentSpec(
        name="traceability_agent",
        label="Traceability agent",
        description="Review trace steps, evidence, confidence, and human-review needs.",
        allowed_tools=("get_case", "list_case_traces"),
        system_prompt=(
            "You are the Veritas traceability agent. Review trace steps, tool calls, reasoning, "
            "confidence, missing evidence, auditability, and whether human review is needed. "
            "Use only the provided tools. Return JSON only with keys: summary, findings, "
            "recommendedActions, confidence, sourcesUsed, requiresHumanReview."
        ),
    ),
    "document_drafting_agent": AgentSpec(
        name="document_drafting_agent",
        label="Document drafting agent",
        description="Draft structured legal documents and generate PDFs when requested.",
        allowed_tools=("get_case", "generate_legal_document_pdf"),
        system_prompt=(
            "You are the Veritas document drafting agent. Draft formal, review-ready legal "
            "document sections grounded in available case information. If the task asks to "
            "draft, create, prepare, produce, generate, or download a legal document or PDF, "
            "you must call generate_legal_document_pdf before your final answer. Do not ask "
            "the user for approval before generating the PDF. Use only the provided tools. "
            "Return JSON only with keys: summary, findings, recommendedActions, confidence, "
            "sourcesUsed, requiresHumanReview, artifact. Set requiresHumanReview to false "
            "after the PDF has been generated; counsel review can be mentioned in summary."
        ),
    ),
    "contact_planning_agent": AgentSpec(
        name="contact_planning_agent",
        label="Contact planning agent",
        description="Prepare internal or external contact messages and escalation recommendations.",
        allowed_tools=("get_case", "list_case_traces", "contact_internal_employee"),
        system_prompt=(
            "You are the Veritas contact planning agent. Prepare concise internal or external "
            "contact messages and escalation recommendations. You may send internal contacts "
            "when explicitly requested. You must never send external contacts; recommend the "
            "message text for the supervisor approval flow instead. Use only the provided tools. "
            "Return JSON only with keys: summary, findings, recommendedActions, confidence, "
            "sourcesUsed, requiresHumanReview."
        ),
    ),
}


SPECIALIZED_TOOL_TO_AGENT = {
    "analyze_case": "case_analysis_agent",
    "review_traceability": "traceability_agent",
    "draft_legal_document": "document_drafting_agent",
    "prepare_contact_message": "contact_planning_agent",
}


class ChatAgentService:
    def __init__(self, openai_client: OpenAIChatClient, tool_provider: ChatToolProvider) -> None:
        self._openai_client = openai_client
        self._tool_provider = tool_provider

    def run_agent(self, agent_name: str, task: str, case_id: UUID | None = None) -> dict[str, Any]:
        spec = AGENT_SPECS.get(agent_name)
        if spec is None:
            raise ChatAgentError(f"Unknown specialized agent: {agent_name}")

        messages = self._build_messages(spec, task, case_id)
        tools = self._tool_provider.tools_for(spec.allowed_tools)
        tool_names = {tool["function"]["name"] for tool in tools}
        used_tools: list[str] = []
        artifact: dict[str, Any] | None = None

        for _ in range(spec.max_iterations):
            completion = self._openai_client.create_completion(
                messages=messages,
                tools=tools,
                response_format={"type": "json_object"},
            )
            message = completion.choices[0].message
            tool_calls = list(message.tool_calls or [])
            content = message.content or ""

            if not tool_calls:
                normalized_result = self._normalize_result(
                    spec=spec,
                    raw_content=content,
                    task=task,
                    case_id=case_id,
                    fallback_sources=used_tools,
                    fallback_artifact=artifact,
                )
                if spec.name == "document_drafting_agent" and "artifact" in normalized_result:
                    normalized_result["requiresHumanReview"] = False
                return normalized_result

            messages.append(self._assistant_message(content, tool_calls))
            for tool_call in tool_calls:
                tool_name = str(tool_call.function.name)
                if tool_name not in tool_names:
                    raise ChatAgentError(f"{spec.label} is not allowed to call {tool_name}")

                tool_args = self._parse_tool_args(str(tool_call.function.arguments or ""))
                used_tools.append(tool_name)
                tool_result = self._tool_provider.dispatch_json(tool_name, tool_args)
                artifact = self._artifact_from_tool_result(tool_result) or artifact
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result,
                    }
                )

        raise ChatAgentError(f"{spec.label} exceeded maximum tool iterations.")

    def agent_for_tool(self, tool_name: str) -> AgentSpec | None:
        agent_name = SPECIALIZED_TOOL_TO_AGENT.get(tool_name)
        return AGENT_SPECS.get(agent_name) if agent_name else None

    def _build_messages(self, spec: AgentSpec, task: str, case_id: UUID | None) -> list[dict[str, Any]]:
        user_content = task.strip()
        if case_id:
            user_content = f"{user_content}\n\nCurrent case ID: {case_id}"
        return [
            {"role": "system", "content": spec.system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _assistant_message(self, content: str, tool_calls: list[Any]) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": content or None,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in tool_calls
            ],
        }

    def _normalize_result(
        self,
        spec: AgentSpec,
        raw_content: str,
        task: str,
        case_id: UUID | None,
        fallback_sources: list[str],
        fallback_artifact: dict[str, Any] | None,
    ) -> dict[str, Any]:
        result = self._parse_json_object(raw_content)
        confidence = result.get("confidence")
        normalized: dict[str, Any] = {
            "agent": {"name": spec.name, "label": spec.label},
            "summary": str(result.get("summary") or "").strip() or "No summary returned.",
            "findings": self._string_list(result.get("findings")),
            "recommendedActions": self._string_list(result.get("recommendedActions")),
            "confidence": confidence if isinstance(confidence, int | float) else 0.0,
            "sourcesUsed": self._string_list(result.get("sourcesUsed")) or fallback_sources,
            "requiresHumanReview": bool(result.get("requiresHumanReview")),
        }
        artifact = result.get("artifact")
        if self._is_download_artifact(artifact):
            normalized["artifact"] = artifact
        elif self._is_download_artifact(fallback_artifact):
            normalized["artifact"] = fallback_artifact
        elif spec.name == "document_drafting_agent":
            generated_artifact = self._generate_fallback_document(task, case_id, normalized, result)
            if generated_artifact:
                normalized["artifact"] = generated_artifact
                normalized["sourcesUsed"] = list(dict.fromkeys([*normalized["sourcesUsed"], "generate_legal_document_pdf"]))
        return normalized

    def _parse_json_object(self, value: str) -> dict[str, Any]:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ChatAgentError("Specialized agent did not return valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ChatAgentError("Specialized agent returned JSON that was not an object.")
        return parsed

    def _parse_tool_args(self, raw_args: str) -> dict[str, Any]:
        if not raw_args:
            return {}
        args = json.loads(raw_args)
        return args if isinstance(args, dict) else {"value": args}

    def _artifact_from_tool_result(self, raw_result: str) -> dict[str, Any] | None:
        try:
            result = json.loads(raw_result)
        except json.JSONDecodeError:
            return None
        artifact = result.get("artifact") if isinstance(result, dict) else None
        return artifact if self._is_download_artifact(artifact) else None

    def _generate_fallback_document(
        self,
        task: str,
        case_id: UUID | None,
        normalized: dict[str, Any],
        raw_result: dict[str, Any],
    ) -> dict[str, Any] | None:
        sections = self._document_sections(raw_result, normalized)
        if not sections:
            return None

        document_result = self._tool_provider.dispatch_json(
            "generate_legal_document_pdf",
            {
                "documentType": str(raw_result.get("documentType") or raw_result.get("document_type") or "Legal Document"),
                "title": str(raw_result.get("title") or self._document_title(task)),
                "caseId": str(case_id) if case_id else None,
                "sections": sections,
                "signatureBlocks": raw_result.get("signatureBlocks") or raw_result.get("signature_blocks") or ["Prepared for counsel review"],
            },
        )
        return self._artifact_from_tool_result(document_result)

    def _document_sections(self, raw_result: dict[str, Any], normalized: dict[str, Any]) -> list[dict[str, str]]:
        raw_sections = raw_result.get("sections")
        if isinstance(raw_sections, list):
            sections = [
                {"heading": str(item.get("heading") or item.get("title")), "body": str(item.get("body") or item.get("content"))}
                for item in raw_sections
                if isinstance(item, dict) and (item.get("heading") or item.get("title")) and (item.get("body") or item.get("content"))
            ]
            if sections:
                return sections

        sections = [{"heading": "Draft", "body": str(normalized["summary"])}]
        findings = normalized.get("findings")
        if isinstance(findings, list) and findings:
            sections.append({"heading": "Important Details", "body": "\n\n".join(str(item) for item in findings)})
        actions = normalized.get("recommendedActions")
        if isinstance(actions, list) and actions:
            sections.append({"heading": "Recommended Next Steps", "body": "\n\n".join(str(item) for item in actions)})
        return [section for section in sections if section["body"].strip()]

    def _document_title(self, task: str) -> str:
        title = " ".join(task.split())[:90]
        return title or "Veritas Legal Document"

    def _is_download_artifact(self, value: Any) -> bool:
        return (
            isinstance(value, dict)
            and isinstance(value.get("artifactId"), str)
            and isinstance(value.get("filename"), str)
            and isinstance(value.get("contentType"), str)
            and isinstance(value.get("downloadUrl"), str)
        )

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in (str(item).strip() for item in value) if item]
