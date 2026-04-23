#!/usr/bin/env python3
"""
Sample questions utility for the DPO study UI.
Provides easy access to pre-written clinical questions for testing and studies.
"""

import json
from pathlib import Path
from typing import Optional, List


QUESTIONS_FILE = Path("sample_questions.json")


def load_questions() -> dict:
    """Load sample questions from JSON file."""
    if not QUESTIONS_FILE.exists():
        print(f"Error: {QUESTIONS_FILE} not found")
        return {}
    
    with open(QUESTIONS_FILE) as f:
        return json.load(f)


def get_all_questions() -> List[str]:
    """Get all questions as a flat list."""
    questions_dict = load_questions()
    all_questions = []
    for category_questions in questions_dict.values():
        all_questions.extend(category_questions)
    return all_questions


def get_questions_by_category(category: str) -> List[str]:
    """Get questions from a specific category."""
    questions_dict = load_questions()
    return questions_dict.get(category, [])


def get_categories() -> List[str]:
    """Get all available question categories."""
    questions_dict = load_questions()
    return list(questions_dict.keys())


def print_all_questions() -> None:
    """Print all questions formatted by category."""
    questions_dict = load_questions()
    
    print("\n" + "=" * 70)
    print("SAMPLE CLINICAL QUESTIONS FOR DPO STUDY")
    print("=" * 70)
    
    total = 0
    for category, questions in questions_dict.items():
        print(f"\n{category.replace('_', ' ').title()}")
        print("-" * 70)
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q}")
            total += 1
    
    print("\n" + "=" * 70)
    print(f"TOTAL QUESTIONS: {total}")
    print("=" * 70)


def print_category(category: str) -> None:
    """Print questions from a specific category."""
    questions = get_questions_by_category(category)
    
    if not questions:
        print(f"Category '{category}' not found.")
        print(f"Available categories: {', '.join(get_categories())}")
        return
    
    print(f"\n{category.replace('_', ' ').title()}")
    print("=" * 70)
    for i, q in enumerate(questions, 1):
        print(f"{i}. {q}")
    print()


def export_as_list(output_file: str = "questions_list.txt") -> None:
    """Export all questions as a simple text file (one per line)."""
    questions = get_all_questions()
    
    with open(output_file, "w") as f:
        for q in questions:
            f.write(q + "\n")
    
    print(f"✓ Exported {len(questions)} questions to {output_file}")


def export_as_csv(output_file: str = "questions_list.csv") -> None:
    """Export all questions with categories as CSV."""
    questions_dict = load_questions()
    
    with open(output_file, "w") as f:
        f.write("category,question\n")
        for category, questions in questions_dict.items():
            for q in questions:
                # Escape quotes in questions
                q_escaped = q.replace('"', '""')
                f.write(f'"{category}","{q_escaped}"\n')
    
    print(f"✓ Exported questions to {output_file}")


def get_random_question(category: Optional[str] = None) -> str:
    """Get a random question, optionally from a specific category."""
    import random
    
    if category:
        questions = get_questions_by_category(category)
    else:
        questions = get_all_questions()
    
    return random.choice(questions) if questions else ""


def main():
    """Main entry point for command-line usage."""
    import sys
    
    if len(sys.argv) < 2:
        print("""
Sample Questions Utility

Usage:
  python sample_questions_util.py all          - Print all questions by category
  python sample_questions_util.py list <cat>   - Print questions from a category
  python sample_questions_util.py categories   - List available categories
  python sample_questions_util.py random       - Get a random question
  python sample_questions_util.py random <cat> - Get random from category
  python sample_questions_util.py export txt   - Export as text file
  python sample_questions_util.py export csv   - Export as CSV file

Categories:
""")
        for cat in get_categories():
            print(f"  - {cat}")
        return
    
    command = sys.argv[1].lower()
    
    if command == "all":
        print_all_questions()
    
    elif command == "list":
        if len(sys.argv) < 3:
            print("Specify a category: python sample_questions_util.py list <category>")
            print(f"Categories: {', '.join(get_categories())}")
        else:
            category = sys.argv[2]
            print_category(category)
    
    elif command == "categories":
        print("Available categories:")
        for cat in get_categories():
            q_count = len(get_questions_by_category(cat))
            print(f"  - {cat}: {q_count} questions")
    
    elif command == "random":
        if len(sys.argv) < 3:
            q = get_random_question()
        else:
            category = sys.argv[2]
            q = get_random_question(category)
        
        if q:
            print(f"\nRandom question:\n  {q}\n")
        else:
            print("No questions found")
    
    elif command == "export":
        if len(sys.argv) < 3:
            print("Specify format: txt or csv")
        else:
            format_type = sys.argv[2].lower()
            if format_type == "txt":
                export_as_list()
            elif format_type == "csv":
                export_as_csv()
            else:
                print("Unknown format. Use: txt or csv")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
