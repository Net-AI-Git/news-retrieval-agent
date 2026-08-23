import json
import os

import redis
from dotenv import load_dotenv

from .opensearch_repository import OpenSearchRepository

load_dotenv()


class RedisRepository:

    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT")
    REDIS_USERNAME = os.getenv("REDIS_USERNAME")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_CERT_PATH = os.getenv("REDIS_CERT_PATH")

    client = redis.StrictRedis(host=REDIS_HOST, port=int(REDIS_PORT), ssl=True, ssl_ca_certs=REDIS_CERT_PATH, username=REDIS_USERNAME, password=REDIS_PASSWORD)

    @staticmethod
    def push_to_queue(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        try:
            queue_id = task_data["queue_id"]
            payload = task_data["payload"]
            RedisRepository.client.lpush(f"queue:{queue_id}", json.dumps(payload, ensure_ascii=False))
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return

    @staticmethod
    def pull_from_queue(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        try:
            queue_id = task_data["queue_id"]
            callback = task_data["callback"]
            while True:
                _, raw_task = RedisRepository.client.brpop(f"queue:{queue_id}")
                callback(json.loads(raw_task))
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return

    @staticmethod
    def get_queue_status(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        items_in_queue = 0
        try:
            queue_id = task_data["queue_id"]
            items_in_queue = len(RedisRepository.client.lrange(f"queue:{queue_id}", 0, -1))
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return items_in_queue
