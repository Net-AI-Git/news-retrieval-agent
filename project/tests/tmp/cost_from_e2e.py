import csv
from pathlib import Path

from observability.logging_dashboard.build_dashboard import BILLED_INPUT_SQL, BILLED_OUTPUT_SQL, costed_rows, estimated_usd, total_billed_tokens, total_estimated_usd
from observability.telemetry_audit.telemetry_audit_client import open_spans

METRICS = Path(__file__).resolve().parents[1] / "live_e2e_gt" / "outputs" / "metrics_2026-08-29_16-09-55.csv"


def main():
    rows = list(csv.DictReader(METRICS.open(encoding="utf-8-sig")))
    question_rows = [row for row in rows if row["question_id"] != "TOTAL"]
    flow_ids = [row["flow_id"] for row in question_rows]
    placeholders = ",".join("?" * len(flow_ids))
    connection = open_spans()
    try:
        agent_rows = costed_rows(connection.execute(f"SELECT agent, COALESCE(model, ''), COALESCE(sum({BILLED_INPUT_SQL}), 0), COALESCE(sum({BILLED_OUTPUT_SQL}), 0) FROM spans WHERE flow_id IN ({placeholders}) GROUP BY agent, model ORDER BY 3 DESC", flow_ids).fetchall())
        flow_rows = costed_rows(connection.execute(f"SELECT COALESCE(flow_id, ''), COALESCE(model, ''), COALESCE(sum({BILLED_INPUT_SQL}), 0), COALESCE(sum({BILLED_OUTPUT_SQL}), 0) FROM spans WHERE flow_id IN ({placeholders}) GROUP BY flow_id, model", flow_ids).fetchall())
        bounds = connection.execute(f"SELECT min(start_time_unix_nano), max(end_time_unix_nano) FROM spans WHERE flow_id IN ({placeholders})", flow_ids).fetchone()
        chat_rows = costed_rows(connection.execute(f"SELECT COALESCE(flow_id, ''), COALESCE(model, ''), COALESCE(sum({BILLED_INPUT_SQL}), 0), COALESCE(sum({BILLED_OUTPUT_SQL}), 0) FROM spans WHERE flow_id IN ({placeholders}) AND coalesce(model, '') != '' GROUP BY flow_id, model", flow_ids).fetchall())
        agent_chat = costed_rows(connection.execute(f"SELECT agent, COALESCE(model, ''), COALESCE(sum({BILLED_INPUT_SQL}), 0), COALESCE(sum({BILLED_OUTPUT_SQL}), 0) FROM spans WHERE flow_id IN ({placeholders}) AND coalesce(model, '') != '' GROUP BY agent, model ORDER BY 3 DESC", flow_ids).fetchall())
    finally:
        connection.close()
    flow_totals = {}
    for flow_id, model, input_tokens, output_tokens, usd in flow_rows:
        flow_totals[flow_id] = flow_totals.get(flow_id, 0) + usd
    question_usd = [(row["question_id"], round(flow_totals.get(row["flow_id"], 0), 6), float(row["duration_ms"])) for row in question_rows]
    total_usd = total_estimated_usd([(None, None, None, None, usd) for usd in flow_totals.values()] if False else [(a, b, c, d, e) for a, b, c, d, e in flow_rows])
    wall_s = (bounds[1] - bounds[0]) / 1e9 if bounds[0] else 0
    print("agent_rows")
    for row in agent_rows:
        print(row)
    print("question_usd")
    for row in question_usd:
        print(row)
    print("total_usd", round(total_usd, 6))
    print("mean_question_usd", round(total_usd / len(question_rows), 6))
    print("billed_tokens", total_billed_tokens(flow_rows))
    print("wall_s", round(wall_s, 2))
    print("sum_duration_s", round(sum(item[2] for item in question_usd) / 1000, 2))
    chat_totals = {}
    for flow_id, model, input_tokens, output_tokens, usd in chat_rows:
        chat_totals[flow_id] = chat_totals.get(flow_id, 0) + usd
    chat_question_usd = [(row["question_id"], round(chat_totals.get(row["flow_id"], 0), 6)) for row in question_rows]
    chat_total = total_estimated_usd(chat_rows)
    print("agent_chat")
    for row in agent_chat:
        print(row)
    print("chat_question_usd")
    for row in chat_question_usd:
        print(row)
    print("chat_total", round(chat_total, 6))
    print("chat_mean", round(chat_total / len(question_rows), 6))
    print("chat_tokens", total_billed_tokens(chat_rows))
    print("chat_min", min(chat_question_usd, key=lambda item: item[1]))
    print("chat_max", max(chat_question_usd, key=lambda item: item[1]))


if __name__ == "__main__":
    main()
