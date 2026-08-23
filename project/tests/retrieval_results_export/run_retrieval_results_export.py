import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.services.retrieval_service import run_retrieval


def format_results_section(section_title, results):
    lines = [f"## {section_title} ({len(results)})", ""]
    if not results:
        return lines + ["No relevant evidence returned.", ""]
    for rank, result in enumerate(results, start=1):
        lines.extend([f"### {rank}. {result['article_title']}", "", f"- Match: {result['match_percentage']:.2f}%", f"- Published at: {result['published_at'] or 'Not available'}", f"- URL: {result['url'] or 'Not available'}", "", result["snippet"], ""])
    return lines


def build_markdown(question_data, retrieval_result, timestamp):
    lines = [f"# {question_data['id']} Retrieval Results", "", f"- Timestamp: {timestamp.isoformat(timespec='seconds')}", f"- Status: {retrieval_result['status']}", "", "## Query", "", question_data["question"], ""]
    lines.extend(format_results_section("Facts", retrieval_result["facts"]))
    lines.extend(format_results_section("Corpus", retrieval_result["corpus"]))
    return "\n".join(lines)


def run_export(project_root, questions, output_directory, timestamp):
    output_directory.mkdir(parents=True, exist_ok=True)
    for question_data in questions:
        task_data = {"question": question_data["question"], "facts_chroma_path": str(project_root / "vector_stores" / "facts_chroma"), "corpus_chroma_path": str(project_root / "vector_stores" / "corpus_chroma")}
        retrieval_result = run_retrieval(task_data, str(uuid4()))
        output_path = output_directory / f"{question_data['id']}_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.md"
        output_path.write_text(build_markdown(question_data, retrieval_result, timestamp), encoding="utf-8")


def main():
    project_root = Path(__file__).resolve().parents[2]
    with (project_root / "src" / "data" / "questions.json").open(encoding="utf-8") as questions_file:
        questions = json.load(questions_file)
    run_export(project_root, questions, Path(__file__).resolve().parent / "outputs", datetime.now().astimezone())


if __name__ == "__main__":
    main()
