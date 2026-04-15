# UMLS API Integration - Code Examples

This file contains practical, copy-paste-ready code examples for using the UMLS ontology integration.

## Setup (Required)

### Step 1: Get API Key
```bash
# Visit https://uts.nlm.nih.gov/uts/
# Sign up → My Profile → API Key
# Copy your key
```

### Step 2: Set Environment Variable
```bash
# In your shell or .bashrc/.zshrc
export UMLS_API_KEY='your-actual-key-here'

# Verify it's set
echo $UMLS_API_KEY
```

## Example 1: Direct UMLS Client Usage

```python
#!/usr/bin/env python3
"""Direct UMLS API client usage."""

import sys
from pathlib import Path

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent / "core"))

from umls_client import UMLSClient, UMLSClientError

def main():
    try:
        # Create client (reads UMLS_API_KEY from environment)
        client = UMLSClient()
        
        # Example 1: Search for a medical concept
        print("=" * 60)
        print("SEARCHING FOR: Lutetium Lu 177 dotatate")
        print("=" * 60)
        
        cui = client.search_concept("Lutetium Lu 177 dotatate")
        
        if cui:
            print(f"✓ Found CUI: {cui}")
            
            # Example 2: Get relationships
            print(f"\nFetching relationships for {cui}...")
            relations = client.get_concept_relations(cui)
            
            print(f"✓ Found {len(relations)} relationships\n")
            
            print("Relationships:")
            for i, rel in enumerate(relations[:10], 1):
                print(f"  {i}. {rel['relationLabel']}: {rel['relatedConceptName']}")
                
        else:
            print("✗ Concept not found")
            
        client.close()
        
    except UMLSClientError as e:
        print(f"ERROR: {e}")
        print("\nMake sure to set UMLS_API_KEY:")
        print("  export UMLS_API_KEY='your-key'")

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
export UMLS_API_KEY='your-key'
python example1_direct_client.py
```

## Example 2: Ontology Tool Wrapper

```python
#!/usr/bin/env python3
"""Using the high-level ontology tool wrapper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "core"))

from ontology_tool import verify_clinical_relationship

def main():
    # Single term verification
    print("Verifying: Lutetium Lu 177 dotatate")
    print("-" * 60)
    
    result = verify_clinical_relationship("Lutetium Lu 177 dotatate")
    
    if result.found:
        print(f"✓ FOUND")
        print(f"  CUI: {result.cui}")
        print(f"  Relationships: {len(result.relationships)}")
        print(f"\n{result.summary}")
    else:
        print(f"✗ NOT FOUND")
        print(f"  Error: {result.error}")

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
export UMLS_API_KEY='your-key'
python example2_wrapper.py
```

## Example 3: Batch Verification

```python
#!/usr/bin/env python3
"""Batch verification of multiple terms."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "core"))

from ontology_tool import verify_multiple_relationships, format_umls_verification_for_llm

def main():
    # Terms to verify
    medical_terms = [
        "Lutetium Lu 177 dotatate",
        "Renal Toxicity",
        "Peptide Receptor Radionuclide Therapy",
        "Kidney Function",
        "Positron Emission Tomography",
    ]
    
    print("Verifying multiple medical terms...")
    print("=" * 60)
    
    # Batch verify
    results = verify_multiple_relationships(medical_terms)
    
    # Format for LLM
    formatted = format_umls_verification_for_llm(list(results.values()))
    
    print(formatted)
    
    # Count results
    found_count = sum(1 for r in results.values() if r.found)
    print(f"\nSummary: {found_count}/{len(results)} terms verified")

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
export UMLS_API_KEY='your-key'
python example3_batch.py
```

## Example 4: Custom Error Handling

