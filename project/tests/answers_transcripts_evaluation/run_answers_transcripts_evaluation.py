import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.conts import ANSWER_REFUSAL_TEXT, DATA_DIR, TRANSCRIPTS_PATH


OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"


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
    return json.loads((Path(DATA_DIR) / "ground_truth" / f"{question_id}.json").read_text(encoding="utf-8"))


def question_evaluation(transcript):
    public = transcript["public"]
    contract = contract_evaluation(public, transcript.get("evidence") or [], transcript.get("turns") or [])
    ground_truth = load_ground_truth(transcript["id"])
    return {"id": transcript["id"], "intents": ground_truth.get("intents") or [], "answer": public.get("answer"), "gt_answer": ground_truth.get("answer"), "gt_match": public.get("answer") == ground_truth.get("answer"), "contract": contract, "contract_passed": contract["schema_answer_is_string"] and contract["non_refusal_has_citation"] and contract["citations_traced_to_evidence"] and contract["tool_calls_present"]}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_report(evaluations):
    return {"question_count": len(evaluations), "contract_pass_count": len([item for item in evaluations if item["contract_passed"]]), "gt_match_count": len([item for item in evaluations if item["gt_match"]]), "failures": [], "known_quality_limitations": "GT match is recorded from the public solution.py path. Schema, transcripts, citation traceability, and tool-only evidence remain the assignment contract.", "questions": evaluations}


def build_markdown(report):
    lines = ["# Answers, Transcripts, and Evaluation", "", f"Contract passes: {report['contract_pass_count']}/{report['question_count']}", f"GT matches: {report['gt_match_count']}/{report['question_count']}", "", report["known_quality_limitations"], "", "| ID | Answer | GT | Contract | GT match | Tool calls |", "|----|--------|----|----------|----------|------------|"]
    for item in report["questions"]:
        lines.append(f"| {item['id']} | {item['answer']} | {item['gt_answer']} | {item['contract_passed']} | {item['gt_match']} | {item['contract']['tool_call_count']} |")
    return "\n".join(lines) + "\n"


def write_evaluation():
    transcripts = json.loads(Path(TRANSCRIPTS_PATH).read_text(encoding="utf-8"))
    evaluations = []
    for transcript in transcripts:
        evaluations.append(question_evaluation(transcript))
    report = build_report(evaluations)
    write_json(OUTPUTS_DIR / "evaluation.json", report)
    (OUTPUTS_DIR / "evaluation.md").write_text(build_markdown(report), encoding="utf-8")
    return report


def main():
    write_evaluation()


if __name__ == "__main__":
    main()
