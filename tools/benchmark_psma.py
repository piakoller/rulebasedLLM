#!/usr/bin/env python3
"""Benchmark PSMA: baseline vs full pipeline.

For each question in data/psma_sample_questions.json this script:
- Calls the baseline system prompt (concise clinical replies) using the same LLM model.
- Calls the full pipeline (`AgentEngine`) with the same model.
- Records graph verification and RAG retrievals.
- Saves results to `results/psma_benchmark.json`.
"""
import json
from pathlib import Path
import sys
import requests

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "core"))

from test_empathy_with_llm import OLLAMA_MODEL, OLLAMA_URL
import baseline_medgemma
import graph_rag
from core.agent_engine import AgentEngine
from rules import detect_language

OUT = Path("results/psma_benchmark.json")
QUESTIONS_FILE = Path("data/psma_sample_questions.json")
VECTOR_STORE = Path("data/vector_store_psma")
TIMEOUT = 180


def call_llm_model(model: str, messages: list[dict]) -> str:
    payload = {"model": model, "messages": messages, "stream": False}
    resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")


def load_questions(path: Path) -> list[tuple[str,str]]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    out = []
    for category, qs in data.items():
        for q in qs:
            out.append((q, category))
    return out


def baseline_reply(question: str) -> str:
    messages = [
        {"role": "system", "content": baseline_medgemma.SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    return call_llm_model(OLLAMA_MODEL, messages)


def main():
    questions = load_questions(QUESTIONS_FILE)
    results = {"model": OLLAMA_MODEL, "rows": []}

    agent = AgentEngine(model=OLLAMA_MODEL)

    for i, (q, cat) in enumerate(questions, start=1):
        row = {"index": i, "category": cat, "question": q}
        try:
            row["baseline_response"] = baseline_reply(q)
        except Exception as e:
            row["baseline_error"] = str(e)

        try:
            # reset agent state per question for fairness
            agent = AgentEngine(model=OLLAMA_MODEL)
            frame_resp = agent.handle_message(q)
            row["pipeline_response"] = frame_resp.model_dump()
        except Exception as e:
            row["pipeline_error"] = str(e)

        # Graph facts and rag retrievals
        try:
            fact = graph_rag.get_knowledge_graph_fact(q)
            row["graph_fact"] = {
                "entities": fact.entities,
                "verified": bool(fact.verified),
                "answer": fact.answer,
                "evidence": fact.evidence,
            }
        except Exception as e:
            row["graph_fact_error"] = str(e)

        try:
            rag = graph_rag.retrieve_similar_documents(q, top_k=5, outdir=VECTOR_STORE)
            row["rag_results"] = rag
        except Exception as e:
            row["rag_error"] = str(e)

        results["rows"].append(row)
        print(f"Processed {i}/{len(questions)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print(f"Saved benchmark to {OUT}")


if __name__ == "__main__":
    main()
