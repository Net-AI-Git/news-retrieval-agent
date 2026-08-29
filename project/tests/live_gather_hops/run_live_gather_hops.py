import csv
import json
from datetime import datetime
from pathlib import Path
from time import sleep
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.agents.gather_agent import run_gather


METRIC_FIELDNAMES = ["question_id", "gold_hop_count", "agent_hop_count", "missing_gold", "packed_needs", "packed_outlets", "extra_hops", "featured_in_hops", "misattached_outlet", "dates_missing", "prompt_leak_hit", "hop_success", "failure_class", "agent_sub_questions", "runtime_error"]
HOP_FIELDNAMES = ["question_id", "hop_index", "gold_source", "gold_question", "matched_agent_index", "matched_agent_text", "source_in_text", "date_in_text", "covered"]
CALL_FIELDNAMES = ["question_id", "hop_index", "sub_question", "gold_match_index", "is_extra", "is_featured_in", "packed_outlets_in_string"]
LIVE_GATHER_PAUSE_SECONDS = 8
LEAK_SKIP_ANSWERS = {"yes", "no", "insufficient information"}
LEAK_MIN_CHARS = 24
STOPWORDS = {"that", "this", "with", "from", "about", "which", "their", "them", "they", "were", "been", "have", "does", "did", "what", "when", "who", "whom", "also", "both", "into", "over", "than", "then", "article", "articles", "report", "reported", "according", "considering", "information", "mentioned", "another", "known"}
SOURCE_ALIASES = {"new york times": ["nyt"], "the new york times": ["nyt", "new york times"], "wall street journal": ["wsj"], "the wall street journal": ["wsj", "wall street journal"], "bbc news": ["bbc"]}
FEATURED_NEEDLES = ("featured in", "featured by", "feature articles", "has been featured")


def add_exam_needle(needles, text):
    value = " ".join((text or "").split())
    if len(value) < LEAK_MIN_CHARS or value.lower() in LEAK_SKIP_ANSWERS:
        return
    if value not in needles:
        needles.append(value)


def exam_needles_from_ground_truth(question_data, ground_truth):
    needles = []
    add_exam_needle(needles, question_data.get("question"))
    add_exam_needle(needles, ground_truth.get("answer"))
    for item in (ground_truth.get("facts") or []) + (ground_truth.get("citations") or []):
        add_exam_needle(needles, item.get("fact") or item.get("snippet"))
        add_exam_needle(needles, item.get("article_title"))
        add_exam_needle(needles, item.get("url"))
    for sub_question in ground_truth.get("sub_questions") or []:
        add_exam_needle(needles, sub_question)
    for call in ground_truth.get("expected_tool_calls") or []:
        add_exam_needle(needles, (call.get("arguments") or {}).get("question"))
    return needles


def collect_exam_needles(project_root, questions):
    needles = []
    for question_data in questions:
        for needle in exam_needles_from_ground_truth(question_data, load_ground_truth(project_root, question_data)):
            add_exam_needle(needles, needle)
    return needles


def prompt_leak_hit(prompt_text, needles):
    for needle in needles:
        if needle in prompt_text:
            return 1
    return 0


def normalize_text(text):
    return " ".join((text or "").lower().split())


