# EMPATHY LAYER IMPLEMENTATION

## Overview

The empathy layer transforms the clinical AI system from a fact-delivery bot into an emotionally intelligent healthcare assistant. It combines **clinical validity** (UMLS-verified facts) with **emotional care** (empathic framing and distress detection) for a complete patient experience.

## Architecture

```
┌─────────────────┐
│  User Message   │  "Ich bin nervös vor der Therapie"
│  (any language) │  (German: "I'm nervous about therapy")
└────────┬────────┘
         │
         ↓
    ┌─────────────────────────────────────────┐
    │  1. LANGUAGE DETECTION (rules.py)       │
    │     detect_language() → 'de' | 'en'    │
    └────────────┬────────────────────────────┘
                 │ Detects: "nervös", "ich" → German
                 ↓
    ┌─────────────────────────────────────────┐
    │  2. DISTRESS DETECTION (rules.py)       │
    │     DISTRESS_KEYWORDS matching          │
    │     sentiment_analyzer() → prefix       │
    └────────────┬────────────────────────────┘
                 │ Finds: "nervös" (anxious) → Distressed
                 ↓
    ┌─────────────────────────────────────────┐
    │  3. TRANSLATE & QUERY UMLS (agent)      │
    │     Term: "Therapie" → "therapy"        │
    │     Clean UMLS query in English         │
    └────────────┬────────────────────────────┘
                 │ Returns: {found, relationships, cui}
                 ↓
    ┌─────────────────────────────────────────┐
    │  4. EMPATHIC FRAMING (empathy_framing.py) │
    │     create_empathic_response_to_umls_  │
    │     result(result, user_msg, distress) │
    └────────────┬────────────────────────────┘
                 │ Returns: Text framed with care
                 ↓
    ┌─────────────────────────────────────────┐
    │  5. AGENT RESPONSE (agent_engine.py)    │
    │     Clinical fact + emotional context   │
    │     In patient's language (German)      │
    │     With appropriate tone (reassuring)  │
    └─────────────────────────────────────────┘
         │
         ↓
    "Ich verstehe Ihre Besorgnis.
     Die Therapie ist wissenschaftlich
     unterstützt und Ihr Team passt die
     Behandlung an, wenn nötig. Sie sind
     nicht allein dabei."
```

## Components

### 1. **Language Detection** (`core/rules.py`)

```python
def detect_language(text: str) -> str:
    """Returns 'de' for German, 'en' for English"""
```

**How it works:**
- Counts presence of German vs English indicator words
- German indicators: "der", "die", "das", "ist", "wie", "warum", "nebenwirkung", etc.
- English indicators: "the", "is", "what", "why", "symptom", "treatment", etc.
- Fallback: Checks for German umlauts (ä, ö, ü, ß)

**Why separate detection:**
- Clinical information must be queried in English (UMLS standard)
- But patient response must be in their language for emotional resonance
- Automatic detection removes burden from clinicians

**Test coverage:**
```python
test_cases = [
    ("What are the side effects?", "en"),
    ("Was sind die Nebenwirkungen?", "de"),  # ✓ Works
    ("Ich bin nervös", "de"),  # ✓ Works
]
```

---

### 2. **Distress Detection** (`core/rules.py`)

**Distress Keywords (28 total):**
- English (14): scared, terrified, fear, afraid, anxious, worried, panic, pain, suffering, overwhelmed, distressed, depressed, desperate, hopeless
- German (14): angst, angespannt, nervös, besorg, panik, schmerz, leid, überfordert, verzweifelt, hoffnung, depressiv, hilflos, traurig, ängstlich

**Supportive Markers (24 total):**
- English (10): "I understand", "I'm sorry", "that sounds difficult", "you are not alone", "we can take this step by step"
- German (12): "Ich verstehe", "Es tut mir leid", "Das klingt schwierig", "Sie sind nicht allein"

```python
def sentiment_analyzer(user_message) -> Optional[dict]:
    """Detects distress and returns language-specific empathic prefix"""
    if distress_detected:
        return {
            "rule": "sentiment_analyzer",
            "mandatory_prefix": "Es tut mir leid, dass Sie das durchmachen..."  # German
        }
```

