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
    return {"id": question_id, "question": question, "flow_id": flow_id, "turns": task_data.get("transcript_turns") or [], "evidence": task_data.get("evidence") or [], "answer_result": task_data.get("answer_result"), "public": public}


def answer(index, question_id, question):
    return recorded_answer(index, question_id, question)["public"]


def write_assignment_file(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_assignment_artifacts():
    print("build_index", DATA_DIR, flush=True)
    index = build_index(DATA_DIR)
    print("index", index, flush=True)
    transcripts = []
    answers = []
    for question_data in json.loads((Path(DATA_DIR) / "questions.json").read_text(encoding="utf-8")):
        record = recorded_answer(index, question_data["id"], question_data["question"])
        print(record["id"], record["public"]["answer"], flush=True)
        transcripts.append(record)
        answers.append({"id": record["id"], "answer": record["public"]["answer"], "citations": record["public"]["citations"]})
    write_assignment_file(ANSWERS_PATH, answers)
    write_assignment_file(TRANSCRIPTS_PATH, transcripts)


if __name__ == "__main__":
    write_assignment_artifacts()
