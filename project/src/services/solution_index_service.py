import os
from pathlib import Path

from ..conts import FACTS_CHROMA_PATH, REQUIRED_SOLUTION_ENV_VARS
from ..repositories.logging_repository import LoggingRepository
from .facts_chroma_index_service import run_facts_chroma_index


def raise_if_missing_solution_env(task_data):
    for env_name in REQUIRED_SOLUTION_ENV_VARS:
        if not (os.getenv(env_name) or "").strip():
            task_data["missing_env_name"] = env_name
            raise ValueError(f"{env_name} is missing")


def resolved_solution_data_dir(task_data):
    data_path = Path(task_data["data_dir"]).resolve()
    if not data_path.is_dir():
        task_data["failure_message"] = f"Data directory does not exist: {data_path}"
        raise ValueError(task_data["failure_message"])
    if not (data_path / "corpus.json").is_file() or not (data_path / "facts.json").is_file():
        task_data["failure_message"] = f"Data directory must contain corpus.json and facts.json: {data_path}"
        raise ValueError(task_data["failure_message"])
    return data_path


def facts_chroma_index_handle(task_data, flow_id, data_path):
    facts_chroma_path = run_facts_chroma_index({"data_dir": str(data_path), "chroma_path": FACTS_CHROMA_PATH}, flow_id)
    if not facts_chroma_path:
        return None
    return {"facts_chroma_path": facts_chroma_path}


def run_solution_index(task_data, flow_id):
    LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    index = None
    try:
        raise_if_missing_solution_env(task_data)
        index = facts_chroma_index_handle(task_data, flow_id, resolved_solution_data_dir(task_data))
    except Exception as err:
        LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return index
