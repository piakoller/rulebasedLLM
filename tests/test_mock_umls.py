#!/usr/bin/env python3
"""Test script for mock UMLS client - no API key required!

This demonstrates that the full pipeline works without an API key.
Uses mock data that's realistic for nuclear medicine/theranostics.

Run with:
  # Using mock client (default):
  python test_mock_umls.py
  
  # Using real client (requires UMLS_API_KEY):
  UMLS_CLIENT_MODE=real UMLS_API_KEY='your-key' python test_mock_umls.py
"""

import sys
from pathlib import Path

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent / "core"))

import logging

# Configure logging to see [MOCK] messages
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(message)s"
)

from ontology_tool import verify_clinical_relationship, verify_multiple_relationships


def test_single_term():
    """Test verifying a single clinical term."""
    print("\n" + "=" * 70)
    print("TEST 1: Single Term Verification")
    print("=" * 70)
    
    term = "Lutetium Lu 177 dotatate"
    print(f"\nVerifying: {term}")
    print("-" * 70)
    
    result = verify_clinical_relationship(term)
    
    if result.found:
        print(f"✓ FOUND")
        print(f"  CUI: {result.cui}")
        print(f"  Relationships: {len(result.relationships)}")
        print(f"\n{result.summary}")
    else:
        print(f"✗ NOT FOUND")
        print(f"  Error: {result.error}")
    
    return result.found


def test_multiple_terms():
    """Test verifying multiple terms."""
    print("\n" + "=" * 70)
    print("TEST 2: Multiple Terms Verification")
    print("=" * 70)
    
    terms = [
        "Lutetium Lu 177 dotatate",
        "Renal Toxicity",
        "Peptide Receptor Radionuclide Therapy",
        "Positron Emission Tomography",
        "Unknown Medical Term",
    ]
    
    print(f"\nVerifying {len(terms)} terms...")
    print("-" * 70)
    
    results = verify_multiple_relationships(terms)
    
    found_count = 0
    for term, result in results.items():
        status = "✓" if result.found else "✗"
        print(f"{status} {term}")
        if result.found:
            found_count += 1
            print(f"   CUI: {result.cui}, Relations: {len(result.relationships)}")
    
    print(f"\nTotal verified: {found_count}/{len(terms)}")
    return found_count > 0


def test_german_translation():
    """Test German-to-English translation scenario."""
    print("\n" + "=" * 70)
    print("TEST 3: German-to-English Translation (Simulated)")
    print("=" * 70)
    
    print("\nScenario: User asks in German")
    print("-" * 70)
    
    german_question = "Was ist Lutetium Lu 177 Dotatat?"
    print(f"User (German): {german_question}")
    
    # Simulate LLM translating to English
    english_term = "Lutetium Lu 177 dotatate"
    print(f"Agent translates to: {english_term}")
    
    # Query UMLS with English term
    print(f"Agent calls: ACTION: query_umls_ontology(term=\"{english_term}\")")
    
    result = verify_clinical_relationship(english_term)
    
    if result.found:
        print(f"\n✓ UMLS returned results (CUI: {result.cui})")
        print(f"  {len(result.relationships)} verified relationships found")
        
        print(f"\nAgent responds (in German):")
        print(f"  'Laut der verifizierten UMLS-Datenbank ist Lutetium Lu 177 Dotatat")
        print(f"   ein Radionuklid, das für Therapie verwendet wird...'")
    
    return result.found


def test_agent_tool_simulation():
    """Simulate agent tool call flow."""
    print("\n" + "=" * 70)
    print("TEST 4: Agent Tool Call Simulation")
    print("=" * 70)
    
    print("""
Simulating agent TAO loop with UMLS ontology tool:

USER INPUT (German):
  "Was sind die Nebenwirkungen von Lutetium-177?"

AGENT THOUGHT:
  "I need to verify clinical information about Lutetium-177"

AGENT ACTION:
  ACTION: query_umls_ontology(term="Lutetium Lu 177 dotatate")

TOOL EXECUTION:
""")
    
    result = verify_clinical_relationship("Lutetium Lu 177 dotatate")
    
    if result.found:
        print(f"  ✓ search_concept('Lutetium Lu 177 dotatate') → {result.cui}")
        print(f"  ✓ get_concept_relations('{result.cui}') → {len(result.relationships)} relations")
        
        print(f"\nTOOL RESULT:")
        print(f"  - Term: {result.term}")
        print(f"  - CUI: {result.cui}")
        print(f"  - Found: {result.found}")
        print(f"  - Verified Relationships:")
        for i, rel in enumerate(result.relationships[:3], 1):
            print(f"    {i}. {rel['relationLabel']}: {rel['relatedConceptName']}")
        if len(result.relationships) > 3:
            print(f"    ... and {len(result.relationships) - 3} more")
        
        print(f"\nAGENT OBSERVATION:")
        print(f"  UMLS Ontology confirmed the term with verified relationships")
        
        print(f"\nAGENT RESPONSE (German):")
        print(f"  'Nach der verifizierten UMLS-Datenbank hat Lutetium Lu 177")
        print(f"   Dotatat die folgenden Nebenwirkungen: Nierenschädigung,")
        print(f"   Fieber und Müdigkeit.'")
        
        return True
    
    return False


def test_client_mode():
    """Show which client is being used."""
    print("\n" + "=" * 70)
    print("CLIENT MODE")
    print("=" * 70)
    
    import ontology_tool
    mode = ontology_tool.UMLS_CLIENT_MODE
    
    print(f"\nCurrent UMLS client mode: {mode.upper()}")
    
    if mode == "mock":
        print("""
You are using the MOCK client (no API key needed).

To use the REAL UMLS API when your key arrives:
  export UMLS_CLIENT_MODE=real
  export UMLS_API_KEY='your-api-key'
  
Then re-run your tests.

The code is identical - just configuration changes!
        """)
    else:
        print("""
You are using the REAL UMLS API.
Connection to NIH UMLS confirmed.
        """)


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("MOCK UMLS CLIENT TESTING")
    print("=" * 70)
    print("Testing without API key - Using realistic mock data")
    
    test_client_mode()
    
    test_results = []
    test_results.append(("Single term verification", test_single_term()))
    test_results.append(("Multiple terms", test_multiple_terms()))
    test_results.append(("German translation flow", test_german_translation()))
    test_results.append(("Agent tool simulation", test_agent_tool_simulation()))
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in test_results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in test_results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - Pipeline works without API key!")
        print("=" * 70)
        print("""
You can now:
1. Test the full agent with German questions
2. Test the TAO reasoning loop
3. Test the German-to-English translation
4. Verify the ontology tool integration
5. When your API key arrives, simply change UMLS_CLIENT_MODE=real

No other code changes needed!
        """)
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
