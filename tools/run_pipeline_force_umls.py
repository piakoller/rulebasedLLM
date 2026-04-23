#!/usr/bin/env python3
"""Run the empathy pipeline forcing UMLS verification before agent reply.

For each question this script:
- Extracts candidate medical terms
- Calls the ontology UMLS verification for those terms
- Prepends a formatted UMLS verification block to the user message so the agent sees verified facts
- Calls `AgentEngine.handle_message()` and saves results
"""
import json
from pathlib import Path
import sys

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "core"))

# Use same default model as tests/test_empathy_with_llm.py
OLLAMA_MODEL = "hf.co/unsloth/medgemma-27b-it-GGUF:Q4_K_M"
from core.agent_engine import AgentEngine
from core.umls_grounding import extract_medical_terms
import core.ontology_tool as ontology_tool

OUT = Path("results/psma_run_with_umls.json")
QUESTIONS_FILE = Path("data/psma_sample_questions.json")


def load_questions(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    out = []
    for category, qs in data.items():
        for q in qs:
            out.append((q, category))
    return out


def format_umls_for_agent(results: dict[str, ontology_tool.UMLSVerificationResult]) -> str:
    # Use ontology_tool.format_umls_verification_for_llm to produce readable block
    rlist = list(results.values())
    try:
        return ontology_tool.format_umls_verification_for_llm(rlist)
    except Exception:
        # Fallback simple text
        lines = ["UMLS Verification Results:"]
        for term, res in results.items():
            lines.append(f"- {term}: found={res.found}, cui={res.cui}")
        return "\n".join(lines)


def main():
    questions = load_questions(QUESTIONS_FILE)
    agent = AgentEngine(model=OLLAMA_MODEL)
    rows = []

    for i, (q, cat) in enumerate(questions, start=1):
        row = {"index": i, "category": cat, "question": q}

        # Extract terms and verify via ontology_tool
        terms = extract_medical_terms(q, language="de", max_terms=6)
        try:
            verif = ontology_tool.verify_multiple_relationships(terms)
            row["umls_verification"] = {t: {"found": bool(r.found), "cui": r.cui, "summary": r.summary[:400]} for t, r in verif.items()}
        except Exception as e:
            verif = {}
            row["umls_verification_error"] = str(e)

        # Prepare agent input with UMLS block
        umls_block = format_umls_for_agent(verif) if verif else "UMLS Verification: none"
        injected_message = f"{umls_block}\n\nUser question: {q}"

        try:
            frame_resp = agent.handle_message(injected_message)
            row["pipeline_response"] = frame_resp.model_dump()
        except Exception as e:
            row["pipeline_error"] = str(e)

        rows.append(row)
        print(f"Processed {i}/{len(questions)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        json.dump({"model": OLLAMA_MODEL, "rows": rows}, fh, ensure_ascii=False, indent=2)
    print(f"Saved results to {OUT}")


if __name__ == "__main__":
    main()
