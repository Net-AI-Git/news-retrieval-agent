import json
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

started = perf_counter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), timeout=180, max_retries=0)
error = ""
embedding_length = 0
try:
    response = client.embeddings.create(input=["Did Sporting News report that the Dallas Cowboys defeated the Seattle Seahawks in Week 13 of the NFL season?"], model=os.getenv("OPENAI_EMBEDDING_MODEL"), encoding_format="float")
    embedding_length = len(response.data[0].embedding)
except Exception as err:
    error = repr(err)
Path(__file__).resolve().parent.joinpath("one_embedding.json").write_text(json.dumps({"elapsed_seconds": round(perf_counter() - started, 2), "embedding_length": embedding_length, "error": error, "model": os.getenv("OPENAI_EMBEDDING_MODEL")}, ensure_ascii=False, indent=2), encoding="utf-8")
