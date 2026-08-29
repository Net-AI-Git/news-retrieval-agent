import csv
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..logging_audit.logging_audit_client import open_logs
from ..telemetry_audit.telemetry_audit_client import open_spans


DASHBOARD_PATH = Path(__file__).parent / "dashboard.html"
DASHBOARD_LOOKBACK_MINUTES = 20
DASHBOARD_LOCK = threading.Lock()
GT_METRICS_DIRECTORY = Path(__file__).resolve().parents[2] / "tests" / "live_e2e_gt" / "outputs"
GT_DIRECTORY = Path(__file__).resolve().parents[2] / "src" / "data" / "ground_truth"
GT_METRIC_FIELDS = ("question_id", "http_status", "flow_id", "trace_id", "task_success", "failure_agent", "gather_success", "retrieve_success", "retrieval_success", "grade_success", "answer_success", "citation_success", "orchestration_success", "gold_url_recall_pct", "gold_snippet_recall_pct", "citation_title_recall_pct", "hop_coverage_pct", "source_fill_pct", "date_fill_pct", "wasted_call_pct", "stop_verdict", "answer_error_type", "gather_turns", "tool_count", "span_count", "duration_ms", "gt_answer", "predicted_answer", "missing_urls", "runtime_error")
CHARS_PER_TOKEN = 4
MODEL_USD_PER_MILLION = (("gpt-4.1-mini", 0.4, 1.6), ("gpt-4.1", 2.0, 8.0), ("gpt-4o-mini", 0.15, 0.6), ("gpt-4o", 2.5, 10.0), ("embed", 0.0, 0.0), ("nemotron", 0.0, 0.0))
STATUS_COLORS = {"FINISHED": "#22c55e", "ERROR": "#ef4444", "STARTING": "#38bdf8"}
BILLED_INPUT_SQL = f"COALESCE(input_tokens, input_chars * 1.0 / {CHARS_PER_TOKEN})"
BILLED_OUTPUT_SQL = f"COALESCE(output_tokens, output_chars * 1.0 / {CHARS_PER_TOKEN})"
DASHBOARD_STYLE = "html,body{margin:0;width:100%;background:#0b1220;color:#e5e7eb;font-family:Segoe UI,sans-serif}h2{margin:8px 0 12px;font-size:20px;color:#86efac}.nav{display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:14px;padding:18px 24px;background:#111827;position:sticky;top:0;z-index:5;border-bottom:1px solid #1f2937}.tab{background:#1f2937;color:#e5e7eb;border:0;padding:14px 28px;border-radius:10px;cursor:pointer;font-weight:700;font-size:18px;min-width:180px}.tab.active{background:#22c55e;color:#052e16}.panel{display:none;width:100%;box-sizing:border-box;padding:12px 16px 32px}.panel.active{display:block}.note{color:#94a3b8;padding:0 18px 8px;font-size:13px;line-height:1.45;text-align:center}.js-plotly-plot,.plotly-graph-div{width:100%!important}"
DASHBOARD_SCRIPT = "function resizePlots(root){root.querySelectorAll('.js-plotly-plot').forEach(function(plot){Plotly.Plots.resize(plot)})}function showTab(id){document.querySelectorAll('.panel').forEach(function(panel){panel.classList.remove('active')});document.querySelectorAll('.tab').forEach(function(tab){tab.classList.remove('active')});document.getElementById(id).classList.add('active');document.getElementById('btn-'+id).classList.add('active');resizePlots(document.getElementById(id))}window.addEventListener('resize',function(){document.querySelectorAll('.panel.active').forEach(function(panel){resizePlots(panel)})})"


def dashboard_cutoffs(lookback_minutes):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    return cutoff.isoformat(), int(cutoff.timestamp() * 1000000000)


def status_color(has_problem):
    return "#ef4444" if has_problem else "#22c55e"


def model_rates(model):
    model_name = (model or "").lower()
    for needle, input_rate, output_rate in MODEL_USD_PER_MILLION:
        if needle in model_name:
            return input_rate, output_rate
    return (1.0, 3.0)


def estimated_usd(model, input_billed, output_billed):
    input_rate, output_rate = model_rates(model)
    return (input_billed or 0) * input_rate / 1000000 + (output_billed or 0) * output_rate / 1000000


def costed_rows(rows):
    costed = []
    for row in rows:
        costed.append((row[0], row[1], row[2], row[3], round(estimated_usd(row[1], row[2], row[3]), 6)))
    return costed


def totaled_by_first_column(costed):
    totals = {}
    ordered_keys = []
    for row in costed:
        if row[0] not in totals:
            ordered_keys.append(row[0])
            totals[row[0]] = 0
        totals[row[0]] += row[4]
    return [(key, round(totals[key], 6)) for key in ordered_keys]


def total_estimated_usd(cost_rows):
    total = 0.0
    for row in cost_rows:
        total += row[4]
    return round(total, 6)


def total_billed_tokens(cost_rows):
    total = 0.0
    for row in cost_rows:
        total += (row[2] or 0) + (row[3] or 0)
    return round(total, 1)


def colored_indicator(value, title, has_problem, valueformat=None):
    return go.Indicator(mode="number", value=value, title={"text": title}, number={"font": {"color": status_color(has_problem), "size": 42}, "valueformat": valueformat or ",.0f"})


