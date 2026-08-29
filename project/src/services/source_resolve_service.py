from ..conts import SOURCE_RESOLVE_MIN_MARGIN, SOURCE_RESOLVE_MIN_SIMILARITY
from ..repositories.embeddings_repository import OpenAIEmbeddingsRepository
from ..repositories.facts_chroma_repository import FactsChromaRepository
from ..repositories.logging_repository import LoggingRepository


def exact_source_match(task_data, catalog):
    source_query = (task_data.get("source") or "").strip()
    if not source_query or not catalog:
        return None
    for item in catalog.get("sources") or []:
        if " ".join((item.get("name") or "").lower().split()) == " ".join(source_query.lower().split()):
            return item["name"]
    return None


def unique_substring_source(task_data, catalog):
    source_query = (task_data.get("source") or "").strip()
    if not source_query or not catalog:
        return None
    substring_matches = []
    for item in catalog.get("sources") or []:
        if " ".join(source_query.lower().split()) in " ".join((item.get("name") or "").lower().split()):
            substring_matches.append(item["name"])
    if len(substring_matches) == 1:
        return substring_matches[0]
    return None


def ranked_source_scores(task_data, catalog, flow_id):
    source_query = (task_data.get("source") or "").strip()
    if not source_query or not catalog:
        return []
    needle = " ".join(source_query.lower().split())
    substring_items = [item for item in catalog.get("sources") or [] if needle in " ".join((item.get("name") or "").lower().split())]
    embeddings = OpenAIEmbeddingsRepository.generate_embeddings({**task_data, "texts": [source_query]}, flow_id)
    scored_names = []
    if not embeddings:
        return scored_names
    for item in substring_items or catalog.get("sources") or []:
        dot_product = 0.0
        left_square_sum = 0.0
        right_square_sum = 0.0
        for left_value, right_value in zip(embeddings[0], item["embedding"]):
            dot_product += left_value * right_value
            left_square_sum += left_value * left_value
            right_square_sum += right_value * right_value
        if not left_square_sum or not right_square_sum:
            scored_names.append((0.0, item["name"]))
            continue
        scored_names.append((dot_product / ((left_square_sum ** 0.5) * (right_square_sum ** 0.5)), item["name"]))
    scored_names.sort(key=lambda row: row[0], reverse=True)
    return scored_names


def accepted_source_name(scored_names):
    if not scored_names:
        return None
    top_score = scored_names[0][0]
    if top_score < SOURCE_RESOLVE_MIN_SIMILARITY:
        return None
    if len(scored_names) > 1 and top_score - scored_names[1][0] < SOURCE_RESOLVE_MIN_MARGIN:
        return None
    return scored_names[0][1]


def run_resolve_source(task_data, flow_id):
    LoggingRepository.log_event(status="STARTING", content=task_data, flow_id=flow_id, level="INFO")
    resolved_source = None
    try:
        catalog = FactsChromaRepository.read_source_catalog({**task_data, "chroma_path": task_data["facts_chroma_path"]}, flow_id)
        resolved_source = exact_source_match(task_data, catalog)
        if not resolved_source:
            resolved_source = unique_substring_source(task_data, catalog)
        if not resolved_source:
            scored_names = ranked_source_scores(task_data, catalog, flow_id)
            resolved_source = accepted_source_name(scored_names)
    except Exception as err:
        LoggingRepository.log_event(status="ERROR", content={"error": repr(err), "task_data": task_data}, flow_id=flow_id, level="ERROR")
    LoggingRepository.log_event(status="FINISHED", content=task_data, flow_id=flow_id, level="INFO")
    return resolved_source
