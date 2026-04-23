# Using Sample Questions with the DPO Study UI

## Overview

A library of **100+ clinical questions** is provided in `sample_questions.json` to help you:
- Test the study UI quickly
- Run full studies without spending time writing questions
- Ensure consistency across evaluators
- Collect comparable preference data

## Question Categories

The library includes 10 categories with 10 questions each:

| Category | Topic | Count |
|----------|-------|-------|
| **oncology_and_cancer** | General cancer treatment concepts | 10 |
| **nuclear_medicine_theranostics** | Nuclear medicine specific topics | 10 |
| **symptoms_and_side_effects** | Managing treatment side effects | 10 |
| **treatment_planning_and_monitoring** | How treatment is planned and monitored | 10 |
| **psychosocial_and_emotional** | Mental health and support resources | 10 |
| **recovery_and_long_term_outcomes** | Recovery and follow-up care | 10 |
| **treatment_modalities** | Different types of treatments | 10 |
| **practical_questions** | Logistics and practical concerns | 10 |
| **misconceptions_and_clarifications** | Correcting common myths | 10 |

**Total: 100 questions**

## How to Use

### Option 1: Manually Copy Questions (Easiest)

1. Open `sample_questions.json` in a text editor
2. Copy a question
3. Paste into the Streamlit UI's question input field
4. Click "Generate Answers"

### Option 2: Use the Utility Script

View all questions:
```bash
python sample_questions_util.py all
```

View questions from a specific category:
```bash
python sample_questions_util.py list oncology_and_cancer
python sample_questions_util.py list symptoms_and_side_effects
python sample_questions_util.py list treatment_planning_and_monitoring
```

Get a random question:
```bash
python sample_questions_util.py random
python sample_questions_util.py random psychosocial_and_emotional
```

See available categories:
```bash
python sample_questions_util.py categories
```

### Option 3: Export for Batch Processing

Export all questions as a text file (one per line):
```bash
python sample_questions_util.py export txt
# Creates: questions_list.txt
```

Export with categories as CSV:
```bash
python sample_questions_util.py export csv
# Creates: questions_list.csv (spreadsheet-friendly)
```

## Using with the Streamlit UI

### Single Question Mode
1. Run: `streamlit run study_ui.py`
2. Copy a question from `sample_questions.json`
3. Paste into the input field
4. Click "Generate Answers"
5. Select your preference
6. Repeat with next question

### Batch Mode (Multiple Evaluators)

If multiple people are evaluating:

1. **Prepare questions**: 
   ```bash
   python sample_questions_util.py export txt
   ```

2. **Share with evaluators**: 
   - Give each evaluator a subset of questions
   - Example: Give 25 questions to each of 4 people

3. **Each evaluator runs UI**:
   ```bash
   streamlit run study_ui.py
   ```

4. **Combine results**:
   ```bash
   # All study_data.jsonl files from each evaluator
   cat evaluator1/study_data.jsonl >> combined_study_data.jsonl
   cat evaluator2/study_data.jsonl >> combined_study_data.jsonl
   cat evaluator3/study_data.jsonl >> combined_study_data.jsonl
   ```

5. **Analyze combined data**:
   ```bash
   python analyze_study_data.py
   ```

## Sample Question Examples

### From oncology_and_cancer Category:
```
"What is targeted therapy and how does it differ from traditional chemotherapy?"
"What are the most common side effects of targeted therapy?"
"How does personalized medicine approach cancer treatment?"
```

### From symptoms_and_side_effects Category:
```
"I've been experiencing fatigue during my treatment. Is this normal?"
"What can I do to manage nausea and loss of appetite?"
"Why might I experience skin reactions during treatment?"
```

### From psychosocial_and_emotional Category:
```
"I'm feeling anxious about my upcoming treatment. What resources can help?"
"How can I talk with my family about my cancer diagnosis?"
"Are there support groups for patients undergoing my type of treatment?"
```

## Suggested Study Designs

### Design 1: Quick Test (5 questions)
- Run UI with 5 random questions
- Should take ~15-20 minutes
- Good for testing the system

**Command:**
```bash
for i in {1..5}; do 
  python sample_questions_util.py random
done
```

### Design 2: Category-Based Study (40 questions)
- 4 evaluators × 10 questions each from different categories
- Diverse topic coverage
- Good for general quality assessment

**Command:**
```bash
python sample_questions_util.py list oncology_and_cancer
python sample_questions_util.py list symptoms_and_side_effects
python sample_questions_util.py list treatment_planning_and_monitoring
python sample_questions_util.py list psychosocial_and_emotional
```

