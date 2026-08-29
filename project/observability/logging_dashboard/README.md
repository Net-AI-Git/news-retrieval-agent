# Local logs and telemetry dashboard

Generate a standalone dashboard from `observability/logging_audit/audit_log/events.jsonl` and `observability/telemetry/spans-*.jsonl`:

```powershell
uv run python -m observability.logging_dashboard.build_dashboard
```

Production also rebuilds this file after each completed `run_grounded_answering` question. Open `observability/logging_dashboard/dashboard.html`. Panels show the last 20 minutes of logs and spans. Plotly is embedded in the file, so no server or internet connection is needed after `uv sync`.

## Tabs

- **Overview** — KPI tiles (green when healthy, red when errors exist), billed tokens, estimated USD, and per-agent success/failure with average latency.
- **Logging** — six-field log contract only: status, errors by process, timeline, recent errors, process FINISHED vs ERROR, recent events.
- **Telemetry** — agent latency, estimated cost by agent and by question, span names, tool calls, error spans, and one trace waterfall.
- **Question flows** — joined `flow_id` / `trace_id` index, routing events, then up to eight full question waterfalls with that flow's lifecycle logs. When a flow was scored in the latest GT CSV, the index also shows GT id, task %, fail agent, GT answer, and predicted answer.
- **GT comparison** — latest `tests/live_e2e_gt/outputs/metrics_*.csv` plus `src/data/ground_truth/Q*.json`. Task/agent success rates, per-question pass/fail, the full scorecard, and GT vs predicted answers. This is evaluation output, not telemetry.

## Cost

`gen_ai.usage.*` is used when the value is numeric. Redacted usage falls back to characters / 4. USD is estimated, not billed:

| Model needle | Input $/1M | Output $/1M |
| --- | --- | --- |
| gpt-4.1-mini | 0.40 | 1.60 |
| gpt-4.1 | 2.00 | 8.00 |
| gpt-4o-mini | 0.15 | 0.60 |
| gpt-4o | 2.50 | 10.00 |
| embed / nemotron | 0 | 0 |
| unmatched | 1.00 | 3.00 |
