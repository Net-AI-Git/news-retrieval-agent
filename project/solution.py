import json
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from src.conts import ANSWERS_PATH, DATA_DIR, TRANSCRIPTS_PATH
from src.orchestration.grounded_answering_workflow import run_grounded_answering
from src.schemas.agent import SolutionAnswer
from src.services.solution_index_service import run_solution_index


def build_index(data_dir):
    return run_solution_index({"data_dir": data_dir}, str(uuid4()))


def recorded_answer(index, question_id, question):
    flow_id = str(uuid4())
    task_data = {**index, "question_id": question_id, "question": question}
    public = SolutionAnswer.model_validate(run_grounded_answering(task_data, flow_id)).model_dump()
    record = {"id": question_id, "question": question, "flow_id": flow_id, "turns": task_data.get("transcript_turns") or [], "evidence": task_data.get("evidence") or [], "answer_result": task_data.get("answer_result"), "public": public}
    write_assignment_file(ANSWERS_PATH, upsert_by_id(load_json_array(ANSWERS_PATH), {"id": record["id"], "answer": record["public"]["answer"], "citations": record["public"]["citations"]}))
    write_assignment_file(TRANSCRIPTS_PATH, upsert_by_id(load_json_array(TRANSCRIPTS_PATH), record))
    return record


def answer(index, question_id, question):
    return recorded_answer(index, question_id, question)["public"]


def load_json_array(path):
    file_path = Path(path)
    if not file_path.is_file():
        return []
    payload = json.loads(file_path.read_text(encoding="utf-8") or "[]")
    if isinstance(payload, list):
        return payload
    return []


def upsert_by_id(rows, row):
    updated = []
    found = False
    for entry in rows:
        if entry.get("id") == row["id"]:
            updated.append(row)
            found = True
            continue
        updated.append(entry)
    if not found:
        updated.append(row)
    question_order = [question_data["id"] for question_data in json.loads((Path(DATA_DIR) / "questions.json").read_text(encoding="utf-8"))]
    return sorted(updated, key=lambda entry: question_order.index(entry["id"]) if entry.get("id") in question_order else len(question_order))


def write_assignment_file(path, payload):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_assignment_artifacts():
    index = build_index(DATA_DIR)
    for question_data in json.loads((Path(DATA_DIR) / "questions.json").read_text(encoding="utf-8")):
        recorded_answer(index, question_data["id"], question_data["question"])


if __name__ == "__main__":
    write_assignment_artifacts()
