import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from solution import answer, build_index
from src.conts import ANSWER_REFUSAL_TEXT, FACTS_CHROMA_PATH, LOG_FILE_PATH, WORKERS


REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "src" / "data"
ANSWERS_PATH = REPO_ROOT / "answers.json"
TRANSCRIPTS_PATH = REPO_ROOT / "transcripts.json"
OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
QUESTIONS = json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))


def loaded_index():
    if Path(FACTS_CHROMA_PATH).is_dir():
        return {"facts_chroma_path": FACTS_CHROMA_PATH}
    return build_index(str(DATA_DIR))


def answer_one(index, question_data):
    return {"id": question_data["id"], "question": question_data["question"], "result": answer(index, question_data["id"], question_data["question"])}


def log_file_offset():
    log_path = Path(LOG_FILE_PATH)
    if not log_path.is_file():
        return 0
    return log_path.stat().st_size


def parse_finished_events(log_bytes):
    events = []
    for line in log_bytes.decode("utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line).get("event") or {}
        if event.get("status") == "FINISHED" and event.get("process") == "run_grounded_answering":
            events.append(event)
    return events


def latest_finished_by_question(events):
    finished = {}
    for event in events:
        question_id = (event.get("content") or {}).get("question_id")
        if question_id:
            finished[question_id] = event
    return finished


def citation_in_evidence(citation, evidence):
    for item in evidence:
        if citation.get("article_title") == item.get("article_title") and citation.get("snippet") == item.get("snippet"):
            return True
    return False


def tool_calls_from_turns(turns):
    calls = []
    for turn in turns:
        if turn.get("stage") == "tools":
            calls.extend(turn.get("tool_calls") or [])
    return calls


def contract_evaluation(public, evidence, turns):
    citations = public.get("citations") or []
    answer_text = public.get("answer") or ""
    ungrounded = []
    for citation in citations:
        if not citation_in_evidence(citation, evidence):
            ungrounded.append(citation)
    tool_calls = tool_calls_from_turns(turns)
    return {"schema_answer_is_string": isinstance(answer_text, str) and bool(answer_text.strip()), "non_refusal_has_citation": answer_text == ANSWER_REFUSAL_TEXT or bool(citations), "citations_traced_to_evidence": not ungrounded, "tool_calls_present": bool(tool_calls), "tool_call_count": len(tool_calls), "ungrounded_citations": ungrounded}


def load_ground_truth(question_id):
    return json.loads((DATA_DIR / "ground_truth" / f"{question_id}.json").read_text(encoding="utf-8"))


def question_evaluation(result, event, ground_truth):
    public = result["result"]
    content = (event or {}).get("content") or {}
    contract = contract_evaluation(public, content.get("evidence") or [], content.get("transcript_turns") or [])
    return {"id": result["id"], "intents": ground_truth.get("intents") or [], "answer": public.get("answer"), "gt_answer": ground_truth.get("answer"), "gt_match": public.get("answer") == ground_truth.get("answer"), "contract": contract, "contract_passed": contract["schema_answer_is_string"] and contract["non_refusal_has_citation"] and contract["citations_traced_to_evidence"] and contract["tool_calls_present"]}


def transcript_record(result, event):
    content = (event or {}).get("content") or {}
    return {"id": result["id"], "question": result["question"], "flow_id": (event or {}).get("flow_id"), "turns": content.get("transcript_turns") or [], "evidence": content.get("evidence") or [], "answer_result": content.get("answer_result"), "public": result["result"]}


def public_answers(results):
    answers = []
    for result in results:
        answers.append({"id": result["id"], "answer": result["result"]["answer"], "citations": result["result"]["citations"]})
    return answers


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_questions(index):
    results = []
    failures = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {}
        for question_data in QUESTIONS:
            futures[pool.submit(answer_one, index, question_data)] = question_data["id"]
        for future in as_completed(futures):
            question_id = futures[future]
            try:
                results.append(future.result())
            except Exception as err:
                failures.append({"id": question_id, "error": repr(err)})
    return results, failures


def build_report(evaluations, failures):
    return {"question_count": len(evaluations), "contract_pass_count": len([item for item in evaluations if item["contract_passed"]]), "gt_match_count": len([item for item in evaluations if item["gt_match"]]), "failures": failures, "known_quality_limitations": "GT match is deferred. This run records schema, transcripts, citation traceability, and tool-only evidence.", "questions": evaluations}


def build_markdown(report):
    lines = ["# Answers, Transcripts, and Evaluation", "", f"Contract passes: {report['contract_pass_count']}/{report['question_count']}", f"GT matches (deferred quality): {report['gt_match_count']}/{report['question_count']}", "", report["known_quality_limitations"], "", "| ID | Answer | GT | Contract | GT match | Tool calls |", "|----|--------|----|----------|----------|------------|"]
    for item in report["questions"]:
        lines.append(f"| {item['id']} | {item['answer']} | {item['gt_answer']} | {item['contract_passed']} | {item['gt_match']} | {item['contract']['tool_call_count']} |")
    return "\n".join(lines) + "\n"


def write_deliverables(results, finished, failures):
    results.sort(key=lambda result: result["id"])
    transcripts = []
    evaluations = []
    for result in results:
        event = finished.get(result["id"])
        transcripts.append(transcript_record(result, event))
        evaluations.append(question_evaluation(result, event, load_ground_truth(result["id"])))
    write_json(ANSWERS_PATH, public_answers(results))
    write_json(TRANSCRIPTS_PATH, transcripts)
    report = build_report(evaluations, failures)
    write_json(OUTPUTS_DIR / "evaluation.json", report)
    (OUTPUTS_DIR / "evaluation.md").write_text(build_markdown(report), encoding="utf-8")
    return report


def main():
    start_offset = log_file_offset()
    results, failures = run_questions(loaded_index())
    finished = latest_finished_by_question(parse_finished_events(Path(LOG_FILE_PATH).read_bytes()[start_offset:] if Path(LOG_FILE_PATH).is_file() else b""))
    if failures or len(results) != len(QUESTIONS):
        write_json(OUTPUTS_DIR / "run_failures.json", {"failures": failures, "completed": [result["id"] for result in results]})
        raise SystemExit(1)
    write_deliverables(results, finished, failures)


if __name__ == "__main__":
    main()
