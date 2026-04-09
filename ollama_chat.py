
import json
from pathlib import Path

import requests

from rules import apply_rules
from dialogue_manager import DialogueStateManager
import graph_rag


DOCUMENT_ROOT = Path(__file__).resolve().parent / "context"

# Function to chat with Ollama model
def ollama_chat(model: str, user_message: str, context: str = "", ollama_url: str = "http://localhost:11434/api/chat"):    
    messages = []
    if context:
        messages.append({"role": "system", "content": f"Use the following knowledge graph context to answer the user: {context}"})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False # Avoid streaming for simpler processing
    }
    response = requests.post(ollama_url, json=payload)
    response.raise_for_status()
    data = response.json()
    # Ollama returns a streaming response; handle accordingly if needed
    if 'message' in data:
        return data['message']['content']
    elif 'response' in data:
        return data['response']
    else:
        return str(data)

def chat_loop(model: str):
    print(f"Chatting with Ollama model: {model}")
    dsm = DialogueStateManager()
    knowledge_graph = graph_rag.get_knowledge_graph([DOCUMENT_ROOT])
    if knowledge_graph.number_of_nodes() == 0:
        print(f"[GraphRAG] No supported documents found in: {DOCUMENT_ROOT}")
    else:
        print(f"[GraphRAG] Loaded document graph from: {DOCUMENT_ROOT}")

    while True:
        user_message = input("You: ")
        if user_message.lower() in ["exit", "quit"]:
            print("Exiting chat.")
            break

        rule_response = dsm.handle_message(user_message, apply_rules)
        mandatory_prefix = ""
        direct_response = None
        stop_chat = False

        if isinstance(rule_response, dict):
            mandatory_prefix = rule_response.get("mandatory_prefix", "")
            direct_response = rule_response.get("direct_response")
            stop_chat = bool(rule_response.get("stop_chat", False))
        elif isinstance(rule_response, str):
            direct_response = rule_response

        if stop_chat and direct_response:
            print(f"Bot (rule): {direct_response}")
            continue

        # Otherwise, send to Ollama
        try:
            # GraphRAG Integration
            entities = graph_rag.extract_entities(user_message, model=model)
            context = ""
            if entities:
                context = graph_rag.retrieve_context(entities, graph=knowledge_graph)
                if context:
                    print(f"[GraphRAG Context Retrieved for: {', '.join(entities)}]")
            
            response = ollama_chat(model, user_message, context=context)
            verification = graph_rag.verify_llm_response(response, entities, graph=knowledge_graph)
            if not verification.get("verified", True):
                response = verification.get("safe_fallback", response)

            final_response = f"{mandatory_prefix}{response}".strip()
            if direct_response and not mandatory_prefix:
                final_response = f"{direct_response} {final_response}".strip()

            print(f"Bot (model): {final_response}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Change 'gemma3:27b' to any model you have in Ollama
    chat_loop("gemma3:27b")
