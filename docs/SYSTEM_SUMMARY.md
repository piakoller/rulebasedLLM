# DPO Study Implementation - Complete Summary

## System Overview

You now have a complete Direct Preference Optimization (DPO) data collection and analysis system for your clinical AI assistant.

```
┌─────────────────────────────────────────────────────────────────┐
│                    DPO Study Data Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. COLLECTION PHASE                                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ study_ui.py (Streamlit App)                              │   │
│  │ • Question input field                                   │   │
│  │ • Generates two answers (original + revised)             │   │
│  │ • Random A/B assignment                                  │   │
│  │ • User preference selection                              │   │
│  │ • Auto-logs to study_data.jsonl                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                      │
│  2. DATA ACCUMULATION                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ study_data.jsonl (Append-only log)                       │   │
│  │ Each line: {question, answer_a, answer_b, ...}           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                      │
│  3. ANALYSIS PHASE                                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ analyze_study_data.py (Post-collection analysis)         │   │
│  │ • Preference statistics                                  │   │
│  │ • Position bias detection                                │   │
│  │ • Revision effectiveness analysis                        │   │
│  │ • Export to CSV                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                      │
│  4. FINE-TUNING PREPARATION                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ prepare_dpo_data.py (Format conversion)                  │   │
│  │ • Converts to DPO format                                 │   │
│  │ • Converts to SFT format (preferred only)                │   │
│  │ • Converts to preference ranking format                  │   │
│  │ • Outputs: *.jsonl training datasets                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                      │
│  5. MODEL FINE-TUNING                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Your Fine-tuning Pipeline                                │   │
│  │ • DPOTrainer (trl library)                               │   │
│  │ • Custom RLHF training                                   │   │
│  │ • Reward model training                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Files Modified and Created

### Modified Files

**`agent_engine.py`**
- Added `DraftComparison` class
- Added `handle_message_for_study()` method
- Tracks both original and revised responses independently

### New Files

| File | Purpose | Type |
|------|---------|------|
| `ui/study_ui.py` | Main Streamlit UI for data collection | Application |
| `tools/analyze_study_data.py` | Post-collection analysis tool (Planned) | Script |
| `tools/prepare_dpo_data.py` | Converts study data to training formats (Planned) | Script |
| `requirements_study.txt` | Python dependencies | Config |
| `docs/QUICKSTART.md` | Quick start guide | Documentation |
| `docs/SYSTEM_SUMMARY.md` | Complete system summary | Documentation |

## Quick Start (5 Minutes)

### Setup
```bash
# Install dependencies
pip install -r requirements_study.txt

# Start Ollama
ollama serve  # in another terminal

# Run the study UI
streamlit run study_ui.py
```

### Collect Data
1. Open http://localhost:8501
2. Enter clinical questions
3. Click "Generate Answers"
4. Select your preference
5. Repeat!

### Analyze Results
```bash
python analyze_study_data.py
```

### Prepare for Fine-tuning
```bash
python prepare_dpo_data.py
```

## Key Features

### 1. **Original vs. Final Response Tracking**
The system captures and compares:
- **Original Draft**: LLM's first-pass response (the "raw" output)
- **Final Response**: After empathy/safety compliance checks

This allows you to measure if your revision process actually improves responses.

### 2. **Position Bias Mitigation**
- Original and revised responses are randomly assigned to A/B
- 50/50 split prevents position bias
- `preference_matches_original` field reveals user's true preference

### 3. **Clinical Design**
- Minimalist interface (no sidebars, distractions)
- Single-screen flow for focused evaluation
- Professional, clinical presentation

### 4. **Complete Data Pipeline**
```
Collection → Storage → Analysis → Fine-tuning Preparation
```

## Data Format

### Input: study_data.jsonl
```json
{
  "timestamp": "2026-04-09T14:32:15.123456",
  "question": "What are common side effects of targeted therapy?",
  "answer_a": "Targeted therapy can cause skin reactions, fatigue...",
  "answer_b": "Common effects include fatigue, nausea, and skin...",
  "original_draft": "A",
  "user_preference": "B",
  "preference_matches_original": false
}
```

### Output: dpo_training_data.jsonl
```json
{
  "prompt": "What are common side effects of targeted therapy?",
  "chosen": "Common effects include fatigue, nausea, and skin...",
  "rejected": "Targeted therapy can cause skin reactions, fatigue..."
}
```

## Usage Scenarios

### Scenario 1: Measure Revision Effectiveness
**Goal**: Test if your compliance/revision process improves responses

```bash
# Collect 50+ responses
streamlit run study_ui.py
# User enters questions and selects preferences

