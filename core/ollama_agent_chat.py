"""Agentic chat loop for the clinical GraphRAG assistant.

This loop drives the Thought-Action-Observation agent engine and prints the
final frame JSON so the output stays aligned with frame_prompt.txt.
"""

from __future__ import annotations

from agent_engine import AgentEngine


def chat_loop(model: str = "gemma3:27b"):
    engine = AgentEngine(model=model)
    print(f"Chatting with Ollama model: {model}")
    print(f"[GraphRAG] Current document roots: {', '.join(str(path) for path in engine.document_roots)}")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting chat.")
            break

        if user_message.lower() in {"exit", "quit"}:
            print("Exiting chat.")
            break

        result = engine.handle_message(user_message)
        print(result.model_dump_json(indent=2, ensure_ascii=False))
        print("-" * 60)


if __name__ == "__main__":
    chat_loop()
