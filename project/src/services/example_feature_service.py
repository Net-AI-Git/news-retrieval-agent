from ..repositories.local_logging_repository import LocalLoggingRepository


def run_example_feature(task_data, flow_id):
    LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    feature_result = ""
    try:
        feature_result = task_data["content"]
    except Exception as err:
        LocalLoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    LocalLoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return feature_result
