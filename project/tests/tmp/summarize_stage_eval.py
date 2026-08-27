import json
from pathlib import Path

rows = json.loads(Path(r"c:\Users\User\Desktop\candidate_bundle\project\tests\end_to_end_gt_evaluation\outputs\traces_2026-08-26_19-54-27.json").read_text(encoding="utf-8"))
print("questions", len(rows))
for row in rows:
    tools = row.get("tool_calls") or {}
    gather = row.get("gather_missing") or {}
    stop = gather.get("stop") or {}
    hops = gather.get("hops") or []
    hop_bits = []
    for hop in hops:
        hop_bits.append("a=%s g=%s" % (hop.get("attempted"), hop.get("gold_hit_count")))
    answer = (row.get("answer_vs_gt") or {})
    print("%s e2e=%s stage=%s err=%s stop=%s pattern=%s gather=%s tools=%s batches=%s missing_hop=%s gold=%s last_tools=%s hops=[%s] pred=%s gt=%s" % (row["question_id"], row.get("e2e_success"), row.get("failure_stage"), row.get("answer_error_type"), stop.get("verdict"), tools.get("pattern"), tools.get("gather_count"), tools.get("tool_count"), tools.get("parallel_batch_sizes"), gather.get("stopped_with_missing_hop"), stop.get("gold_complete"), stop.get("last_gather_called_tools"), "; ".join(hop_bits), answer.get("predicted_answer"), answer.get("gt_answer")))
