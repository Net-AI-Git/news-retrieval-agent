from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from local_logging_audit.local_logging_audit_client import open_local_logs


DASHBOARD_PATH = Path(__file__).parent / "dashboard.html"


def load_dashboard_data():
    connection = open_local_logs()
    try:
        totals = connection.execute("SELECT count(*) AS total, COALESCE(sum(CASE WHEN level = 'ERROR' THEN 1 ELSE 0 END), 0) AS errors FROM local_logs").fetchone()
        return {"total": totals[0], "errors": totals[1], "statuses": connection.execute("SELECT status, count(*) AS events FROM local_logs GROUP BY status ORDER BY events DESC").fetchall(), "error_processes": connection.execute("SELECT process, count(*) AS errors FROM local_logs WHERE level = 'ERROR' GROUP BY process ORDER BY errors DESC LIMIT 10").fetchall(), "timeline": connection.execute("SELECT substr(time, 1, 16) AS minute, count(*) AS events FROM local_logs GROUP BY minute ORDER BY minute").fetchall(), "recent_errors": connection.execute("SELECT time, process, flow_id, content FROM local_logs WHERE level = 'ERROR' ORDER BY time DESC LIMIT 20").fetchall()}
    finally:
        connection.close()


def build_dashboard():
    dashboard_data = load_dashboard_data()
    figure = make_subplots(rows=3, cols=2, specs=[[{"type": "indicator"}, {"type": "indicator"}], [{"type": "xy"}, {"type": "xy"}], [{"type": "xy"}, {"type": "table"}]], subplot_titles=["", "", "Events by status", "Errors by process", "Events over time", "Recent errors"], vertical_spacing=0.12)
    figure.add_trace(go.Indicator(mode="number", value=dashboard_data["total"], title={"text": "Total events"}), row=1, col=1)
    figure.add_trace(go.Indicator(mode="number", value=dashboard_data["errors"], title={"text": "Errors"}), row=1, col=2)
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["statuses"]], y=[row[1] for row in dashboard_data["statuses"]], name="Events"), row=2, col=1)
    figure.add_trace(go.Bar(x=[row[0] for row in dashboard_data["error_processes"]], y=[row[1] for row in dashboard_data["error_processes"]], name="Errors"), row=2, col=2)
    figure.add_trace(go.Scatter(x=[row[0] for row in dashboard_data["timeline"]], y=[row[1] for row in dashboard_data["timeline"]], mode="lines+markers", name="Events"), row=3, col=1)
    figure.add_trace(go.Table(header={"values": ["Time", "Process", "Flow", "Content"]}, cells={"values": [[row[column_index] for row in dashboard_data["recent_errors"]] for column_index in range(4)]}), row=3, col=2)
    figure.update_layout(title="Local logging dashboard", height=1100, showlegend=False, template="plotly_white")
    figure.write_html(DASHBOARD_PATH, include_plotlyjs=True, full_html=True, auto_open=False)
    return DASHBOARD_PATH


if __name__ == "__main__":
    print(build_dashboard())