---

### 3. **Empathic Framing** (`core/empathy_framing.py`)

**Two main functions:**

#### A. `frame_clinical_information_empathically()`
Wraps raw clinical facts with emotional context.

**Template categories:**
1. **Side Effect Framing**
   - Non-distressed: "These side effects are manageable..."
   - Distressed: "You won't go through this alone..."

2. **Therapy Purpose Framing**
   - Non-distressed: "Your doctors chose this because..."
   - Distressed: "I know you might feel worried..."

3. **Relationship Framing**
   - Fallback for other clinical relationships

**Example (English, non-distressed):**
```
Based on verified medical data, I want to be honest about what 
patients typically experience so we can plan together. {{clinical_info}} 
These side effects are manageable, and we have strategies to help you 
through them.
```

**Example (German, distressed):**
```
Ich verstehe, dass das viel ist. Hier ist, was die Forschung zeigt: 
{{clinical_info}} Das Wichtigste ist, dass Ihr Team aufmerksam ist 
und wir Ihre Behandlung anpassen können. Sie gehen das nicht alleine 
durch.
```

#### B. `create_empathic_response_to_umls_result()`
Converts UMLS tool output into conversational empathic text.

```python
empathic_response = create_empathic_response_to_umls_result(
    umls_result={
        "found": True,
        "term": "Lutetium Lu 177",
        "relationships": [
            {"relationLabel": "has_adverse_effect", 
             "relatedConceptName": "Renal Toxicity"}
        ]
    },
    user_message="Ich bin nervös vor Nebenwirkungen",  # German
    user_distressed=True
)
```

Returns:
```
Die überprüfte Datenbank zeigt folgende wichtige Informationen:

hat_nebenwirkung: Nierenschädigung

Lassen Sie mich erklären, was das für Sie bedeutet...
```

---

### 4. **Agent Integration** (`core/agent_engine.py`)

**Updated `_execute_tool()` signature:**
```python
def _execute_tool(self, tool_call: ToolCall, user_message: str = "") -> ToolResult:
```

**For `query_umls_ontology` tool:**
```python
elif tool_call.function_name == "query_umls_ontology":
    term = tool_call.arguments.get("term", "")
    result = verify_clinical_relationship(term)
    
    # NEW: Detect distress
    user_distressed = any(kw in user_message.lower() 
                          for kw in DISTRESS_KEYWORDS) if user_message else False
    
    tool_result = {
        "term": result.term,
        "cui": result.cui,
        "found": result.found,
        "relationships": result.relationships,
        "summary": result.summary
    }
    
    # NEW: Apply empathy framing
    if user_message and result.found:
        empathic_response = create_empathic_response_to_umls_result(
            tool_result,
            user_message,
            user_distressed
        )
        tool_result["empathic_framing"] = empathic_response
    
    return ToolResult(...)
```

**Call site update in `handle_message()`:**
```python
# OLD: tool_result = self._execute_tool(tool_call)
# NEW:
tool_result = self._execute_tool(tool_call, user_message=user_message)
```

---

## How It Works End-to-End

### Example: German Patient with Anxiety

**Input:**
```
User: "Ich bin Angst vor den Nebenwirkungen der Lutetium-177 Therapie"
      (I'm afraid of the side effects of Lutetium-177 therapy)
```

**Processing:**

1. **Language Detection:**
   - detect_language("Ich bin Angst vor...") → "de"
   - Agent knows to respond in German

2. **Distress Detection:**
   - "angst" matches DISTRESS_KEYWORDS
   - user_distressed = True

3. **UMLS Query:**
   - Agent translates: "Lutetium-177" → "Lutetium Lu 177"
   - UMLS returns: CUI C4050279, relationships include "has_adverse_effect: Renal Toxicity"

