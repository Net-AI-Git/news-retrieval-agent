import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from solution import answer, build_index
from src.conts import FACTS_CHROMA_PATH

DATA_DIR = Path(__file__).resolve().parents[2] / "src" / "data"
QUESTIONS = json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))
WORKER_COUNT = 4


def loaded_index():
    if Path(FACTS_CHROMA_PATH).is_dir():
        return {"facts_chroma_path": FACTS_CHROMA_PATH}
    return build_index(str(DATA_DIR))


def answer_one(index, question_data):
    result = answer(index, question_data["id"], question_data["question"])
    return {"question_id": question_data["id"], "result": result}


def main():
    index = loaded_index()
    results = []
    failures = []
    with ThreadPoolExecutor(max_workers=WORKER_COUNT) as pool:
        futures = {}
        for question_data in QUESTIONS:
            futures[pool.submit(answer_one, index, question_data)] = question_data["id"]
        for future in as_completed(futures):
            question_id = futures[future]
            try:
                answered = future.result()
                results.append(answered)
                print(json.dumps(answered, ensure_ascii=False), flush=True)
            except Exception as err:
                failures.append({"question_id": question_id, "error": repr(err)})
                print(json.dumps(failures[-1], ensure_ascii=False), flush=True)
    results.sort(key=lambda item: item["question_id"])
    output_path = Path(__file__).resolve().parent / "parallel_questions_last.json"
    output_path.write_text(json.dumps({"completed": len(results), "failed": len(failures), "failures": failures, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"completed": len(results), "failed": len(failures), "failures": failures, "output_path": str(output_path)}, ensure_ascii=False), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
