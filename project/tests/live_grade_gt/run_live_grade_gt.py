import csv
import json
from datetime import datetime
from pathlib import Path
from time import sleep
from uuid import uuid4

from dotenv import load_dotenv
from langgraph.errors import GraphInterrupt

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.agents.grade_agent import run_grade
from src.conts import GRADE_CONTINUE_VERDICTS


METRIC_FIELDNAMES = ["case_id", "expected_route", "predicted_verdict", "predicted_route", "route_match", "note_repeats_prior", "prompt_leak_hit", "case_success", "note", "runtime_error"]
LIVE_GRADE_PAUSE_SECONDS = 8
LEAK_SKIP_ANSWERS = {"yes", "no", "insufficient information"}
LEAK_MIN_CHARS = 24


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
        ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
        for needle in exam_needles_from_ground_truth(question_data, ground_truth):
            add_exam_needle(needles, needle)
    return needles


def prompt_leak_hit(prompt_text, needles):
    for needle in needles:
        if needle in prompt_text:
            return 1
    return 0


def normalize_text(text):
    return " ".join((text or "").lower().split())


def predicted_route(verdict):
    if (verdict or "").strip().lower() in GRADE_CONTINUE_VERDICTS:
        return "continue"
    return "stop"


def note_repeats_prior(note, prior_queries):
    haystack = normalize_text(note)
    if not haystack:
        return 0
    for record in prior_queries or []:
        needle = normalize_text(record.get("question") or "")
        if needle and needle == haystack:
            return 1
    return 0


def empty_score(case_data, leak_hit, runtime_error):
    return {"case_id": case_data.get("case_id") or "", "expected_route": case_data.get("expected_route") or "", "predicted_verdict": "", "predicted_route": "", "route_match": 0, "note_repeats_prior": 0, "prompt_leak_hit": leak_hit, "case_success": 0, "note": "", "runtime_error": runtime_error}


def score_case(case_data, grade_result, leak_hit):
    verdict = (grade_result.verdict or "").strip().lower()
    route = predicted_route(verdict)
    repeats = note_repeats_prior(grade_result.note, case_data.get("prior_queries") or [])
    route_match = int(route == case_data.get("expected_route"))
    return {"case_id": case_data.get("case_id") or "", "expected_route": case_data.get("expected_route") or "", "predicted_verdict": verdict, "predicted_route": route, "route_match": route_match, "note_repeats_prior": repeats, "prompt_leak_hit": leak_hit, "case_success": int(route_match and not leak_hit and not (case_data.get("expected_route") == "continue" and repeats)), "note": grade_result.note or "", "runtime_error": ""}


def evaluate_case(case_data, leak_hit):
    try:
        grade_result = run_grade({"question": case_data["question"], "evidence": case_data.get("evidence") or [], "prior_queries": case_data.get("prior_queries") or []}, str(uuid4()))
        return score_case(case_data, grade_result, leak_hit)
    except Exception as err:
        if isinstance(err, GraphInterrupt):
            raise
        return empty_score(case_data, leak_hit, repr(err))


def evaluate_all_cases(cases, leak_hit):
    rows = []
    for case_data in cases:
        if rows:
            sleep(LIVE_GRADE_PAUSE_SECONDS)
        rows.append(evaluate_case(case_data, leak_hit))
    return rows


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(output_directory, timestamp, rows):
    write_csv(output_directory / f"metrics_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv", METRIC_FIELDNAMES, rows)


def main():
    project_root = Path(__file__).resolve().parents[2]
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    leak_hit = prompt_leak_hit((project_root / "src" / "prompts" / "grade_agent.md").read_text(encoding="utf-8"), collect_exam_needles(project_root, questions))
    write_outputs(Path(__file__).resolve().parent / "outputs", datetime.now().astimezone(), evaluate_all_cases(json.loads((project_root / "src" / "data" / "ground_truth" / "grade_invented_midloop_stop_continue.json").read_text(encoding="utf-8")), leak_hit))


if __name__ == "__main__":
    main()
