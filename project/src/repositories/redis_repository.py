import json
import os

import redis
from dotenv import load_dotenv

from .opensearch_repository import OpenSearchRepository

load_dotenv()


class RedisRepository:

    client = redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")), ssl=True, ssl_ca_certs=os.getenv("REDIS_CERT_PATH"), username=os.getenv("REDIS_USERNAME"), password=os.getenv("REDIS_PASSWORD"))

    @staticmethod
    def push_to_queue(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        try:
            RedisRepository.client.lpush(f"queue:{task_data['queue_id']}", json.dumps(task_data["payload"], ensure_ascii=False))
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return

    @staticmethod
    def pull_from_queue(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        try:
            callback = task_data["callback"]
            while True:
                callback(json.loads(RedisRepository.client.brpop(f"queue:{task_data['queue_id']}")[1]))
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return

    @staticmethod
    def get_queue_status(task_data, flow_id):
        OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        items_in_queue = 0
        try:
            items_in_queue = len(RedisRepository.client.lrange(f"queue:{task_data['queue_id']}", 0, -1))
        except Exception as err:
            OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
        return items_in_queue
