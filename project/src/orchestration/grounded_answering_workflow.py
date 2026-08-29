import operator
import os
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphInterrupt
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from ..agents.answer_agent import run_answer
from ..agents.gather_agent import run_gather
from ..agents.grade_agent import run_grade
from ..agents.retrieve_agent import build_retrieve_tools, run_retrieve
from ..conts import ANSWER_STATUS_ANSWERED, ANSWER_STATUS_REFUSED, GATHER_MAX_LLM_TURNS, GATHER_MAX_TOOL_CALLS, GRADE_CONTINUE_VERDICTS, GRADE_VERDICT_EMPTY_STOP, GRADE_VERDICT_ENOUGH, GRADE_VERDICT_MISSING_HOP, GROUNDED_ANSWERING_RECURSION_LIMIT, REQUIRED_SOLUTION_ENV_VARS, TELEMETRY_WORKFLOW_NAME, TELEMETRY_WORKFLOW_OPERATION_NAME
from ..repositories.logging_repository import LoggingRepository
from ..repositories.telemetry_repository import TelemetryRepository
from ..schemas.agent import AnswerResult, SearchEvidenceOutput


class GroundedAnsweringState(TypedDict):
    question: str
    messages: Annotated[list, add_messages]
    evidence: Annotated[list, operator.add]
    prior_queries: Annotated[list, operator.add]
    sub_questions: list
    gather_count: int
    tool_count: int
    grade_verdict: Optional[str]
    grade_note: Optional[str]
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


def cleaned_sub_questions(sub_questions, limit):
    cleaned = []
    for sub_question in sub_questions or []:
        if len(cleaned) >= limit:
            break
        text = (sub_question or "").strip()
        if text:
            cleaned.append(text)
    return cleaned


def route_after_gather(state):
    if state.get("gather_count", 0) >= GATHER_MAX_LLM_TURNS or state.get("tool_count", 0) >= GATHER_MAX_TOOL_CALLS:
        return "answer"
    if state.get("sub_questions"):
        return "retrieve"
    return "answer"


def route_after_retrieve(state):
    if state.get("gather_count", 0) >= GATHER_MAX_LLM_TURNS or state.get("tool_count", 0) >= GATHER_MAX_TOOL_CALLS:
        return "answer"
    last_message = state["messages"][-1]
    pending_tool_calls = getattr(last_message, "tool_calls", None) or []
    if pending_tool_calls and len(pending_tool_calls) <= GATHER_MAX_TOOL_CALLS - state.get("tool_count", 0):
        return "tools"
    return "answer"


def prior_query_records(tool_calls):
    records = []
    for tool_call in tool_calls or []:
        arguments = tool_call.get("args") if isinstance(tool_call.get("args"), dict) else {}
        question = arguments.get("question") or ""
        if question:
            records.append({"question": question, "source": arguments.get("source") or "", "published_from": arguments.get("published_from") or "", "published_to": arguments.get("published_to") or ""})
    return records


def normalize_grade_verdict(verdict, gather_count, tool_count):
    cleaned = (verdict or "").strip().lower()
    if gather_count >= GATHER_MAX_LLM_TURNS or tool_count >= GATHER_MAX_TOOL_CALLS:
        return GRADE_VERDICT_EMPTY_STOP
    if cleaned in (GRADE_VERDICT_ENOUGH, GRADE_VERDICT_MISSING_HOP, GRADE_VERDICT_EMPTY_STOP):
        return cleaned
    return GRADE_VERDICT_EMPTY_STOP


def route_after_grade(state):
    if state.get("gather_count", 0) >= GATHER_MAX_LLM_TURNS or state.get("tool_count", 0) >= GATHER_MAX_TOOL_CALLS:
        return "answer"
    if state.get("grade_verdict") in GRADE_CONTINUE_VERDICTS:
        return "gather"
    return "answer"