def dark_layout(figure, title, height, showlegend=False):
    figure.update_layout(title=title, height=height, showlegend=showlegend, template="plotly_dark", paper_bgcolor="#111827", plot_bgcolor="#0b1220", autosize=True)
    return figure


def metric_number(value):
    if value in (None, ""):
        return 0.0
    return float(value)


def gt_column(rows, field_name):
    return [row[field_name] for row in rows]


def latest_gt_metrics_path(metrics_directory=None):
    metrics_directory = Path(metrics_directory or GT_METRICS_DIRECTORY)
    if not metrics_directory.exists():
        return None
    metric_files = sorted(metrics_directory.glob("metrics_*.csv"))
    if not metric_files:
        return None
    return metric_files[-1]


def load_gt_question_text(ground_truth_directory=None):
    ground_truth_directory = Path(ground_truth_directory or GT_DIRECTORY)
    questions = {}
    if not ground_truth_directory.exists():
        return questions
    for path in sorted(ground_truth_directory.glob("Q*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        citation_titles = []
        for item in payload.get("citations") or []:
            citation_titles.append(item.get("article_title") or "")
        questions[payload["id"]] = (payload.get("question") or "", payload.get("answer") or "", ", ".join(payload.get("intents") or []), " | ".join(citation_titles))
    return questions


def parse_gt_metric_row(row, questions):
    question_text, gt_answer, intents, citation_titles = questions.get(row.get("question_id") or "", ("", "", "", ""))
    return {"question_id": row.get("question_id") or "", "question": question_text, "http_status": row.get("http_status") or "", "task_success": metric_number(row.get("task_success")), "failure_agent": row.get("failure_agent") or "", "gather_success": metric_number(row.get("gather_success")), "retrieve_success": metric_number(row.get("retrieve_success")), "retrieval_success": metric_number(row.get("retrieval_success")), "grade_success": metric_number(row.get("grade_success")), "answer_success": metric_number(row.get("answer_success")), "citation_success": metric_number(row.get("citation_success")), "orchestration_success": metric_number(row.get("orchestration_success")), "gold_url_recall_pct": metric_number(row.get("gold_url_recall_pct")), "gold_snippet_recall_pct": metric_number(row.get("gold_snippet_recall_pct")), "citation_title_recall_pct": metric_number(row.get("citation_title_recall_pct")), "hop_coverage_pct": metric_number(row.get("hop_coverage_pct")), "source_fill_pct": metric_number(row.get("source_fill_pct")), "date_fill_pct": metric_number(row.get("date_fill_pct")), "wasted_call_pct": metric_number(row.get("wasted_call_pct")), "stop_verdict": row.get("stop_verdict") or "", "answer_error_type": row.get("answer_error_type") or "", "gt_answer": row.get("gt_answer") or gt_answer, "predicted_answer": row.get("predicted_answer") or "", "missing_urls": row.get("missing_urls") or "", "flow_id": row.get("flow_id") or "", "intents": intents, "citation_titles": citation_titles, "gather_turns": row.get("gather_turns") or "", "tool_count": row.get("tool_count") or "", "duration_ms": row.get("duration_ms") or "", "runtime_error": row.get("runtime_error") or ""}


def gt_agent_rate_rows(total):
    return [("task", metric_number(total.get("task_success"))), ("gather", metric_number(total.get("gather_success"))), ("retrieve", metric_number(total.get("retrieve_success"))), ("retrieval", metric_number(total.get("retrieval_success"))), ("grade", metric_number(total.get("grade_success"))), ("answer", metric_number(total.get("answer_success"))), ("citation", metric_number(total.get("citation_success"))), ("orchestration", metric_number(total.get("orchestration_success")))]


def gt_failure_counts(rows):
    counts = {}
    ordered_names = []
    for row in rows:
        agent_name = row["failure_agent"] or "none"
        if agent_name not in counts:
            ordered_names.append(agent_name)
            counts[agent_name] = 0
        counts[agent_name] += 1
    return [(agent_name, counts[agent_name]) for agent_name in ordered_names]


def load_gt_metrics(metrics_directory=None, ground_truth_directory=None):
    metrics_path = latest_gt_metrics_path(metrics_directory)
    if not metrics_path:
        return {"gt_metrics_name": "", "gt_total": {}, "gt_rows": [], "gt_agent_rates": [], "gt_failures": []}
    questions = load_gt_question_text(ground_truth_directory)
    rows = []
    total = {}
    with metrics_path.open(encoding="utf-8-sig", newline="") as metrics_file:
        reader = csv.DictReader(metrics_file)
        missing_fields = []
        for field_name in GT_METRIC_FIELDS:
            if field_name not in (reader.fieldnames or []):
                missing_fields.append(field_name)
        if missing_fields:
            raise ValueError(f"GT metrics CSV missing fields: {missing_fields}")
        for row in reader:
            if row.get("question_id") == "TOTAL":
                total = row
                continue
            rows.append(parse_gt_metric_row(row, questions))
    return {"gt_metrics_name": metrics_path.name, "gt_total": total, "gt_rows": rows, "gt_agent_rates": gt_agent_rate_rows(total), "gt_failures": gt_failure_counts(rows)}


def correlated_flows_with_gt(correlated_flows, gt_rows):
    by_flow = {}
    for row in gt_rows:
        if row["flow_id"]:
            by_flow[row["flow_id"]] = row
    enriched = []
    for row in correlated_flows:
        gt_row = by_flow.get(row[0], {})
        enriched.append(row + (gt_row.get("question_id") or "", gt_row.get("task_success") if gt_row else "", gt_row.get("failure_agent") or "", gt_row.get("gt_answer") or "", gt_row.get("predicted_answer") or ""))
    return enriched


def load_log_panels(connection, cutoff_time):
    totals = connection.execute("SELECT count(*) AS total, COALESCE(sum(CASE WHEN level = 'ERROR' THEN 1 ELSE 0 END), 0) AS errors FROM logs WHERE time >= ?", (cutoff_time,)).fetchone()
    return {"log_total": totals[0], "log_errors": totals[1], "statuses": connection.execute("SELECT status, count(*) AS events FROM logs WHERE time >= ? GROUP BY status ORDER BY events DESC", (cutoff_time,)).fetchall(), "error_processes": connection.execute("SELECT process, count(*) AS errors FROM logs WHERE level = 'ERROR' AND time >= ? GROUP BY process ORDER BY errors DESC LIMIT 10", (cutoff_time,)).fetchall(), "timeline": connection.execute("SELECT substr(time, 1, 16) AS minute, count(*) AS events FROM logs WHERE time >= ? GROUP BY minute ORDER BY minute", (cutoff_time,)).fetchall(), "recent_errors": connection.execute("SELECT time, process, flow_id, trace_id, content FROM logs WHERE level = 'ERROR' AND time >= ? ORDER BY time DESC LIMIT 20", (cutoff_time,)).fetchall()}


def load_log_health(connection, cutoff_time):
    return {"log_health": connection.execute("SELECT process, COALESCE(sum(CASE WHEN status = 'FINISHED' THEN 1 ELSE 0 END), 0) AS finished, COALESCE(sum(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END), 0) AS errors, count(*) AS events FROM logs WHERE time >= ? GROUP BY process ORDER BY errors DESC, events DESC LIMIT 20", (cutoff_time,)).fetchall(), "recent_events": connection.execute("SELECT time, status, process, flow_id, level FROM logs WHERE time >= ? ORDER BY time DESC LIMIT 25", (cutoff_time,)).fetchall()}


def load_span_panels(connection, cutoff_ns):
    totals = connection.execute("SELECT count(*) AS total, COALESCE(sum(CASE WHEN status_code = 2 THEN 1 ELSE 0 END), 0) AS errors, count(DISTINCT trace_id) AS traces, count(DISTINCT CASE WHEN coalesce(flow_id, '') != '' THEN flow_id END) AS questions FROM spans WHERE start_time_unix_nano >= ?", (cutoff_ns,)).fetchone()
    return {"span_total": totals[0], "span_errors": totals[1], "traces": totals[2], "questions": totals[3], "span_names": connection.execute("SELECT name, count(*) AS spans FROM spans WHERE start_time_unix_nano >= ? GROUP BY name ORDER BY spans DESC LIMIT 15", (cutoff_ns,)).fetchall(), "span_durations": connection.execute("SELECT name, avg(duration_ms) AS avg_ms, max(duration_ms) AS max_ms FROM spans WHERE start_time_unix_nano >= ? GROUP BY name ORDER BY avg_ms DESC LIMIT 15", (cutoff_ns,)).fetchall(), "error_spans": connection.execute("SELECT name, error_type, flow_id, trace_id, duration_ms, input_preview FROM spans WHERE status_code = 2 AND start_time_unix_nano >= ? ORDER BY duration_ms DESC LIMIT 20", (cutoff_ns,)).fetchall(), "tool_spans": connection.execute("SELECT name, tool_name, task_status, duration_ms, flow_id, trace_id FROM spans WHERE tool_name IS NOT NULL AND start_time_unix_nano >= ? ORDER BY start_time_unix_nano DESC LIMIT 20", (cutoff_ns,)).fetchall(), "span_events": connection.execute("SELECT span_events.name, span_events.details, spans.flow_id, spans.trace_id FROM span_events JOIN spans ON spans.span_id = span_events.span_id AND spans.trace_id = span_events.trace_id WHERE span_events.name IN ('routing_decision', 'budget_update', 'workflow_interrupt', 'exception') AND spans.start_time_unix_nano >= ? ORDER BY span_events.time_unix_nano DESC LIMIT 30", (cutoff_ns,)).fetchall()}


def load_agent_panels(connection, cutoff_ns):
    return {"agent_health": connection.execute("SELECT agent, count(*) AS spans, COALESCE(sum(CASE WHEN status_code = 2 THEN 1 ELSE 0 END), 0) AS errors, COALESCE(sum(CASE WHEN status_code = 2 THEN 0 ELSE 1 END), 0) AS ok, avg(duration_ms) AS avg_ms, max(duration_ms) AS max_ms FROM spans WHERE start_time_unix_nano >= ? GROUP BY agent ORDER BY avg_ms DESC", (cutoff_ns,)).fetchall()}


def load_cost_rows(connection, cutoff_ns):
    return connection.execute(f"SELECT agent, COALESCE(model, ''), COALESCE(sum({BILLED_INPUT_SQL}), 0), COALESCE(sum({BILLED_OUTPUT_SQL}), 0) FROM spans WHERE start_time_unix_nano >= ? GROUP BY agent, model ORDER BY 3 DESC", (cutoff_ns,)).fetchall()


def load_flow_cost_rows(connection, cutoff_ns):
    return connection.execute(f"SELECT COALESCE(flow_id, ''), COALESCE(model, ''), COALESCE(sum({BILLED_INPUT_SQL}), 0), COALESCE(sum({BILLED_OUTPUT_SQL}), 0) FROM spans WHERE start_time_unix_nano >= ? AND coalesce(flow_id, '') != '' GROUP BY flow_id, model ORDER BY 3 DESC LIMIT 40", (cutoff_ns,)).fetchall()


def load_waterfall(connection, cutoff_ns):
    selected = connection.execute("SELECT trace_id FROM spans WHERE status_code = 2 AND start_time_unix_nano >= ? ORDER BY duration_ms DESC LIMIT 1", (cutoff_ns,)).fetchone() or connection.execute("SELECT trace_id FROM spans WHERE start_time_unix_nano >= ? ORDER BY duration_ms DESC LIMIT 1", (cutoff_ns,)).fetchone()
    if not selected:
        return {"waterfall_trace_id": None, "waterfall": []}
    return {"waterfall_trace_id": selected[0], "waterfall": connection.execute("SELECT name, start_time_unix_nano, duration_ms, agent, status_code FROM spans WHERE trace_id = ? AND start_time_unix_nano >= ? ORDER BY start_time_unix_nano LIMIT 40", (selected[0], cutoff_ns)).fetchall()}


def load_correlated_flows(logs_connection, spans_connection, cutoff_time, cutoff_ns):
    logs_by_key = {}
    for row in logs_connection.execute("SELECT COALESCE(flow_id, ''), COALESCE(trace_id, ''), count(*) AS events, COALESCE(sum(CASE WHEN level = 'ERROR' THEN 1 ELSE 0 END), 0) AS errors FROM logs WHERE time >= ? GROUP BY flow_id, trace_id", (cutoff_time,)).fetchall():
        logs_by_key[(row[0], row[1])] = row
    correlated_flows = []
    for row in spans_connection.execute("SELECT COALESCE(flow_id, ''), COALESCE(trace_id, ''), count(*) AS spans, COALESCE(sum(CASE WHEN status_code = 2 THEN 1 ELSE 0 END), 0) AS span_errors, COALESCE(max(CASE WHEN parent_span_id IS NULL THEN duration_ms END), max(duration_ms)) AS duration_ms FROM spans WHERE start_time_unix_nano >= ? GROUP BY flow_id, trace_id ORDER BY span_errors DESC, duration_ms DESC LIMIT 20", (cutoff_ns,)).fetchall():
        log_row = logs_by_key.get((row[0], row[1]), ("", "", 0, 0))
        correlated_flows.append((row[0], row[1], log_row[2], log_row[3], row[2], row[3], row[4]))
    return correlated_flows


def load_question_flows(spans_connection, logs_connection, cutoff_ns, cutoff_time):
    question_flows = []
    for row in spans_connection.execute("SELECT COALESCE(flow_id, ''), trace_id, COALESCE(max(CASE WHEN parent_span_id IS NULL THEN duration_ms END), max(duration_ms)), COALESCE(sum(CASE WHEN status_code = 2 THEN 1 ELSE 0 END), 0), count(*), max(CASE WHEN operation_name = 'invoke_workflow' THEN input_preview END), max(start_time_unix_nano) FROM spans WHERE start_time_unix_nano >= ? AND coalesce(flow_id, '') != '' GROUP BY flow_id, trace_id ORDER BY max(start_time_unix_nano) DESC LIMIT 8", (cutoff_ns,)).fetchall():
        question_flows.append({"flow_id": row[0], "trace_id": row[1], "duration_ms": row[2], "span_errors": row[3], "spans": row[4], "preview": row[5], "waterfall": spans_connection.execute("SELECT name, start_time_unix_nano, duration_ms, agent, status_code FROM spans WHERE trace_id = ? AND start_time_unix_nano >= ? ORDER BY start_time_unix_nano LIMIT 40", (row[1], cutoff_ns)).fetchall(), "logs": logs_connection.execute("SELECT time, status, process, level FROM logs WHERE flow_id = ? AND time >= ? ORDER BY time LIMIT 20", (row[0], cutoff_time)).fetchall()})
    return question_flows


def load_dashboard_data(lookback_minutes=None, log_file_path=None, telemetry_directory_path=None, metrics_directory_path=None, ground_truth_directory_path=None):
    lookback_minutes = lookback_minutes or DASHBOARD_LOOKBACK_MINUTES
    cutoff_time, cutoff_ns = dashboard_cutoffs(lookback_minutes)
    logs_connection = open_logs(log_file_path)
    spans_connection = open_spans(telemetry_directory_path)
    try:
        dashboard_data = {"lookback_minutes": lookback_minutes}
        dashboard_data.update(load_log_panels(logs_connection, cutoff_time))
        dashboard_data.update(load_log_health(logs_connection, cutoff_time))
        dashboard_data.update(load_span_panels(spans_connection, cutoff_ns))
        dashboard_data.update(load_agent_panels(spans_connection, cutoff_ns))
        dashboard_data["cost_rows"] = costed_rows(load_cost_rows(spans_connection, cutoff_ns))
        dashboard_data["flow_cost_rows"] = costed_rows(load_flow_cost_rows(spans_connection, cutoff_ns))
        dashboard_data["agent_usd"] = totaled_by_first_column(dashboard_data["cost_rows"])
        dashboard_data["flow_usd"] = totaled_by_first_column(dashboard_data["flow_cost_rows"])
        dashboard_data.update(load_waterfall(spans_connection, cutoff_ns))
        dashboard_data.update(load_gt_metrics(metrics_directory_path, ground_truth_directory_path))
        dashboard_data["correlated_flows"] = correlated_flows_with_gt(load_correlated_flows(logs_connection, spans_connection, cutoff_time, cutoff_ns), dashboard_data["gt_rows"])
        dashboard_data["question_flows"] = load_question_flows(spans_connection, logs_connection, cutoff_ns, cutoff_time)
        return dashboard_data
    finally:
        logs_connection.close()
        spans_connection.close()


def waterfall_bars(waterfall):
    if not waterfall:
        return [], [], [], []
    minimum_start = min(row[1] for row in waterfall)
    names = [f"{row[3]} · {row[0]}" if len(row) > 3 else row[0] for row in waterfall]
    offsets = [(row[1] - minimum_start) / 1000000 for row in waterfall]
    durations = [row[2] for row in waterfall]
    colors = ["#ef4444" if len(row) > 4 and row[4] == 2 else "#22c55e" for row in waterfall]
    return names[::-1], offsets[::-1], durations[::-1], colors[::-1]


def build_overview_figure(dashboard_data):
    figure = make_subplots(rows=2, cols=4, specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}], [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]])
    figure.add_trace(colored_indicator(dashboard_data["log_total"], "Log events", False), row=1, col=1)
    figure.add_trace(colored_indicator(dashboard_data["log_errors"], "Log errors", dashboard_data["log_errors"] > 0), row=1, col=2)
    figure.add_trace(colored_indicator(dashboard_data["span_total"], "Spans", False), row=1, col=3)
    figure.add_trace(colored_indicator(dashboard_data["span_errors"], "Span errors", dashboard_data["span_errors"] > 0), row=1, col=4)
    figure.add_trace(colored_indicator(dashboard_data["traces"], "Traces", False), row=2, col=1)
    figure.add_trace(colored_indicator(dashboard_data["questions"], "Questions", False), row=2, col=2)
    figure.add_trace(colored_indicator(total_billed_tokens(dashboard_data["cost_rows"]), "Billed tokens", False), row=2, col=3)
    figure.add_trace(colored_indicator(total_estimated_usd(dashboard_data["cost_rows"]), "Estimated USD", False, "$.4f"), row=2, col=4)
    return dark_layout(figure, f"Local logs and telemetry dashboard (last {dashboard_data['lookback_minutes']} minutes)", 420)