```python
#!/usr/bin/env python3
"""Error handling patterns."""

import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent / "core"))

from umls_client import UMLSClient, UMLSClientError

# Enable logging to see retries and errors
logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s - %(levelname)s - %(message)s"
)

def verify_term_safely(term: str) -> dict:
    """Verify a term with comprehensive error handling."""
    
    try:
        client = UMLSClient()
        
        # Search for concept
        cui = client.search_concept(term)
        
        if not cui:
            return {
                "success": False,
                "error": f"Term '{term}' not found in UMLS",
                "term": term
            }
        
        # Get relationships
        relations = client.get_concept_relations(cui)
        
        client.close()
        
        return {
            "success": True,
            "term": term,
            "cui": cui,
            "relationships": relations,
            "relation_count": len(relations)
        }
        
    except UMLSClientError as e:
        return {
            "success": False,
            "error": f"UMLS client error: {str(e)}",
            "term": term
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}", 
            "term": term
        }

def main():
    print("Demonstrating error handling patterns")
    print("=" * 60)
    
    test_terms = [
        "Lutetium Lu 177 dotatate",      # Should work
        "Definitely Not A Real Term!",   # Will fail gracefully
        "Kidney",                         # Should work
    ]
    
    for term in test_terms:
        result = verify_term_safely(term)
        
        print(f"\n{term}")
        print("-" * 40)
        
        if result["success"]:
            print(f"✓ CUI: {result['cui']}")
            print(f"✓ Found {result['relation_count']} relationships")
        else:
            print(f"✗ {result['error']}")

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
export UMLS_API_KEY='your-key'
python example4_error_handling.py
```

## Example 5: Integration with Agent

```python
#!/usr/bin/env python3
"""Simulating how the agent engine uses UMLS."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "core"))

from ontology_tool import verify_clinical_relationship
from pydantic import BaseModel

# Simulate ToolResult from agent_engine.py
class ToolResult(BaseModel):
    tool_name: str
    success: bool
    result: dict = {}
    error: str = ""

def execute_umls_tool(term: str) -> ToolResult:
    """Simulates agent_engine._execute_tool() for query_umls_ontology."""
    
    if not term:
        return ToolResult(
            tool_name="query_umls_ontology",
            success=False,
            error="Missing 'term' argument"
        )
    
    # Call the ontology verification
    result = verify_clinical_relationship(term)
    
    # Format as ToolResult
    return ToolResult(
        tool_name="query_umls_ontology",
        success=result.found,
        result={
            "term": result.term,
            "cui": result.cui,
            "found": result.found,
            "relationships": result.relationships,
            "summary": result.summary
        },
        error=result.error if not result.found else ""
    )

def main():
    print("Agent Tool Simulation: query_umls_ontology")
    print("=" * 60)
    
    # Simulate agent calling the tool
    test_queries = [
        "Lutetium Lu 177 dotatate",
        "Renal Toxicity",
        "Nonexistent Medical Term",
    ]
    
    for query in test_queries:
        print(f"\nAgent ACTION: query_umls_ontology(term=\"{query}\")")
        print("-" * 60)
        
        tool_result = execute_umls_tool(query)
        
        print("Tool Result:")
        print(json.dumps(tool_result.model_dump(), indent=2))
        
        # Simulate agent using result
        if tool_result.success:
            result_data = tool_result.result
            print(f"\nAgent Response:")
            print(f"  CUI: {result_data['cui']}")
            print(f"  Found {len(result_data['relationships'])} verified relationships")
        else:
            print(f"\nAgent Response:")
            print(f"  Cannot verify term: {tool_result.error}")

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
export UMLS_API_KEY='your-key'
python example5_agent_integration.py
```

## Example 6: Clinical Verification Flow

