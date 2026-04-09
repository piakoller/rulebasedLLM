# DPO Study UI Setup

## Quick Start

### Prerequisites
- Streamlit installed: `pip install streamlit`
- Ollama running with the configured model (default: gemma3:27b)

### Running the Study UI

```bash
streamlit run study_ui.py
```

The app will open at http://localhost:8501

## What the Study UI Does

### For Researchers:
1. **Question Input** - Enter any clinical question
2. **Generate Answers** - Produces two versions:
   - **Original Draft**: First-pass response from the LLM
   - **Final Response**: Response after empathy/safety revision (if revision occurred)
3. **Comparison Interface** - Displays answers side-by-side with random A/B assignment
4. **Preference Logging** - Records which answer was preferred

### Data Collection

Results are automatically saved to `study_data.jsonl` with each entry containing:

```json
{
  "timestamp": "2026-04-09T14:32:15.123456",
  "question": "What are common side effects of targeted therapy?",
  "answer_a": "Answer text...",
  "answer_b": "Answer text...",
  "original_draft": "A",
  "user_preference": "B",
  "preference_matches_original": false
}
```

## Design Features

✅ **Minimalist Design**
- No sidebars, settings, or distractions
- Focus entirely on: Question → Generate → Compare → Select

✅ **Clinical Presentation** 
- Clean, professional layout
- Clear question display
- Side-by-side answer comparison

✅ **Position Bias Mitigation**
- Answers are randomly assigned to A/B each generation
- User doesn't know which is original until after preference

✅ **Preference Tracking**
- Records which answer was original vs. final
- `preference_matches_original` field shows if user preferred original
- Useful for analyzing when revisions help vs. hurt

## Data Analysis

To analyze collected preferences:

```python
import json
import pandas as pd

# Load data
data = []
with open("study_data.jsonl") as f:
    for line in f:
        data.append(json.loads(line))

df = pd.DataFrame(data)

# Preference analysis
print(f"Total responses: {len(df)}")
print(f"Preference for original: {(df['preference_matches_original']).mean():.2%}")
print(f"Preference for revised: {(~df['preference_matches_original']).mean():.2%}")
```

## Key Implementation Details

### Modified Method: `handle_message_for_study()`
Located in `agent_engine.py`, this method:
- Uses the same reasoning loop as `handle_message()`
- **Captures the first-pass response** (original draft)
- **Tracks revisions** that occur during compliance checking
- **Returns both versions** in a `DraftComparison` object

### Random Assignment
```python
if random.random() < 0.5:
    answer_a = original
    answer_b = final
else:
    answer_a = final
    answer_b = original
```

This 50/50 split prevents position bias while collecting preference data.

## Troubleshooting

**"Connection refused" error**
- Ensure Ollama is running: `ollama serve`
- Check model is available: `ollama list`

**Streamlit caching issues**
- Clear cache: `streamlit cache clear`
- Restart app

**JSON parsing errors in study_data.jsonl**
- Each line should be valid JSON
- Don't edit file manually while app is running
- Clear file and restart if corrupted: `rm study_data.jsonl`

## Extending the UI

To add more features (without breaking minimalism):

1. **Custom model selection** (add dropdown, remove cache):
   ```python
   model = st.selectbox("Select Model", ["gemma3:27b", "llama2"])
   engine = AgentEngine(model=model)  # Remove @st.cache_resource
   ```

2. **Export functionality**:
   ```python
   if st.button("Export Data"):
       df = pd.read_json(STUDY_DATA_PATH, lines=True)
       st.download_button("Download CSV", df.to_csv(index=False), "study_data.csv")
   ```

3. **Revision reason display**:
   ```python
   if comparison.revision_occurred:
       st.info(f"Note: Original response was revised. Reason: {comparison.revision_reason}")
   ```

## Study Insights

The collected data reveals:

- **Revision Effectiveness**: How often are final responses preferred over originals?
- **Failure Modes**: When does revision help vs. hurt?
- **Position Bias**: Are preferences independent of A/B position? (Should average 50/50)
- **Response Quality**: Which clinical topics benefit most from revision?

Use this data to improve the revision process and empathy compliance checking.
