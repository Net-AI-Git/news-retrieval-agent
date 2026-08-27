import inspect
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents import answer_agent, gather_agent
from src.conts import ANSWER_STATUS_ANSWERED, ANSWER_STATUS_REFUSED, CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH, GATHER_MAX_LLM_TURNS, GATHER_MAX_TOOL_CALLS, GROUNDED_ANSWERING_RECURSION_LIMIT
from src.orchestration import grounded_answering_workflow as workflow
from src.schemas.agent import AnswerCitation, AnswerResult, SearchEvidenceOutput


EVIDENCE_ITEM = {"article_title": "One year later, ChatGPT is still alive and kicking", "snippet": "ChatGPT can complete and debug code.", "url": "https://techcrunch.com/2023/11/30/one-year-later-chatgpt-is-still-alive-and-kicking/", "published_at": "2023-11-30T14:10:43+00:00", "match_percentage": 82.0}
QUESTIONS = {item["id"]: item["question"] for item in json.loads((PROJECT_ROOT / "src" / "data" / "questions.json").read_text(encoding="utf-8"))}


def invoke_live_question(question_id):
    task_data = {"question": QUESTIONS[question_id], "facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}
    return workflow.build_grounded_answering_graph(task_data, str(uuid4())).invoke({"question": task_data["question"], "messages": [HumanMessage(task_data["question"])], "evidence": [], "gather_count": 0, "tool_count": 0, "answer_result": None}, {"recursion_limit": GROUNDED_ANSWERING_RECURSION_LIMIT})


def snippet_is_in_evidence(citation, evidence):
    for item in evidence:
        if citation.snippet == item.get("snippet") and citation.url == item.get("url"):
            return True
    return False


class GroundedAnsweringTests(unittest.TestCase):

    def test_filter_keeps_matching_snippet_and_url(self):
        answer_result = AnswerResult(status=ANSWER_STATUS_ANSWERED, answer="ChatGPT", citations=[AnswerCitation(article_title=EVIDENCE_ITEM["article_title"], url=EVIDENCE_ITEM["url"], snippet=EVIDENCE_ITEM["snippet"])])
        filtered = workflow.filter_answer_citations(answer_result, [EVIDENCE_ITEM])
        self.assertEqual(ANSWER_STATUS_ANSWERED, filtered.status)
        self.assertEqual("ChatGPT", filtered.answer)
        self.assertEqual(EVIDENCE_ITEM["snippet"], filtered.citations[0].snippet)
        self.assertEqual(EVIDENCE_ITEM["url"], filtered.citations[0].url)

    def test_filter_refuses_when_url_is_not_in_evidence(self):
        answer_result = AnswerResult(status=ANSWER_STATUS_ANSWERED, answer="ChatGPT", citations=[AnswerCitation(article_title="Other", url="https://example.com/other", snippet=EVIDENCE_ITEM["snippet"])])
        filtered = workflow.filter_answer_citations(answer_result, [EVIDENCE_ITEM])
        self.assertEqual({"status": ANSWER_STATUS_REFUSED, "answer": "", "citations": []}, filtered.model_dump())

    def test_filter_refuses_when_snippet_is_not_in_evidence(self):
        answer_result = AnswerResult(status=ANSWER_STATUS_ANSWERED, answer="ChatGPT", citations=[AnswerCitation(article_title=EVIDENCE_ITEM["article_title"], url=EVIDENCE_ITEM["url"], snippet="A different sentence.")])
        filtered = workflow.filter_answer_citations(answer_result, [EVIDENCE_ITEM])
        self.assertEqual({"status": ANSWER_STATUS_REFUSED, "answer": "", "citations": []}, filtered.model_dump())

    def test_route_goes_to_answer_without_tool_calls(self):
        self.assertEqual("answer", workflow.route_after_gather({"gather_count": 1, "tool_count": 0, "messages": [SimpleNamespace(tool_calls=[])]}))

    def test_route_goes_to_tools_when_budget_remains(self):
        self.assertEqual("tools", workflow.route_after_gather({"gather_count": 1, "tool_count": 0, "messages": [SimpleNamespace(tool_calls=[{"name": "search_facts"}])]}))

    def test_route_caps_llm_and_tool_budget(self):
        self.assertEqual("answer", workflow.route_after_gather({"gather_count": GATHER_MAX_LLM_TURNS, "tool_count": 0, "messages": [SimpleNamespace(tool_calls=[{"name": "search_facts"}])]}))
        self.assertEqual("answer", workflow.route_after_gather({"gather_count": 1, "tool_count": GATHER_MAX_TOOL_CALLS, "messages": [SimpleNamespace(tool_calls=[{"name": "search_facts"}])]}))

    def test_collect_tool_evidence_reads_tool_payload_results(self):
        payload = SearchEvidenceOutput(status="ok", question="Who?", results=[EVIDENCE_ITEM]).model_dump_json()
        evidence = workflow.collect_tool_evidence([SimpleNamespace(content=payload)])
        self.assertEqual([EVIDENCE_ITEM], evidence)

    def test_agents_do_not_import_services_or_repositories(self):
        self.assertNotIn("services", inspect.getsource(gather_agent))
        self.assertNotIn("repositories", inspect.getsource(gather_agent))
        self.assertNotIn("services", inspect.getsource(answer_agent))
        self.assertNotIn("repositories", inspect.getsource(answer_agent))

    def test_prompts_exist_and_require_verbatim_snippet(self):
        prompts_dir = PROJECT_ROOT / "src" / "prompts"
        gather_prompt = (prompts_dir / "gather_agent.md").read_text(encoding="utf-8")
        answer_prompt = (prompts_dir / "answer_agent.md").read_text(encoding="utf-8")
        self.assertIn("[INSTRUCTIONS]", gather_prompt)
        self.assertIn("search_facts", gather_prompt)
        self.assertIn("Do not request source files", gather_prompt)
        self.assertIn("# Identity", answer_prompt)
        self.assertIn("published_at", answer_prompt)
        self.assertIn("copy article_title, url, and snippet exactly", answer_prompt)
        self.assertNotIn("Flipboard", answer_prompt)
        self.assertNotIn("Forerunner", answer_prompt)
        self.assertNotIn("Tremblant", answer_prompt)

    def test_workflow_does_not_read_source_json(self):
        source = inspect.getsource(workflow)
        self.assertNotIn("facts.json", source)
        self.assertNotIn("corpus.json", source)

    def test_extract_tool_calls_keeps_name_and_args(self):
        self.assertEqual([{"name": "search_facts", "args": {"question": "Who?"}}], workflow.extract_tool_calls(SimpleNamespace(tool_calls=[{"name": "search_facts", "args": {"question": "Who?"}}])))

    @patch("src.orchestration.grounded_answering_workflow.run_answer")
    def test_answer_node_sends_gathered_evidence(self, run_answer):
        run_answer.return_value = AnswerResult(status=ANSWER_STATUS_ANSWERED, answer="Yes", citations=[AnswerCitation(article_title=EVIDENCE_ITEM["article_title"], url=EVIDENCE_ITEM["url"], snippet=EVIDENCE_ITEM["snippet"])])
        result = workflow.answer_node({"question": "Who?", "evidence": [EVIDENCE_ITEM]}, {}, str(uuid4()))
        self.assertEqual([EVIDENCE_ITEM], run_answer.call_args[0][0]["evidence"])
        self.assertEqual(ANSWER_STATUS_ANSWERED, result["answer_result"].status)

    def test_live_q01_answers_yes_with_grounded_snippets(self):
        state = invoke_live_question("Q01")
        answer_result = state["answer_result"]
        self.assertEqual(ANSWER_STATUS_ANSWERED, answer_result.status)
        self.assertEqual("Yes", answer_result.answer)
        self.assertTrue(answer_result.citations)
        for citation in answer_result.citations:
            self.assertTrue(snippet_is_in_evidence(citation, state.get("evidence") or []))

    def test_live_q07_answers_chatgpt_with_grounded_snippets(self):
        state = invoke_live_question("Q07")
        answer_result = state["answer_result"]
        self.assertEqual(ANSWER_STATUS_ANSWERED, answer_result.status)
        self.assertEqual("ChatGPT", answer_result.answer)
        self.assertTrue(answer_result.citations)
        for citation in answer_result.citations:
            self.assertTrue(snippet_is_in_evidence(citation, state.get("evidence") or []))

    def test_live_q09_refuses_without_citations(self):
        state = invoke_live_question("Q09")
        self.assertEqual({"status": ANSWER_STATUS_REFUSED, "answer": "", "citations": []}, state["answer_result"].model_dump())


if __name__ == "__main__":
    unittest.main()
