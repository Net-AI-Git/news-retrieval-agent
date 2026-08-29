# Local logs and telemetry dashboard

Generate a standalone dashboard from `observability/logging_audit/audit_log/events.jsonl` and `observability/telemetry/spans-*.jsonl`:

```powershell
uv run python -m observability.logging_dashboard.build_dashboard
```

Production also rebuilds this file after each completed `run_grounded_answering` question. Open `observability/logging_dashboard/dashboard.html` or the copy at `output_for_mission/dashboard.html`. Log and span panels show the last 20 minutes. The GT tab uses the latest exam CSV, not that window. Plotly is embedded in the file, so no server or internet connection is needed after `uv sync`.

Every tab states what it is for. Every chart has a caption and axis units.

## Tabs

- **Overview** — traffic lights only: log errors, span errors, latest GT task success, question count, workflow latency (ms), estimated USD for all questions, plus log volume over time. Green is healthy. Red means open Errors or GT.
- **Errors** — failures only: log status vs ERROR by process, FINISHED vs ERROR by process, recent ERROR logs, error spans.
- **Agents** — per-agent average and max latency (ms), OK vs error span counts, agent totals, recent tool calls. No money on this tab.
- **Questions** — one row per `flow_id`, routing events, then up to eight waterfalls. Waterfall x-axis is elapsed milliseconds. Cost for a question is on Cost.
- **Cost** — estimated USD only. Left chart: each bar is one agent, value = sum of every question in the window. Right chart: each bar is one question. Tables split the same way (agent+model vs flow+model).
- **GT comparison** — latest `tests/live_e2e_gt/outputs/metrics_*.csv` plus `src/data/ground_truth/Q*.json`. 100% is a pass. This is evaluation output, not the 20-minute operations window.

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
