import csv
import json
from datetime import datetime
from pathlib import Path
from time import sleep
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.agents.retrieve_agent import run_retrieve


METRIC_FIELDNAMES = ["question_id", "hop_count", "hops_passed", "retrieve_success", "prompt_leak_hit", "rewritten_question_count", "source_fail_count", "dates_fail_count", "call_fail_count", "answered_count", "fail_reasons", "runtime_error"]
HOP_FIELDNAMES = ["question_id", "hop_index", "sub_question", "agent_question", "question_copied", "gt_source", "agent_source", "source_ok", "gt_published_from", "gt_published_to", "agent_published_from", "agent_published_to", "dates_ok", "tool_name", "call_count", "answered", "hop_success", "fail_reason", "runtime_error"]
LIVE_RETRIEVE_PAUSE_SECONDS = 12
LEAK_SKIP_ANSWERS = {"yes", "no", "insufficient information"}
LEAK_MIN_CHARS = 24
SOURCE_STOPWORDS = {"the", "a", "an", "and", "or", "of", "in", "on", "for", "to", "by", "from", "did", "who", "which", "that", "this", "article", "report"}


def add_exam_needle(needles, text):
    value = " ".join((text or "").split())
    if len(value) < LEAK_MIN_CHARS or value.lower() in LEAK_SKIP_ANSWERS:
        return
    if value not in needles:
        needles.append(value)


def exam_needles_from_ground_truth(question_data, ground_truth):
    needles = []
    add_exam_needle(needles, question_data.get("question"))
    add_exam_needle(needles, ground_truth.get("answer"))
    for item in (ground_truth.get("facts") or []) + (ground_truth.get("citations") or []):
        add_exam_needle(needles, item.get("fact") or item.get("snippet"))
        add_exam_needle(needles, item.get("article_title"))
        add_exam_needle(needles, item.get("url"))
    for sub_question in ground_truth.get("sub_questions") or []:
        add_exam_needle(needles, sub_question)
    for call in ground_truth.get("expected_tool_calls") or []:
        add_exam_needle(needles, (call.get("arguments") or {}).get("question"))
    return needles


def collect_exam_needles(project_root, questions):
    needles = []
    for question_data in questions:
        for needle in exam_needles_from_ground_truth(question_data, load_ground_truth(project_root, question_data)):
            add_exam_needle(needles, needle)
    return needles


def prompt_leak_hit(prompt_text, needles):
    for needle in needles:
        if needle in prompt_text:
            return 1
    return 0


def normalize_text(text):
    return " ".join((text or "").lower().split())


def has_utc_offset(value):
    text = value or ""
    return "Z" in text or "+" in text[10:]


def source_ok(agent_source, sub_question, gt_source):
    agent = normalize_text(agent_source)
    gold = normalize_text(gt_source)
    haystack = normalize_text(sub_question)
    if not gold:
        return int(not agent)
    if not agent or agent in SOURCE_STOPWORDS or agent not in haystack:
        return 0
    return int(agent in gold or gold in agent)


def dates_ok(agent_from, agent_to, gt_from, gt_to):
    if not gt_from and not gt_to:
        return int(not agent_from and not agent_to)
    if not agent_from or not agent_to:
        return 0
    if not has_utc_offset(agent_from) or not has_utc_offset(agent_to):
        return 0
    return int(agent_from[:10] == (gt_from or "")[:10] and agent_to[:10] == (gt_to or "")[:10])


def load_ground_truth(project_root, question_data):
    ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
        raise ValueError(f"Ground truth mismatch for {question_data['id']}")
    return ground_truth


def retrieve_gt_calls(ground_truth):
    calls = []
    for item in ground_truth.get("expected_tool_calls") or []:
        if item.get("agent") == "retrieve":
            calls.append(item)
    return calls


def hop_sub_question(ground_truth, call):
    arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
    index = call.get("sub_question_index") or 0
    sub_questions = ground_truth.get("sub_questions") or []
    if index >= 1 and index <= len(sub_questions) and (sub_questions[index - 1] or "").strip():
        return sub_questions[index - 1]
    return arguments.get("question") or ""


def message_calls(message):
    calls = []
    for tool_call in getattr(message, "tool_calls", None) or []:
        arguments = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)
        if not isinstance(arguments, dict):
            arguments = {}
        name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
        calls.append({"tool": name or "", "question": arguments.get("question") or "", "source": arguments.get("source") or "", "published_from": arguments.get("published_from") or "", "published_to": arguments.get("published_to") or ""})
    return calls


def message_answered(message):
    content = getattr(message, "content", "") or ""
    if isinstance(content, list):
        content = " ".join(str(part) for part in content)
    return int(bool(str(content).strip()))


def hop_fail_reason(question_copied_flag, source_ok_flag, dates_ok_flag, call_count, tool_name, answered_flag, leak_hit, runtime_error):
    if runtime_error:
        return "runtime_error"
    if leak_hit:
        return "prompt_leak"
    if call_count != 1:
        return "call_count"
    if tool_name != "search_facts":
        return "wrong_tool"
    if answered_flag:
        return "answered"
    if not question_copied_flag:
        return "rewritten_question"
    if not source_ok_flag:
        return "source"
    if not dates_ok_flag:
        return "dates"
    return ""


