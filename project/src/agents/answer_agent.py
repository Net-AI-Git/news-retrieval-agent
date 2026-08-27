import json
import os
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..schemas.agent import AnswerResult


def run_answer(task_data, flow_id):
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL"), api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"), temperature=0, seed=151).with_structured_output(AnswerResult).invoke([SystemMessage((Path(__file__).resolve().parents[1] / "prompts" / "answer_agent.md").read_text(encoding="utf-8")), HumanMessage(json.dumps({"evidence": task_data["evidence"], "question": task_data["question"]}, ensure_ascii=False))])
