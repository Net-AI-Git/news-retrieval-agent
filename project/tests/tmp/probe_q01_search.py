import json
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.conts import CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH
from src.services.retrieval_service import run_retrieval

result = run_retrieval({"question": "What did the Sporting News report about a victory for the Dallas Cowboys over the Seattle Seahawks in Week 13 of the NFL season?", "source": "Sporting News", "published_from": None, "published_to": None, "evidence_store": "facts", "facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}, str(uuid4()))
Path(__file__).resolve().parent.joinpath("probe_q01.json").write_text(json.dumps({"status": result.get("status"), "facts": [{"title": item.get("article_title"), "url": item.get("url"), "match": item.get("match_percentage")} for item in (result.get("facts") or [])]}, ensure_ascii=False, indent=2), encoding="utf-8")
