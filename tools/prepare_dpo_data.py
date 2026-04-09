#!/usr/bin/env python3
"""
Convert DPO study data to training format for fine-tuning with DPO or preference-based learning.

This script takes the study_data.jsonl collected via study_ui.py and converts it into
formats suitable for various fine-tuning approaches.
"""

import json
from pathlib import Path
from typing import Optional
import sys


def load_study_data(filepath: str = "study_data.jsonl") -> list[dict]:
    """Load study data from JSONL file."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: No data file found at {path}")
        sys.exit(1)
    
    data = []
    with open(path) as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Skipping invalid JSON: {e}")
    
    return data


def convert_to_dpo_format(data: list[dict]) -> list[dict]:
    """
    Convert study data to DPO format for use with trl library.
    
    DPO format (for trl.SFTTrainer):
    {
        "prompt": "...",
        "chosen": "...",      # preferred response
        "rejected": "..."     # non-preferred response
    }
    """
    dpo_data = []
    
    for entry in data:
        question = entry.get("question", "")
        answer_a = entry.get("answer_a", "")
        answer_b = entry.get("answer_b", "")
        preference = entry.get("user_preference", "")
        
        if preference == "A":
            chosen = answer_a
            rejected = answer_b
        elif preference == "B":
            chosen = answer_b
            rejected = answer_a
        else:
            continue  # Skip entries without clear preference
        
        dpo_data.append({
            "prompt": question,
            "chosen": chosen,
            "rejected": rejected,
        })
    
    return dpo_data


def convert_to_preference_format(data: list[dict]) -> list[dict]:
    """
    Convert to preference ranking format for reward modeling.
    
    Format:
    {
        "prompt": "...",
        "response_a": "...",
        "response_b": "...",
        "preference_score": 1 or 0,  # 1 for A, 0 for B
        "confidence": 0.5 or 1.0
    }
    """
    preference_data = []
    
    for entry in data:
        question = entry.get("question", "")
        answer_a = entry.get("answer_a", "")
        answer_b = entry.get("answer_b", "")
        preference = entry.get("user_preference", "")
        
        if preference == "A":
            preference_score = 1
        elif preference == "B":
            preference_score = 0
        else:
            continue
        
        preference_data.append({
            "prompt": question,
            "response_a": answer_a,
            "response_b": answer_b,
            "preference_score": preference_score,
            "confidence": 1.0,  # All preferences equally confident
        })
    
    return preference_data


def convert_to_sft_format(data: list[dict]) -> list[dict]:
    """
    Convert to SFT (Supervised Fine-Tuning) format using only preferred responses.
    
    Format:
    {
        "text": "prompt\\n\\nresponse" or "[INST] prompt [/INST] response",
        "prompt": "...",
        "response": "..."
    }
    """
    sft_data = []
    
    for entry in data:
        question = entry.get("question", "")
        preference = entry.get("user_preference", "")
        
        if preference == "A":
            response = entry.get("answer_a", "")
        elif preference == "B":
            response = entry.get("answer_b", "")
        else:
            continue
        
        sft_data.append({
            "text": f"{question}\n\n{response}",
            "prompt": question,
            "response": response,
        })
    
    return sft_data


def save_as_jsonl(data: list[dict], filepath: str) -> None:
    """Save data to JSONL format."""
    with open(filepath, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    print(f"✓ Saved {len(data)} items to {filepath}")


def print_conversion_summary(original_count: int, converted_count: int) -> None:
    """Print summary of conversion."""
    print("\n" + "=" * 70)
    print("CONVERSION SUMMARY")
    print("=" * 70)
    print(f"Original entries: {original_count}")
    print(f"Converted entries: {converted_count}")
    print(f"Conversion rate: {100*converted_count/original_count:.1f}%")
    if converted_count < original_count:
        print(f"⚠ {original_count - converted_count} entries skipped (missing data)")


def main():
    """Main conversion script."""
    print("=" * 70)
    print("DPO Study Data Format Converter")
    print("=" * 70)
    
    # Load data
    data = load_study_data()
    print(f"\nLoaded {len(data)} entries from study_data.jsonl")
    
    # Convert to different formats
    print("\nConverting to different formats...\n")
    
    # DPO Format
    dpo_data = convert_to_dpo_format(data)
    save_as_jsonl(dpo_data, "dpo_training_data.jsonl")
    print("Use with: trl.DPOTrainer or similar DPO fine-tuning methods")
    print("  Example: https://huggingface.co/docs/trl/dpo_trainer\n")
    
    # Preference Format
    pref_data = convert_to_preference_format(data)
    save_as_jsonl(pref_data, "preference_training_data.jsonl")
    print("Use with: Reward model training or preference-based learning")
    print("  Example: RLHF reward model, BT (Bradley-Terry) models\n")
    
    # SFT Format (preferred only)
    sft_data = convert_to_sft_format(data)
    save_as_jsonl(sft_data, "sft_training_data.jsonl")
    print("Use with: Standard supervised fine-tuning")
    print("  Example: huggingface transformers, training only with preferred responses\n")
    
    # Print summaries
    print_conversion_summary(len(data), len(dpo_data))
    
    # Try to import pandas for analysis
    try:
        import pandas as pd
        
        print("\n" + "=" * 70)
        print("DATASET STATISTICS")
        print("=" * 70)
        
        # Calculate additional stats
        original_preferred = sum(1 for d in data if d.get("preference_matches_original"))
        revised_preferred = len(data) - original_preferred
        
        print(f"\nPreference Distribution:")
        print(f"  Original preferred: {original_preferred} ({100*original_preferred/len(data):.1f}%)")
        print(f"  Revised preferred: {revised_preferred} ({100*revised_preferred/len(data):.1f}%)")
        
        # Position bias
        pref_a = sum(1 for d in data if d.get("user_preference") == "A")
        pref_b = len(data) - pref_a
        print(f"\nPosition Bias (A vs B):")
        print(f"  Preference for A: {100*pref_a/len(data):.1f}%")
        print(f"  Preference for B: {100*pref_b/len(data):.1f}%")
        
    except ImportError:
        pass
    
    print("\n" + "=" * 70)
    print("OUTPUT FILES CREATED:")
    print("=" * 70)
    print("\n1. dpo_training_data.jsonl")
    print("   → Format: {prompt, chosen, rejected}")
    print("   → Use for: DPO fine-tuning with trl.DPOTrainer")
    
    print("\n2. preference_training_data.jsonl")
    print("   → Format: {prompt, response_a, response_b, preference_score}")
    print("   → Use for: Reward model training, preference learning")
    
    print("\n3. sft_training_data.jsonl")
    print("   → Format: {text, prompt, response}")
    print("   → Use for: Standard supervised fine-tuning (preferred responses only)")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    
    print("""
1. DPO Fine-tuning (Recommended for LLMs):
   pip install trl transformers
   
   from trl import DPOTrainer
   trainer = DPOTrainer(
       model=model,
       args=training_args,
       train_dataset=load_dataset("json", data_files="dpo_training_data.jsonl"),
       tokenizer=tokenizer,
   )
   trainer.train()

2. SFT Fine-tuning (Use preferred responses):
   from transformers import TextGenerationPipeline
   # Standard SFT with labeled preferred data
   trainer.train_dataset = load_dataset("json", data_files="sft_training_data.jsonl")

3. Reward Model Training (Build preferences model):
   # Train a model to predict which response is better
   from transformers import AutoModelForSequenceClassification
   # Use preference_training_data.jsonl for reward model

4. Multi-turn Evaluation:
   # Use data to evaluate other models
   # Compare responses from different models on same questions
""")


if __name__ == "__main__":
    main()
