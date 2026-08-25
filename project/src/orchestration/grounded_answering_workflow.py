import operator
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphInterrupt
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from ..agents.answer_agent import run_answer
from ..agents.gather_agent import run_gather
from ..conts import ANSWER_STATUS_ANSWERED, ANSWER_STATUS_REFUSED, GATHER_MAX_LLM_TURNS, GATHER_MAX_TOOL_CALLS, GROUNDED_ANSWERING_RECURSION_LIMIT
from ..repositories.opensearch_repository import OpenSearchRepository
from ..schemas.agent import AnswerResult, SearchEvidenceOutput
from ..tools.retrieval_tools import RetrievalTools


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
        if citation.url and any(item.get("url") == citation.url for item in evidence):
            grounded_citations.append(citation)
        elif not citation.url and any(item.get("article_title") == citation.article_title for item in evidence):
            grounded_citations.append(citation)
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


def gather_node(state, langchain_tools, flow_id):
    return {"messages": [run_gather({"tools": langchain_tools, "messages": state["messages"]}, flow_id)], "gather_count": state.get("gather_count", 0) + 1}


def tools_node(state, tool_node):
    tool_messages = tool_node.invoke(state)["messages"]
    return {"messages": tool_messages, "evidence": collect_tool_evidence(tool_messages), "tool_count": state.get("tool_count", 0) + len(state["messages"][-1].tool_calls)}


def answer_node(state, flow_id):
    evidence = state.get("evidence") or []
    if not evidence:
        return {"answer_result": AnswerResult(status=ANSWER_STATUS_REFUSED, answer="", citations=[])}
    return {"answer_result": filter_answer_citations(run_answer({"question": state["question"], "evidence": evidence}, flow_id), evidence)}


def build_grounded_answering_graph(task_data, flow_id):
    langchain_tools = RetrievalTools(task_data, flow_id).as_langchain_tools()
    tool_node = ToolNode(langchain_tools)
    graph = StateGraph(GroundedAnsweringState)
    graph.add_node("gather", lambda state: gather_node(state, langchain_tools, flow_id))
    graph.add_node("tools", lambda state: tools_node(state, tool_node))
    graph.add_node("answer", lambda state: answer_node(state, flow_id))
    graph.set_entry_point("gather")
    graph.add_conditional_edges("gather", route_after_gather, {"tools": "tools", "answer": "answer"})
    graph.add_edge("tools", "gather")
    graph.add_edge("answer", END)
    return graph.compile()


def invoke_grounded_answering_graph(task_data, flow_id):
    graph_state = build_grounded_answering_graph(task_data, flow_id).invoke({"question": task_data["question"], "messages": [HumanMessage(task_data["question"])], "evidence": [], "gather_count": 0, "tool_count": 0, "answer_result": None}, {"recursion_limit": GROUNDED_ANSWERING_RECURSION_LIMIT})
    return graph_state.get("answer_result") or AnswerResult(status=ANSWER_STATUS_REFUSED, answer="", citations=[])


def run_grounded_answering(task_data, flow_id):
    OpenSearchRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    answer_result = AnswerResult(status=ANSWER_STATUS_REFUSED, answer="", citations=[])
    try:
        answer_result = invoke_grounded_answering_graph(task_data, flow_id)
    except Exception as err:
        if isinstance(err, GraphInterrupt):
            raise
        OpenSearchRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    OpenSearchRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return answer_result.model_dump()
