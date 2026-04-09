# Empathic LLM with DPO Study System

A clinical conversational agent for nuclear medicine patients with integrated Direct Preference Optimization (DPO) data collection infrastructure. The system combines hybrid rule-based and LLM-driven responses with built-in preference learning and iterative improvement through collected human feedback.

## Project Overview

This repository contains:
- **Conversational Agent**: Frame-based dialogue manager with rule-based empathy layer and GraphRAG fact verification
- **Tool Integration**: LLM-callable tools for dynamic patient context retrieval and knowledge graph queries
- **DPO Study System**: Streamlit interface for collecting human preference data on response pairs
- **Analysis Pipeline**: Post-collection analysis, statistics, and conversion to training formats (DPO/SFT)
- **Sample Questions**: Pre-curated 90-question library across clinical categories for consistent testing

## Directory Structure

```
rulebasedLLM/
├── README.md                          # This file
├── requirements_study.txt             # Python dependencies
│
├── docs/                              # Documentation
│   ├── QUICKSTART.md                 # 30-second setup guide
│   ├── DPO_STUDY_GUIDE.md            # Implementation guide and troubleshooting
│   ├── SYSTEM_SUMMARY.md             # Architecture and workflow overview
│   ├── STUDY_UI_SETUP.md             # Detailed UI setup and configuration
│   └── USING_SAMPLE_QUESTIONS.md     # Sample questions library usage
│
├── ui/                                # User interfaces
│   └── study_ui.py                   # Streamlit preference data collection interface
│
├── core/                              # Core agent and dialogue engines
│   ├── agent_engine.py               # Agentic orchestrator with tool integration
│   ├── dialogue_manager.py           # Lightweight state manager
│   ├── frame_dialogue_manager.py     # Frame-based JSON dialogue manager
│   ├── rules.py                      # Rule logic (distress, empathy, safety)
│   ├── graph_rag.py                  # GraphRAG and fact verification
│   ├── ollama_chat.py                # Main chat loop (rules + graph + LLM)
│   ├── ollama_agent_chat.py          # Agentic chat with frame JSON output
│   ├── demo_dpo_system.py            # 4 worked examples of system usage
│   └── example_tool_calls.py         # Tool call syntax examples
│
├── tools/                             # Analysis and utility tools
│   ├── analyze_study_data.py         # Post-collection preference analysis
│   ├── prepare_dpo_data.py           # Convert study data to training formats
│   └── sample_questions_util.py      # Question library management utility
│
└── data/                              # Configuration and data files
    ├── sample_questions.json          # 90 clinical questions (9 categories)
    ├── frame_prompt.txt               # LLM steering prompt
    └── context/
        └── static_patient_records.json # De-identified patient context
```

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements_study.txt
```

### 2. Launch the study UI
```bash
streamlit run ui/study_ui.py
```
The interface opens at `http://localhost:8501`. 

**Quick workflow:**
1. Enter a question or load from sample library
2. Click "Generate Answers" to get original and revised responses
3. Compare side-by-side (randomized A/B assignment)
4. Select preferred answer and click "Log Preference"
5. Results auto-save to `study_data.jsonl`

### 3. Access sample questions
```bash
# View all 90 questions
python tools/sample_questions_util.py all

# Filter by category
python tools/sample_questions_util.py oncology_and_cancer

# Get random question
python tools/sample_questions_util.py random

# Export to CSV
python tools/sample_questions_util.py export csv
```

### 4. Analyze collected preferences
```bash
python tools/analyze_study_data.py
```
Generates: preference statistics, position bias detection, answer quality metrics

### 5. Prepare training data
```bash
python tools/prepare_dpo_data.py
```
Outputs:
- `dpo_training_data.jsonl` - for trl.DPOTrainer
- `sft_training_data.jsonl` - SFT format (preferred answers only)
- `preference_training_data.jsonl` - All preferences with metadata

## Core Systems

### Agent Architecture

Three-layer hybrid system:

1. **Dialogue Control** (`frame_dialogue_manager.py`)
   - Structured conversation flow using JSON frames
   - Context-aware branching based on user responses

2. **Safety & Tone** (`rules.py`)
   - Distress detection (scared, terrified, pain, anxious, worried)
   - Mandatory empathy prefixes for distressed users
   - Medical claim validation

3. **Fact Verification** (`graph_rag.py`)
   - Entity extraction from user messages
   - Knowledge graph retrieval (NetworkX-based)
   - Response verification against established relationships

