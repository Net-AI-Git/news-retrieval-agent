import json
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.conts import CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH
from src.tools.retrieval_tools import RetrievalTools

query = "What information did The Age report about the founding of OpenAI, including any financial figure stated in the article?"
gold_url = "https://www.theage.com.au/business/entrepreneurship/how-ego-and-fear-fuelled-the-rise-of-artificial-intelligence-20231205-p5ep7j.html?ref=rss&utm_medium=rss&utm_source=rss_business"
tools = RetrievalTools({"facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}, str(uuid4())).as_langchain_tools()
payload = next(tool for tool in tools if tool.name == "search_facts").invoke({"question": query})
titles = [item.get("article_title") for item in payload.get("results") or []]
urls = [item.get("url") for item in payload.get("results") or []]
Path(__file__).resolve().parent.joinpath("q10_hop2_retry.json").write_text(json.dumps({"status": payload.get("status"), "result_count": len(payload.get("results") or []), "url_hit": int(gold_url in urls), "titles": titles}, ensure_ascii=False, indent=2), encoding="utf-8")