def extract_tool_calls(message):
    tool_calls = []
    for tool_call in getattr(message, "tool_calls", None) or []:
        tool_calls.append({"name": tool_call["name"] if isinstance(tool_call, dict) else tool_call.name, "args": tool_call["args"] if isinstance(tool_call, dict) else tool_call.args})
    return tool_calls


def gather_node(state, task_data, flow_id):
    sub_questions = cleaned_sub_questions(run_gather({**task_data, "question": state["question"], "prior_queries": state.get("prior_queries") or [], "grade_note": state.get("grade_note") or ""}, flow_id).sub_questions, GATHER_MAX_TOOL_CALLS - state.get("tool_count", 0))
    task_data["gather_count"] = state.get("gather_count", 0) + 1
    task_data["sub_questions"] = sub_questions
    task_data["next_route"] = route_after_gather({"sub_questions": sub_questions, "gather_count": task_data["gather_count"], "tool_count": state.get("tool_count", 0)})
    task_data.setdefault("transcript_turns", []).append({"stage": "gather", "gather_count": task_data["gather_count"], "sub_questions": sub_questions, "tool_calls": [], "next_route": task_data["next_route"]})
    TelemetryRepository.add_event("routing_decision", {"stage": "gather", "route": task_data["next_route"], "gather_count": task_data["gather_count"], "tool_count": state.get("tool_count", 0)})
    return {"sub_questions": sub_questions, "gather_count": task_data["gather_count"]}


def retrieve_node(state, task_data, flow_id):
    limit = GATHER_MAX_TOOL_CALLS - state.get("tool_count", 0)
    sub_questions = cleaned_sub_questions(state.get("sub_questions"), limit)
    tool_calls = []
    for sub_question in sub_questions:
        if len(tool_calls) >= limit:
            break
        message = run_retrieve({**task_data, "sub_question": sub_question}, flow_id)
        for tool_call in getattr(message, "tool_calls", None) or []:
            if len(tool_calls) >= limit:
                break
            tool_calls.append(tool_call)
    retrieve_message = AIMessage(content="", tool_calls=tool_calls)
    task_data["tool_calls"] = extract_tool_calls(retrieve_message)
    task_data["next_route"] = route_after_retrieve({"messages": [retrieve_message], "gather_count": state.get("gather_count", 0), "tool_count": state.get("tool_count", 0)})
    task_data.setdefault("transcript_turns", []).append({"stage": "retrieve", "gather_count": state.get("gather_count", 0), "tool_calls": task_data["tool_calls"], "next_route": task_data["next_route"]})
    TelemetryRepository.add_event("routing_decision", {"stage": "retrieve", "route": task_data["next_route"], "tool_count": state.get("tool_count", 0)})
    return {"messages": [retrieve_message]}


def tools_node(state, tool_node, task_data, flow_id):
    tool_messages = tool_node.invoke(state)["messages"]
    evidence = collect_tool_evidence(tool_messages)
    task_data["tool_calls"] = extract_tool_calls(state["messages"][-1])
    task_data["tool_count"] = state.get("tool_count", 0) + len(task_data["tool_calls"])
    task_data["evidence"] = (state.get("evidence") or []) + evidence
    prior_queries = prior_query_records(task_data["tool_calls"])
    task_data["prior_queries"] = (state.get("prior_queries") or []) + prior_queries
    task_data.setdefault("transcript_turns", []).append({"stage": "tools", "tool_count": task_data["tool_count"], "tool_calls": task_data["tool_calls"], "evidence": evidence})
    TelemetryRepository.add_event("budget_update", {"stage": "tools", "tool_count": task_data["tool_count"], "tool_limit": GATHER_MAX_TOOL_CALLS})
    return {"messages": tool_messages, "evidence": evidence, "tool_count": task_data["tool_count"], "prior_queries": prior_queries}


