import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from solution import answer, build_index
from src.routes.grounded_answering import grounded_answering
from src.schemas.request import Request


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = {item["id"]: item["question"] for item in json.loads((PROJECT_ROOT / "src" / "data" / "questions.json").read_text(encoding="utf-8"))}


class SolutionInterfaceTests(unittest.TestCase):

    def test_harness_can_import_build_index_and_answer(self):
        self.assertTrue(callable(build_index))
        self.assertTrue(callable(answer))

    def test_live_endpoint_returns_answer_and_citations(self):
        response = grounded_answering(Request(content=QUESTIONS["Q01"]))
        payload = json.loads(response.content)
        self.assertTrue(response.flow_id)
        self.assertTrue(response.trace_id)
        self.assertIn("answer", payload)
        self.assertIn("citations", payload)
        self.assertIsInstance(payload["answer"], str)
        for citation in payload["citations"]:
            self.assertIn("article_title", citation)
            self.assertIn("snippet", citation)


if __name__ == "__main__":
    unittest.main()
