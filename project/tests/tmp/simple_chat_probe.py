import json
import os
from pathlib import Path
from time import perf_counter

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

base_url = (os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
api_key = os.getenv("OPENAI_API_KEY") or ""
chat_model = os.getenv("OPENAI_ANSWER_AGENT_MODEL")
started = perf_counter()
report = {"chat_model": chat_model, "http_status": None, "elapsed_seconds": None, "response_body": None, "error": ""}
try:
    response = httpx.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json={"model": chat_model, "messages": [{"role": "user", "content": "Reply with the single word ok."}], "max_tokens": 8}, timeout=45.0)
    report["http_status"] = response.status_code
    report["elapsed_seconds"] = round(perf_counter() - started, 2)
    body = response.json()
    if isinstance(body, dict) and body.get("choices"):
        report["response_body"] = {"id": body.get("id"), "model": body.get("model"), "content": (((body.get("choices") or [{}])[0].get("message") or {}).get("content"))}
    else:
        report["response_body"] = body
except Exception as err:
    report["elapsed_seconds"] = round(perf_counter() - started, 2)
    report["error"] = repr(err)
Path(__file__).resolve().parent.joinpath("simple_chat_probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
