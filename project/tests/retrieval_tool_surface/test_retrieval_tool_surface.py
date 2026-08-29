import inspect
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.conts import RETRIEVAL_EVIDENCE_STORE_CORPUS, RETRIEVAL_EVIDENCE_STORE_FACTS, RETRIEVAL_STATUS_INVALID, RETRIEVAL_TOP_K
from src.services.retrieval_service import run_retrieval
from src.tools import retrieval_tools as retrieval_tools_module
from src.tools.retrieval_tools import RetrievalTools

FACT_ITEM = {"article_title": "Fact Title", "snippet": "A curated fact.", "url": "https://example.com/fact", "published_at": "2024-01-01T00:00:00", "match_percentage": 82.0}
CORPUS_ITEM = {"article_title": "Corpus Title", "snippet": "A corpus passage.", "url": "https://example.com/corpus", "published_at": "2024-02-01T00:00:00", "match_percentage": 75.0}
CHROMA_HIT = {"documents": [["A curated fact."]], "metadatas": [[{"article_title": "Fact Title", "url": "https://example.com/fact", "published_at": "2024-01-01T00:00:00"}]], "distances": [[0.18]]}


class RetrievalToolSurfaceTests(unittest.TestCase):

    @patch("src.tools.retrieval_tools.run_retrieval")
    def test_search_facts_queries_only_facts_and_hides_corpus(self, run_retrieval_mock):
        run_retrieval_mock.return_value = {"status": "ok", "question": "Who won?", "facts": [FACT_ITEM], "corpus": [CORPUS_ITEM]}
        result = RetrievalTools({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4())).search_facts("Who won?")
        self.assertEqual(RETRIEVAL_EVIDENCE_STORE_FACTS, run_retrieval_mock.call_args[0][0]["evidence_store"])
        self.assertEqual("ok", result["status"])
        self.assertEqual([FACT_ITEM], result["results"])
        self.assertNotIn("facts", result)
        self.assertNotIn("corpus", result)

    @patch("src.tools.retrieval_tools.run_retrieval")
    def test_search_corpus_queries_only_corpus_and_hides_facts(self, run_retrieval_mock):
        run_retrieval_mock.return_value = {"status": "ok", "question": "Who won?", "facts": [FACT_ITEM], "corpus": [CORPUS_ITEM]}
        result = RetrievalTools({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4())).search_corpus("Who won?")
        self.assertEqual(RETRIEVAL_EVIDENCE_STORE_CORPUS, run_retrieval_mock.call_args[0][0]["evidence_store"])
        self.assertEqual([CORPUS_ITEM], result["results"])
        self.assertNotIn("facts", result)
        self.assertNotIn("corpus", result)

    @patch("src.tools.retrieval_tools.run_retrieval")
    def test_invalid_question_returns_invalid_status(self, run_retrieval_mock):
        run_retrieval_mock.return_value = {"status": "empty", "question": "", "facts": [], "corpus": []}
        result = RetrievalTools({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4())).search_facts(None)
        self.assertEqual({"status": RETRIEVAL_STATUS_INVALID, "question": "", "results": []}, result)
        run_retrieval_mock.assert_not_called()

    def test_search_facts_bad_date_returns_invalid_status(self):
        result = RetrievalTools({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4())).search_facts("Who won?", published_from="not-a-date")
        self.assertEqual({"status": RETRIEVAL_STATUS_INVALID, "question": "Who won?", "results": []}, result)

    @patch("src.tools.retrieval_tools.run_retrieval")
    def test_search_facts_empty_status_is_machine_readable(self, run_retrieval_mock):
        run_retrieval_mock.return_value = {"status": "empty", "question": "Who won?", "facts": [], "corpus": []}
        result = RetrievalTools({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4())).search_facts("Who won?")
        self.assertEqual("empty", result["status"])
        self.assertEqual([], result["results"])

    @patch("src.tools.retrieval_tools.run_retrieval")
    def test_search_facts_results_include_citation_fields(self, run_retrieval_mock):
        run_retrieval_mock.return_value = {"status": "ok", "question": "Who won?", "facts": [FACT_ITEM], "corpus": []}
        result = RetrievalTools({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4())).search_facts("Who won?")
        self.assertEqual({"article_title", "snippet", "url", "published_at", "match_percentage"}, set(result["results"][0]))

    @patch("src.services.retrieval_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.retrieval_service.FactsChromaRepository.query_records")
    @patch("src.services.retrieval_service.CorpusChromaRepository.query_records")
    def test_facts_evidence_store_does_not_query_corpus(self, corpus_query, facts_query, generate_embeddings):
        generate_embeddings.return_value = [[0.1, 0.2]]
        facts_query.return_value = CHROMA_HIT
        result = run_retrieval({"question": "Who won?", "facts_chroma_path": "facts", "corpus_chroma_path": "corpus", "evidence_store": RETRIEVAL_EVIDENCE_STORE_FACTS}, str(uuid4()))
        facts_query.assert_called_once()
        corpus_query.assert_not_called()
        self.assertEqual("ok", result["status"])
        self.assertEqual([], result["corpus"])
        self.assertEqual(RETRIEVAL_TOP_K, facts_query.call_args[0][0]["top_k"])
        self.assertNotIn("query_embedding", facts_query.call_args[0][0])
        self.assertLessEqual(len(result["facts"]), RETRIEVAL_TOP_K)

    @patch("src.services.retrieval_service.LoggingRepository.log_event")
    @patch("src.services.retrieval_service.OpenAIEmbeddingsRepository.generate_embeddings")
    def test_missing_question_logs_error_without_embedding(self, generate_embeddings, log_event_mock):
        result = run_retrieval({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4()))
        generate_embeddings.assert_not_called()
        self.assertEqual({"status": "invalid", "question": "", "facts": [], "corpus": []}, result)
        self.assertIn("ERROR", [call.kwargs["status"] for call in log_event_mock.call_args_list])

    @patch("src.services.retrieval_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.retrieval_service.FactsChromaRepository.query_records")
    @patch("src.services.retrieval_service.CorpusChromaRepository.query_records")
    def test_missing_evidence_store_queries_both_stores(self, corpus_query, facts_query, generate_embeddings):
        generate_embeddings.return_value = [[0.1, 0.2]]
        facts_query.return_value = CHROMA_HIT
        corpus_query.return_value = CHROMA_HIT
        result = run_retrieval({"question": "Who won?", "facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4()))
        facts_query.assert_called_once()
        corpus_query.assert_called_once()
        self.assertEqual("ok", result["status"])

    @patch("src.tools.retrieval_tools.run_retrieval")
    def test_langchain_wrappers_hide_handle_and_keep_bound_store(self, run_retrieval_mock):
        run_retrieval_mock.return_value = {"status": "ok", "question": "Who won?", "facts": [FACT_ITEM], "corpus": []}
        langchain_tools = RetrievalTools({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4())).as_langchain_tools()
        schema_keys = set(langchain_tools[0].args_schema.model_json_schema()["properties"])
        self.assertEqual(["search_facts"], [tool.name for tool in langchain_tools])
        self.assertEqual({"question", "published_from", "published_to", "source"}, schema_keys)
        self.assertEqual([FACT_ITEM], langchain_tools[0].invoke({"question": "Who won?"})["results"])
        self.assertEqual(RETRIEVAL_EVIDENCE_STORE_FACTS, run_retrieval_mock.call_args[0][0]["evidence_store"])
        self.assertEqual("facts", run_retrieval_mock.call_args[0][0]["facts_chroma_path"])

    @patch("src.tools.retrieval_tools.run_retrieval")
    def test_search_facts_passes_source(self, run_retrieval_mock):
        run_retrieval_mock.return_value = {"status": "ok", "question": "Who won?", "facts": [FACT_ITEM], "corpus": []}
        RetrievalTools({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4())).search_facts("Who won?", source="The Age")
        self.assertEqual("The Age", run_retrieval_mock.call_args[0][0]["source"])

    @patch("src.services.source_resolve_service.FactsChromaRepository.read_source_catalog")
    @patch("src.services.retrieval_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.retrieval_service.FactsChromaRepository.query_records")
    @patch("src.services.retrieval_service.CorpusChromaRepository.query_records")
    def test_resolved_source_is_chroma_equality_filter(self, corpus_query, facts_query, generate_embeddings, read_source_catalog):
        read_source_catalog.return_value = {"sources": [{"name": "The Age", "embedding": [1.0, 0.0]}]}
        generate_embeddings.return_value = [[0.1, 0.2]]
        facts_query.return_value = CHROMA_HIT
        run_retrieval({"question": "Who won?", "source": "The Age", "facts_chroma_path": "facts", "corpus_chroma_path": "corpus", "evidence_store": RETRIEVAL_EVIDENCE_STORE_FACTS}, str(uuid4()))
        self.assertEqual({"source": "The Age"}, facts_query.call_args[0][0]["where"])
        generate_embeddings.assert_called_once()

    @patch("src.services.source_resolve_service.FactsChromaRepository.read_source_catalog")
    @patch("src.services.retrieval_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.retrieval_service.FactsChromaRepository.query_records")
    @patch("src.services.retrieval_service.CorpusChromaRepository.query_records")
    def test_source_filter_keeps_weak_similarity_hits(self, corpus_query, facts_query, generate_embeddings, read_source_catalog):
        read_source_catalog.return_value = {"sources": [{"name": "The Age", "embedding": [1.0, 0.0]}]}
        generate_embeddings.return_value = [[0.1, 0.2]]
        facts_query.return_value = {"documents": [["A curated fact."]], "metadatas": [[{"article_title": "Fact Title", "url": "https://example.com/fact", "published_at": "2024-01-01T00:00:00"}]], "distances": [[0.8]]}
        result = run_retrieval({"question": "Who won?", "source": "The Age", "facts_chroma_path": "facts", "corpus_chroma_path": "corpus", "evidence_store": RETRIEVAL_EVIDENCE_STORE_FACTS}, str(uuid4()))
        self.assertEqual(1, len(result["facts"]))
        self.assertEqual(20.0, result["facts"][0]["match_percentage"])

    @patch("src.services.retrieval_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.retrieval_service.FactsChromaRepository.query_records")
    @patch("src.services.retrieval_service.CorpusChromaRepository.query_records")
    def test_facts_keeps_weak_similarity_without_source_filter(self, corpus_query, facts_query, generate_embeddings):
        generate_embeddings.return_value = [[0.1, 0.2]]
        facts_query.return_value = {"documents": [["A curated fact."]], "metadatas": [[{"article_title": "Fact Title", "url": "https://example.com/fact", "published_at": "2024-01-01T00:00:00"}]], "distances": [[0.8]]}
        result = run_retrieval({"question": "Who won?", "facts_chroma_path": "facts", "corpus_chroma_path": "corpus", "evidence_store": RETRIEVAL_EVIDENCE_STORE_FACTS}, str(uuid4()))
        self.assertEqual(1, len(result["facts"]))
        self.assertEqual(20.0, result["facts"][0]["match_percentage"])

    def test_tools_module_reads_knowledge_only_through_run_retrieval(self):
        source = inspect.getsource(retrieval_tools_module)
        self.assertIn("run_retrieval", source)
        self.assertNotIn("corpus.json", source)
        self.assertNotIn("facts.json", source)
        self.assertNotIn("open(", source)


if __name__ == "__main__":
    unittest.main()