4. **Tool Integration** (`agent_engine.py`)
   - ACTION syntax for dynamic tool calls (e.g., `ACTION: get_patient_context(patient_id="A")`)
   - Three available tools: `get_patient_context`, `search_knowledge_graph`, `verify_fact`
   - Observation capture and response refinement

### DPO Study System

**Data Collection** (`study_ui.py`):
- Dual-response comparison: original draft vs. revised response
- Random 50/50 A/B assignment to prevent position bias
- Auto-logging to append-only `study_data.jsonl`
- Cached engine initialization for performance

**Analysis** (`analyze_study_data.py`):
- Preference distribution and statistics
- Position bias detection
- Revision effectiveness (did revision change preference?)
- Answer quality metrics

**Training Data Export** (`prepare_dpo_data.py`):
- Convert preferences to DPO format (chosen/rejected pairs)
- SFT format (preferred responses only)
- Preference format (all info with metadata)

### Sample Questions Library

**Content** (`data/sample_questions.json`):
- 90 clinical questions across 9 categories
- Categories:
  - Oncology and Cancer (treatment, prognosis, side effects)
  - Nuclear Medicine Theranostics (procedures, isotopes)
  - Symptoms and Side Effects (management, timeline)
  - Treatment Planning and Monitoring (protocols, expectations)
  - Psychosocial and Emotional (coping, support resources)
  - Recovery and Long-term Outcomes (lifestyle, follow-up)
  - Treatment Modalities (types, approaches)
  - Practical Questions (logistics, scheduling, costs)
  - Misconceptions and Clarifications (myths vs. facts)

**Management** (`tools/sample_questions_util.py`):
- View all or filter by category
- Get random questions for testing
- Export to CSV or TXT formats
- Perfect for consistent UI/UX testing

## Documentation

Start here based on your role:

- **[QUICKSTART.md](docs/QUICKSTART.md)** (5 min)
  - 30-second setup guide
  - Core commands and entry points
  - Troubleshooting first steps

- **[DPO_STUDY_GUIDE.md](docs/DPO_STUDY_GUIDE.md)** (20 min)
  - Complete implementation walkthrough
  - Data flow overview
  - Customization examples
  - Common troubleshooting scenarios

- **[SYSTEM_SUMMARY.md](docs/SYSTEM_SUMMARY.md)** (15 min)
  - Architecture overview
  - Component responsibilities
  - Workflow diagram and description
  - Integration points

- **[STUDY_UI_SETUP.md](docs/STUDY_UI_SETUP.md)** (10 min)
  - Detailed UI configuration
  - UI state management and caching
  - Session handling
  - Advanced options

- **[USING_SAMPLE_QUESTIONS.md](docs/USING_SAMPLE_QUESTIONS.md)** (10 min)
  - Sample questions library structure
  - Access methods (code and CLI)
  - Category descriptions
  - Custom question addition

## Key Features

✅ **Hybrid Control System**
- Rule-based safety constraints + LLM flexibility
- Graph-verified facts prevent hallucinations
- Distress detection triggers empathy prefixes

✅ **Tool Integration**
- LLM can call tools during reasoning
- Dynamic patient context retrieval
- Knowledge graph queries via ACTION syntax

✅ **DPO Study Infrastructure**
- Minimalist UI for preference collection
- Dual-response comparison (original vs. revision)
- Automatic position bias prevention
- Append-only data logging

✅ **Analysis & Training Ready**
- Post-collection statistics and insights
- Conversion to multiple training formats
- Ready for trl.DPOTrainer integration

✅ **Sample Questions Library**
- 90 pre-curated clinical questions
- 9 categories for comprehensive testing
- Multiple access methods (CLI, code, API)

## Technical Stack

- **Core**: Python 3.8+, Pydantic for type safety
- **LLM**: Ollama (local inference)
- **UI**: Streamlit (minimalist, caching-optimized)
- **Graph**: NetworkX (knowledge representation)
- **Training**: Integration ready for HuggingFace trl.DPOTrainer
- **Data**: Append-only JSONL (study_data.jsonl)

## Data Files

- `study_data.jsonl` - Auto-generated during study collection, append-only
- `dpo_training_data.jsonl` - Auto-generated from preference analysis
- `sft_training_data.jsonl` - Auto-generated, SFT format
- `preference_training_data.jsonl` - Auto-generated, full metadata

## Typical Workflow

