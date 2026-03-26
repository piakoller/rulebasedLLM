
import requests
import json
from rules import apply_rules
from dialogue_manager import DialogueStateManager
from graph_rag import extract_entities, retrieve_context

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
    while True:
        user_message = input("You: ")
        if user_message.lower() in ["exit", "quit"]:
            print("Exiting chat.")
            break
        # Apply rules via dialogue state manager
        rule_response = dsm.handle_message(user_message, apply_rules)
        if rule_response:
            print(f"Bot (rule): {rule_response}")
            continue
        # Otherwise, send to Ollama
        try:
            # GraphRAG Integration
            entities = extract_entities(user_message, model=model)
            context = ""
            if entities:
                context = retrieve_context(entities)
                if context:
                    print(f"[GraphRAG Context Retrieved for: {', '.join(entities)}]")
            
            response = ollama_chat(model, user_message, context=context)
            print(f"Bot (model): {response}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Change 'gpt-oss:20b' to any model you have in Ollama
    chat_loop("gpt-oss:20b")
