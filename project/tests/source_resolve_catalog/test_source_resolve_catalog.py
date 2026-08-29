import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.services.source_resolve_service import accepted_source_name, run_resolve_source


CATALOG = {"sources": [{"name": "The Age", "embedding": [1.0, 0.0]}, {"name": "The Independent - Travel", "embedding": [1.0, 0.0]}, {"name": "The Independent - Sports", "embedding": [0.7, 0.7]}, {"name": "The Independent - Life and Style", "embedding": [0.6, 0.8]}, {"name": "TechCrunch", "embedding": [0.0, 1.0]}, {"name": "BBC News - Entertainment & Arts", "embedding": [0.2, 0.3]}]}


def resolve_task(source):
    return {"source": source, "facts_chroma_path": "facts"}


class SourceResolveCatalogTests(unittest.TestCase):

    @patch("src.services.source_resolve_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.source_resolve_service.FactsChromaRepository.read_source_catalog")
    def test_exact_source_skips_embeddings(self, read_source_catalog, generate_embeddings):
        read_source_catalog.return_value = CATALOG
        self.assertEqual("The Age", run_resolve_source(resolve_task("The Age"), str(uuid4())))
        generate_embeddings.assert_not_called()

    @patch("src.services.source_resolve_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.source_resolve_service.FactsChromaRepository.read_source_catalog")
    def test_unique_substring_skips_embeddings(self, read_source_catalog, generate_embeddings):
        read_source_catalog.return_value = CATALOG
        self.assertEqual("The Age", run_resolve_source(resolve_task("Age"), str(uuid4())))
        generate_embeddings.assert_not_called()

    @patch("src.services.source_resolve_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.source_resolve_service.FactsChromaRepository.read_source_catalog")
    def test_bbc_news_unique_substring(self, read_source_catalog, generate_embeddings):
        read_source_catalog.return_value = CATALOG
        self.assertEqual("BBC News - Entertainment & Arts", run_resolve_source(resolve_task("BBC News"), str(uuid4())))
        generate_embeddings.assert_not_called()

    @patch("src.services.source_resolve_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.source_resolve_service.FactsChromaRepository.read_source_catalog")
    def test_ambiguous_independent_picks_nearest_with_margin(self, read_source_catalog, generate_embeddings):
        read_source_catalog.return_value = CATALOG
        generate_embeddings.return_value = [[0.99, 0.01]]
        self.assertEqual("The Independent - Travel", run_resolve_source(resolve_task("Independent"), str(uuid4())))
        generate_embeddings.assert_called_once()

    @patch("src.services.source_resolve_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.source_resolve_service.FactsChromaRepository.read_source_catalog")
    def test_empty_source_does_not_filter(self, read_source_catalog, generate_embeddings):
        read_source_catalog.return_value = CATALOG
        self.assertIsNone(run_resolve_source(resolve_task(""), str(uuid4())))
        generate_embeddings.assert_not_called()

    @patch("src.services.source_resolve_service.OpenAIEmbeddingsRepository.generate_embeddings")
    @patch("src.services.source_resolve_service.FactsChromaRepository.read_source_catalog")
    def test_missing_catalog_does_not_filter(self, read_source_catalog, generate_embeddings):
        read_source_catalog.return_value = None
        self.assertIsNone(run_resolve_source(resolve_task("The Age"), str(uuid4())))
        generate_embeddings.assert_not_called()

    def test_low_similarity_is_rejected(self):
        self.assertIsNone(accepted_source_name([(0.4, "TechCrunch")]))

    def test_tight_margin_is_rejected(self):
        self.assertIsNone(accepted_source_name([(0.81, "The Independent - Travel"), (0.8, "The Independent - Sports")]))


if __name__ == "__main__":
    unittest.main()
