# Local logging dashboard

Generate a standalone dashboard from `local_logging_audit/audit_log/events.jsonl`:

```powershell
uv run python -m local_logging_dashboard.build_dashboard
```

Open `local_logging_dashboard/dashboard.html`. It contains total events, errors, status counts, errors by process, an event timeline, and recent errors. Plotly is embedded in the file, so no server or internet connection is needed after installation.
