import os
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from ..tools.retrieval_tools import RetrievalTools


def build_gather_tools(task_data, flow_id):
    return RetrievalTools(task_data, flow_id).as_langchain_tools()


def run_gather(task_data, flow_id):
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), temperature=0, seed=151).bind_tools(build_gather_tools(task_data, flow_id)).invoke([SystemMessage((Path(__file__).resolve().parents[1] / "prompts" / "gather_agent.md").read_text(encoding="utf-8")), *task_data["messages"]])
