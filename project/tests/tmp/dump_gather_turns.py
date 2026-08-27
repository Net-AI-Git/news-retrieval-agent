import json
from pathlib import Path

rows = json.loads(Path(r"c:\Users\User\Desktop\candidate_bundle\project\tests\end_to_end_gt_evaluation\outputs\traces_2026-08-26_19-54-27.json").read_text(encoding="utf-8"))
for question_id in ["Q02", "Q03", "Q04", "Q05", "Q07", "Q08", "Q09"]:
    row = next(item for item in rows if item["question_id"] == question_id)
    stop = (row.get("gather_missing") or {}).get("stop") or {}
    tools = row.get("tool_calls") or {}
    print("====", question_id, "verdict", stop.get("verdict"), "pattern", tools.get("pattern"))
    print("progress", stop.get("progress"))
    print("turns")
    for turn in tools.get("turns") or []:
        print(" ", turn.get("stage"), "gather", turn.get("gather_count"), "route", turn.get("next_route"), "tool_count", turn.get("tool_count"), "ncalls", len(turn.get("tool_calls") or []), "hits", turn.get("hit_count"), "urls", turn.get("urls"))
    print("calls")
    for call in tools.get("calls") or []:
        print(" ", call.get("tool"), "gold", call.get("gold_hit_count"), "empty", call.get("empty"), "q", (call.get("question") or "")[:90])
    print("wasted", row.get("wasted_tool_calls"))
    print()
