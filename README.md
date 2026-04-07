# Empathic LLM: Clinical Theranostics Conversational Agent

This project is a prototype conversational agent for nuclear medicine patients undergoing theranostics and related targeted therapies. It combines three layers of control:

- a frame-based dialogue manager for structured conversation flow
- a rule-based empathy layer for mandatory supportive language
- a GraphRAG layer for checking clinical facts against a knowledge graph built from documents

The goal is to keep the assistant warm and responsive while preventing unsafe medical output such as dosing, prognosis, or unsupported claims.

## What lives in this repository

- `frame_dialogue_manager.py` - frame-based JSON dialogue manager
- `frame_prompt.txt` - the frame prompt used to steer the LLM
- `dialogue_manager.py` - a lightweight finite-state manager used by the rule-based chatbot
- `rules.py` - rule logic, including the new distress detector and empathy prefix
- `graph_rag.py` - document-driven GraphRAG and response verification logic
- `ollama_chat.py` - the main chat loop that combines rules, graph retrieval, and Ollama responses
- `agent_engine.py` - the agentic Thought-Action-Observation orchestrator
- `ollama_agent_chat.py` - the agentic chat loop that prints the final frame JSON
- `context/static_patient_records.json` - local de-identified patient context for personalization

## High-level architecture

The chatbot runs as a layered pipeline:

1. The user enters a message.
2. `DialogueStateManager` updates the conversation state.
3. `rules.py` checks for rule triggers such as distress or farewell.
4. `graph_rag.py` extracts entities from the user message and retrieves related context from a NetworkX knowledge graph.
5. The agent engine looks up static patient context from a local JSON file.
6. Ollama generates a structured frame response using the graph context and patient context.
7. `verify_llm_response()` checks whether the medical relationships mentioned in the generated response are supported by the graph.
8. The final response is assembled from:
   - a mandatory empathy prefix, if distress was detected
   - the validated LLM response, or a safe fallback if the response appears unsupported

This means the chatbot is not purely rule-based and not purely generative. It is a hybrid system in which rules constrain tone, the graph constrains facts, and the LLM handles natural language generation.

## Conversation flow in practice

A typical interaction looks like this:

- The user asks a question or expresses concern.
- The sentiment rule checks for distress words such as scared, terrified, pain, worried, or anxious.
- If distress is detected, the assistant must begin with a supportive empathy prefix.
- The graph retriever extracts entities from the message and looks up related concepts in the knowledge graph.
- The LLM answers with that context in mind.
- The verifier checks whether the response mentions relationships that exist in the graph.
- If the answer looks hallucinated or unverified, the assistant falls back to a safe response that only states what can be confirmed.

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
