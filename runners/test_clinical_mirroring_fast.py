#!/usr/bin/env python3
import sys
from pathlib import Path
import json

# Ensure imports resolve
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "core"))
sys.path.insert(0, str(repo_root))

from core.agent_engine import AgentEngine

TEST_CASES = [
    {
        "name": "Anxiety with PSMA",
        "question": "I'm worried about the Lutetium-177 therapy. Is it dangerous?",
    }
]

def run_fast_test():
    print("=" * 80)
    print("FAST CLINICAL MIRRORING TEST (FALLBACK GRAPH)")
    print("=" * 80)
    
    # Pass an empty list to document_roots to trigger fallback graph
    agent = AgentEngine(use_graph_rag=True, document_roots=[])
    
    for case in TEST_CASES:
        print(f"\n--- TEST CASE: {case['name']} ---")
        print(f"User: {case['question']}")
        
        # We use handle_message_for_study to see if revisions occurred
        comparison = agent.handle_message_for_study(case["question"])
        
        print(f"\nThinking block:")
        thinking = comparison.original_draft.filled_slots.get("thinking", "N/A")
        print(f"  {thinking}")
        
        print(f"\nRevision Occurred: {comparison.revision_occurred}")
        if comparison.revision_occurred:
            print(f"Reason: {comparison.revision_reason}")
            
        print(f"\nFinal Response:")
        print(f"  {comparison.final_response.agent_response}")
        
        agent.reset()

if __name__ == "__main__":
    run_fast_test()
