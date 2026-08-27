import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.conts import ANSWER_STATUS_ANSWERED, ANSWER_STATUS_REFUSED, RERANK_KEEP_TOP_K
from src.orchestration import grounded_answering_workflow as workflow
from src.repositories.rerank_repository import OpenAIRerankRepository
from src.schemas.agent import AnswerCitation, AnswerResult
from src.services.rerank_evidence_service import run_rerank_evidence


ITEM_A = {"article_title": "A", "snippet": "Alpha fact.", "url": "https://example.com/a", "published_at": "2024-01-01T00:00:00", "match_percentage": 25.0}
ITEM_A_OTHER = {"article_title": "A", "snippet": "Another sentence from A.", "url": "https://example.com/a", "published_at": "2024-01-01T00:00:00", "match_percentage": 10.0}
ITEM_B = {"article_title": "B", "snippet": "Beta fact.", "url": "https://example.com/b", "published_at": "2024-01-02T00:00:00", "match_percentage": 80.0}
ITEM_C = {"article_title": "C", "snippet": "Gamma fact.", "url": "https://example.com/c", "published_at": "2024-01-03T00:00:00", "match_percentage": 40.0}


class RerankEvidenceTests(unittest.TestCase):

    def test_empty_evidence_skips_the_rerank_api(self):
        with patch("src.services.rerank_evidence_service.OpenAIRerankRepository.rerank_documents") as rerank_documents:
            self.assertEqual([], run_rerank_evidence({"question": "Who?", "evidence": []}, str(uuid4())))
            rerank_documents.assert_not_called()

    @patch("src.services.rerank_evidence_service.OpenAIRerankRepository.rerank_documents")
    def test_union_is_reordered_and_low_scores_are_dropped(self, rerank_documents):
        rerank_documents.return_value = [{"index": 0, "relevance_score": -0.1}, {"index": 1, "relevance_score": 0.9}, {"index": 2, "relevance_score": 0.4}]
        kept = run_rerank_evidence({"question": "Who?", "evidence": [ITEM_A, ITEM_B, ITEM_C]}, str(uuid4()))
        self.assertEqual([ITEM_B, ITEM_C], kept)

    @patch("src.services.rerank_evidence_service.OpenAIRerankRepository.rerank_documents")
    def test_duplicate_chunks_are_unioned_before_rerank(self, rerank_documents):
        rerank_documents.return_value = [{"index": 0, "relevance_score": 0.5}, {"index": 1, "relevance_score": 0.8}]
        kept = run_rerank_evidence({"question": "Who?", "evidence": [ITEM_A, ITEM_A, ITEM_B]}, str(uuid4()))
        self.assertEqual(["Alpha fact.", "Beta fact."], rerank_documents.call_args[0][0]["documents"])
        self.assertEqual([ITEM_B, ITEM_A], kept)

    @patch("src.services.rerank_evidence_service.OpenAIRerankRepository.rerank_documents")
    def test_same_url_keeps_distinct_facts(self, rerank_documents):
        rerank_documents.return_value = [{"index": 0, "relevance_score": 0.2}, {"index": 1, "relevance_score": 0.5}, {"index": 2, "relevance_score": 0.8}]
        kept = run_rerank_evidence({"question": "Who?", "evidence": [ITEM_A_OTHER, ITEM_A, ITEM_B]}, str(uuid4()))
        self.assertEqual(["Another sentence from A.", "Alpha fact.", "Beta fact."], rerank_documents.call_args[0][0]["documents"])
        self.assertEqual([ITEM_B, ITEM_A, ITEM_A_OTHER], kept)

    @patch("src.services.rerank_evidence_service.OpenAIRerankRepository.rerank_documents")
    def test_same_fact_from_two_hops_is_sent_once(self, rerank_documents):
        stronger_copy = {**ITEM_A, "match_percentage": 40.0}
        rerank_documents.return_value = [{"index": 0, "relevance_score": 0.5}, {"index": 1, "relevance_score": 0.8}]
        kept = run_rerank_evidence({"question": "Who?", "evidence": [ITEM_A, stronger_copy, ITEM_B]}, str(uuid4()))
        self.assertEqual(["Alpha fact.", "Beta fact."], rerank_documents.call_args[0][0]["documents"])
        self.assertEqual([ITEM_B, stronger_copy], kept)

    @patch("src.services.rerank_evidence_service.OpenAIRerankRepository.rerank_documents")
    def test_keep_cap_limits_answer_evidence(self, rerank_documents):
        evidence = []
        ranked_rows = []
        for index in range(RERANK_KEEP_TOP_K + 1):
            evidence.append({"article_title": str(index), "snippet": str(index), "url": "https://example.com/" + str(index), "published_at": "2024-01-01T00:00:00", "match_percentage": 50.0})
            ranked_rows.append({"index": index, "relevance_score": float(index)})
        rerank_documents.return_value = ranked_rows
        kept = run_rerank_evidence({"question": "Who?", "evidence": evidence}, str(uuid4()))
        self.assertEqual(RERANK_KEEP_TOP_K, len(kept))
        self.assertEqual(str(RERANK_KEEP_TOP_K), kept[0]["snippet"])

    @patch("src.services.rerank_evidence_service.OpenAIRerankRepository.rerank_documents")
    def test_api_failure_returns_none(self, rerank_documents):
        rerank_documents.return_value = []
        self.assertIsNone(run_rerank_evidence({"question": "Who?", "evidence": [ITEM_A]}, str(uuid4())))

    @patch("src.repositories.rerank_repository.requests.post")
    def test_repository_reads_index_and_score(self, post):
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"results": [{"index": 1, "relevance_score": 0.2}, {"index": 0, "relevance_score": 0.9}]}
        self.assertEqual([{"index": 1, "relevance_score": 0.2}, {"index": 0, "relevance_score": 0.9}], OpenAIRerankRepository.rerank_documents({"question": "Who?", "documents": ["a", "b"]}, str(uuid4())))

    @patch("src.orchestration.grounded_answering_workflow.run_answer")
    @patch("src.orchestration.grounded_answering_workflow.run_rerank_evidence")
    def test_answer_node_sends_reranked_evidence(self, run_rerank_evidence, run_answer):
        run_rerank_evidence.return_value = [ITEM_A]
        run_answer.return_value = AnswerResult(status=ANSWER_STATUS_ANSWERED, answer="Yes", citations=[AnswerCitation(article_title=ITEM_A["article_title"], url=ITEM_A["url"], snippet=ITEM_A["snippet"])])
        result = workflow.answer_node({"question": "Who?", "evidence": [ITEM_B, ITEM_A]}, {}, str(uuid4()))
        self.assertEqual([ITEM_A], run_answer.call_args[0][0]["evidence"])
        self.assertEqual(ANSWER_STATUS_ANSWERED, result["answer_result"].status)

    @patch("src.orchestration.grounded_answering_workflow.run_answer")
    @patch("src.orchestration.grounded_answering_workflow.run_rerank_evidence")
    def test_answer_node_keeps_gathered_evidence_when_rerank_fails(self, run_rerank_evidence, run_answer):
        run_rerank_evidence.return_value = None
        run_answer.return_value = AnswerResult(status=ANSWER_STATUS_REFUSED, answer="", citations=[])
        workflow.answer_node({"question": "Who?", "evidence": [ITEM_A]}, {}, str(uuid4()))
        self.assertEqual([ITEM_A], run_answer.call_args[0][0]["evidence"])


if __name__ == "__main__":
    unittest.main()
