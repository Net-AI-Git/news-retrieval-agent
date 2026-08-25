import inspect
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents import answer_agent, gather_agent
from src.conts import ANSWER_STATUS_ANSWERED, ANSWER_STATUS_REFUSED, CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH, GATHER_MAX_LLM_TURNS, GATHER_MAX_TOOL_CALLS
from src.orchestration import grounded_answering_workflow as workflow
from src.routes.grounded_answering import grounded_answering
from src.schemas.agent import AnswerCitation, AnswerResult, SearchEvidenceOutput
from src.schemas.request import Request


EVIDENCE_ITEM = {"article_title": "One year later, ChatGPT is still alive and kicking", "snippet": "ChatGPT can complete and debug code.", "url": "https://techcrunch.com/2023/11/30/one-year-later-chatgpt-is-still-alive-and-kicking/", "published_at": "2023-11-30T14:10:43+00:00", "match_percentage": 82.0}


class GroundedAnsweringTests(unittest.TestCase):

    def test_filter_keeps_url_that_is_in_evidence(self):
        answer_result = AnswerResult(status=ANSWER_STATUS_ANSWERED, answer="ChatGPT", citations=[AnswerCitation(article_title=EVIDENCE_ITEM["article_title"], url=EVIDENCE_ITEM["url"])])
        filtered = workflow.filter_answer_citations(answer_result, [EVIDENCE_ITEM])
        self.assertEqual(ANSWER_STATUS_ANSWERED, filtered.status)
        self.assertEqual("ChatGPT", filtered.answer)
        self.assertEqual(EVIDENCE_ITEM["url"], filtered.citations[0].url)

    def test_filter_refuses_when_url_is_not_in_evidence(self):
        answer_result = AnswerResult(status=ANSWER_STATUS_ANSWERED, answer="ChatGPT", citations=[AnswerCitation(article_title="Other", url="https://example.com/other")])
        filtered = workflow.filter_answer_citations(answer_result, [EVIDENCE_ITEM])
        self.assertEqual({"status": ANSWER_STATUS_REFUSED, "answer": "", "citations": []}, filtered.model_dump())

    def test_filter_matches_title_when_url_is_missing(self):
        answer_result = AnswerResult(status=ANSWER_STATUS_ANSWERED, answer="ChatGPT", citations=[AnswerCitation(article_title=EVIDENCE_ITEM["article_title"], url=None)])
        filtered = workflow.filter_answer_citations(answer_result, [EVIDENCE_ITEM])
        self.assertEqual(ANSWER_STATUS_ANSWERED, filtered.status)
        self.assertEqual(EVIDENCE_ITEM["article_title"], filtered.citations[0].article_title)

    def test_empty_evidence_skips_answer_llm(self):
        with patch("src.orchestration.grounded_answering_workflow.run_answer") as run_answer_mock:
            result = workflow.answer_node({"question": "Who?", "evidence": []}, str(uuid4()))
        run_answer_mock.assert_not_called()
        self.assertEqual(ANSWER_STATUS_REFUSED, result["answer_result"].status)

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

    def test_prompts_exist_and_forbid_source_files(self):
        prompts_dir = Path(__file__).resolve().parents[2] / "src" / "prompts"
        gather_prompt = (prompts_dir / "gather_agent.md").read_text(encoding="utf-8")
        answer_prompt = (prompts_dir / "answer_agent.md").read_text(encoding="utf-8")
        self.assertIn("[INSTRUCTIONS]", gather_prompt)
        self.assertIn("search_facts", gather_prompt)
        self.assertIn("Do not request source files", gather_prompt)
        self.assertIn("REFUSAL", answer_prompt)
        self.assertIn("Do NOT wrap the response in markdown code blocks", answer_prompt)

    def test_workflow_does_not_read_source_json(self):
        source = inspect.getsource(workflow)
        self.assertNotIn("facts.json", source)
        self.assertNotIn("corpus.json", source)

    def test_run_grounded_answering_refuses_on_error(self):
        with patch("src.orchestration.grounded_answering_workflow.invoke_grounded_answering_graph", side_effect=RuntimeError("boom")):
            with patch("src.orchestration.grounded_answering_workflow.OpenSearchRepository.log_event"):
                result = workflow.run_grounded_answering({"question": "Who?", "facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4()))
        self.assertEqual({"status": ANSWER_STATUS_REFUSED, "answer": "", "citations": []}, result)

    @patch("src.routes.grounded_answering.run_grounded_answering")
    def test_route_creates_one_flow_id_and_calls_orchestration(self, run_grounded_answering_mock):
        run_grounded_answering_mock.return_value = {"status": ANSWER_STATUS_REFUSED, "answer": "", "citations": []}
        result = grounded_answering(Request(content="Who won?"))
        task_data, flow_id = run_grounded_answering_mock.call_args[0]
        self.assertEqual({"question": "Who won?", "facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}, task_data)
        self.assertTrue(flow_id)
        self.assertEqual(1, run_grounded_answering_mock.call_count)
        self.assertEqual('{"status": "refused", "answer": "", "citations": []}', result.content)


if __name__ == "__main__":
    unittest.main()
