import json
import os
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..schemas.agent import GradeResult


def run_grade(task_data, flow_id):
    return ChatOpenAI(model=os.getenv("OPENAI_GRADE_AGENT_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), temperature=0.3, seed=42).with_structured_output(GradeResult).invoke([SystemMessage((Path(__file__).resolve().parents[1] / "prompts" / "grade_agent.md").read_text(encoding="utf-8")), HumanMessage(json.dumps({"question": task_data["question"], "evidence": task_data["evidence"], "prior_queries": task_data["prior_queries"]}, ensure_ascii=False))])
