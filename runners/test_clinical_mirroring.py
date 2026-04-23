#!/usr/bin/env python3
import sys
from pathlib import Path
import json

# Ensure imports resolve
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "core"))
sys.path.insert(0, str(repo_root))

from core.agent_engine import AgentEngine
from core.empathy_framing import STRATEGY_SENTENCE_STARTERS

TEST_CASES = [
    {
        "name": "Technical Overwhelm (German)",
        "question": "Das ist alles so kompliziert. Was bedeutet dieser PSA-Wert eigentlich genau? Ich verstehe die ganzen Abkürzungen nicht.",
        "expected_emotion": "technical_overwhelm"
    },
    {
        "name": "Emotional Anxiety (English)",
        "question": "I'm so worried about the side effects of PSMA therapy. Is it going to be painful? I'm scared for my quality of life.",
        "expected_emotion": "anxiety"
    },
    {
        "name": "Frustration with Wait Times",
        "question": "I've been waiting for my results for two weeks. This is unacceptable! Why is it taking so long?",
        "expected_emotion": "frustration"
    }
]

def run_mirroring_test():
    print("=" * 80)
    print("CLINICAL MIRRORING METHOD TEST")
    print("=" * 80)
    
    agent = AgentEngine(use_frames=True)
    
    for case in TEST_CASES:
        print(f"\n--- TEST CASE: {case['name']} ---")
        print(f"User: {case['question']}")
        
        # We use handle_message_for_study to see if revisions occurred
        comparison = agent.handle_message_for_study(case["question"])
        
        print(f"\nOriginal thinking block snippet:")
        thinking = comparison.original_draft.filled_slots.get("thinking", "N/A")
        print(f"  {thinking[:200]}...")
        
        print(f"\nRevision Occurred: {comparison.revision_occurred}")
        if comparison.revision_occurred:
            print(f"Reason: {comparison.revision_reason}")
            
        print(f"\nFinal Response:")
        print(f"  {comparison.final_response.agent_response}")
        
        # Check for strategy starters (even if translated, we look for concepts)
        found_starter = False
        response_lowered = comparison.final_response.agent_response.lower()
        
        # Simple heuristic check for supportive language
        supportive_markers = ["understand", "makes sense", "sorry", "help", "verstehe", "sinn", "helfen"]
        if any(marker in response_lowered for marker in supportive_markers):
            found_starter = True
            
        print(f"\nEvaluation:")
        print(f"  - Empathy markers found: {'YES' if found_starter else 'NO'}")
        
        # Cleanup for next case
        agent.reset()

if __name__ == "__main__":
    run_mirroring_test()
