# DPO Study UI - Quick Start Guide

## What Was Created

A complete system for collecting, analyzing, and preparing Direct Preference Optimization (DPO) data for your clinical AI assistant.

## Files Summary

```
agent_engine.py           ← MODIFIED: Added DraftComparison class & handle_message_for_study()
study_ui.py              ← NEW: Streamlit app for data collection
analyze_study_data.py    ← NEW: Post-collection analysis
prepare_dpo_data.py      ← NEW: Format conversion for fine-tuning
demo_dpo_system.py       ← NEW: Demonstration script
requirements_study.txt   ← NEW: Python dependencies
SYSTEM_SUMMARY.md        ← NEW: Complete system documentation
STUDY_UI_SETUP.md        ← NEW: Setup and troubleshooting
DPO_STUDY_GUIDE.md       ← NEW: Comprehensive guide
```

## 30-Second Setup

```bash
# 1. Install dependencies
pip install -r requirements_study.txt

# 2. Start Ollama (in another terminal)
ollama serve

# 3. Run the study UI
streamlit run study_ui.py

# 4. Open browser
# http://localhost:8501
```

## The UI Workflow

```
┌─────────────────────────────────────────┐
│  1. Enter a clinical question            │
│  ┌──────────────────────────────────┐    │
│  │ "What are common side effects    │    │
│  │  of targeted therapy?"           │    │
│  └──────────────────────────────────┘    │
│                                          │
│  [Generate Answers] button              │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  2. Two versions appear side-by-side    │
│  ┌────────┐            ┌────────┐       │
│  │         │            │         │       │
│  │ Answer  │            │ Answer  │       │
│  │    A    │            │    B    │       │
│  │         │            │         │       │
│  │[Prefer] │            │[Prefer] │       │
│  └────────┘            └────────┘       │
└─────────────────────────────────────────┘
                   ↓
    Your preference is auto-saved!
```

## Three Ways to Get Started

### Option 1: Use the Streamlit UI (Easiest)
```bash
streamlit run study_ui.py
# • Enter questions manually
# • Compare answers visually
# • Click to save preferences
# • Best for interactive studies
```

### Option 2: Run the Demo Script
```bash
python demo_dpo_system.py
# • See how the system works
# • Process sample questions
# • Analyze example data
# • Good for understanding the pipeline
```

### Option 3: Integrate with Your Code
```python
from agent_engine import AgentEngine

engine = AgentEngine(model="gemma3:27b")

# Get both original and final response
comparison = engine.handle_message_for_study("Your question")

print(f"Original: {comparison.original_draft.agent_response}")
print(f"Final: {comparison.final_response.agent_response}")
```

## After You Have Data

### 1. Analyze Preferences
```bash
python analyze_study_data.py
# Outputs:
# • Preference distribution (original vs revised)
# • Position bias check (A vs B preference)
# • Revision effectiveness
# • First/last entries preview
```

### 2. Prepare for Fine-tuning
```bash
python prepare_dpo_data.py
# Creates three output files:
# • dpo_training_data.jsonl (for DPO training)
# • sft_training_data.jsonl (for SFT only)
# • preference_training_data.jsonl (for reward models)
```

### 3. Fine-tune Your Model
```python
from trl import DPOTrainer
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-7b-hf")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")

# Load your DPO data
from datasets import load_dataset
train_dataset = load_dataset("json", data_files="dpo_training_data.jsonl")

# Train
trainer = DPOTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset["train"],
    tokenizer=tokenizer,
)
trainer.train()
```

## Key Metrics to Track

After collecting data:

| Metric | Target | Meaning |
|--------|--------|---------|
| Preference for A | ~50% | No position bias |
| Preference for B | ~50% | No position bias |
| Revision win rate | >50% | Revisions improve responses |
| Data collected | 200+ | Enough for good model |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused" | Start Ollama: `ollama serve` |
| "No module named streamlit" | Install: `pip install -r requirements_study.txt` |
| Streamlit not updating | Clear cache: `streamlit cache clear` |
| JSON parse errors | Delete corrupted file, restart app |

## Next Steps

### For Researchers:
1. ✅ Run the UI: `streamlit run study_ui.py`
2. ✅ Collect data: Enter 10-20 questions as a test
3. ✅ Analyze: `python analyze_study_data.py`
4. ✅ Scale: Have multiple evaluators collect 200+ responses
5. ✅ Prepare: `python prepare_dpo_data.py`

### For ML Engineers:
1. ✅ Review system design: Read `SYSTEM_SUMMARY.md`
2. ✅ Understand the data format: Check `study_data.jsonl`
3. ✅ Prepare training data: `python prepare_dpo_data.py`
4. ✅ Fine-tune your model with DPO
5. ✅ Evaluate improvement on test set

### For Everyone:
- Read **STUDY_UI_SETUP.md** for detailed setup
- Read **DPO_STUDY_GUIDE.md** for comprehensive documentation
- Check **analyze_study_data.py** for analysis options
- See **demo_dpo_system.py** for example usage

## File Locations

All files are in: `/home/pia/projects/rulebasedLLM/`

```
/home/pia/projects/rulebasedLLM/
├── study_ui.py                    ← Run this for the UI
├── analyze_study_data.py          ← Run this to analyze
├── prepare_dpo_data.py            ← Run this to prepare for training
├── demo_dpo_system.py             ← Run this for examples
├── agent_engine.py                ← Modified with new methods
├── study_data.jsonl               ← Auto-created, stores your data
├── requirements_study.txt         ← Dependencies
├── SYSTEM_SUMMARY.md              ← System overview
├── STUDY_UI_SETUP.md              ← Setup details
├── DPO_STUDY_GUIDE.md             ← Full documentation
└── README.md                       ← Original project README
```

## Example Data Output

After collecting 1 response, your `study_data.jsonl` will contain:

```json
{
  "timestamp": "2026-04-09T14:32:15.123456",
  "question": "What are common side effects of targeted therapy?",
  "answer_a": "Targeted therapy can cause various side effects...",
  "answer_b": "Common side effects include fatigue, nausea, skin...",
  "original_draft": "A",
  "user_preference": "B",
  "preference_matches_original": false
}
```

## Commands Summary

```bash
# Start Ollama
ollama serve

# Run the Streamlit UI
streamlit run study_ui.py

# Demo the system
python demo_dpo_system.py

# Analyze collected data
python analyze_study_data.py

# Prepare for fine-tuning
python prepare_dpo_data.py

# Clear Streamlit cache if issues
streamlit cache clear

# View collected data
cat study_data.jsonl | head -1 | python -m json.tool
```

## Success Criteria ✓

After setup, you should see:
- [ ] Streamlit UI opens at localhost:8501
- [ ] Text input field for questions
- [ ] "Generate Answers" button works
- [ ] Two side-by-side responses appear
- [ ] Preference buttons save data
- [ ] `study_data.jsonl` grows after each preference

## Need Help?

1. Check **STUDY_UI_SETUP.md** for troubleshooting
2. Review **DPO_STUDY_GUIDE.md** for detailed explanations
3. Run **demo_dpo_system.py** to see working examples
4. Check that Ollama is running: `curl http://localhost:11434`

## What You Now Have

✅ Complete DPO data collection system
✅ Preference comparison UI (minimalist, clinical)
✅ Automatic data logging
✅ Post-collection analysis tools
✅ Fine-tuning data preparation
✅ Complete documentation
✅ Example code and demos

**You're ready to collect preference data and improve your clinical AI assistant with DPO!**

---

**Start here**: `streamlit run study_ui.py`
