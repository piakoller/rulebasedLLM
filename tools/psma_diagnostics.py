#!/usr/bin/env python3
"""Run diagnostics for PSMA questions: graph facts and RAG retrievals.

Saves a JSON report to results/psma_diagnostics.json by default.
"""
import json
from pathlib import Path
import sys

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "core"))
sys.path.insert(0, str(repo_root))

import graph_rag

from tests.run_empathy_pipeline import load_sample_questions

OUT = Path("results/psma_diagnostics.json")
VECTOR_STORE = Path("data/vector_store_psma")


def main():
    questions = load_sample_questions(path="data/psma_sample_questions.json", limit=None)
    report = {"rows": []}
    for i, (q, category) in enumerate(questions, start=1):
        row = {"index": i, "category": category, "question": q}
        try:
            # Knowledge graph fact verification
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

        report["rows"].append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"Saved diagnostics to {OUT}")


if __name__ == "__main__":
    main()