def grade_node(state, task_data, flow_id):
    grade_result = run_grade({**task_data, "question": state["question"], "evidence": state.get("evidence") or [], "prior_queries": state.get("prior_queries") or []}, flow_id)
    verdict = normalize_grade_verdict(grade_result.verdict, state.get("gather_count", 0), state.get("tool_count", 0))
    task_data["grade_verdict"] = verdict
    task_data["grade_note"] = grade_result.note
    task_data.setdefault("transcript_turns", []).append({"stage": "grade", "verdict": verdict, "note": grade_result.note})
    TelemetryRepository.add_event("routing_decision", {"stage": "grade", "verdict": verdict, "route": "gather" if verdict in GRADE_CONTINUE_VERDICTS else "answer"})
    if verdict in GRADE_CONTINUE_VERDICTS and grade_result.note:
        return {"messages": [HumanMessage(grade_result.note)], "grade_verdict": verdict, "grade_note": grade_result.note}
    return {"grade_verdict": verdict, "grade_note": ""}


def answer_node(state, task_data, flow_id):
    evidence = state.get("evidence") or []
    answer_result = filter_answer_citations(run_answer({**task_data, "question": state["question"], "evidence": evidence}, flow_id), evidence)
    task_data["evidence"] = evidence
    task_data["answer_result"] = answer_result.model_dump()
    task_data.setdefault("transcript_turns", []).append({"stage": "answer", "answer_result": task_data["answer_result"]})
    return {"answer_result": answer_result}


def build_grounded_answering_graph(task_data, flow_id):
    tool_node = ToolNode(build_retrieve_tools(task_data, flow_id))
    graph = StateGraph(GroundedAnsweringState)
    graph.add_node("gather", lambda state: gather_node(state, task_data, flow_id))
    graph.add_node("retrieve", lambda state: retrieve_node(state, task_data, flow_id))
    graph.add_node("tools", lambda state: tools_node(state, tool_node, task_data, flow_id))
    graph.add_node("grade", lambda state: grade_node(state, task_data, flow_id))
    graph.add_node("answer", lambda state: answer_node(state, task_data, flow_id))
    graph.set_entry_point("gather")
    graph.add_conditional_edges("gather", route_after_gather, {"retrieve": "retrieve", "answer": "answer"})
    graph.add_conditional_edges("retrieve", route_after_retrieve, {"tools": "tools", "answer": "answer"})
    graph.add_edge("tools", "grade")
    graph.add_conditional_edges("grade", route_after_grade, {"gather": "gather", "answer": "answer"})
    graph.add_edge("answer", END)
    return graph.compile()


def raise_if_missing_solution_env(task_data):
    for env_name in REQUIRED_SOLUTION_ENV_VARS:
        if not (os.getenv(env_name) or "").strip():
            task_data["missing_env_name"] = env_name
            raise ValueError(f"{env_name} is missing")


def run_grounded_answering(task_data, flow_id):
    answer_result = AnswerResult(status=ANSWER_STATUS_REFUSED, answer="", citations=[])
    with TelemetryRepository.start_span(TELEMETRY_WORKFLOW_OPERATION_NAME, TELEMETRY_WORKFLOW_NAME, flow_id, task_data) as workflow_span:
        task_data["trace_id"] = LoggingRepository.current_trace_id()
        LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
        try:
            raise_if_missing_solution_env(task_data)
            graph_state = build_grounded_answering_graph(task_data, flow_id).invoke({"question": task_data["question"], "messages": [HumanMessage(task_data["question"])], "evidence": [], "prior_queries": [], "sub_questions": [], "gather_count": 0, "tool_count": 0, "grade_verdict": None, "grade_note": None, "answer_result": None}, {"recursion_limit": GROUNDED_ANSWERING_RECURSION_LIMIT, "metadata": {"flow_id": flow_id}})
            answer_result = graph_state.get("answer_result") or AnswerResult(status=ANSWER_STATUS_REFUSED, answer="", citations=[])
            task_data["answer_result"] = answer_result.model_dump()
            TelemetryRepository.record_output(workflow_span, task_data)
        except Exception as err:
            if isinstance(err, GraphInterrupt):
                TelemetryRepository.add_event("workflow_interrupt", {"error_type": type(err).__name__})
                raise
            TelemetryRepository.record_error(workflow_span, err)
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return answer_result.model_dump()
