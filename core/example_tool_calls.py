#!/usr/bin/env python3
"""
Example demonstrating tool calls in the orchestrator.

This shows how the LLM can invoke tools like get_patient_context(),
search_knowledge_graph(), and verify_fact() during reasoning.
"""

from agent_engine import AgentEngine, parse_tool_call

def demonstrate_tool_call_parsing():
    """Show how tool calls are parsed from LLM output."""
    print("=" * 70)
    print("TOOL CALL PARSING EXAMPLES")
    print("=" * 70)
    
    examples = [
        'ACTION: get_patient_context(patient_id="Patient A")',
        'ACTION: search_knowledge_graph(query="radiation therapy side effects")',
        'ACTION: verify_fact(statement="The therapy may cause fatigue")',
        'This is not a tool call',
        'ACTION: unknown_tool(arg="value")',  # Will parse but fail execution
    ]
    
    for example in examples:
        tool_call = parse_tool_call(example)
        if tool_call:
            print(f"\n✓ Parsed: {example}")
            print(f"  Function: {tool_call.function_name}")
            print(f"  Arguments: {tool_call.arguments}")
        else:
            print(f"\n✗ Not a tool call: {example}")


def demonstrate_tool_execution():
    """Show how tools are executed by the orchestrator."""
    print("\n" + "=" * 70)
    print("TOOL EXECUTION EXAMPLES")
    print("=" * 70)
    
    engine = AgentEngine(model="gemma3:27b")
    
    # Example 1: get_patient_context
    print("\n[1] Executing: get_patient_context(patient_id='Patient A')")
    tool_call = parse_tool_call('ACTION: get_patient_context(patient_id="Patient A")')
    if tool_call:
        result = engine._execute_tool(tool_call)
        print(f"    Success: {result.success}")
        print(f"    Result keys: {list(result.result.keys()) if result.result else 'None'}")
        if result.result and result.result.get("summary"):
            print(f"    Summary: {result.result['summary'][:100]}...")
    
    # Example 2: search_knowledge_graph
    print("\n[2] Executing: search_knowledge_graph(query='therapy')")
    tool_call = parse_tool_call('ACTION: search_knowledge_graph(query="therapy")')
    if tool_call:
        result = engine._execute_tool(tool_call)
        print(f"    Success: {result.success}")
        if result.result:
            print(f"    Answer preview: {result.result.get('answer', '')[:80]}...")
            print(f"    Verified: {result.result.get('verified')}")
    
    # Example 3: Unknown tool
    print("\n[3] Executing: unknown_tool(arg='value')")
    tool_call = parse_tool_call('ACTION: unknown_tool(arg="value")')
    if tool_call:
        result = engine._execute_tool(tool_call)
        print(f"    Success: {result.success}")
        print(f"    Error: {result.error}")


def demonstrate_orchestrator_flow():
    """Show how the orchestrator handles user messages with tool calls."""
    print("\n" + "=" * 70)
    print("ORCHESTRATOR FLOW WITH TOOL CALLS")
    print("=" * 70)
    
    engine = AgentEngine(model="gemma3:27b")
    
    # The orchestrator automatically detects and executes tool calls
    user_message = "What can you tell me about the therapy for patients like Patient A?"
    print(f"\nUser: {user_message}")
    print("\nProcessing with AgentEngine.handle_message():")
    print("- Input analysis")
    print("- Tool call detection and execution (if LLM outputs ACTION: lines)")
    print("- Empathy and safety compliance checking")
    print("- Response generation")
    
    try:
        result = engine.handle_message(user_message)
        print(f"\n✓ Response generated:")
        print(f"  - Active frame: {result.active_frame}")
        print(f"  - Agent response: {result.agent_response}")
        print(f"  - Next frame: {result.next_frame}")
        print(f"  - Filled slots: {list(result.filled_slots.keys())}")
    except Exception as e:
        print(f"\nNote: Example requires Ollama to be running.")
        print(f"Error: {type(e).__name__}")


if __name__ == "__main__":
    print("\nTOOL CALL ORCHESTRATOR EXAMPLES\n")
    
    demonstrate_tool_call_parsing()
    demonstrate_tool_execution()
    demonstrate_orchestrator_flow()
    
    print("\n" + "=" * 70)
    print("For more information, see TOOL_CALLS.md")
    print("=" * 70)
