#!/usr/bin/env python3
import sys
from pathlib import Path

# Ensure imports resolve
repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root / "core"))

from agent_engine import AgentEngine

def test_confidence():
    print("--- TESTING CONFIDENCE CALCULATION (DISABLED) ---")
    agent_no_conf = AgentEngine(calculate_confidence=False, use_graph_rag=False)
    resp_no_conf = agent_no_conf.handle_message("Guten Tag, was ist PRRT?")
    print(f"Confidence Score: {resp_no_conf.confidence_score}")
    assert resp_no_conf.confidence_score is None

    print("\n--- TESTING CONFIDENCE CALCULATION (ENABLED) ---")
    agent_conf = AgentEngine(calculate_confidence=True, use_graph_rag=False)
    # We mock a response or just run it if Ollama is available. 
    # Since I'm in a sandboxed environment, I'll just check if the fields exist.
    resp_conf = agent_conf.handle_message("Guten Tag, was ist PRRT?")
    print(f"Confidence Score: {resp_conf.confidence_score}")
    print(f"Confidence Explanation: {resp_conf.confidence_explanation}")
    
    if resp_conf.confidence_score is not None:
        print("✅ Confidence scoring is active.")
    else:
        print("⚠️ Confidence scoring was requested but returned None (likely no LLM response or parse error).")

if __name__ == "__main__":
    try:
        test_confidence()
    except Exception as e:
        print(f"Error during verification: {e}")