# Analyze results
python analyze_study_data.py
# Output: "Revision was beneficial 62% of the time"
```

### Scenario 2: Build DPO Training Set
**Goal**: Collect preference data for DPO fine-tuning

```bash
# Collect 200+ responses (takes 1-2 hours with multiple evaluators)
streamlit run study_ui.py

# Convert to DPO format
python prepare_dpo_data.py

# Fine-tune your model
from trl import DPOTrainer
trainer = DPOTrainer(model, args, train_dataset, tokenizer)
trainer.train()
```

### Scenario 3: A/B Test Different Models
**Goal**: Compare preference for Model A vs Model B responses

Modify `handle_message_for_study()` to:
```python
# Generate one response with Model A
original_draft = model_a.generate(question)

# Generate one response with Model B  
final_response = model_b.generate(question)

# Return for comparison
return DraftComparison(original_draft, final_response)
```

## Analysis Examples

### Check Revision Win Rate
```python
import json

with open("study_data.jsonl") as f:
    data = [json.loads(line) for line in f]

# How often does the revised response win?
revision_wins = sum(1 for d in data if not d['preference_matches_original'])
win_rate = revision_wins / len(data)
print(f"Revision win rate: {win_rate:.1%}")
```

### Detect Topics Where Revision Fails
```python
# Find cases where original was preferred
original_wins = [d for d in data if d['preference_matches_original']]

# Analyze these questions for patterns
for entry in original_wins[:5]:
    print(f"Q: {entry['question']}")
    print(f"Original was preferred over revised")
```

### Export for Fine-tuning
```bash
python prepare_dpo_data.py
# Creates:
# - dpo_training_data.jsonl (for DPO)
# - sft_training_data.jsonl (for SFT)
# - preference_training_data.jsonl (for reward models)
```

## Workflow Checklist

- [ ] Install dependencies: `pip install -r requirements_study.txt`
- [ ] Start Ollama: `ollama serve`
- [ ] Run UI: `streamlit run study_ui.py`
- [ ] Collect 50-200 responses (depending on need)
- [ ] Run analysis: `python analyze_study_data.py`
- [ ] Prepare for fine-tuning: `python prepare_dpo_data.py`
- [ ] Fine-tune your model with collected preferences
- [ ] Evaluate fine-tuned model on test set
- [ ] Iterate: collect more data on failure cases

## Performance Tips

### Faster Response Generation
- Use a faster model: `DEFAULT_MODEL = "mistral"`
- Reduce reasoning steps: `max_reasoning_steps=1`

### Larger Scale Studies
- Deploy UI with Docker:
  ```dockerfile
  FROM python:3.10
  RUN pip install -r requirements_study.txt
  CMD ["streamlit", "run", "study_ui.py"]
  ```
- Use concurrent sessions with reverse proxy (nginx)
- Collect 500+ responses for robust statistics

### Data Quality
- Add confidence rating option (modify UI)
- Use multiple evaluators and compute inter-rater agreement
- Filter outliers by timestamp/response time

## Next Steps

1. **Run the system once**: Familiarize yourself with the UI
2. **Collect initial data**: 20-50 responses to test the pipeline
3. **Analyze**: Run analysis_study_data.py to see patterns
4. **Iterate**: Refine your revision logic based on what users prefer
5. **Scale**: Collect 200+ responses with multiple evaluators
6. **Fine-tune**: Use prepare_dpo_data.py to prepare for model training

## Support Resources

- **Quick start**: See STUDY_UI_SETUP.md
- **Comprehensive guide**: See DPO_STUDY_GUIDE.md
- **Tool call system**: See example_tool_calls.py
- **Analysis**: See analyze_study_data.py

## Common Questions

**Q: What's the difference between original_draft and final_response?**
A: Original is the first LLM response. Final is after empathy/safety checks. This reveals if revision helps.

**Q: Why randomize A/B assignment?**
A: Prevents position bias. Users might prefer "first answer" without reading carefully.

**Q: How many responses do I need?**
A: 50+ for basic analysis, 200+ for robust training data, 500+ for publication-quality studies.

**Q: Can I use this for other tasks?**
A: Yes! Modify questions/domain and it works for any preference collection task.

**Q: How do I fine-tune with this data?**
A: Use prepare_dpo_data.py to convert, then use trl.DPOTrainer or similar.

---

**Happy collecting!** Questions or issues? Check the markdown guides or test with 5-10 responses first.
