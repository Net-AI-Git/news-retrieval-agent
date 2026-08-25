import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent / "project"
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from src.conts import CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH
from src.services.corpus_chroma_index_service import run_corpus_chroma_index
from src.services.facts_chroma_index_service import run_facts_chroma_index


def build_index(data_dir: str) -> object:
    data_path = Path(data_dir).resolve()
    if not data_path.is_dir():
        raise ValueError(f"Data directory does not exist: {data_path}")
    if not (data_path / "corpus.json").is_file() or not (data_path / "facts.json").is_file():
        raise ValueError(f"Data directory must contain corpus.json and facts.json: {data_path}")
    flow_id = str(uuid4())
    return {"corpus_chroma_path": run_corpus_chroma_index({"data_dir": str(data_path), "chroma_path": CORPUS_CHROMA_PATH}, flow_id), "facts_chroma_path": run_facts_chroma_index({"data_dir": str(data_path), "chroma_path": FACTS_CHROMA_PATH}, flow_id)}
