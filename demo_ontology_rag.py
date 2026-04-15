#!/usr/bin/env python3
"""
Demo of the Ontology-Grounded RAG System for Clinical Nuclear Medicine.

This script demonstrates:
1. Entity extraction and mapping to medical ontology
2. Deterministic relationship verification
3. Integration with the AgentEngine tool system
"""

import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent / "core"))

import json
import ontology_rag
from agent_engine import parse_tool_call, ToolResult, ToolCall


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def demo_entity_extraction():
    """Demonstrate entity extraction and mapping."""
    print_section("1. Entity Extraction & Mapping")
    
    test_queries = [
        "What are the side effects of Lutetium-177?",
        "Tell me about PRRT therapy",
        "How does kidney function relate to radiotherapy?",
    ]
    
    for query in test_queries:
        print(f"Query: \"{query}\"")
        entities = ontology_rag.extract_and_map_entities(query)
        
        if entities:
            print(f"  Mapped entities ({len(entities)}):")
            for entity in entities:
                print(f"    • {entity['name']}")
                print(f"      CUI: {entity['cui']}")
                print(f"      Type: {entity['type']}")
                print(f"      Matched term: {entity['matched_term']}")
        else:
            print("  No recognized medical entities found.")
        print()


def demo_relationship_verification():
    """Demonstrate ontology-based relationship verification."""
    print_section("2. Relationship Verification via Ontology")
    
    test_statements = [
        ("Luzetium-177 is used in PRRT", "What relationship exists between these concepts?"),
        ("PRRT may cause renal toxicity", "Is this relationship supported?"),
        ("Imaging is required for PRRT", "Can we verify this clinical relationship?"),
    ]
    
    for statement, question in test_statements:
        print(f"Statement: \"{statement}\"")
        print(f"Question: {question}\n")
        
        verification = ontology_rag.verify_statement_against_ontology(statement)
        print(f"  Verified: {'Yes' if verification['verified'] else 'No'}")
        print(f"  Confidence: {verification['confidence']:.0%}")
        if verification['extracted_entities']:
            print(f"  Entities found: {', '.join([e['name'] for e in verification['extracted_entities']])}")
        print(f"  Reason: {verification['reason']}")
        print()


def demo_tool_integration():
    """Demonstrate integration with AgentEngine tools."""
    print_section("3. Tool Integration with AgentEngine")
    
    test_tool_calls = [
        'ACTION: query_medical_ontology(terms="Lutetium-177 PRRT therapy")',
        'ACTION: query_medical_ontology(terms="kidney renal toxicity")',
        'ACTION: query_medical_ontology(terms="cancer imaging diagnostic")',
    ]
    
    print("Tool calls received from LLM:\n")
    for tool_call_str in test_tool_calls:
        print(f"Raw LLM output: {tool_call_str}")
        
        # Parse the tool call
        tool_call = parse_tool_call(tool_call_str)
        if tool_call:
            print(f"  ✓ Parsed successfully")
            print(f"    Function: {tool_call.function_name}")
            print(f"    Arguments: {tool_call.arguments}\n")
            
            # Execute the tool
            result = ontology_rag.query_medical_ontology(tool_call.arguments.get('terms', ''))
            print(f"  Tool Result:")
            print(f"    Success: {result.success}")
            if result.success and result.mapped_entities:
                print(f"    Mapped entities: {len(result.mapped_entities)}")
                for entity in result.mapped_entities:
                    print(f"      - {entity['name']} ({entity['cui']})")
            if result.relationships and not result.relationships.startswith("No"):
                print(f"    Relationships found (first 150 chars):")
                print(f"      {result.relationships[:150]}...")
            print()
        else:
            print(f"  ✗ Failed to parse tool call\n")


def demo_clinical_scenarios():
    """Demonstrate realistic clinical scenarios."""
    print_section("4. Clinical Scenarios")
    
    scenarios = [
        {
            "user_query": "What should patients expect from PRRT?",
            "ai_response": "I can explain that PRRT uses Lutetium-177, but I should verify the specific clinical relationships with the ontology first.",
        },
        {
            "user_query": "Is PRRT safe for patients with kidney problems?",
            "ai_response": "According to the medical ontology, PRRT may cause renal toxicity. Patients with existing kidney issues should discuss this with their care team.",
        },
        {
            "user_query": "How does this therapy work?",
            "ai_response": "The ontology confirms that PRRT treats cancer using Lutetium-177 with imaging. I can explain the concept simply while checking facts against established relationships.",
        },
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"Scenario {i}:")
        print(f"  Patient: \"{scenario['user_query']}\"")
        print(f"  AI Approach: {scenario['ai_response']}")
        print()


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("  ONTOLOGY-GROUNDED RAG FOR CLINICAL NUCLEAR MEDICINE")
    print("  Deterministic Medical Relationship Verification")
    print("="*70)
    
    try:
        demo_entity_extraction()
        demo_relationship_verification()
        demo_tool_integration()
        demo_clinical_scenarios()
        
        print_section("Summary")
        print("""
Key Benefits of Ontology-Grounded RAG:

1. DETERMINISTIC: No LLM guessing—all relationships come from static ontology
2. VERIFIABLE: Each clinical claim is traceable to defined relationships
3. SAFE: System explicitly states when relationships cannot be confirmed
4. AUDITABLE: Complete record of what ontology relationships were queried
5. EXTENSIBLE: Easy to add new concepts and relationships to the ontology

The Agent now:
  ✓ Maps user queries to medical ontology concepts (CUIs)
  ✓ Returns only ontology-verified relationships
  ✓ Refuses to make clinical claims without ontology support
  ✓ Explicitly tells users when claims cannot be confirmed
        """)
        
    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
