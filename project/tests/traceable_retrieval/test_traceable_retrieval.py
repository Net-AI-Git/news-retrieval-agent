import json
import os
import sys
import unittest
from pathlib import Path
from uuid import uuid4

import chromadb
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from solution import build_index
from src.conts import CORPUS_ACTIVE_COLLECTION, FACTS_ACTIVE_COLLECTION
from src.services.retrieval_service import run_retrieval


class TraceableRetrievalTests(unittest.TestCase):

    def test_retrieval_uses_real_embedding_and_both_chroma_stores(self):
        project_root = Path(__file__).resolve().parents[2]
        with (project_root / "src" / "data" / "questions.json").open(encoding="utf-8") as questions_file:
            question = next(item["question"] for item in json.load(questions_file) if item["id"] == "Q01")
        result = run_retrieval({"question": question, "facts_chroma_path": str(project_root / "vector_stores" / "facts_chroma"), "corpus_chroma_path": str(project_root / "vector_stores" / "corpus_chroma")}, str(uuid4()))
        self.assertEqual("ok", result["status"])
        self.assertLessEqual(len(result["facts"]), 10)
        self.assertLessEqual(len(result["corpus"]), 10)
        self.assertTrue(any("Cowboys" in item["snippet"] and "Seahawks" in item["snippet"] for item in result["facts"] + result["corpus"]))
        self.assertTrue(any("Lions" in item["snippet"] and "Packers" in item["snippet"] for item in result["facts"] + result["corpus"]))
        for item in result["facts"] + result["corpus"]:
            self.assertEqual({"article_title", "snippet", "url", "published_at", "match_percentage"}, set(item))

    @unittest.skipUnless(os.getenv("RUN_INDEX_REBUILD_TEST") == "true", "Set RUN_INDEX_REBUILD_TEST=true to rebuild the real indexes")
    def test_build_index_handle_is_reused_for_multiple_questions(self):
        project_root = Path(__file__).resolve().parents[2]
        index = build_index(str(project_root / "src" / "data"))
        self.assertTrue(index["facts_chroma_path"] and Path(index["facts_chroma_path"]).is_dir())
        self.assertTrue(index["corpus_chroma_path"] and Path(index["corpus_chroma_path"]).is_dir())
        facts_collection = chromadb.PersistentClient(path=index["facts_chroma_path"]).get_collection(FACTS_ACTIVE_COLLECTION, embedding_function=None)
        corpus_collection = chromadb.PersistentClient(path=index["corpus_chroma_path"]).get_collection(CORPUS_ACTIVE_COLLECTION, embedding_function=None)
        counts_before_queries = (facts_collection.count(), corpus_collection.count())
        with (project_root / "src" / "data" / "questions.json").open(encoding="utf-8") as questions_file:
            questions = {item["id"]: item["question"] for item in json.load(questions_file)}
        for question_id in ["Q01", "Q02"]:
            result = run_retrieval({**index, "question": questions[question_id]}, str(uuid4()))
            self.assertEqual("ok", result["status"])
            self.assertTrue(result["facts"] or result["corpus"])
        self.assertEqual(counts_before_queries, (facts_collection.count(), corpus_collection.count()))


if __name__ == "__main__":
    unittest.main()
