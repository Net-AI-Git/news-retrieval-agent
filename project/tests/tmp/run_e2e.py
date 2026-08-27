import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from solution import answer, build_index

DATA_DIR = Path(__file__).resolve().parents[2] / "src" / "data"
QUESTIONS = json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))
question_data = next(item for item in QUESTIONS if item["id"] == "Q01")
index = build_index(str(DATA_DIR))
print(json.dumps({"handle_type": type(index).__name__, "handle": index}, ensure_ascii=False))
result = answer(index, question_data["id"], question_data["question"])
citation_keys = []
for citation in result.get("citations") or []:
    citation_keys.append(sorted(citation.keys()))
print(json.dumps({"question_id": question_data["id"], "result_keys": sorted(result.keys()), "citation_keys": citation_keys, "result": result}, ensure_ascii=False))