def build_agent_health_figure(dashboard_data):
    figure = make_subplots(rows=1, cols=2, specs=[[{"type": "xy"}, {"type": "table"}]], subplot_titles=["Agent latency (avg ms)", "Agent successes and failures"], column_widths=[0.42, 0.58])
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["agent_health"]], y=[row[4] for row in dashboard_data["agent_health"]], marker_color=[status_color(row[2]) for row in dashboard_data["agent_health"]], name="Avg ms"), row=1, col=1)
    figure.add_trace(go.Table(header={"values": ["Agent", "Spans", "Errors", "OK", "Avg ms", "Max ms"], "fill_color": "#14532d", "font": {"color": "#dcfce7"}}, cells={"values": [[row[column_index] for row in dashboard_data["agent_health"]] for column_index in range(6)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=1, col=2)
    return dark_layout(figure, "Agent monitoring", 560)


def build_log_figure(dashboard_data):
    figure = make_subplots(rows=2, cols=2, specs=[[{"type": "xy"}, {"type": "xy"}], [{"type": "xy"}, {"type": "table"}]], subplot_titles=["Events by status", "Errors by process", "Events over time", "Recent errors"], vertical_spacing=0.14)
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["statuses"]], y=[row[1] for row in dashboard_data["statuses"]], marker_color=[STATUS_COLORS.get(row[0], "#64748b") for row in dashboard_data["statuses"]], name="Events"), row=1, col=1)
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["error_processes"]], y=[row[1] for row in dashboard_data["error_processes"]], marker_color="#ef4444", name="Errors"), row=1, col=2)
    figure.add_trace(go.Scatter(x=[row[0] for row in dashboard_data["timeline"]], y=[row[1] for row in dashboard_data["timeline"]], mode="lines+markers", line={"color": "#38bdf8"}, name="Events"), row=2, col=1)
    figure.add_trace(go.Table(header={"values": ["Time", "Process", "Flow", "Trace", "Content"], "fill_color": "#7f1d1d", "font": {"color": "#fecaca"}}, cells={"values": [[row[column_index] for row in dashboard_data["recent_errors"]] for column_index in range(5)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=2, col=2)
    return dark_layout(figure, "Logs", 900)


def build_log_process_figure(dashboard_data):
    figure = make_subplots(rows=1, cols=2, specs=[[{"type": "xy"}, {"type": "table"}]], subplot_titles=["Process finished vs errors", "Recent events"])
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["log_health"]], y=[row[1] for row in dashboard_data["log_health"]], name="FINISHED", marker_color="#22c55e"), row=1, col=1)
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["log_health"]], y=[row[2] for row in dashboard_data["log_health"]], name="ERROR", marker_color="#ef4444"), row=1, col=1)
    figure.add_trace(go.Table(header={"values": ["Time", "Status", "Process", "Flow", "Level"], "fill_color": "#14532d", "font": {"color": "#dcfce7"}}, cells={"values": [[row[column_index] for row in dashboard_data["recent_events"]] for column_index in range(5)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=1, col=2)
    figure.update_layout(barmode="stack")
    return dark_layout(figure, "Logging process health", 560, True)


def build_agent_latency_figure(dashboard_data):
    figure = go.Figure()
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["agent_health"]], y=[row[4] for row in dashboard_data["agent_health"]], name="Avg ms", marker_color="#22c55e"))
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["agent_health"]], y=[row[5] for row in dashboard_data["agent_health"]], name="Max ms", marker_color="#f59e0b"))
    figure.update_layout(barmode="group")
    return dark_layout(figure, "Latency by agent", 520, True)


