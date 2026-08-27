from pathlib import Path
from time import perf_counter
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.conts import CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH
from src.tools.retrieval_tools import RetrievalTools

started = perf_counter()
tools = RetrievalTools({"facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}, str(uuid4())).as_langchain_tools()
search_facts = next(tool for tool in tools if tool.name == "search_facts")
payload = search_facts.invoke({"question": "Did Sporting News report that the Dallas Cowboys defeated the Seattle Seahawks in Week 13 of the NFL season?"})
elapsed = round(perf_counter() - started, 2)
Path(__file__).resolve().parent.joinpath("one_search_facts_call.json").write_text(__import__("json").dumps({"elapsed_seconds": elapsed, "status": payload.get("status"), "result_count": len(payload.get("results") or []), "first_title": ((payload.get("results") or [{}])[0].get("article_title") if payload.get("results") else "")}, ensure_ascii=False, indent=2), encoding="utf-8")
