import json
from pathlib import Path

log_path = Path(__file__).resolve().parents[2] / "observability" / "logging_audit" / "audit_log" / "events.jsonl"
out_path = Path(__file__).with_name("e2e_fail_extract.txt")
flow_ids = {
    "2abe8674-333c-4287-bd13-d15c8c4be95e",
    "5ea633fa-e03e-453f-9a68-4dfcb5025c9d",
    "68158d16-d7cf-44d7-81ee-9f0fa18fd9fe",
    "1e43aa0b-80eb-48cb-aef2-b63bdfccdda5",
}
lines = []
for raw in log_path.read_text(encoding="utf-8").splitlines():
    record = json.loads(raw)
    event = record.get("event") or {}
    flow_id = event.get("flow_id")
    if flow_id not in flow_ids:
        continue
    status = event.get("status")
    process = event.get("process")
    content = event.get("content") or {}
    if status == "ERROR":
        lines.append(f"ERROR {flow_id[:8]} {process} err={content.get('error')}")
        task_data = content.get("task_data") or {}
        chroma_path = task_data.get("chroma_path") or task_data.get("facts_chroma_path")
        lines.append(f"  chroma={chroma_path} q={str(task_data.get('question', ''))[:140]}")
        continue
    if status != "FINISHED":
        continue
    if process == "run_retrieval":
        lines.append(f"FIN retrieval {flow_id[:8]} q={str(content.get('question', ''))[:100]} path={content.get('facts_chroma_path')}")
    elif process == "execute_grounded_answering":
        evidence = content.get("evidence")
        urls = [item.get("url") for item in evidence] if isinstance(evidence, list) else []
        lines.append(f"FIN workflow {flow_id[:8]} evidence_n={len(urls)} urls={urls} answer={content.get('answer_result')}")
    elif process == "query_records":
        lines.append(f"FIN query {flow_id[:8]} chroma={content.get('chroma_path')}")
out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {len(lines)} lines to {out_path}")