def load_ground_truth(project_root, question_data):
    ground_truth = json.loads((project_root / "src" / "data" / "ground_truth" / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    if ground_truth["id"] != question_data["id"] or ground_truth["question"] != question_data["question"]:
        raise ValueError(f"Ground truth mismatch for {question_data['id']}")
    return ground_truth


def retrieve_arguments(ground_truth, hop_index):
    for item in ground_truth.get("expected_tool_calls") or []:
        if item.get("agent") == "retrieve" and item.get("sub_question_index") == hop_index:
            arguments = item.get("arguments")
            if isinstance(arguments, dict):
                return arguments
    raise ValueError(f"Ground truth {ground_truth.get('id')} sub_question {hop_index} has no retrieve expected_tool_call")


def gold_hops(ground_truth):
    hops = []
    sub_questions = [text.strip() for text in (ground_truth.get("sub_questions") or []) if (text or "").strip()]
    if not sub_questions:
        raise ValueError(f"Ground truth {ground_truth.get('id')} has no sub_questions")
    for hop_index, sub_question in enumerate(sub_questions, start=1):
        arguments = retrieve_arguments(ground_truth, hop_index)
        hops.append({"question": sub_question, "source": arguments.get("source") or "", "published_from": arguments.get("published_from") or "", "published_to": arguments.get("published_to") or ""})
    return hops


def content_tokens(text):
    tokens = set()
    for raw in normalize_text(text).replace("'", " ").split():
        token = "".join(character for character in raw if character.isalnum())
        if len(token) >= 4 and token not in STOPWORDS:
            tokens.add(token)
    return tokens


def folded_text(text):
    stripped = []
    for character in (text or "").lower():
        stripped.append(character if character.isalnum() or character.isspace() else " ")
    return " ".join("".join(stripped).split())


def source_needles(source):
    cleaned = folded_text(source)
    needles = [cleaned]
    if cleaned.startswith("the "):
        needles.append(cleaned[4:])
    for alias in SOURCE_ALIASES.get(cleaned) or []:
        if alias not in needles:
            needles.append(alias)
    return needles


def source_in_text(text, source):
    if not source:
        return False
    haystack = f" {folded_text(text)} "
    for needle in source_needles(source):
        if needle and f" {needle} " in haystack:
            return True
    return False


def date_in_text(text, published_from):
    if not published_from:
        return True
    parsed = datetime.fromisoformat(published_from)
    haystack = normalize_text(text)
    day = str(parsed.day)
    if parsed.strftime("%Y-%m-%d") in haystack:
        return True
    if parsed.strftime("%B").lower() in haystack and day in haystack:
        return True
    if parsed.strftime("%b").lower() in haystack and day in haystack:
        return True
    return False


def unique_markers(hops):
    token_lists = []
    for gold_hop in hops:
        token_lists.append(content_tokens(gold_hop["question"]) - content_tokens(gold_hop["source"]))
    uniques = []
    for index, tokens in enumerate(token_lists):
        others = set()
        for other_index, other_tokens in enumerate(token_lists):
            if other_index != index:
                others |= other_tokens
        uniques.append(tokens - others)
    return uniques


def hop_covers(agent_text, gold_hop, unique_tokens):
    if gold_hop["source"] and not source_in_text(agent_text, gold_hop["source"]):
        return False
    agent_tokens = content_tokens(agent_text)
    if unique_tokens:
        overlap = agent_tokens & unique_tokens
        if len(unique_tokens) >= 2:
            return len(overlap) >= 2
        return bool(overlap)
    if gold_hop["source"]:
        return True
    return len(agent_tokens & content_tokens(gold_hop["question"])) >= 2


def assign_matches(hops, agent_hops, uniques):
    pairs = []
    for gold_index, gold_hop in enumerate(hops):
        for agent_index, agent_text in enumerate(agent_hops):
            if hop_covers(agent_text, gold_hop, uniques[gold_index]):
                pairs.append((len(content_tokens(agent_text) & content_tokens(gold_hop["question"])), gold_index, agent_index))
    pairs.sort(reverse=True)
    matched = {}
    used_gold = set()
    used_agent = set()
    for pair in pairs:
        if pair[1] in used_gold or pair[2] in used_agent:
            continue
        matched[pair[1]] = pair[2]
        used_gold.add(pair[1])
        used_agent.add(pair[2])
    return matched


def gold_source_list(hops):
    sources = []
    for gold_hop in hops:
        source = gold_hop.get("source") or ""
        if source and source not in sources:
            sources.append(source)
    return sources


def packed_outlet_count(hops, agent_hops):
    packed = 0
    sources = gold_source_list(hops)
    for agent_text in agent_hops:
        hits = 0
        for source in sources:
            if source_in_text(agent_text, source):
                hits += 1
        if hits >= 2:
            packed += 1
    return packed


def packed_need_count(hops, agent_hops, uniques):
    packed = 0
    for agent_text in agent_hops:
        hits = 0
        for gold_index, gold_hop in enumerate(hops):
            if hop_covers(agent_text, gold_hop, uniques[gold_index]):
                hits += 1
        if hits >= 2:
            packed += 1
    return packed


def is_featured_in(text):
    haystack = normalize_text(text)
    for needle in FEATURED_NEEDLES:
        if needle in haystack:
            return True
    return False


def featured_only_count(hops, agent_hops, uniques):
    featured = 0
    for agent_text in agent_hops:
        if not is_featured_in(agent_text):
            continue
        covered = False
        for gold_index, gold_hop in enumerate(hops):
            if hop_covers(agent_text, gold_hop, uniques[gold_index]):
                covered = True
        if not covered:
            featured += 1
    return featured


def misattached_count(hops, agent_hops, uniques):
    scoped = []
    sources = gold_source_list(hops)
    for source in sources:
        hop_count = 0
        for gold_hop in hops:
            if normalize_text(gold_hop.get("source") or "") == normalize_text(source):
                hop_count += 1
        if 0 < hop_count < len(hops):
            scoped.append(source)
    attached = 0
    for agent_text in agent_hops:
        agent_tokens = content_tokens(agent_text)
        for source in scoped:
            if not source_in_text(agent_text, source):
                continue
            for gold_index, gold_hop in enumerate(hops):
                if normalize_text(gold_hop.get("source") or "") == normalize_text(source):
                    continue
                if uniques[gold_index] and len(agent_tokens & uniques[gold_index]) >= min(2, len(uniques[gold_index])):
                    attached += 1
    return attached


def missing_date_count(hops, agent_hops, matched):
    missing = 0
    for gold_index, gold_hop in enumerate(hops):
        if not gold_hop.get("published_from"):
            continue
        agent_index = matched.get(gold_index)
        text = agent_hops[agent_index] if agent_index is not None else ""
        if not date_in_text(text, gold_hop["published_from"]):
            missing += 1
    return missing


def classify_failure(row):
    if row["prompt_leak_hit"]:
        return "leak"
    if row["runtime_error"]:
        return "runtime_error"
    if row["packed_outlets"]:
        return "packed_outlets"
    if row["packed_needs"]:
        return "packed_needs"
    if row["featured_in_hops"]:
        return "featured_in"
    if row["misattached_outlet"]:
        return "misattached_outlet"
    if row["missing_gold"]:
        return "missing_gold"
    if row["extra_hops"]:
        return "extra_hops"
    if row["dates_missing"]:
        return "dates_missing"
    return ""


def hop_success(row):
    if row["prompt_leak_hit"] or row["runtime_error"]:
        return 0
    if row["packed_outlets"] or row["packed_needs"] or row["missing_gold"] or row["extra_hops"]:
        return 0
    if row["featured_in_hops"] or row["misattached_outlet"] or row["dates_missing"]:
        return 0
    return 1


def empty_score(question_id, hops, leak_hit, runtime_error):
    row = {"question_id": question_id, "gold_hops": hops, "agent_hops": [], "matched": {}, "gold_hop_count": len(hops), "agent_hop_count": 0, "missing_gold": len(hops), "packed_needs": 0, "packed_outlets": 0, "extra_hops": 0, "featured_in_hops": 0, "misattached_outlet": 0, "dates_missing": 0, "prompt_leak_hit": leak_hit, "runtime_error": runtime_error, "uniques": unique_markers(hops)}
    row["failure_class"] = classify_failure(row)
    row["hop_success"] = hop_success(row)
    return row


def score_inventory(question_id, hops, agent_hops, leak_hit):
    uniques = unique_markers(hops)
    matched = assign_matches(hops, agent_hops, uniques)
    row = {"question_id": question_id, "gold_hops": hops, "agent_hops": agent_hops, "matched": matched, "uniques": uniques, "gold_hop_count": len(hops), "agent_hop_count": len(agent_hops), "missing_gold": len(hops) - len(matched), "packed_needs": packed_need_count(hops, agent_hops, uniques), "packed_outlets": packed_outlet_count(hops, agent_hops), "extra_hops": len(agent_hops) - len(set(matched.values())), "featured_in_hops": featured_only_count(hops, agent_hops, uniques), "misattached_outlet": misattached_count(hops, agent_hops, uniques), "dates_missing": missing_date_count(hops, agent_hops, matched), "prompt_leak_hit": leak_hit, "runtime_error": ""}
    row["failure_class"] = classify_failure(row)
    row["hop_success"] = hop_success(row)
    return row


def evaluate_question(project_root, question_data, leak_hit):
    hops = gold_hops(load_ground_truth(project_root, question_data))
    try:
        return score_inventory(question_data["id"], hops, [text.strip() for text in (run_gather({"question": question_data["question"], "prior_queries": [], "grade_note": ""}, str(uuid4())).sub_questions or []) if (text or "").strip()], leak_hit)
    except Exception as err:
        return empty_score(question_data["id"], hops, leak_hit, repr(err))


def evaluate_all_questions(project_root, questions, leak_hit):
    rows = []
    for question_data in questions:
        if rows:
            sleep(LIVE_GATHER_PAUSE_SECONDS)
        rows.append(evaluate_question(project_root, question_data, leak_hit))
    return rows


def gold_match_index(row, agent_index):
    for gold_index, matched_index in row["matched"].items():
        if matched_index == agent_index:
            return gold_index + 1
    return ""


def hop_csv_rows(rows):
    csv_rows = []
    for row in rows:
        for hop_index, gold_hop in enumerate(row.get("gold_hops") or [], start=1):
            agent_index = row.get("matched", {}).get(hop_index - 1)
            agent_text = (row.get("agent_hops") or [])[agent_index] if agent_index is not None else ""
            csv_rows.append({"question_id": row["question_id"], "hop_index": hop_index, "gold_source": gold_hop.get("source") or "", "gold_question": gold_hop.get("question") or "", "matched_agent_index": "" if agent_index is None else agent_index + 1, "matched_agent_text": agent_text, "source_in_text": int(not gold_hop.get("source") or source_in_text(agent_text, gold_hop.get("source") or "")), "date_in_text": int(date_in_text(agent_text, gold_hop.get("published_from") or "")), "covered": int(agent_index is not None)})
    return csv_rows


def call_csv_rows(rows):
    csv_rows = []
    for row in rows:
        sources = gold_source_list(row.get("gold_hops") or [])
        for hop_index, agent_text in enumerate(row.get("agent_hops") or [], start=1):
            outlet_hits = 0
            for source in sources:
                if source_in_text(agent_text, source):
                    outlet_hits += 1
            csv_rows.append({"question_id": row["question_id"], "hop_index": hop_index, "sub_question": agent_text, "gold_match_index": gold_match_index(row, hop_index - 1), "is_extra": int((hop_index - 1) not in set((row.get("matched") or {}).values())), "is_featured_in": int(is_featured_in(agent_text)), "packed_outlets_in_string": int(outlet_hits >= 2)})
    return csv_rows


def metric_csv_row(row):
    return {"question_id": row["question_id"], "gold_hop_count": row["gold_hop_count"], "agent_hop_count": row["agent_hop_count"], "missing_gold": row["missing_gold"], "packed_needs": row["packed_needs"], "packed_outlets": row["packed_outlets"], "extra_hops": row["extra_hops"], "featured_in_hops": row["featured_in_hops"], "misattached_outlet": row["misattached_outlet"], "dates_missing": row["dates_missing"], "prompt_leak_hit": row["prompt_leak_hit"], "hop_success": row["hop_success"], "failure_class": row["failure_class"], "agent_sub_questions": " | ".join(row.get("agent_hops") or []), "runtime_error": row["runtime_error"]}


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(output_directory, timestamp, rows):
    stamp = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    write_csv(output_directory / f"metrics_{stamp}.csv", METRIC_FIELDNAMES, [metric_csv_row(row) for row in rows])
    write_csv(output_directory / f"hops_{stamp}.csv", HOP_FIELDNAMES, hop_csv_rows(rows))
    write_csv(output_directory / f"calls_{stamp}.csv", CALL_FIELDNAMES, call_csv_rows(rows))


def main():
    project_root = Path(__file__).resolve().parents[2]
    questions = json.loads((project_root / "src" / "data" / "questions.json").read_text(encoding="utf-8"))
    leak_hit = prompt_leak_hit((project_root / "src" / "prompts" / "gather_agent.md").read_text(encoding="utf-8"), collect_exam_needles(project_root, questions))
    write_outputs(Path(__file__).resolve().parent / "outputs", datetime.now().astimezone(), evaluate_all_questions(project_root, questions, leak_hit))


if __name__ == "__main__":
    main()
