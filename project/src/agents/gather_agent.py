import json
import os
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..schemas.agent import GatherResult


def run_gather(task_data, flow_id):
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), temperature=0, seed=151).with_structured_output(GatherResult).invoke([SystemMessage((Path(__file__).resolve().parents[1] / "prompts" / "gather_agent.md").read_text(encoding="utf-8")), HumanMessage(json.dumps({"question": task_data["question"], "prior_queries": task_data.get("prior_queries") or [], "grade_note": task_data.get("grade_note") or ""}, ensure_ascii=False))])
