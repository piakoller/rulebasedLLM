# Empathic LLM: Clinical Theranostics Conversational Agent

This project is a sophisticated, prototype conversational agent designed for nuclear medicine patients undergoing theranostics and targeted therapies. It safely blends structured dialogue management with real-time Knowledge Graph Retrieval (GraphRAG) and an empathetic Large Language Model (LLM) powered by Ollama.

## Core Features Breakdown

### 1. Frame-Based Dialogue Manager (`frame_dialogue_manager.py` & `frame_prompt.txt`)
Unlike a standard unstructured ChatGPT clone, this system forces the LLM to follow a strict, clinical **"Frame-Based Architecture"**. 
* **How it works:** The conversation is broken down into specific psychological and informational "frames" (e.g., `greeting` -> `emotion_check` -> `therapy_explanation` -> `safety_instructions`).
* **Slot Filling:** The LLM actively manages missing information (slots) and must output a strict JSON payload on every message. It answers direct clinical questions first, then smoothly guides the patient back to filling the required active slots, such as validating their emotions or asking about their specific medication.

### 2. Clinical GraphRAG (`graph_rag.py`)
To prevent the LLM from "hallucinating" or providing unsourced medical advice, the project uses a specialized **Knowledge Graph Retrieval-Augmented Generation (GraphRAG)** system.
* **How it works:** When a user asks a question, the LLM first acts as an Entity Extractor to pull out keywords. It then searches a hardcoded internal Clinical Graph (built via `networkx`).
* **The Graph Base:** The graph perfectly maps out the strict relationships between clinical concepts like **Nuclear Medicine, Theranostics, Dosimetry, PRRT**, and **Lutetium-177**. If a match is found, the exact, true relationships are injected into the LLM's prompt context, forcing its answer to remain medically accurate to the graph.

### 3. Legacy Rule-Based Fallbacks (`dialogue_manager.py`, `rules.py`, `ollama_chat.py`)
The project initially started with a standard **Finite State Machine (FSM)** and manual keyword rules. 
* `dialogue_manager.py` uses hardcoded states (`"START"`, `"GREETED"`) rather than LLM-interpreted frames.
* `rules.py` provides exact string-matching responses for specific triggers. 
* `ollama_chat.py` demonstrates how to cleanly interleave these rigid rules with the dynamic LLM output.

## How it comes together
The ultimate goal of the project is to create an LLM that feels incredibly warm, empathetic, and human, while remaining **safely caged** by strict JSON frame boundaries and verifiable clinical GraphRAG data—ensuring it acts as a perfect sidekick for patients navigating the complexities of modern radioactive therapies.
