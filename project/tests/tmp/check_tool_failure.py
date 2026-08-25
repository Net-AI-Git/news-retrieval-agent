import json
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from src.conts import ANSWER_STATUS_ANSWERED
from src.orchestration.grounded_answering_workflow import collect_tool_evidence, filter_answer_citations, run_grounded_answering
from src.schemas.agent import AnswerCitation, AnswerResult, SearchEvidenceOutput
from src.tools.retrieval_tools import RetrievalTools


def report(name, payload):
    sys.stdout.write(name + "\n" + json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n")


tools = RetrievalTools({"facts_chroma_path": "facts", "corpus_chroma_path": "corpus"}, str(uuid4()))
report("A_invalid_question", tools.search_facts(None))
report("B_bad_date_filter", tools.search_facts("Who won?", published_from="not-a-date"))

invalid_payload = SearchEvidenceOutput(status="invalid", question="", results=[]).model_dump_json()
report("C_collect_invalid_results", collect_tool_evidence([SimpleNamespace(content=invalid_payload)]))

answered = AnswerResult(status=ANSWER_STATUS_ANSWERED, answer="ChatGPT", citations=[AnswerCitation(article_title="T", url="https://example.com", snippet="s")])
report("D_filter_empty_evidence", filter_answer_citations(answered, []).model_dump())

try:
    collect_tool_evidence([SimpleNamespace(content="not-json")])
    report("E_collect_non_json", {"raised": False})
except Exception as err:
    report("E_collect_non_json", {"raised": True, "error": repr(err)})

missing = str(PROJECT_ROOT / "vector_stores" / "missing_chroma")
crash_result = run_grounded_answering({"question": "What is the name of the general-purpose chatbot developed by OpenAI?", "facts_chroma_path": missing, "corpus_chroma_path": missing}, str(uuid4()))
report("F_live_missing_chroma", crash_result)
