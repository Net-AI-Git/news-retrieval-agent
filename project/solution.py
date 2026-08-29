import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent / "project"
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.grounded_answering_workflow import run_grounded_answering
from src.schemas.agent import SolutionAnswer
from src.services.solution_index_service import run_solution_index


def build_index(data_dir: str) -> object:
    return run_solution_index({"data_dir": data_dir}, str(uuid4()))


def answer(index: object, question_id: str, question: str) -> dict:
    return SolutionAnswer.model_validate(run_grounded_answering({**index, "question_id": question_id, "question": question}, str(uuid4()))).model_dump()