1. **Setup** → Install dependencies, run `requirements_study.txt`
2. **Demo** → Run `core/demo_dpo_system.py` to see 4 worked examples
3. **Study** → Launch `streamlit run ui/study_ui.py`
4. **Collect** → Use sample questions or custom prompts to gather preferences
5. **Analyze** → Run `tools/analyze_study_data.py` after collection
6. **Train** → Export to training format and integrate with trl.DPOTrainer

## References

- [Demo Examples](core/demo_dpo_system.py) - 4 worked system examples
- [Tool Syntax](core/example_tool_calls.py) - ACTION: format and parsing
- [Clinical Context](data/context/static_patient_records.json) - Patient personalization data

## License & Attribution

This is a research prototype combining clinical AI safety principles with direct preference optimization techniques.

This is designed to keep the system clinically conservative.

## Frame-based dialogue management

The frame system in `frame_dialogue_manager.py` and `frame_prompt.txt` structures the assistant around clinically useful conversation frames.

### Frames

- `greeting` - opens the conversation and sets a supportive tone
- `emotion_check` - detects emotion and validates the patient
- `therapy_explanation` - explains the therapy in short, understandable chunks
- `safety_instructions` - provides general safety information
- `dosimetry_explanation` - explains dosimetry in high-level terms
- `closing` - ends the conversation with reassurance and openness

### SPIKES mapping in the prompt

The prompt now explicitly integrates parts of the SPIKES protocol:

- P - Perception is represented in `emotion_check` through the `patient_perception` slot
- K - Knowledge is represented in `therapy_explanation` through the chunking constraint

This reflects the clinical principle of asking what the patient already understands before explaining more, then delivering information in small, checkable parts.

### Why the frame system matters

The frame manager ensures the LLM does not freely improvise the conversation flow. It must:

- stay inside the active frame
- fill required slots
- ask follow-up questions when needed
- avoid forbidden content such as dosing or prognosis

## Hybrid empathy layer

The empathy layer was added in `rules.py` and is designed to intervene before the model output is shown to the user.

### Distress detection

The `sentiment_analyzer()` rule scans the user message for distress-related words such as:

- scared
- terrified
- fear
- afraid
- anxious
- worried
- panic
- pain
- suffering
- overwhelmed
- distressed

If one of these appears, the rule returns a mandatory empathy prefix. That prefix is prepended to the final response, regardless of what the LLM generates.

### Why this matters

In clinical conversation, tone is not optional. If a patient sounds scared or in pain, the bot should not answer in a cold or purely factual way. The rule layer guarantees a supportive opening even when the model output is terse or overly technical.

## Document-driven GraphRAG

The `graph_rag.py` module builds a knowledge graph from provided documents instead of relying only on a fixed manual graph.

### Document discovery

By default, the graph builder searches these folders inside `rulebasedLLM`:

- `context`
- `docs`
- `data`

You can also override the search path with the `GRAPH_RAG_DOCUMENT_ROOTS` environment variable.

Supported file types:

- `.pdf`
- `.txt`
- `.md`
- `.markdown`

### How ingestion works

For each document:

1. The text is loaded.
2. It is normalized and split into chunks.
3. Each chunk is sent to Ollama with a structured extraction prompt.
4. Ollama returns JSON with entities and relations.
5. The entities become graph nodes.
6. The relations become graph edges.
7. Source metadata is stored on nodes and edges so the origin of each fact remains visible.

If no documents are found, the module falls back to a small built-in clinical graph so the chatbot still works.

### Why a graph is useful

The graph is used for:

- retrieving concept neighborhoods around extracted entities
- checking whether the assistant mentions supported relationships
- providing a conservative safety layer against hallucinated medical claims

### Response verification

`verify_llm_response(response, entities)` checks whether the relationships mentioned in the model response are supported by the graph.

If the response appears to mention unsupported relationships, the system replaces it with a safe fallback such as:

- I want to keep this safe and only share what I can confirm from the provided document.
- If you want, I can explain the confirmed parts more simply or focus on one question at a time.

This is intentionally conservative. The verifier is designed to reduce risk, not to maximize coverage.

## Chat loop behavior

The main chat loop lives in `ollama_chat.py`.

### What it does

- loads the document-driven graph once at startup
- reads user input in a loop
- applies rules first
- extracts entities for GraphRAG retrieval
- sends the user message plus graph context to Ollama
- validates the answer against the graph
- prepends the empathy prefix when required
- prints the final response

### Agentic loop

The newer `ollama_agent_chat.py` loop uses `agent_engine.py` and adds a Thought-Action-Observation pattern:

1. Analyze user intent, distress, and forbidden topics.
2. Retrieve the relevant de-identified static patient context.
3. Verify supporting medical facts against the NetworkX graph.
4. Ask Ollama to produce a JSON frame response.
5. Check empathy compliance and graph safety.
6. Retry once with revision notes if the draft is too clinical or unsafe.
7. Return the final JSON response that matches `frame_prompt.txt`.

### Important behavior change

The chatbot no longer treats rules and model output as mutually exclusive.

Instead:

- rules can add mandatory tone or safety text
- the model generates the main answer
- the final response is composed from both

This is the core of the hybrid design.

## Safety constraints

The assistant is constrained to remain clinically cautious.

It should not provide:

- specific dosing instructions
- prognosis predictions
- numerical dosimetry values
- unsupported treatment claims
- personalized medical advice beyond the document-backed level

If a question requires clinical details that are not present in the graph or prompt, the assistant should ask for clarification or provide a safe high-level answer.

## File-by-file details

### `rules.py`

Contains the rule engine.

Current responsibilities:

- detect distress and return a mandatory empathy prefix
- handle greeting and farewell rules
- provide simple rule outputs that can be merged with model output

### `frame_prompt.txt`

Defines the frame-based operating instructions for the clinical assistant.

Current responsibilities:

- describe each frame
- define required and optional slots
- forbid unsafe content
- map SPIKES concepts to the frame structure

### `graph_rag.py`

Handles all graph-related logic.

Current responsibilities:

- discover and read source documents
- chunk text for extraction
- call Ollama for entity and relation extraction
- build and maintain a NetworkX graph
- retrieve graph context for user questions
- verify generated responses against the graph

### `ollama_chat.py`

Runs the chatbot loop.

Current responsibilities:

- accept user input
- apply rule-based overrides
- retrieve graph context
- generate model output through Ollama
- merge rule and model responses
- display the final message

### `frame_dialogue_manager.py`

Handles the frame-based JSON conversation flow.

Current responsibilities:

- maintain conversation history
- send prompts to Ollama
- parse JSON frame output
- support structured slot filling

### `dialogue_manager.py`

Provides a lightweight finite-state machine for early rule-based interactions.

Current responsibilities:

- track conversation state
- classify user input
- route messages through rule handlers

## Setup

### 1. Install dependencies

Install the Python packages required for the chatbot and graph extraction.

### 2. Start Ollama

Make sure Ollama is running locally and that the model you want to use is available.

### 3. Add documents

Place your source documents in one of the supported folders, usually:

- `rulebasedLLM/context`

For example, if you want the graph to be built from `SPIKES.pdf`, place the file in that folder.

### 4. Run the chatbot

Start the chat loop from `ollama_chat.py`.

## Configuration

The graph layer can be configured with environment variables:

- `OLLAMA_URL` - Ollama chat endpoint
- `GRAPH_RAG_EXTRACTION_MODEL` - model used to extract entities and relations from document chunks
- `GRAPH_RAG_ANSWER_MODEL` - optional separate answer model setting
- `GRAPH_RAG_DOCUMENT_ROOTS` - comma-separated list of folders to scan for documents
- `OLLAMA_MODEL` - default model used by `agent_engine.py` and `ollama_agent_chat.py`

If these are not set, the project uses sensible local defaults.

## Current clinical scope

This project is designed for theranostics and patient communication. It is not a general medical advice system.

The assistant should stay within:

- supportive communication
- document-backed explanations
- general safety guidance
- high-level descriptions of therapy and dosimetry

It should avoid:

- dose calculation
- treatment planning specifics
- prognosis statements
- individualized medical decisions

## Design rationale

The system is intentionally layered because each layer solves a different problem:

- frames control conversation structure
- rules control tone and non-negotiable behavior
- graph retrieval controls factual grounding
- verification controls hallucination risk
- the LLM controls fluency and natural language quality

That combination makes the assistant more suitable for a clinical setting than a plain free-form chatbot.

## If you want to extend it

Good next steps include:

- saving the extracted graph to disk so it does not rebuild every run
- adding citation output that references document chunks directly
- refining the verifier with more precise relation extraction
- connecting the frame manager and GraphRAG into a single orchestrated pipeline
- adding unit tests for distress detection, graph verification, and safe fallback behavior

## Summary

This repository now combines:

- structured clinical dialogue via frames
- mandatory empathy behavior for distressed users
- document-driven GraphRAG for medical grounding
- graph-based verification to reduce hallucinations
- conservative safety rules to keep the bot clinically bounded

That is the intended operating model of the agent.
