from pathlib import Path
import json

prompt = Path("src/prompts/gather_agent.md").read_text(encoding="utf-8")
lines = prompt.strip().splitlines()
print("lines", len(lines))
print("words", len(prompt.split()))
print("has_identity", prompt.startswith("# Identity"))
print("has_instructions", "# Instructions" in prompt)
print("has_examples", "# Examples" in prompt)
print("has_context", "# Context" in prompt)
old = ["[INSTRUCTIONS]", "[DEFINITIONS]", "ROLE:", "TASK:", "RULES:", "CONFIDENCE SCORE", "[EXAMPLE 01]", "RESPONSE FORMAT"]
print("old_template", [item for item in old if item in prompt])
questions = json.loads(Path("src/data/questions.json").read_text(encoding="utf-8"))
needles = []

def add(text):
    value = " ".join((text or "").split())
    if len(value) >= 24 and value.lower() not in {"yes", "no", "insufficient information"} and value not in needles:
        needles.append(value)

for question_data in questions:
    ground_truth = json.loads((Path("src/data/ground_truth") / f"{question_data['id']}.json").read_text(encoding="utf-8"))
    add(question_data.get("question"))
    add(ground_truth.get("answer"))
    for item in (ground_truth.get("facts") or []) + (ground_truth.get("citations") or []):
        add(item.get("fact") or item.get("snippet"))
        add(item.get("article_title"))
        add(item.get("url"))
    for sub_question in ground_truth.get("sub_questions") or []:
        add(sub_question)
    for call in ground_truth.get("expected_tool_calls") or []:
        add((call.get("arguments") or {}).get("question"))

hits = [needle for needle in needles if needle in prompt]
print("leak_hits", len(hits))
for hit in hits:
    print("LEAK", hit[:120])

tokens = ["Sporting News", "Dallas Cowboys", "Seahawks", "Flipboard", "ActivityPub", "FTX", "Caroline Ellison", "Jane Street", "Pets Best", "Wall Street Journal", "anticompetitive", "Aboriginal", "ChatGPT", "Engadget", "Zermatt", "Tremblant", "Forerunner", "Gemini", "DeepMind", "TechCrunch", "The Verge", "The Age", "The Guardian", "New York Times", "BBC News", "Forbes", "OpenAI", "Microsoft"]
print("lookalike_tokens", [token for token in tokens if token.lower() in prompt.lower()])
