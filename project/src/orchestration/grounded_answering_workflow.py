import operator
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphInterrupt
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from ..agents.answer_agent import run_answer
from ..agents.gather_agent import build_gather_tools, run_gather
from ..conts import ANSWER_STATUS_ANSWERED, ANSWER_STATUS_REFUSED, GATHER_MAX_LLM_TURNS, GATHER_MAX_TOOL_CALLS, GROUNDED_ANSWERING_RECURSION_LIMIT
from ..repositories.local_logging_repository import LocalLoggingRepository
from ..schemas.agent import AnswerResult, SearchEvidenceOutput


class GroundedAnsweringState(TypedDict):
    question: str
    messages: Annotated[list, add_messages]
    evidence: Annotated[list, operator.add]
    gather_count: int
    tool_count: int
    answer_result: Optional[AnswerResult]


def collect_tool_evidence(tool_messages):
    evidence = []
    for tool_message in tool_messages:
        evidence.extend(SearchEvidenceOutput.model_validate_json(tool_message.content).model_dump()["results"])
    return evidence


def filter_answer_citations(answer_result, evidence):
    grounded_citations = []
    for citation in answer_result.citations:
        for item in evidence:
            if citation.snippet == item.get("snippet") and citation.url == item.get("url"):
                grounded_citations.append(citation)
                break
    if answer_result.status != ANSWER_STATUS_ANSWERED or not grounded_citations:
        return AnswerResult(status=ANSWER_STATUS_REFUSED, answer="", citations=[])
    return AnswerResult(status=ANSWER_STATUS_ANSWERED, answer=answer_result.answer, citations=grounded_citations)


def route_after_gather(state):
    if state.get("gather_count", 0) >= GATHER_MAX_LLM_TURNS or state.get("tool_count", 0) >= GATHER_MAX_TOOL_CALLS:
        return "answer"
    last_message = state["messages"][-1]
    pending_tool_calls = getattr(last_message, "tool_calls", None) or []
    if pending_tool_calls and len(pending_tool_calls) <= GATHER_MAX_TOOL_CALLS - state.get("tool_count", 0):
        return "tools"
    return "answer"


def extract_tool_calls(message):
    tool_calls = []
    for tool_call in getattr(message, "tool_calls", None) or []:
        tool_calls.append({"name": tool_call["name"] if isinstance(tool_call, dict) else tool_call.name, "args": tool_call["args"] if isinstance(tool_call, dict) else tool_call.args})
    return tool_calls


def gather_node(state, task_data, flow_id):
    gather_message = run_gather({**task_data, "messages": state["messages"]}, flow_id)
    task_data["gather_count"] = state.get("gather_count", 0) + 1
    task_data["model_text"] = gather_message.content
    task_data["tool_calls"] = extract_tool_calls(gather_message)
    task_data["next_route"] = route_after_gather({"messages": [gather_message], "gather_count": task_data["gather_count"], "tool_count": state.get("tool_count", 0)})
    return {"messages": [gather_message], "gather_count": task_data["gather_count"]}


def tools_node(state, tool_node, task_data, flow_id):
    tool_messages = tool_node.invoke(state)["messages"]
    evidence = collect_tool_evidence(tool_messages)
    task_data["tool_calls"] = extract_tool_calls(state["messages"][-1])
    task_data["tool_count"] = state.get("tool_count", 0) + len(task_data["tool_calls"])
    task_data["evidence"] = (state.get("evidence") or []) + evidence
    return {"messages": tool_messages, "evidence": evidence, "tool_count": task_data["tool_count"]}


def answer_node(state, task_data, flow_id):
    evidence = state.get("evidence") or []
    answer_result = filter_answer_citations(run_answer({**task_data, "question": state["question"], "evidence": evidence}, flow_id), evidence)
    task_data["evidence"] = evidence
    task_data["answer_result"] = answer_result.model_dump()
    return {"answer_result": answer_result}


def build_grounded_answering_graph(task_data, flow_id):
    tool_node = ToolNode(build_gather_tools(task_data, flow_id))
    graph = StateGraph(GroundedAnsweringState)
    graph.add_node("gather", lambda state: gather_node(state, task_data, flow_id))
    graph.add_node("tools", lambda state: tools_node(state, tool_node, task_data, flow_id))
    graph.add_node("answer", lambda state: answer_node(state, task_data, flow_id))
    graph.set_entry_point("gather")
    graph.add_conditional_edges("gather", route_after_gather, {"tools": "tools", "answer": "answer"})
    graph.add_edge("tools", "gather")
    graph.add_edge("answer", END)
    return graph.compile()


def run_grounded_answering(task_data, flow_id):
    LocalLoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    answer_result = AnswerResult(status=ANSWER_STATUS_REFUSED, answer="", citations=[])
    try:
        graph_state = build_grounded_answering_graph(task_data, flow_id).invoke({"question": task_data["question"], "messages": [HumanMessage(task_data["question"])], "evidence": [], "gather_count": 0, "tool_count": 0, "answer_result": None}, {"recursion_limit": GROUNDED_ANSWERING_RECURSION_LIMIT})
        answer_result = graph_state.get("answer_result") or AnswerResult(status=ANSWER_STATUS_REFUSED, answer="", citations=[])
        task_data["answer_result"] = answer_result.model_dump()
    except Exception as err:
        if isinstance(err, GraphInterrupt):
            raise
        LocalLoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    LocalLoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return answer_result.model_dump()
