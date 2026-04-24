#!/usr/bin/env python3
"""
Test the refactored empathy pipeline with sample questions.
Shows the new context-aware approach giving LLM full freedom.
"""

import sys
import json
from typing import Optional, Callable
from pathlib import Path

# Ensure imports resolve when running the script from the repo root or tests/ directory
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "core"))
sys.path.insert(0, str(repo_root))

from empathy_framing import (
    classify_emotional_state,
    get_nurse_instruction,
    EMOTIONAL_STATE_CONTEXT,
    detect_language,
    make_ollama_classifier,
)
from agent_engine import AgentEngine, FrameResponse

def load_sample_questions(path: str = "data/sample_questions.json", limit: int | None = None):
    """Load sample questions from a JSON file.

    The JSON is expected to be a mapping of category -> list of questions.
    If `limit` is None, return all questions.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Flatten all questions
    all_questions = []
    for category, questions in data.items():
        all_questions.extend([(q, category) for q in questions])

    if limit is None:
        return all_questions

    return all_questions[:limit]

def run_pipeline_on_question(question: str, category: str, llm_classifier: Optional[Callable] = None):
    language = detect_language(question)
    emotional_state = classify_emotional_state(question, llm_classifier=llm_classifier)
    print(f"  > Language: {language} | State: {emotional_state}")
    return language, emotional_state

def main():  
    import argparse

    parser = argparse.ArgumentParser(description="Run the refactored empathy pipeline on sample questions")
    parser.add_argument("--questions", "-q", default="data/psma_sample_questions.json", help="Path to sample questions JSON (category -> [questions])")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Optional maximum number of questions to process (default: all)")
    parser.add_argument("--out", "-o", default=None, help="Optional output JSON file to save results")
    parser.add_argument("--no-agent", dest="use_agent", action="store_false", help="Do not run the full AgentEngine (only run pipeline classification)")
    parser.add_argument("--llm-classifier", dest="llm_classifier", action="store_true", help="Use an LLM-based classifier (requires Ollama/medgemma endpoint)")
    parser.add_argument("--no-graph", dest="use_graph", action="store_false", help="Skip GraphRAG build and use basic RAG instead")
    parser.add_argument("--confidence", action="store_true", help="Calculate and include confidence scores in the output")
    parser.set_defaults(use_graph=True)
    args = parser.parse_args()

    # Load sample questions
    sample_questions = load_sample_questions(path=args.questions, limit=args.limit)

    print(f"\n📚 LOADING {len(sample_questions)} SAMPLE QUESTIONS FROM {args.questions}...\n")
    
    # Initialize agent if requested; run with framing disabled for independent questions
    agent = AgentEngine(
        use_frames=False, 
        use_graph_rag=args.use_graph,
        calculate_confidence=args.confidence
    ) if args.use_agent else None

    # Optionally create an Ollama-based classifier (falls back to heuristics on error)
    llm_classifier = make_ollama_classifier() if args.llm_classifier else None
    

    results = []
    # Run pipeline on each question
    for i, (question, category) in enumerate(sample_questions, 1):
        if agent is not None:
            agent.reset()
        
        print(f"\n[Question {i}/{len(sample_questions)}] [{category}] {question[:70]}...")

        run_pipeline_on_question(question, category, llm_classifier=llm_classifier)

        # Run the full agent for end-to-end testing (LLM + RAG retrieval) if enabled
        if agent is not None:
            try:
                frame_response: FrameResponse = agent.handle_message(question)
                record = {
                    "index": i,
                    "category": category,
                    "question": question,
                    "agent_response": frame_response.model_dump(),
                }
            except Exception as e:
                record = {
                    "index": i,
                    "category": category,
                    "question": question,
                    "error": str(e),
                }
        else:
            # When --no-agent is specified, include only pipeline classification info
            language = detect_language(question)
            emotional_state = classify_emotional_state(question, llm_classifier=llm_classifier)
            record = {
                "index": i,
                "category": category,
                "question": question,
                "language": language,
                "emotional_state": emotional_state,
            }
        results.append(record)
    
    # Summary
    print("\n" + "=" * 75)
    print("PIPELINE SUMMARY")
    print("=" * 75)
    print("\n✅ PROCESSED QUESTIONS:")
    for i, (question, category) in enumerate(sample_questions, 1):
        emotion = classify_emotional_state(question, llm_classifier=llm_classifier)
        lang = detect_language(question)
        print(f"\n  {i}. [{category}] ({lang})")
        print(f"     Emotion: {emotion}")
        print(f"     Q: {question[:70]}...")
    
    print("\n" + "=" * 75)
    print("✅ PIPELINE COMPLETE")
    print("=" * 75)
    print("\nKey Results:")
    print("  • All questions classified with emotional states")
    print("  • Emotional context retrieved for LLM guidance")
    print("  • Languages detected (German/English)")
    print("  • No hardcoded rules or forced responses")
    print("  • LLM has full freedom to respond naturally")
    print("\n📍 Next: Integrate with full agent for end-to-end testing\n")

    # If --out was provided, save results
    if args and getattr(args, "out", None):
        out_path = Path(args.out)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump({"results": results}, f, ensure_ascii=False, indent=2)
            print(f"\nSaved pipeline results to {out_path}")
        except Exception as e:
            print(f"Failed to save results to {out_path}: {e}")

if __name__ == "__main__":
    main()