```python
#!/usr/bin/env python3
"""Complete clinical verification workflow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "core"))

from ontology_tool import verify_clinical_relationship

def verify_clinical_claim(claim: str, drug: str, side_effect: str) -> bool:
    """
    Verify if a clinical claim is supported by UMLS.
    
    Example: 
      claim = "Lutetium-177 can cause kidney damage"
      drug = "Lutetium Lu 177 dotatate"
      side_effect = "Renal Toxicity"
    """
    
    print(f"\nVerifying Clinical Claim")
    print("=" * 60)
    print(f"Claim: {claim}")
    print(f"Drug: {drug}")
    print(f"Side Effect: {side_effect}")
    print("-" * 60)
    
    # Verify the drug
    drug_result = verify_clinical_relationship(drug)
    
    if not drug_result.found:
        print(f"❌ Cannot verify: Drug '{drug}' not found in UMLS")
        return False
    
    print(f"✓ Found drug: {drug_result.cui}")
    
    # Check if side effect is listed in drug's relationships
    side_effect_found = False
    for rel in drug_result.relationships:
        if "adverse" in rel['relationLabel'].lower():
            if side_effect.lower() in rel['relatedConceptName'].lower():
                side_effect_found = True
                print(f"✓ Found adverse effect: {rel['relatedConceptName']}")
                break
    
    if side_effect_found:
        print(f"\n✓ VERIFIED: Claim is supported by UMLS data")
        return True
    else:
        # Verify side effect independently
        se_result = verify_clinical_relationship(side_effect)
        print(f"⚠ Side effect '{side_effect}' not directly linked in UMLS")
        print(f"  (Found independently: {se_result.found})")
        print(f"\n❌ CANNOT VERIFY: Relationship not in UMLS data")
        return False

def main():
    # Example clinical claims to verify
    claims = [
        {
            "claim": "Lutetium-177 can cause kidney damage",
            "drug": "Lutetium Lu 177 dotatate",
            "side_effect": "Renal Toxicity"
        },
        {
            "claim": "PET imaging uses positrons",
            "drug": "Positron Emission Tomography",
            "side_effect": "Radiation Exposure"
        },
    ]
    
    results = []
    for claim_data in claims:
        verified = verify_clinical_claim(
            claim_data["claim"],
            claim_data["drug"],
            claim_data["side_effect"]
        )
        results.append({
            "claim": claim_data["claim"],
            "verified": verified
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    for result in results:
        status = "✓ VERIFIED" if result["verified"] else "❌ UNVERIFIED"
        print(f"{status}: {result['claim']}")

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
export UMLS_API_KEY='your-key'
python example6_clinical_verification.py
```

## Example 7: Caching Results

```python
#!/usr/bin/env python3
"""Caching UMLS results to improve performance."""

import sys
from pathlib import Path
from functools import lru_cache
import time

sys.path.insert(0, str(Path(__file__).parent / "core"))

from ontology_tool import verify_clinical_relationship

# Cache up to 128 unique term verifications
@lru_cache(maxsize=128)
def cached_verify_clinical_relationship(term: str):
    """Cached version of verify_clinical_relationship."""
    return verify_clinical_relationship(term)

def main():
    print("UMLS Result Caching Demo")
    print("=" * 60)
    
    # Terms to verify (some repeated)
    terms = [
        "Lutetium Lu 177 dotatate",
        "Renal Toxicity",
        "Lutetium Lu 177 dotatate",  # Repeated
        "Kidney",
        "Renal Toxicity",  # Repeated
        "Lutetium Lu 177 dotatate",  # Repeated
    ]
    
    print(f"Verifying {len(terms)} terms ({len(set(terms))} unique)\n")
    
    # Verify with timing
    start_time = time.time()
    
    for i, term in enumerate(terms, 1):
        verify_start = time.time()
        result = cached_verify_clinical_relationship(term)
        verify_time = time.time() - verify_start
        
        status = "✓" if result.found else "✗"
        print(f"{i}. {status} {term} ({verify_time:.2f}s)")
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print(f"Total time: {total_time:.2f}s")
    print(f"Unique terms cached: {cached_verify_clinical_relationship.cache_info().currsize}")
    print(f"Cache hits: {cached_verify_clinical_relationship.cache_info().hits}")
    
    # Show cache stats
    info = cached_verify_clinical_relationship.cache_info()
    print(f"\nCache Statistics:")
    print(f"  Hits: {info.hits}")
    print(f"  Misses: {info.misses}")
    print(f"  Hit ratio: {info.hits / (info.hits + info.misses) * 100:.1f}%")

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
export UMLS_API_KEY='your-key'
python example7_caching.py
```