def build_cost_figure(dashboard_data):
    figure = make_subplots(rows=2, cols=2, specs=[[{"type": "xy"}, {"type": "xy"}], [{"type": "table"}, {"type": "table"}]], subplot_titles=["Estimated USD by agent", "Estimated USD by question", "Cost by agent and model", "Cost by question and model"], vertical_spacing=0.14)
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["agent_usd"]], y=[row[1] for row in dashboard_data["agent_usd"]], marker_color="#22c55e", name="USD"), row=1, col=1)
    figure.add_trace(go.Bar(x=[(row[0] or "")[:8] for row in dashboard_data["flow_usd"]], y=[row[1] for row in dashboard_data["flow_usd"]], marker_color="#38bdf8", name="USD"), row=1, col=2)
    figure.add_trace(go.Table(header={"values": ["Agent", "Model", "Input tokens", "Output tokens", "Est. USD"], "fill_color": "#14532d", "font": {"color": "#dcfce7"}}, cells={"values": [[row[column_index] for row in dashboard_data["cost_rows"]] for column_index in range(5)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=2, col=1)
    figure.add_trace(go.Table(header={"values": ["Flow", "Model", "Input tokens", "Output tokens", "Est. USD"], "fill_color": "#14532d", "font": {"color": "#dcfce7"}}, cells={"values": [[row[column_index] for row in dashboard_data["flow_cost_rows"]] for column_index in range(5)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=2, col=2)
    return dark_layout(figure, "Estimated model cost", 900)


def build_span_figure(dashboard_data):
    figure = make_subplots(rows=2, cols=2, specs=[[{"type": "xy"}, {"type": "xy"}], [{"type": "table"}, {"type": "table"}]], subplot_titles=["Spans by name", "Avg duration by name (ms)", "Tool calls", "Error spans"], vertical_spacing=0.16)
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["span_names"]], y=[row[1] for row in dashboard_data["span_names"]], marker_color="#38bdf8", name="Spans"), row=1, col=1)
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["span_durations"]], y=[row[1] for row in dashboard_data["span_durations"]], marker_color="#f59e0b", name="Avg ms"), row=1, col=2)
    figure.add_trace(go.Table(header={"values": ["Name", "Tool", "Status", "Duration ms", "Flow", "Trace"], "fill_color": "#14532d", "font": {"color": "#dcfce7"}}, cells={"values": [[row[column_index] for row in dashboard_data["tool_spans"]] for column_index in range(6)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=2, col=1)
    figure.add_trace(go.Table(header={"values": ["Name", "Error", "Flow", "Trace", "Duration ms", "Input"], "fill_color": "#7f1d1d", "font": {"color": "#fecaca"}}, cells={"values": [[row[column_index] for row in dashboard_data["error_spans"]] for column_index in range(6)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=2, col=2)
    return dark_layout(figure, "Telemetry", 900)


def build_waterfall_figure(dashboard_data):
    names, offsets, durations, colors = waterfall_bars(dashboard_data["waterfall"])
    figure = go.Figure(go.Bar(base=offsets, x=durations, y=names, orientation="h", marker_color=colors, name="ms", hovertemplate="%{y}<br>%{x:.1f} ms<extra></extra>"))
    return dark_layout(figure, f"Trace waterfall {dashboard_data['waterfall_trace_id'] or ''}".strip(), 560)


def build_flow_table_figure(dashboard_data):
    figure = make_subplots(rows=1, cols=2, specs=[[{"type": "table"}, {"type": "table"}]], subplot_titles=["Flows joined on flow_id / trace_id", "Routing and budget events"])
    figure.add_trace(go.Table(header={"values": ["Flow", "Trace", "Log events", "Log errors", "Spans", "Span errors", "Duration ms", "GT id", "Task %", "Fail agent", "GT answer", "Predicted"], "fill_color": "#14532d", "font": {"color": "#dcfce7"}}, cells={"values": [[row[column_index] for row in dashboard_data["correlated_flows"]] for column_index in range(12)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=1, col=1)
    figure.add_trace(go.Table(header={"values": ["Event", "Details", "Flow", "Trace"], "fill_color": "#1e3a8a", "font": {"color": "#dbeafe"}}, cells={"values": [[row[column_index] for row in dashboard_data["span_events"]] for column_index in range(4)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=1, col=2)
    return dark_layout(figure, "Question flow index", 560)


def build_one_flow_figure(question_flow):
    names, offsets, durations, colors = waterfall_bars(question_flow["waterfall"])
    figure = make_subplots(rows=2, cols=1, specs=[[{"type": "xy"}], [{"type": "table"}]], subplot_titles=[f"Trace waterfall · {question_flow['flow_id']} · {question_flow['span_errors']} span errors · {round(question_flow['duration_ms'] or 0, 1)} ms", "Lifecycle logs"], row_heights=[0.65, 0.35], vertical_spacing=0.12)
    figure.add_trace(go.Bar(base=offsets, x=durations, y=names, orientation="h", marker_color=colors, name="ms", hovertemplate="%{y}<br>%{x:.1f} ms<extra></extra>"), row=1, col=1)
    figure.add_trace(go.Table(header={"values": ["Time", "Status", "Process", "Level"], "fill_color": "#14532d", "font": {"color": "#dcfce7"}}, cells={"values": [[row[column_index] for row in question_flow["logs"]] for column_index in range(4)], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}), row=2, col=1)
    return dark_layout(figure, question_flow["preview"] or question_flow["trace_id"], 760)


def build_gt_overview_figure(dashboard_data):
    total = dashboard_data["gt_total"]
    scored = bool(dashboard_data["gt_rows"])
    figure = make_subplots(rows=2, cols=4, specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}], [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]])
    figure.add_trace(colored_indicator(metric_number(total.get("task_success")), "Task success %", scored and metric_number(total.get("task_success")) < 100, ".1f"), row=1, col=1)
    figure.add_trace(colored_indicator(metric_number(total.get("gather_success")), "Gather %", scored and metric_number(total.get("gather_success")) < 100, ".1f"), row=1, col=2)
    figure.add_trace(colored_indicator(metric_number(total.get("retrieve_success")), "Retrieve %", scored and metric_number(total.get("retrieve_success")) < 100, ".1f"), row=1, col=3)
    figure.add_trace(colored_indicator(metric_number(total.get("retrieval_success")), "Retrieval %", scored and metric_number(total.get("retrieval_success")) < 100, ".1f"), row=1, col=4)
    figure.add_trace(colored_indicator(metric_number(total.get("grade_success")), "Grade %", scored and metric_number(total.get("grade_success")) < 100, ".1f"), row=2, col=1)
    figure.add_trace(colored_indicator(metric_number(total.get("answer_success")), "Answer %", scored and metric_number(total.get("answer_success")) < 100, ".1f"), row=2, col=2)
    figure.add_trace(colored_indicator(metric_number(total.get("citation_success")), "Citation %", scored and metric_number(total.get("citation_success")) < 100, ".1f"), row=2, col=3)
    figure.add_trace(colored_indicator(metric_number(total.get("orchestration_success")), "Orchestration %", scored and metric_number(total.get("orchestration_success")) < 100, ".1f"), row=2, col=4)
    return dark_layout(figure, f"GT success rates · {dashboard_data['gt_metrics_name'] or 'no metrics CSV'}", 420)


def build_gt_question_figure(dashboard_data):
    rows = dashboard_data["gt_rows"]
    figure = make_subplots(rows=1, cols=2, specs=[[{"type": "xy"}, {"type": "xy"}]], subplot_titles=["Task success by question", "Failure agent counts"])
    figure.add_trace(go.Bar(x=gt_column(rows, "question_id"), y=gt_column(rows, "task_success"), marker_color=[status_color(row["task_success"] != 100) for row in rows], name="Task %"), row=1, col=1)
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["gt_failures"]], y=[row[1] for row in dashboard_data["gt_failures"]], marker_color=[status_color(row[0] not in ("none", "")) for row in dashboard_data["gt_failures"]], name="Count"), row=1, col=2)
    figure.update_layout(yaxis={"range": [0, 100]}, yaxis2={"rangemode": "tozero"})
    return dark_layout(figure, "GT question outcomes", 520)


def build_gt_score_table_figure(dashboard_data):
    rows = dashboard_data["gt_rows"]
    figure = go.Figure(go.Table(header={"values": ["Q", "HTTP", "Task %", "Fail", "Gather", "Retrieve", "Retrieval", "Grade", "Answer", "Citation", "Orch", "URL recall", "Snippet recall", "Cite recall", "Hop", "Source fill", "Date fill", "Waste", "Stop", "Error", "Turns", "Tools", "ms"], "fill_color": "#14532d", "font": {"color": "#dcfce7"}}, cells={"values": [gt_column(rows, "question_id"), gt_column(rows, "http_status"), gt_column(rows, "task_success"), gt_column(rows, "failure_agent"), gt_column(rows, "gather_success"), gt_column(rows, "retrieve_success"), gt_column(rows, "retrieval_success"), gt_column(rows, "grade_success"), gt_column(rows, "answer_success"), gt_column(rows, "citation_success"), gt_column(rows, "orchestration_success"), gt_column(rows, "gold_url_recall_pct"), gt_column(rows, "gold_snippet_recall_pct"), gt_column(rows, "citation_title_recall_pct"), gt_column(rows, "hop_coverage_pct"), gt_column(rows, "source_fill_pct"), gt_column(rows, "date_fill_pct"), gt_column(rows, "wasted_call_pct"), gt_column(rows, "stop_verdict"), gt_column(rows, "answer_error_type"), gt_column(rows, "gather_turns"), gt_column(rows, "tool_count"), gt_column(rows, "duration_ms")], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}))
    return dark_layout(figure, "GT scorecard", 640)


def build_gt_compare_table_figure(dashboard_data):
    rows = dashboard_data["gt_rows"]
    figure = go.Figure(go.Table(header={"values": ["Q", "Intents", "Question", "GT answer", "Predicted", "Error type", "GT citation titles", "Missing gold URLs", "Flow", "Runtime error"], "fill_color": "#14532d", "font": {"color": "#dcfce7"}}, cells={"values": [gt_column(rows, "question_id"), gt_column(rows, "intents"), gt_column(rows, "question"), gt_column(rows, "gt_answer"), gt_column(rows, "predicted_answer"), gt_column(rows, "answer_error_type"), gt_column(rows, "citation_titles"), gt_column(rows, "missing_urls"), gt_column(rows, "flow_id"), gt_column(rows, "runtime_error")], "fill_color": "#1f2937", "font": {"color": "#e5e7eb"}}))
    return dark_layout(figure, "GT vs predicted answers", 760)


def write_tabbed_html(tab_figures, lookback_minutes, gt_metrics_name):
    html_parts = [f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Local logs and telemetry dashboard</title><style>{DASHBOARD_STYLE}</style></head><body><div class='nav'>"]
    for tab_index, tab_spec in enumerate(tab_figures):
        html_parts.append(f"<button class='tab{' active' if tab_index == 0 else ''}' id='btn-{tab_spec[0]}' onclick=\"showTab('{tab_spec[0]}')\">{tab_spec[1]}</button>")
    html_parts.append(f"</div><p class='note'>Local logs and telemetry dashboard (last {lookback_minutes} minutes). Latency from span timestamps. Tokens from gen_ai.usage when numeric, otherwise characters/{CHARS_PER_TOKEN}. USD is estimated from listed model rates. GT comparison is the latest live_e2e_gt CSV ({gt_metrics_name or 'none'}), not span fields.</p>")
    include_plotlyjs = True
    for tab_index, tab_spec in enumerate(tab_figures):
        html_parts.append(f"<div class='panel{' active' if tab_index == 0 else ''}' id='{tab_spec[0]}'><h2>{tab_spec[1]}</h2>")
        for figure in tab_spec[2]:
            html_parts.append(figure.to_html(full_html=False, include_plotlyjs=include_plotlyjs, config={"responsive": True}))
            include_plotlyjs = False
        html_parts.append("</div>")
    html_parts.append(f"<script>{DASHBOARD_SCRIPT}</script></body></html>")
    DASHBOARD_PATH.write_text("".join(html_parts), encoding="utf-8")
    return DASHBOARD_PATH


def build_dashboard(lookback_minutes=None, log_file_path=None, telemetry_directory_path=None, metrics_directory_path=None, ground_truth_directory_path=None):
    with DASHBOARD_LOCK:
        dashboard_data = load_dashboard_data(lookback_minutes, log_file_path, telemetry_directory_path, metrics_directory_path, ground_truth_directory_path)
        flow_figures = []
        for question_flow in dashboard_data["question_flows"]:
            flow_figures.append(build_one_flow_figure(question_flow))
        return write_tabbed_html([("overview", "Overview", [build_overview_figure(dashboard_data), build_agent_health_figure(dashboard_data)]), ("logging", "Logging", [build_log_figure(dashboard_data), build_log_process_figure(dashboard_data)]), ("telemetry", "Telemetry", [build_agent_latency_figure(dashboard_data), build_cost_figure(dashboard_data), build_span_figure(dashboard_data), build_waterfall_figure(dashboard_data)]), ("flows", "Question flows", [build_flow_table_figure(dashboard_data)] + flow_figures), ("gt", "GT comparison", [build_gt_overview_figure(dashboard_data), build_gt_question_figure(dashboard_data), build_gt_score_table_figure(dashboard_data), build_gt_compare_table_figure(dashboard_data)])], dashboard_data["lookback_minutes"], dashboard_data["gt_metrics_name"])


if __name__ == "__main__":
    print(build_dashboard())