### Design 3: Large-Scale Study (100 questions)
- All 100 questions
- Multiple evaluators per question
- Robust statistical power

**Command:**
```bash
python sample_questions_util.py all
# Then distribute questions among evaluators
```

### Design 4: Domain-Specific Study (30 questions)
- Focus on one category
- Deep understanding of specific topic
- Example: Only theranostics questions

**Command:**
```bash
python sample_questions_util.py list nuclear_medicine_theranostics
python sample_questions_util.py list treatment_planning_and_monitoring
python sample_questions_util.py list practical_questions
```

## Data Analysis with Sample Questions

After collecting data with sample questions:

### 1. Basic Analysis
```bash
python analyze_study_data.py
```

### 2. Category-Based Analysis
```python
import json
import pandas as pd

# Load data
with open("study_data.jsonl") as f:
    data = [json.loads(line) for line in f]

# Create DataFrame
df = pd.DataFrame(data)

# Analyze by question
question_stats = df.groupby("question").agg({
    "user_preference": "count",
    "preference_matches_original": "mean"
}).rename(columns={
    "user_preference": "responses",
    "preference_matches_original": "revision_win_rate"
})

print(question_stats.sort_values("revision_win_rate"))
```

### 3. Find Easy vs Hard Questions
```python
# Questions where original is frequently preferred
original_preferred = df[df["preference_matches_original"]]
easy_questions = original_preferred["question"].value_counts()

# Questions where revised is frequently preferred
revised_preferred = df[~df["preference_matches_original"]]
hard_questions = revised_preferred["question"].value_counts()

print("Questions where revision helps most:")
print(hard_questions.head())

print("\nQuestions where original is preferred:")
print(easy_questions.head())
```

## Adding Your Own Questions

To add more questions:

1. Edit `sample_questions.json`
2. Add new category or extend existing:
   ```json
   {
     "your_category": [
       "Question 1?",
       "Question 2?"
     ]
   }
   ```
3. Save and use normally

## Best Practices

### Question Selection
- ✓ Use diverse questions to test different aspects
- ✓ Mix easy and challenging topics
- ✓ Include both practical and clinical questions
- ✓ Vary question length and complexity

### Study Design
- ✓ Define your sample set in advance
- ✓ Keep sample consistent across evaluators
- ✓ Use multiple evaluators per question for reliability
- ✓ Track which questions each evaluator answered

### Data Quality
- ✓ Check for position bias (should be ~50/50 A/B preference)
- ✓ Verify no single evaluator dominates results
- ✓ Remove evaluators with low agreement with others
- ✓ Track evaluation time per question

## Example Scripts

### Script 1: Run All Questions
```bash
cat sample_questions.json | jq -r '.[] | .[]' > all_questions.txt
wc -l all_questions.txt  # 100 questions
```

### Script 2: Prepare Study for Team
```bash
# Export questions with categories
python sample_questions_util.py export csv

# Share with team
mail -s "Study Questions" team@example.com < questions_list.csv
```

### Script 3: Analyze Question Difficulty
```python
import json
import pandas as pd

with open("study_data.jsonl") as f:
    data = [json.loads(line) for line in f]

df = pd.DataFrame(data)

# Questions with highest revision help
print("Questions where revisions work best:**
df[~df["preference_matches_original"]]["question"].value_counts().head()

# Questions where original is preferred
print("\nQuestions where original works better:")
df[df["preference_matches_original"]]["question"].value_counts().head()
```

## Tips for Success

1. **Start Small**: Use 10 questions to test (Sample 5 from different categories)
2. **Be Systematic**: Define your system (which questions, how many evaluators)
3. **Track Metadata**: Note evaluator, date, time for each batch
4. **Check Quality**: Ensure position bias isn't present (A/B should be ~50/50)
5. **Iterate**: Use results to refine your model and revision process

## Questions by Difficulty Level

**Easier** (testing fundamental knowledge):
- "What is targeted therapy?"
- "What are common side effects?"
- "What should I expect during treatment?"

**Medium** (requiring nuanced explanation):
- "Why might my blood counts change?"
- "How is personalized dosimetry used?"
- "What is the difference between internal and external radiation?"

**Harder** (requiring comprehensive explanation):
- "How does personalized medicine approach cancer treatment?"
- "What is theranostics and how is it different?"
- "When should I be concerned about side effects?"

## Support & Help

- See all questions: `python sample_questions_util.py all`
- List categories: `python sample_questions_util.py categories`
- Get one random: `python sample_questions_util.py random`
- Export all: `python sample_questions_util.py export csv`

---

**Ready to start?** 
```bash
streamlit run study_ui.py
# Paste a question from sample_questions.json
# Generate answers and select your preference!
```
