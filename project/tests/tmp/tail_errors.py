from pathlib import Path

log_path = Path(__file__).resolve().parents[2] / "local_logging_audit" / "audit_log" / "events.jsonl"
snippets = []
for line in log_path.read_text(encoding="utf-8").splitlines()[-2000:]:
    if '"status": "ERROR"' not in line or "2026-08-27T16:28" not in line:
        continue
    start = line.find('"error":')
    snippets.append(line[start:start + 350])
Path(__file__).resolve().parent.joinpath("tail_errors.txt").write_text("\n---\n".join(snippets) or "none\n", encoding="utf-8")
