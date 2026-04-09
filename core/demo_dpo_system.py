#!/usr/bin/env python3
"""
Demo script showing how to use the DPO study system programmatically.
This is useful for batch processing or integration with other systems.
"""

import json
from pathlib import Path
from datetime import datetime
import random

from agent_engine import AgentEngine


def demo_single_question():
    """Demo 1: Process a single question and save the result."""
    print("\n" + "=" * 70)
    print("DEMO 1: Single Question Processing")
    print("=" * 70)
    
    # Initialize engine
    print("\nInitializing AgentEngine...")
    engine = AgentEngine(model="gemma3:27b")
    
    # Process a question
    question = "What are the most common side effects of targeted therapy?"
    print(f"\nQuestion: {question}")
    print("Generating responses...")
    
    try:
        comparison = engine.handle_message_for_study(question)
        
        print("\n✓ Successfully generated both versions:")
        print(f"  Original: {comparison.original_draft.agent_response[:80]}...")
        print(f"  Final: {comparison.final_response.agent_response[:80]}...")
        print(f"  Revision occurred: {comparison.revision_occurred}")
        if comparison.revision_reason:
            print(f"  Reason: {comparison.revision_reason}")
        
        # Save to study data
        study_data_path = Path("study_data.jsonl")
        
        # Randomly assign to A/B
        if random.random() < 0.5:
            answer_a = comparison.original_draft.agent_response
            answer_b = comparison.final_response.agent_response
            original_is_a = True
        else:
            answer_a = comparison.final_response.agent_response
            answer_b = comparison.original_draft.agent_response
            original_is_a = False
        
        # Simulate a preference (in real usage, this would be user input)
        user_preference = "A" if random.random() < 0.5 else "B"
        
        # Create entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer_a": answer_a,
            "answer_b": answer_b,
            "original_draft": "A" if original_is_a else "B",
            "user_preference": user_preference,
            "preference_matches_original": ("A" if original_is_a else "B") == user_preference,
        }
        
        # Save
        with open(study_data_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        print(f"\n✓ Saved to {study_data_path}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("Make sure Ollama is running: ollama serve")


def demo_batch_processing():
    """Demo 2: Process multiple questions in batch mode."""
    print("\n" + "=" * 70)
    print("DEMO 2: Batch Processing")
    print("=" * 70)
    
    # Sample questions (you would load these from a file or database)
    questions = [
        "What is targeted therapy?",
        "How does personalized medicine work?",
        "What are common side effects of radiation therapy?",
    ]
    
    print(f"\nProcessing {len(questions)} questions...")
    
    engine = AgentEngine(model="gemma3:27b")
    results = []
    
    for i, question in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] Processing: {question[:50]}...")
        
        try:
            comparison = engine.handle_message_for_study(question)
            results.append({
                "question": question,
                "original": comparison.original_draft.agent_response,
                "final": comparison.final_response.agent_response,
                "revised": comparison.revision_occurred,
            })
            print(f"  ✓ Completed")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n✓ Batch processing complete: {len(results)}/{len(questions)} successful")
    
    # Save batch results
    output_path = Path("batch_results.jsonl")
    with open(output_path, "w") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")
    print(f"✓ Results saved to {output_path}")


def demo_analysis():
    """Demo 3: Analyze collected data programmatically."""
    print("\n" + "=" * 70)
    print("DEMO 3: Data Analysis")
    print("=" * 70)
    
    study_data_path = Path("study_data.jsonl")
    
    if not study_data_path.exists():
        print(f"\nNo data file found at {study_data_path}")
        print("Run Demo 1 or 2 first to collect data.")
        return
    
    # Load data
    data = []
    with open(study_data_path) as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    
    if not data:
        print("No data to analyze")
        return
    
    print(f"\nAnalyzing {len(data)} entries...")
    
    # Basic statistics
    original_wins = sum(1 for d in data if d.get("preference_matches_original"))
    revised_wins = len(data) - original_wins
    
    print(f"\nPreference Distribution:")
    print(f"  Original preferred: {original_wins} ({100*original_wins/len(data):.1f}%)")
    print(f"  Revised preferred: {revised_wins} ({100*revised_wins/len(data):.1f}%)")
    
    # Position bias
    pref_a = sum(1 for d in data if d.get("user_preference") == "A")
    pref_b = len(data) - pref_a
    
    print(f"\nPosition Analysis:")
    print(f"  Preference for A: {pref_a} ({100*pref_a/len(data):.1f}%)")
    print(f"  Preference for B: {pref_b} ({100*pref_b/len(data):.1f}%)")
    print(f"  Balance: {abs(pref_a-pref_b)} difference (should be <5%)")
    
    # Revision tracking
    revised_cases = sum(1 for d in data if d.get("original_draft") != d.get("user_preference"))
    print(f"\nRevision Effectiveness:")
    print(f"  Cases where revision occurred: {revised_cases}")
    print(f"  User preferred revision: {revised_wins}/{revised_cases if revised_cases else 1}")


def demo_export():
    """Demo 4: Export data for DPO fine-tuning."""
    print("\n" + "=" * 70)
    print("DEMO 4: Export for Fine-tuning")
    print("=" * 70)
    
    study_data_path = Path("study_data.jsonl")
    
    if not study_data_path.exists():
        print(f"\nNo data found at {study_data_path}")
        return
    
    # Load data
    data = []
    with open(study_data_path) as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    
    # Convert to DPO format
    dpo_data = []
    for entry in data:
        question = entry.get("question", "")
        answer_a = entry.get("answer_a", "")
        answer_b = entry.get("answer_b", "")
        preference = entry.get("user_preference", "")
        
        if preference == "A":
            dpo_data.append({
                "prompt": question,
                "chosen": answer_a,
                "rejected": answer_b,
            })
        elif preference == "B":
            dpo_data.append({
                "prompt": question,
                "chosen": answer_b,
                "rejected": answer_a,
            })
    
    # Save DPO format
    output_path = Path("dpo_training_data_demo.jsonl")
    with open(output_path, "w") as f:
        for item in dpo_data:
            f.write(json.dumps(item) + "\n")
    
    print(f"\n✓ Exported {len(dpo_data)} entries to {output_path}")
    print("\nFormat: {prompt, chosen, rejected}")
    print("Use with: trl.DPOTrainer or similar")
    
    # Show first entry
    if dpo_data:
        print(f"\nExample entry:")
        print(f"  Prompt: {dpo_data[0]['prompt'][:60]}...")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("DPO STUDY SYSTEM - DEMO SCRIPT")
    print("=" * 70)
    print("""
This script demonstrates how to use the DPO study system programmatically:

1. Single Question - Process one question
2. Batch Processing - Process multiple questions
3. Analysis - Analyze collected data
4. Export - Export for DPO fine-tuning

Note: Demos that require Ollama will skip if it's not running.
""")
    
    # Run demos
    demo_single_question()
    demo_analysis()
    demo_export()
    
    # Batch demo has a lot of output, optional
    user_input = input("\nRun batch processing demo? (y/n): ").lower()
    if user_input == "y":
        demo_batch_processing()
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("""
Next steps:
1. Use Streamlit UI: streamlit run study_ui.py
2. Analyze data: python analyze_study_data.py
3. Prepare for training: python prepare_dpo_data.py
4. Fine-tune: Use your DPO/RLHF training pipeline
""")


if __name__ == "__main__":
    main()
