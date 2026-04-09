#!/usr/bin/env python3
"""
Analysis tools for DPO study data collected via study_ui.py
"""

import json
from pathlib import Path
from collections import Counter
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def load_study_data(filepath: str = "study_data.jsonl") -> list[dict]:
    """Load study data from JSONL file."""
    path = Path(filepath)
    if not path.exists():
        print(f"No data file found at {path}")
        return []
    
    data = []
    with open(path) as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Skipping invalid JSON: {e}")
    return data


def analyze_basic(data: list[dict]) -> None:
    """Print basic statistics about the collected data."""
    if not data:
        print("No data to analyze")
        return
    
    print("=" * 70)
    print("DPO STUDY ANALYSIS - BASIC STATISTICS")
    print("=" * 70)
    
    total_responses = len(data)
    original_preferred = sum(1 for d in data if d.get("preference_matches_original"))
    revised_preferred = total_responses - original_preferred
    
    print(f"\nTotal Responses: {total_responses}")
    print(f"  Original Draft Preferred: {original_preferred} ({100*original_preferred/total_responses:.1f}%)")
    print(f"  Revised Response Preferred: {revised_preferred} ({100*revised_preferred/total_responses:.1f}%)")
    
    # Check position bias
    preference_a = sum(1 for d in data if d.get("user_preference") == "A")
    preference_b = total_responses - preference_a
    
    print(f"\nPosition Analysis:")
    print(f"  Preference for Answer A: {preference_a} ({100*preference_a/total_responses:.1f}%)")
    print(f"  Preference for Answer B: {preference_b} ({100*preference_b/total_responses:.1f}%)")
    print(f"  Position balance: {abs(preference_a - preference_b)} difference (aim for < 10%)")
    
    # Time analysis
    if data and "timestamp" in data[0]:
        first_time = datetime.fromisoformat(data[0]["timestamp"])
        last_time = datetime.fromisoformat(data[-1]["timestamp"])
        duration = last_time - first_time
        print(f"\nData Collection:")
        print(f"  Duration: {duration}")
        print(f"  First response: {first_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Last response: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")


def analyze_questions(data: list[dict]) -> None:
    """Analyze the clinical topics/questions in the dataset."""
    if not data:
        return
    
    print("\n" + "=" * 70)
    print("QUESTION ANALYSIS")
    print("=" * 70)
    
    # Extract keywords from questions
    questions = [d.get("question", "") for d in data]
    keywords = Counter()
    
    common_terms = [
        "therapy", "treatment", "side effect", "risk", "cancer",
        "patient", "symptom", "radiation", "drug", "dose",
        "safe", "effect", "pain", "fatigue", "nausea"
    ]
    
    for question in questions:
        question_lower = question.lower()
        for term in common_terms:
            if term in question_lower:
                keywords[term] += 1
    
    print("\nMost common topics in questions:")
    for term, count in keywords.most_common(10):
        print(f"  {term}: {count} ({100*count/len(questions):.1f}%)")
    
    print(f"\nTotal unique questions: {len(set(questions))}")


def analyze_revision_effectiveness(data: list[dict]) -> None:
    """Analyze whether revisions improved responses."""
    if not data:
        return
    
    print("\n" + "=" * 70)
    print("REVISION EFFECTIVENESS ANALYSIS")
    print("=" * 70)
    
    revised = [d for d in data if d.get("original_draft") == d.get("user_preference")]
    not_revised = [d for d in data if d.get("original_draft") != d.get("user_preference")]
    
    print(f"\nPreference for Original Draft: {len(revised)} ({100*len(revised)/len(data):.1f}%)")
    print(f"Preference for Revised Response: {len(not_revised)} ({100*len(not_revised)/len(data):.1f}%)")
    
    if len(not_revised) > 0:
        print(f"\n✓ Revision was beneficial {len(not_revised)} times")
        print("  This indicates the compliance/revision process improved responses.")
    if len(revised) > 0:
        print(f"\n⚠ Original was preferred {len(revised)} times")
        print("  Review these cases to understand when revision hurts response quality.")


def export_to_csv(data: list[dict], output_path: str = "study_data.csv") -> None:
    """Export study data to CSV for further analysis."""
    if not HAS_PANDAS:
        print("pandas required: pip install pandas")
        return
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"\n✓ Exported {len(data)} records to {output_path}")


def print_sample_entry(data: list[dict], index: int = 0) -> None:
    """Print a sample entry from the dataset."""
    if not data or index >= len(data):
        print("No data available")
        return
    
    entry = data[index]
    print("\n" + "=" * 70)
    print("SAMPLE ENTRY")
    print("=" * 70)
    
    print(f"\nQuestion: {entry.get('question', 'N/A')}")
    print(f"\nAnswer A ({entry.get('original_draft, 'N/A')}):")
    print(f"  {entry.get('answer_a', 'N/A')[:200]}...")
    print(f"\nAnswer B ({entry.get('original_draft', 'N/A')}):")
    print(f"  {entry.get('answer_b', 'N/A')[:200]}...")
    print(f"\nUser Preference: Answer {entry.get('user_preference', 'N/A')}")
    print(f"Original Draft Was: Answer {entry.get('original_draft', 'N/A')}")
    print(f"Match: {'Yes ✓' if entry.get('preference_matches_original') else 'No ✗'}")


def print_full_report(data: list[dict]) -> None:
    """Print comprehensive analysis report."""
    if not data:
        print("No data to analyze")
        return
    
    analyze_basic(data)
    analyze_questions(data)
    analyze_revision_effectiveness(data)
    
    print("\n" + "=" * 70)
    print("SAMPLE ENTRIES")
    print("=" * 70)
    
    if len(data) > 0:
        print("\nFirst entry:")
        print_sample_entry(data, 0)
    
    if len(data) > 1:
        print("\n\nLast entry:")
        print_sample_entry(data, -1)


def main():
    """Main analysis entry point."""
    import sys
    
    # Load data
    filepath = "study_data.jsonl"
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    
    data = load_study_data(filepath)
    
    if not data:
        return
    
    # Print full report
    print_full_report(data)
    
    # Offer to export
    if HAS_PANDAS:
        print("\n" + "=" * 70)
        if input("\nExport to CSV? (y/n): ").lower() == "y":
            export_to_csv(data)


if __name__ == "__main__":
    main()
