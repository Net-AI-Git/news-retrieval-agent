from observability.logging_dashboard.build_dashboard import build_dashboard

from ..repositories.logging_repository import LoggingRepository


def run_logging_dashboard(task_data, flow_id):
    LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    try:
        build_dashboard()
    except Exception as err:
        LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return
