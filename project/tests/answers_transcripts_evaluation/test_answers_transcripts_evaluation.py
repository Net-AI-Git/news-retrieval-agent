import json
import unittest
from pathlib import Path

from src.conts import ANSWER_REFUSAL_TEXT, ANSWERS_PATH, DATA_DIR, TRANSCRIPTS_PATH


QUESTIONS = json.loads((Path(DATA_DIR) / "questions.json").read_text(encoding="utf-8"))


class AnswersTranscriptsEvaluationTests(unittest.TestCase):

    def setUp(self):
        self.assertTrue(Path(ANSWERS_PATH).is_file(), "answers.json is missing; run python solution.py first")
        self.assertTrue(Path(TRANSCRIPTS_PATH).is_file(), "transcripts.json is missing; run python solution.py first")
        self.answers = json.loads(Path(ANSWERS_PATH).read_text(encoding="utf-8"))
        self.transcripts = json.loads(Path(TRANSCRIPTS_PATH).read_text(encoding="utf-8"))

    def test_answers_have_all_question_ids(self):
        self.assertEqual([entry["id"] for entry in self.answers], [question["id"] for question in QUESTIONS])
        self.assertEqual(len(self.answers), len({entry["id"] for entry in self.answers}))

    def test_answers_match_public_schema(self):
        for entry in self.answers:
            self.assertEqual(sorted(entry.keys()), ["answer", "citations", "id"])
            self.assertIsInstance(entry["answer"], str)
            self.assertTrue(entry["answer"].strip())
            self.assertIsInstance(entry["citations"], list)
            for citation in entry["citations"]:
                self.assertEqual(sorted(citation.keys()), ["article_title", "snippet"])
                self.assertIsInstance(citation["article_title"], str)
                self.assertIsInstance(citation["snippet"], str)

    def test_non_refusal_has_citation(self):
        for entry in self.answers:
            if entry["answer"] != ANSWER_REFUSAL_TEXT:
                self.assertTrue(entry["citations"], entry["id"])

    def test_transcripts_cover_all_questions_with_tool_calls(self):
        self.assertEqual([entry["id"] for entry in self.transcripts], [question["id"] for question in QUESTIONS])
        for entry in self.transcripts:
            calls = []
            for turn in entry.get("turns") or []:
                calls.extend(turn.get("tool_calls") or [])
            self.assertTrue(calls, entry["id"])

    def test_citations_trace_to_transcript_evidence(self):
        evidence_by_id = {}
        for entry in self.transcripts:
            evidence_by_id[entry["id"]] = entry.get("evidence") or []
        for entry in self.answers:
            for citation in entry["citations"]:
                traced = False
                for item in evidence_by_id[entry["id"]]:
                    if citation["article_title"] == item.get("article_title") and citation["snippet"] == item.get("snippet"):
                        traced = True
                        break
                self.assertTrue(traced, entry["id"])


if __name__ == "__main__":
    unittest.main()