4. **Empathic Framing:**
   - `create_empathic_response_to_umls_result()` called with:
     - umls_result={found:True, relationships:[...]}
     - user_message="Ich bin Angst vor..."
     - user_distressed=True
   - Template selected: "side_effect" with distressed variant
   - Output in German:
     ```
     Ich verstehe, dass das viel ist. Hier ist, was die Forschung zeigt:
     Die Therapie ist wissenschaftlich unterstützt.
     Das Wichtigste ist, dass Ihr Team aufmerksam ist und wir Ihre
     Behandlung anpassen können. Sie gehen das nicht alleine durch.
     ```

5. **Agent Response:**
   - Agent combines empathic framing with clinical facts
   - Delivers in German with reassuring tone
   - Patient feels heard AND informed

---

## Testing

### Test Files

#### 1. `test_empathy_pipeline.py` - Unit Tests
Tests individual empathy components in isolation.

**Tests:**
- TEST 1: Language Detection (4/4 passing)
- TEST 2: Distress Detection (4/4 passing)
- TEST 3: Empathic Framing (4 variants)
- TEST 4: UMLS Result Wrapping (3 scenarios)
- TEST 5: Full Scenario - German distressed patient

**Run:**
```bash
python test_empathy_pipeline.py
```

#### 2. `test_integrated_empathy_agent.py` - Integration Tests
Tests empathy layer integrated with agent TAO loop.

**Scenarios:**
- SCENARIO 1: German patient — concern about side effects
- SCENARIO 2: German patient — anxiety about treatment
- SCENARIO 3: English patient — for comparison

**Run:**
```bash
python test_integrated_empathy_agent.py
```

#### 3. `test_mock_umls.py` - Full System Tests
Tests complete pipeline with mock UMLS client.

---

## Validation Metrics

| Metric | Status | Notes |
|--------|--------|-------|
| Language Detection | ✓ | 4/4 test cases pass |
| German Distress Keywords | ✓ | 14 keywords implemented |
| English Distress Keywords | ✓ | 14 keywords implemented |
| Empathy Frame Templates | ✓ | 3 categories × 2 languages × distress variant |
| German Framing | ✓ | Native speaker review recommended |
| Agent Integration | ✓ | _execute_tool updated, tested |
| Mock UMLS Compatibility | ✓ | Works without API key |
| End-to-End German Flow | ✓ | Tested with distressed patient scenario |

---

## Extending the Empathy Layer

### Adding More Distress Keywords

**File:** `core/rules.py`

```python
DISTRESS_KEYWORDS = {
    # Existing English keywords...
    "scared",
    "terrified",
    # Add new ones:
    "petrified",      # New
    "apprehensive",   # New
}
```

### Adding More Supportive Markers

**File:** `core/rules.py`

```python
SUPPORTIVE_MARKERS = {
    # Existing English markers...
    "i understand",
    # Add new ones:
    "i hear you",           # New
    "your concerns are valid",  # New
}
```

### Adding More Framing Categories

**File:** `core/empathy_framing.py`

```python
def _frame_english(clinical_info: str, context: str, distressed: bool) -> str:
    frames = {
        # Existing categories...
        "side_effect": (...),
        "therapy_purpose": (...),
        # Add new category:
        "prognosis": (
            "I want to help you understand what to expect. "
            "{clinical_info} This information is based on research "
            "and your doctors will personalize it for your situation."
        ),
    }
```

### Adding New Languages

**Template for German is already there. To add Spanish:**

1. **Add Spanish distress keywords (core/rules.py):**
```python
DISTRESS_KEYWORDS = {
    # Existing German/English...
    # Add Spanish:
    "miedo",           # fear
    "nervioso",        # nervous
    "asustado",        # scared
    ...
}
```

2. **Update detect_language() for Spanish:**
```python
def detect_language(text: str) -> str:
    spanish_indicators = {"mi", "está", "qué", "cómo", "por qué", ...}
    # Count Spanish words too
```

3. **Add Spanish framing (core/empathy_framing.py):**
```python
def _frame_spanish(clinical_info: str, context: str, distressed: bool) -> str:
    frames = {
        "side_effect": (
            "Entiendo que esto es importante para usted. "
            "{clinical_info} Estos efectos secundarios son manejables..."
        ),
        ...
    }
```

