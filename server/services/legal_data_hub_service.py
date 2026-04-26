import os
import re
from typing import Any
from uuid import UUID

import httpx

from data_access.legal_case_repository import LegalCaseRepository
from data_access.trace_repository import TraceRepository, TraceRepositoryError


LEGAL_DATA_HUB_ENDPOINT = "/api/semantic-search"
DEFAULT_LEGAL_DATA_HUB_BASE_URL = "https://otto-schmidt.legal-data-hub.com"
LEGAL_DATA_HUB_FAILURE_MESSAGE = (
    "Legal Data Hub could not be reached. Veritas AI can still provide a case-context summary, "
    "but legal source grounding is unavailable."
)


class LegalDataHubConfigurationError(RuntimeError):
    """Raised when Legal Data Hub credentials are missing."""


class LegalDataHubService:
    def __init__(
        self,
        case_repository: LegalCaseRepository,
        trace_repository: TraceRepository,
        client: httpx.Client | None = None,
    ) -> None:
        self._case_repository = case_repository
        self._trace_repository = trace_repository
        self._client = client

    def search_for_chat(self, case_id: UUID, user_question: str) -> dict[str, Any]:
        legal_case = self._case_repository.get_by_id(case_id)
        if legal_case is None:
            return {
                "available": False,
                "message": "Case context could not be loaded for Legal Data Hub research.",
                "sources": [],
            }

        sanitized_question = self._sanitize(user_question, max_length=900)
        traces = self._safe_trace_context(case_id)
        case_context = self._case_context(legal_case, traces)
        data_asset = self._select_data_asset(sanitized_question, case_context)
        search_query = self._build_search_query(sanitized_question, case_context, data_asset)
        reasoning = self._reasoning(search_query, data_asset, case_context)

        input_payload = {
            "user_question": sanitized_question,
            "generated_search_query": search_query,
            "selected_data_asset": data_asset,
            "case_id": str(case_id),
        }
        tool_calls = [
            {
                "tool_name": "Legal Data Hub",
                "endpoint": LEGAL_DATA_HUB_ENDPOINT,
                "data_asset": data_asset,
            }
        ]

        try:
            raw_response = self._call_semantic_search(search_query=search_query, data_asset=data_asset)
            sources = self._parse_sources(raw_response)
            top_score = max((source.get("relevance_score") or 0 for source in sources), default=0)
            confidence = self._confidence(top_score=top_score, result_count=len(sources))
            human_in_loop_required = confidence < 0.75
            output_payload = {
                "returned_sources": sources,
                "number_of_results": len(sources),
                "top_relevance_score": top_score,
                "human_in_loop_required": human_in_loop_required,
            }
            self._save_trace(
                case_id=case_id,
                input_payload=input_payload,
                output_payload=output_payload,
                reasoning=reasoning,
                confidence=confidence,
                tool_calls=tool_calls,
            )
            return {
                "available": True,
                "message": "Legal Data Hub search completed.",
                "search_query": search_query,
                "data_asset": data_asset,
                "sources": sources,
                "confidence": confidence,
                "human_in_loop_required": human_in_loop_required,
                "answer_instructions": (
                    "Use these sources for a preliminary internal assessment only. State that the "
                    "answer is based on available case data, requires legal review, and should not be "
                    "treated as final legal advice."
                ),
            }
        except Exception:
            output_payload = {
                "returned_sources": [],
                "number_of_results": 0,
                "top_relevance_score": None,
                "human_in_loop_required": True,
                "status": "failed",
                "message": LEGAL_DATA_HUB_FAILURE_MESSAGE,
            }
            self._save_trace(
                case_id=case_id,
                input_payload=input_payload,
                output_payload=output_payload,
                reasoning=reasoning,
                confidence=0.35,
                tool_calls=tool_calls,
            )
            return {
                "available": False,
                "message": LEGAL_DATA_HUB_FAILURE_MESSAGE,
                "search_query": search_query,
                "data_asset": data_asset,
                "sources": [],
                "confidence": 0.35,
                "human_in_loop_required": True,
            }

    def _call_semantic_search(self, search_query: str, data_asset: str) -> dict[str, Any] | list[Any]:
        payload = {
            "candidates": self._candidate_count,
            "data_asset": data_asset,
            "filter": [{}],
            "search_query": search_query,
        }
        response = self._get_client().post(
            f"{self._base_url}{LEGAL_DATA_HUB_ENDPOINT}",
            json=payload,
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()

    def _parse_sources(self, raw_response: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
        items = self._result_items(raw_response)
        sources: list[dict[str, Any]] = []
        for item in items[: self._candidate_count]:
            source = self._source_from_item(item)
            if source:
                sources.append(source)
        return sources

    def _source_from_item(self, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None

        hit_source = self._first_record(item, ("_source", "source"))
        metadata = self._first_record(item, ("metadata", "meta", "document")) or {}
        if hit_source:
            source_metadata = self._first_record(hit_source, ("metadata", "meta", "document")) or {}
            metadata = {**source_metadata, **metadata}
        merged = {**metadata, **item}
        title = self._first_text(
            merged,
            (
                "title",
                "name",
                "headline",
                "document_title",
                "entscheidung",
                "caption",
                "leitsatz",
                "kontext",
                "normenkette",
                "ebene0",
                "ebene1",
            ),
        )
        excerpt = self._first_text(
            merged,
            ("highlight", "highlights", "excerpt", "snippet", "leitsatz", "text", "content", "abstract"),
            max_length=700,
        )
        score = self._score(merged)
        if not title and not excerpt:
            return None

        return {
            "title": title or "Legal Data Hub source",
            "court": self._first_text(merged, ("court", "gericht", "spruchkoerper", "gertyp")),
            "date": self._first_text(merged, ("date", "decision_date", "datum", "publication_date")),
            "ecli": self._first_text(merged, ("ecli", "ECLI")),
            "aktenzeichen": self._first_text(merged, ("aktenzeichen", "file_number", "az", "case_number")),
            "document_type": self._first_text(
                merged,
                ("document_type", "dokumententyp", "type", "doktyp", "category"),
            ),
            "relevance_score": score,
            "excerpt": excerpt,
            "why_used": self._why_used(title=title, excerpt=excerpt, score=score),
        }

    def _result_items(self, raw_response: dict[str, Any] | list[Any]) -> list[Any]:
        if isinstance(raw_response, list):
            return raw_response
        for key in ("results", "hits", "documents", "items", "data", "candidates"):
            value = raw_response.get(key)
            if key == "hits" and isinstance(value, dict):
                nested_hits = value.get("hits")
                if isinstance(nested_hits, list):
                    return nested_hits
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = self._result_items(value)
                if nested:
                    return nested
        return []

    def _case_context(self, legal_case: dict[str, object], traces: list[dict[str, object]]) -> dict[str, str]:
        return {
            "title": self._sanitize(legal_case.get("title"), max_length=180),
            "summary": self._sanitize(legal_case.get("case_summary"), max_length=900),
            "source_documents": self._sanitize(legal_case.get("source_documents"), max_length=900),
            "plaintiff": self._sanitize(legal_case.get("plaintiff"), max_length=160),
            "defendant": self._sanitize(legal_case.get("defendant"), max_length=160),
            "jurisdiction": self._sanitize(legal_case.get("jurisdiction"), max_length=160),
            "court_authority": self._sanitize(legal_case.get("court_authority"), max_length=160),
            "legal_issue": self._sanitize(legal_case.get("legal_issue"), max_length=260),
            "case_facts": self._sanitize(legal_case.get("case_facts"), max_length=700),
            "information_gaps": self._sanitize(legal_case.get("information_gaps"), max_length=400),
            "recent_trace": self._sanitize(self._trace_summary(traces), max_length=700),
        }

    def _build_search_query(self, user_question: str, case_context: dict[str, str], data_asset: str) -> str:
        parts = [
            user_question,
            case_context.get("legal_issue", ""),
            case_context.get("summary", ""),
            case_context.get("case_facts", ""),
            case_context.get("jurisdiction", ""),
        ]
        if data_asset == "Rechtsprechung":
            parts.extend(["deutsche Rechtsprechung", "BGH", "OLG", "Sachmangel", "Nachbesserung"])
        elif data_asset == "Gesetze":
            parts.extend(["BGB", "gesetzliche Anspruchsgrundlage", "deutsches Recht"])
        elif data_asset == "StEKs":
            parts.extend(["Steuerrecht", "Verwaltungsauffassung"])

        query = self._sanitize(" ".join(part for part in parts if part), max_length=1000)
        return query or user_question

    def _select_data_asset(self, question: str, case_context: dict[str, str]) -> str:
        text = f"{question} {case_context.get('legal_issue', '')}".lower()
        if re.search(r"\b(steuer|tax|stek|ust|estg|ao|verwaltungsanweisung)\b", text):
            return "StEKs"
        if re.search(r"(gesetz|statute|law|bgb|hgb|paragraph|§|norm|anspruchsgrundlage)", text):
            return "Gesetze"
        return "Rechtsprechung"

    def _reasoning(self, search_query: str, data_asset: str, case_context: dict[str, str]) -> str:
        legal_issue = case_context.get("legal_issue") or "the current legal issue"
        return (
            f"The query combines the user's legal question with {legal_issue}, case facts, jurisdiction, "
            f"and available trace context. {data_asset} was selected because it best matches the legal "
            "research intent for the question."
        )

    def _safe_trace_context(self, case_id: UUID) -> list[dict[str, object]]:
        try:
            return self._trace_repository.list_by_case_id(case_id)[:2]
        except Exception:
            return []

    def _trace_summary(self, traces: list[dict[str, object]]) -> str:
        summaries: list[str] = []
        for trace in traces:
            steps = trace.get("trace_steps")
            if not isinstance(steps, list):
                continue
            for step in steps[-3:]:
                if isinstance(step, dict):
                    summaries.append(
                        self._sanitize(
                            f"{step.get('step')}: {step.get('reasoning')} {step.get('output')}",
                            max_length=260,
                        )
                    )
        return " | ".join(item for item in summaries if item)

    def _save_trace(
        self,
        case_id: UUID,
        input_payload: dict[str, object],
        output_payload: dict[str, object],
        reasoning: str,
        confidence: float,
        tool_calls: list[dict[str, object]],
    ) -> None:
        try:
            self._trace_repository.create_trace_step(
                case_id=case_id,
                step="LEGAL_DATA_HUB_SEARCH",
                input_payload=input_payload,
                output_payload=output_payload,
                reasoning=reasoning,
                confidence=confidence,
                tool_calls=tool_calls,
            )
        except TraceRepositoryError:
            return

    def _sanitize(self, value: object, max_length: int) -> str:
        if isinstance(value, list):
            text = "; ".join(str(item) for item in value if item)
        elif isinstance(value, dict):
            text = " ".join(f"{key}: {item}" for key, item in value.items() if item)
        else:
            text = str(value or "")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_length]

    def _first_record(self, item: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any] | None:
        for key in keys:
            value = item.get(key)
            if isinstance(value, dict):
                return value
        return None

    def _first_text(self, item: dict[str, Any], keys: tuple[str, ...], max_length: int = 260) -> str:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                value = " ".join(str(entry) for entry in value if entry)
            text = self._sanitize(value, max_length=max_length)
            if text:
                return text
        return ""

    def _score(self, item: dict[str, Any]) -> float | None:
        for key in ("score", "relevance_score", "relevance", "_score", "similarity"):
            value = item.get(key)
            try:
                if value is not None:
                    score = float(value)
                    return round(score, 3)
            except (TypeError, ValueError):
                continue
        return None

    def _confidence(self, top_score: float | None, result_count: int) -> float:
        if not result_count:
            return 0.45
        if top_score is None:
            return 0.72
        normalized_score = top_score if top_score <= 1 else min(top_score / 100, 1)
        return round(max(0.55, min(0.92, normalized_score)), 2)

    def _why_used(self, title: str, excerpt: str, score: float | None) -> str:
        relevance = f" with relevance {score}" if score is not None else ""
        basis = title or excerpt[:120] or "the returned Legal Data Hub metadata"
        return f"Relevant to the case research question based on {basis}{relevance}."

    @property
    def _base_url(self) -> str:
        return os.getenv("LEGAL_DATA_HUB_BASE_URL", DEFAULT_LEGAL_DATA_HUB_BASE_URL).rstrip("/")

    @property
    def _candidate_count(self) -> int:
        raw_value = os.getenv("LEGAL_DATA_HUB_CANDIDATES", "5")
        try:
            return max(1, min(10, int(raw_value)))
        except ValueError:
            return 5

    @property
    def _headers(self) -> dict[str, str]:
        token = (
            os.getenv("api_hub_access_token")
            or os.getenv("API_HUB_ACCESS_TOKEN")
            or os.getenv("LEGAL_DATA_HUB_ACCESS_TOKEN")
            or os.getenv("LEGAL_DATA_HUB_TOKEN")
            or os.getenv("secret_data_hub")
            or os.getenv("SECRET_DATA_HUB")
        )
        client_id = os.getenv("LEGAL_DATA_HUB_CLIENT_ID") or os.getenv("client_id_data_hub")
        if not token:
            raise LegalDataHubConfigurationError("Legal Data Hub credentials are not configured.")

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if client_id:
            headers["X-Client-Id"] = client_id
        return headers

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            timeout = float(os.getenv("LEGAL_DATA_HUB_TIMEOUT_SECONDS", "12"))
            self._client = httpx.Client(timeout=timeout)
        return self._client