## Example 8: Logging Configuration

```python
#!/usr/bin/env python3
"""Configuring logging for UMLS operations."""

import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent / "core"))

from umls_client import UMLSClient

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("UMLS Client with Detailed Logging")
    print("=" * 60)
    
    # Create client (will log detailed operations)
    client = UMLSClient()
    
    # This will show:
    # - Search request details
    # - API response parsing
    # - Retry attempts
    # - Timing information
    
    print("\nSearching for concept (watch logs below):")
    print("-" * 60)
    
    cui = client.search_concept("Lutetium Lu 177 dotatate")
    
    print("-" * 60)
    print(f"\nResult: {cui}")
    
    if cui:
        print("\nFetching relationships (watch logs below):")
        print("-" * 60)
        
        relations = client.get_concept_relations(cui)
        
        print("-" * 60)
        print(f"\nFound {len(relations)} relationships")
    
    client.close()

if __name__ == "__main__":
    main()
```

**Run it with logging:**
```bash
export UMLS_API_KEY='your-key'
python example8_logging.py 2>&1 | head -50
```

## Example 9: Testing Your Setup

```python
#!/usr/bin/env python3
"""Test your UMLS setup."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "core"))

def test_environment():
    """Test environment setup."""
    print("Testing UMLS Integration Setup")
    print("=" * 60)
    
    # Test 1: API Key
    print("\n1. Checking UMLS_API_KEY...")
    api_key = os.getenv("UMLS_API_KEY")
    if api_key:
        print(f"   ✓ API Key is set ({len(api_key)} chars)")
    else:
        print("   ✗ API Key not set")
        print("     Run: export UMLS_API_KEY='your-key'")
        return False
    
    # Test 2: Import modules
    print("\n2. Checking Python imports...")
    try:
        from umls_client import UMLSClient
        print("   ✓ umls_client imported")
    except ImportError as e:
        print(f"   ✗ Cannot import umls_client: {e}")
        return False
    
    try:
        from ontology_tool import verify_clinical_relationship
        print("   ✓ ontology_tool imported")
    except ImportError as e:
        print(f"   ✗ Cannot import ontology_tool: {e}")
        return False
    
    # Test 3: Create client
    print("\n3. Creating UMLS client...")
    try:
        from umls_client import UMLSClient, UMLSClientError
        client = UMLSClient()
        print("   ✓ Client created successfully")
        client.close()
    except UMLSClientError as e:
        print(f"   ✗ Cannot create client: {e}")
        return False
    
    # Test 4: Make API request
    print("\n4. Testing API connection...")
    try:
        cui = verify_clinical_relationship("Kidney").cui
        if cui:
            print(f"   ✓ API call successful (found CUI: {cui})")
        else:
            print("   ⚠ API call succeeded but no result (try different term)")
    except Exception as e:
        print(f"   ✗ API call failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All checks passed! Ready to use UMLS integration")
    return True

if __name__ == "__main__":
    success = test_environment()
    sys.exit(0 if success else 1)
```

**Run it:**
```bash
export UMLS_API_KEY='your-key'
python example9_test_setup.py
```

## Quick Reference

| Task | Code |
|------|------|
| Search concept | `search_concept("term")` |
| Get relations | `get_concept_relations("CUI")` |
| Verify term | `verify_clinical_relationship("term")` |
| Batch verify | `verify_multiple_relationships(["term1", "term2"])` |
| Format for LLM | `format_umls_verification_for_llm(results)` |

---

All examples require `export UMLS_API_KEY='your-key'` before running.