---

## German Language Notes

### Native Speaker Considerations

The current German framing uses:
- **Formal "Sie" address** (respect, clinical setting)
- **Medical terminology** ("Nebenwirkung", "Therapie", "Datenbank")
- **Empathic connectors** ("Ich verstehe", "Es tut mir leid")

**For Better Naturalization:**
- Have German-speaking clinicians review phrasing
- Test with German-speaking patient groups
- Adjust tone if needed (formal vs. warm vs. reassuring)

### German-Specific Phrases

Current implementation uses:
- "Ich verstehe" (I understand) — validates patient
- "Es tut mir leid" (I'm sorry) — shows empathy
- "Sie sind nicht allein" (You're not alone) — provides support
- "Das ist völlig normal" (That's completely normal) — reassurance

---

## Known Limitations & Future Work

### Current Limitations

1. **Language Detection:**
   - Works for German/English; other languages default to English
   - Can occasionally misclassify mixed-language input

2. **Keyword-Based Distress:**
   - Simple keyword matching doesn't catch sarcasm or context
   - Example: "I'm not worried" contains "worried" but isn't expressing distress

3. **Framing Categories:**
   - Only 3 categories (side effect, therapy purpose, relationship)
   - May need more specific categories for complex relationships

### Planned Improvements

1. **Sentiment Analysis:**
   - Use transformer models (e.g., German BERT) for better distress detection
   - Handle negation ("not worried" → not distressed)

2. **Contextual Framing:**
   - Use LLM to dynamically generate frames based on patient profile
   - Personalize based on age, experience level

3. **Multi-Language:**
   - Add French, Italian, Spanish (common languages in UMLS context)
   - Implement language-specific emotion detection

4. **User Profiling:**
   - Track patient emotional patterns over conversation
   - Adjust empathy intensity based on receptiveness

---

## Files Modified/Created

### New Files
- `core/empathy_framing.py` (180 lines)
- `test_empathy_pipeline.py` (300+ lines)
- `test_integrated_empathy_agent.py` (350+ lines)

### Modified Files
- `core/rules.py` — Updated with expanded `detect_language()`, added German keywords
- `core/agent_engine.py` — Updated `_execute_tool()` signature, added empathy framing to query_umls_ontology handler

### Unchanged Core Files
- `core/umls_client.py` — UMLS API communication (no changes needed)
- `core/umls_client_mock.py` — Mock for testing (no changes needed)
- `core/ontology_tool.py` — Verification wrapper (no changes needed)

---

## Clinical Validation Checklist

- [ ] German-speaking clinician reviews phrasing
- [ ] Patient testing with German-speaking cohort
- [ ] Validate that empathy doesn't compromise clinical accuracy
- [ ] Test with various distress levels (mild, moderate, severe)
- [ ] A/B testing: empathy-enabled vs. clinical-only responses
- [ ] Measure patient satisfaction/trust scores
- [ ] Long-term conversation quality assessment

---

## References

### Related Code Sections
- Language detection: [core/rules.py](core/rules.py) - `detect_language()`
- Distress detection: [core/rules.py](core/rules.py) - `DISTRESS_KEYWORDS`, `sentiment_analyzer()`
- Empathy framing: [core/empathy_framing.py](core/empathy_framing.py)
- Agent integration: [core/agent_engine.py](core/agent_engine.py) - `_execute_tool()` method

### Testing
- Unit tests: [test_empathy_pipeline.py](test_empathy_pipeline.py)
- Integration tests: [test_integrated_empathy_agent.py](test_integrated_empathy_agent.py)
- System tests: [test_mock_umls.py](test_mock_umls.py)

---

## Summary

The empathy layer transforms a clinically valid information system into an emotionally intelligent healthcare assistant by:

1. **Detecting user language** → Respond in their language
2. **Detecting user distress** → Adjust tone and reassurance level
3. **Framing clinical facts emotionally** → Make information feel supportive
4. **Integrating into the workflow** → No disruption to existing TAO loop

The result: **Evidence-based medical information delivered with compassion.**
