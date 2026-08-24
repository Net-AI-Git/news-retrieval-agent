import os
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI


def run_gather(task_data, flow_id):
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), temperature=0, seed=151).bind_tools(task_data["tools"]).invoke([SystemMessage((Path(__file__).resolve().parents[1] / "prompts" / "gather_agent.md").read_text(encoding="utf-8")), *task_data["messages"]])
