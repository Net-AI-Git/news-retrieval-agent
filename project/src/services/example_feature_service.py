from ..repositories.opensearch_repository import OpenSearchRepository


def run_example_feature(task_data, flow_id):
    OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id)
    feature_result = ""
    try:
        feature_result = task_data["content"]
    except Exception as err:
        OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id)
    OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id)
    return feature_result
