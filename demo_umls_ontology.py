"""Demo script showing UMLS-based ontology verification in the clinical AI assistant.

This script demonstrates:
1. Direct UMLS API client usage
2. Ontology tool wrapper for clinical relationship verification
3. Integration with the agent engine
4. Error handling and retry logic

To run this demo:
1. Set UMLS_API_KEY environment variable
2. Run: python demo_umls_ontology.py
"""

import os
import sys
from pathlib import Path

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent / "core"))

import logging
from umls_client import UMLSClient, UMLSClientError
from ontology_tool import verify_clinical_relationship, verify_multiple_relationships, format_umls_verification_for_llm

# Configure logging for demo
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def demo_umls_client():
    """Demonstrate direct UMLS client usage."""
    print("\n" + "="*70)
    print("DEMO 1: Direct UMLS Client Usage")
    print("="*70)
    
    try:
        client = UMLSClient()
    except UMLSClientError as e:
        print(f"ERROR: {e}")
        print("\nTo run this demo, set the UMLS_API_KEY environment variable:")
        print("  export UMLS_API_KEY='your-api-key'")
        return False
    
    # Example 1: Search for a radioisotope
    print("\n1. Searching for 'Lutetium Lu 177 dotatate'...")
    cui = client.search_concept("Lutetium Lu 177 dotatate")
    if cui:
        print(f"   ✓ Found CUI: {cui}")
        
        # Get relationships
        print(f"\n2. Retrieving relationships for CUI {cui}...")
        relations = client.get_concept_relations(cui)
        print(f"   ✓ Found {len(relations)} relationships")
        
        if relations:
            print("\n   First 5 relationships:")
            for i, rel in enumerate(relations[:5], 1):
                print(f"     {i}. {rel['relationLabel']}: {rel['relatedConceptName']}")
    else:
        print("   ✗ Concept not found")
    
    # Example 2: Search for a side effect
    print("\n3. Searching for 'Renal Toxicity'...")
    cui = client.search_concept("Renal Toxicity")
    if cui:
        print(f"   ✓ Found CUI: {cui}")
    else:
        print("   ✗ Concept not found")
    
    # Example 3: Search for a therapy
    print("\n4. Searching for 'PRRT'...")
    cui = client.search_concept("PRRT")
    if cui:
        print(f"   ✓ Found CUI: {cui}")
    else:
        print("   ✗ Concept not found")
    
    client.close()
    return True


def demo_ontology_tool():
    """Demonstrate the ontology verification wrapper."""
    print("\n" + "="*70)
    print("DEMO 2: Ontology Verification Wrapper")
    print("="*70)
    
    test_terms = [
        "Lutetium Lu 177 dotatate",
        "Radioactive decay",
        "Kidney function",
        "Positron emission tomography",
    ]
    
    print("\nVerifying multiple clinical terms...")
    results = verify_multiple_relationships(test_terms)
    
    for term, result in results.items():
        status = "✓" if result.found else "✗"
        print(f"\n{status} {term}")
        if result.found:
            print(f"   CUI: {result.cui}")
            print(f"   Relationships: {len(result.relationships)}")
            if result.relationships:
                for rel in result.relationships[:3]:
                    print(f"     • {rel['relationLabel']}: {rel['relatedConceptName']}")
        else:
            print(f"   Error: {result.error}")


def demo_llm_formatted_output():
    """Demonstrate LLM-friendly formatting of verification results."""
    print("\n" + "="*70)
    print("DEMO 3: LLM-Formatted Ontology Output")
    print("="*70)
    
    print("\nVerifying terms for LLM integration...")
    terms = ["Lutetium Lu 177 dotatate", "Renal Toxicity", "Unknown Term"]
    results = [verify_clinical_relationship(term) for term in terms]
    
    formatted = format_umls_verification_for_llm(results)
    print("\nFormatted output for LLM prompt:")
    print(formatted)


def demo_agent_tool_call():
    """Demonstrate how the tool would be called from the agent."""
    print("\n" + "="*70)
    print("DEMO 4: Agent Tool Call Example (Simulated)")
    print("="*70)
    
    print("""
The agent can call the UMLS ontology tool like this:

    ACTION: query_umls_ontology(term="Lutetium Lu 177 dotatate")

When executed, the agent engine's _execute_tool method will:

1. Extract the term from the function arguments
2. Call verify_clinical_relationship(term)
3. Return a ToolResult with:
   - success: True/False depending on whether the term was found
   - result: Contains CUI, relationships, and formatted summary
   - error: Any error message if lookup failed

The formatted summary is then added to the observation history
for the LLM to use in its next reasoning step.
    """)
    
    print("\nExample ToolResult structure:")
    result = verify_clinical_relationship("Lutetium Lu 177 dotatate")
    
    if result.found:
        print(f"""
    {{
        "tool_name": "query_umls_ontology",
        "success": true,
        "result": {{
            "term": "{result.term}",
            "cui": "{result.cui}",
            "found": true,
            "relationships": [...],  # List of verified relationships
            "summary": "{result.summary[:80]}..."
        }},
        "error": ""
    }}
        """)
    else:
        print(f"""
    {{
        "tool_name": "query_umls_ontology",
        "success": false,
        "result": {{}},
        "error": "{result.error}"
    }}
        """)


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("UMLS ONTOLOGY INTEGRATION DEMO")
    print("=" * 70)
    print("""
This demo showcases the new UMLS-based ontology verification system
for the clinical AI assistant. The system replaces LLM-guessing with
verified medical relationships from the NIH UMLS database.
    """)
    
    # Check environment variable
    if not os.getenv("UMLS_API_KEY"):
        print("⚠ WARNING: UMLS_API_KEY not set")
        print("   Some demos will not work without a valid API key.")
        print("   Get one at: https://uts.nlm.nih.gov/uts/\n")
    
    # Run demos
    has_api_key = bool(os.getenv("UMLS_API_KEY"))
    
    if has_api_key:
        success = demo_umls_client()
        if success:
            demo_ontology_tool()
            demo_llm_formatted_output()
    else:
        print("Skipping API-dependent demos (APIs require valid UMLS_API_KEY)")
    
    demo_agent_tool_call()
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("""
Next steps:

1. Set your UMLS API key:
   export UMLS_API_KEY='your-key-here'

2. Verify the agent engine integration:
   grep -n "query_umls_ontology" core/agent_engine.py

3. The agent will now:
   - Automatically call UMLS for medical term verification
   - Return verified relationships to the LLM
   - Enforce constraints: "If not verified by UMLS, you cannot confirm it"

For more information:
  - UMLS API docs: https://documentation.uts.nlm.nih.gov/rest/home.html
  - Read core/umls_client.py for implementation details
  - Read core/ontology_tool.py for the wrapper logic
    """)


if __name__ == "__main__":
    main()
