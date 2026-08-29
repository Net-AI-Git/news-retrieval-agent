import os
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..tools.retrieval_tools import RetrievalTools


def build_retrieve_tools(task_data, flow_id):
    return RetrievalTools(task_data, flow_id).as_langchain_tools()


def run_retrieve(task_data, flow_id):
    return ChatOpenAI(model=os.getenv("OPENAI_RETRIEVE_AGENT_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), temperature=0.3, seed=42).bind_tools(build_retrieve_tools(task_data, flow_id), tool_choice="search_facts").invoke([SystemMessage((Path(__file__).resolve().parents[1] / "prompts" / "retrieve_agent.md").read_text(encoding="utf-8")), HumanMessage(task_data["sub_question"])])
