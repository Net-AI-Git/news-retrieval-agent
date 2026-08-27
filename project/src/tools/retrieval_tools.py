from typing import Optional

from langchain_core.tools import StructuredTool

from ..conts import RETRIEVAL_EVIDENCE_STORE_CORPUS, RETRIEVAL_EVIDENCE_STORE_FACTS, RETRIEVAL_STATUS_INVALID
from ..schemas.agent import SearchEvidenceInput, SearchEvidenceOutput
from ..services.retrieval_service import run_retrieval


class RetrievalTools:

    def __init__(self, task_data, flow_id):
        self.task_data = task_data
        self.flow_id = flow_id

    def search_facts(self, question: str, published_from: Optional[str] = None, published_to: Optional[str] = None, source: Optional[str] = None) -> dict:
        """Search curated one-sentence facts. Call this first when a short factual answer may exist. Optional published_from and published_to are inclusive ISO-8601 timestamps that keep only facts whose article date is in range. Optional source is a news-outlet name copied from the question when present; partial names are allowed; omit source when the question does not name an outlet. Returns status, the query, and a bounded citation-ready result list."""
        try:
            payload = SearchEvidenceInput.model_validate({"question": question, "published_from": published_from, "published_to": published_to, "source": source})
            retrieval_result = run_retrieval({**self.task_data, "question": payload.question, "published_from": payload.published_from, "published_to": payload.published_to, "source": payload.source, "evidence_store": RETRIEVAL_EVIDENCE_STORE_FACTS}, self.flow_id)
            return SearchEvidenceOutput(status=retrieval_result["status"], question=payload.question, results=retrieval_result[RETRIEVAL_EVIDENCE_STORE_FACTS]).model_dump()
        except Exception:
            return SearchEvidenceOutput(status=RETRIEVAL_STATUS_INVALID, question="", results=[]).model_dump()

    def search_corpus(self, question: str, published_from: Optional[str] = None, published_to: Optional[str] = None, source: Optional[str] = None) -> dict:
        """Search article passages for broader context, cross-article evidence, and details missing from curated facts. Use after search_facts when more support is needed. Optional published_from and published_to are inclusive ISO-8601 timestamps that keep only passages whose article date is in range. Optional source is a news-outlet name copied from the question when present; partial names are allowed; omit source when the question does not name an outlet. Returns status, the query, and a bounded citation-ready result list."""
        try:
            payload = SearchEvidenceInput.model_validate({"question": question, "published_from": published_from, "published_to": published_to, "source": source})
            retrieval_result = run_retrieval({**self.task_data, "question": payload.question, "published_from": payload.published_from, "published_to": payload.published_to, "source": payload.source, "evidence_store": RETRIEVAL_EVIDENCE_STORE_CORPUS}, self.flow_id)
            return SearchEvidenceOutput(status=retrieval_result["status"], question=payload.question, results=retrieval_result[RETRIEVAL_EVIDENCE_STORE_CORPUS]).model_dump()
        except Exception:
            return SearchEvidenceOutput(status=RETRIEVAL_STATUS_INVALID, question="", results=[]).model_dump()

    def as_langchain_tools(self):
        return [StructuredTool.from_function(self.search_facts, args_schema=SearchEvidenceInput)]