def score_hop(question_id, hop_index, gt_arguments, sub_question, message, leak_hit, runtime_error):
    calls = message_calls(message)
    first_call = calls[0] if calls else {"tool": "", "question": "", "source": "", "published_from": "", "published_to": ""}
    question_copied_flag = int(normalize_text(first_call["question"]) == normalize_text(sub_question))
    source_ok_flag = source_ok(first_call["source"], sub_question, gt_arguments.get("source") or "")
    dates_ok_flag = dates_ok(first_call["published_from"], first_call["published_to"], gt_arguments.get("published_from") or "", gt_arguments.get("published_to") or "")
    answered_flag = message_answered(message)
    reason = hop_fail_reason(question_copied_flag, source_ok_flag, dates_ok_flag, len(calls), first_call["tool"], answered_flag, leak_hit, runtime_error)
    return {"question_id": question_id, "hop_index": hop_index, "sub_question": sub_question, "agent_question": first_call["question"], "question_copied": question_copied_flag, "gt_source": gt_arguments.get("source") or "", "agent_source": first_call["source"], "source_ok": source_ok_flag, "gt_published_from": gt_arguments.get("published_from") or "", "gt_published_to": gt_arguments.get("published_to") or "", "agent_published_from": first_call["published_from"], "agent_published_to": first_call["published_to"], "dates_ok": dates_ok_flag, "tool_name": first_call["tool"], "call_count": len(calls), "answered": answered_flag, "hop_success": int(not reason), "fail_reason": reason, "runtime_error": runtime_error, "prompt_leak_hit": leak_hit}


def empty_message():
    return type("Message", (), {"tool_calls": [], "content": ""})()


def empty_hop(question_id, hop_index, gt_arguments, sub_question, leak_hit, runtime_error):
    return score_hop(question_id, hop_index, gt_arguments, sub_question, empty_message(), leak_hit, runtime_error)


def evaluate_hop(question_id, hop_index, call, sub_question, leak_hit):
    arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
    try:
        return score_hop(question_id, hop_index, arguments, sub_question, run_retrieve({"sub_question": sub_question}, str(uuid4())), leak_hit, "")
    except Exception as err:
        return empty_hop(question_id, hop_index, arguments, sub_question, leak_hit, repr(err))


def score_question(question_id, question_hops, leak_hit):
    fail_reasons = []
    hops_passed = 0
    rewritten_question_count = 0
    source_fail_count = 0
    dates_fail_count = 0
    call_fail_count = 0
    answered_count = 0
    runtime_error = ""
    for hop_row in question_hops:
        hops_passed += hop_row["hop_success"]
        rewritten_question_count += int(not hop_row["question_copied"])
        source_fail_count += int(not hop_row["source_ok"])
        dates_fail_count += int(not hop_row["dates_ok"])
        call_fail_count += int(hop_row["call_count"] != 1 or hop_row["tool_name"] != "search_facts")
        answered_count += hop_row["answered"]
        runtime_error = runtime_error or hop_row["runtime_error"]
        if hop_row["fail_reason"] and hop_row["fail_reason"] not in fail_reasons:
            fail_reasons.append(hop_row["fail_reason"])
    return {"question_id": question_id, "hop_count": len(question_hops), "hops_passed": hops_passed, "retrieve_success": int(bool(question_hops) and hops_passed == len(question_hops) and not leak_hit), "prompt_leak_hit": leak_hit, "rewritten_question_count": rewritten_question_count, "source_fail_count": source_fail_count, "dates_fail_count": dates_fail_count, "call_fail_count": call_fail_count, "answered_count": answered_count, "fail_reasons": " | ".join(fail_reasons), "runtime_error": runtime_error}


def evaluate_all_questions(project_root, questions, leak_hit):
    rows = []
    hop_rows = []
    for question_data in questions:
        ground_truth = load_ground_truth(project_root, question_data)
        question_hops = []
        for hop_index, call in enumerate(retrieve_gt_calls(ground_truth), start=1):
            if hop_rows:
                sleep(LIVE_RETRIEVE_PAUSE_SECONDS)
            hop_row = evaluate_hop(question_data["id"], hop_index, call, hop_sub_question(ground_truth, call), leak_hit)
            question_hops.append(hop_row)
            hop_rows.append(hop_row)
        rows.append(score_question(question_data["id"], question_hops, leak_hit))
    return rows, hop_rows


def hop_csv_rows(hop_rows):
    csv_rows = []
    for hop_row in hop_rows:
        row = {}
        for key in HOP_FIELDNAMES:
            row[key] = hop_row[key]
        csv_rows.append(row)
    return csv_rows


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(output_directory, timestamp, rows, hop_rows):
    stamp = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    write_csv(output_directory / f"metrics_{stamp}.csv", METRIC_FIELDNAMES, rows)
    write_csv(output_directory / f"hops_{stamp}.csv", HOP_FIELDNAMES, hop_csv_rows(hop_rows))


def main():
    project_root = Path(__file__).resolve().parents[2]
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    leak_hit = prompt_leak_hit((project_root / "src" / "prompts" / "retrieve_agent.md").read_text(encoding="utf-8"), collect_exam_needles(project_root, questions))
    rows, hop_rows = evaluate_all_questions(project_root, questions, leak_hit)
    write_outputs(Path(__file__).resolve().parent / "outputs", datetime.now().astimezone(), rows, hop_rows)


if __name__ == "__main__":
    main()
