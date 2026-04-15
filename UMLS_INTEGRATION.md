# UMLS Ontology Integration Guide

## Overview

The clinical AI assistant now uses the **NIH UMLS (Unified Medical Language System) REST API** for verified medical ontology queries instead of relying on LLM guessing or static mock data.

### Architecture

```
User Query
    ↓
Agent Engine (Thought-Action-Observation Loop)
    ↓
LLM Analysis → Triggers ACTION: query_umls_ontology(term="...")
    ↓
UMLS API Client
├─ search_concept(query) → CUI
└─ get_concept_relations(CUI) → Verified Relationships
    ↓
Ontology Tool (Verification & Formatting)
    ↓
LLM Result with Verified Facts
    ↓
Agent Response
```

## Components

### 1. UMLS Client (`core/umls_client.py`)

**Purpose**: Low-level interface to the NIH UMLS REST API.

**Key Functions**:

- **`search_concept(query: str) -> Optional[str]`**
  - Searches for a medical term (e.g., "Lutetium Lu 177 dotatate")
  - Returns the CUI (Concept Unique Identifier) of the top match
  - Uses exact search first, falls back to approximate if needed
  - Includes retry logic for rate limits and timeouts
  
  ```python
  from umls_client import search_concept
  
  cui = search_concept("Lutetium Lu 177 dotatate")
  # Returns: "C4050279"
  ```

- **`get_concept_relations(cui: str) -> list[dict]`**
  - Retrieves all relationships for a CUI
  - Filters to English terms only
  - Returns list of dicts with:
    - `relatedId`: CUI of related concept
    - `relationLabel`: Type of relationship (e.g., "has_adverse_effect")
    - `relatedConceptName`: Name of related concept
  
  ```python
  from umls_client import get_concept_relations
  
  relations = get_concept_relations("C4050279")
  # Returns relationships like:
  # [
  #   {"relatedId": "...", "relationLabel": "used_for", "relatedConceptName": "PRRT"},
  #   {"relatedId": "...", "relationLabel": "has_adverse_effect", "relatedConceptName": "Renal Toxicity"}
  # ]
  ```

**Configuration**:
- **API Key**: Set `UMLS_API_KEY` environment variable
  ```bash
  export UMLS_API_KEY='your-api-key-here'
  ```
- Get your API key at: https://uts.nlm.nih.gov/uts/

**Error Handling**:
- Automatic retries with exponential backoff for rate limits (429)
- Timeout handling with configurable retry count
- Graceful fallback for missing concepts

### 2. Ontology Tool (`core/ontology_tool.py`)

**Purpose**: Wrapper around UMLS client for clinical verification and LLM-friendly formatting.

**Key Functions**:

- **`verify_clinical_relationship(term: str) -> UMLSVerificationResult`**
  - Searches UMLS for a term
  - Retrieves and formats relationships
  - Returns structured result with CUI, relationships, and summary
  
  ```python
  from ontology_tool import verify_clinical_relationship
  
  result = verify_clinical_relationship("Lutetium Lu 177 dotatate")
  
  # result.found: bool - Was the term found?
  # result.cui: str - Concept Unique Identifier
  # result.relationships: list[dict] - Verified relationships
  # result.summary: str - Formatted text for LLM
  # result.error: str - Error message if not found
  ```

- **`verify_multiple_relationships(terms: list[str]) -> dict`**
  - Batch verification of multiple terms
  - Returns dict mapping term → UMLSVerificationResult
  
  ```python
  results = verify_multiple_relationships([
      "Lutetium Lu 177 dotatate",
      "Renal Toxicity",
      "PRRT"
  ])
  ```

- **`format_umls_verification_for_llm(results: list) -> str`**
  - Formats verification results for inclusion in LLM prompts
  - Creates human-readable verification summary
  - Marks verified (✓) and unverified (✗) terms

### 3. Agent Engine Integration (`core/agent_engine.py`)

**Changes Made**:

1. **Imports**:
   ```python
   from ontology_tool import verify_clinical_relationship, UMLSVerificationResult
   ```

2. **Tool Handler in `_execute_tool()`**:
   ```python
   elif tool_call.function_name == "query_umls_ontology":
       term = tool_call.arguments.get("term", "")
       result = verify_clinical_relationship(term)
       return ToolResult(
           tool_name=tool_call.function_name,
           success=result.found,
           result={...},
           error=result.error if not result.found else ""
       )
   ```

3. **System Prompt Update in `_build_prompt()`**:
   ```
   - ACTION: query_umls_ontology(term="medical_term") 
     - Use this to retrieve medically verified relationships for a specific drug, therapy, 
       or side effect from the NIH UMLS database.
   
   - CRITICAL: If a medical relationship is not explicitly verified by the query_umls_ontology 
     or query_medical_ontology tool, you MUST state that you cannot confirm the clinical relationship.
   ```

## Usage Examples

### Example 1: Direct API Usage

```python
from umls_client import UMLSClient

client = UMLSClient()

# Search for a concept
cui = client.search_concept("Lutetium Lu 177 dotatate")
print(f"CUI: {cui}")

# Get relationships
relations = client.get_concept_relations(cui)
for rel in relations:
    print(f"  → {rel['relationLabel']}: {rel['relatedConceptName']}")
```

### Example 2: Ontology Tool Wrapper

```python
from ontology_tool import verify_clinical_relationship

result = verify_clinical_relationship("Lutetium Lu 177 dotatate")

if result.found:
    print(f"Verified: {result.term} (CUI: {result.cui})")
    print(result.summary)
else:
    print(f"Error: {result.error}")
```

### Example 3: Agent Tool Call

The agent automatically uses the UMLS tool when needed:

```
User: "What are the side effects of Lutetium Lu 177 dotatate?"

Agent Thought:
"I should verify the approved side effects using the UMLS ontology."

Agent Action:
ACTION: query_umls_ontology(term="Lutetium Lu 177 dotatate")

Tool Result:
{
    "term": "Lutetium Lu 177 dotatate",
    "cui": "C4050279",
    "found": true,
    "relationships": [
        {"relationLabel": "has_adverse_effect", "relatedConceptName": "Renal Toxicity"},
        ...
    ],
    "summary": "UMLS Ontology Verification (CUI: C4050279)..."
}

Agent Response:
"According to the verified UMLS ontology, Lutetium Lu 177 dotatate has several known 
relationships including adverse effects. The most commonly documented side effect is 
renal toxicity..."
```

### Example 4: Running the Demo

```bash
# Set your API key
export UMLS_API_KEY='your-key-here'

# Run the demo
cd /home/pia/projects/rulebasedLLM
python demo_umls_ontology.py
```

## Error Handling

The system handles several error scenarios:

### Missing API Key
```
UMLSClientError: UMLS_API_KEY not found. Set it as an environment variable...
```

**Solution**: 
```bash
export UMLS_API_KEY='your-key-here'
```

### Rate Limiting (429)
```
WARNING: UMLS API request: Rate limited. Retrying after 1s...
```

**Handling**: Automatic retry with exponential backoff (max 3 retries)

### Concept Not Found
```python
result = verify_clinical_relationship("Nonexistent Medical Term")
# result.found == False
# result.error == "Term 'Nonexistent Medical Term' not found in UMLS database"
```

### Network Timeout
```
WARNING: UMLS API request: Request timeout (attempt 1/3)
```

**Handling**: Automatic retry with backoff

## Configuration

### Environment Variables

```bash
# UMLS API Key (required)
export UMLS_API_KEY='your-api-key'

# Optional: Configure retry behavior
# Maximum retries for failed requests
# UMLS_MAX_RETRIES=3

# Delay between retries in seconds
# UMLS_RETRY_DELAY=1

# Request timeout in seconds
# UMLS_REQUEST_TIMEOUT=30
```

### Logging

```python
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('umls_client')
```

## Performance Considerations

### Caching
The system uses a single shared UMLS client instance with session pooling:
```python
from umls_client import search_concept, get_concept_relations

# These use the shared client instance and connection pooling
cui = search_concept("term1")
relations = get_concept_relations(cui)
```

### Rate Limits
UMLS API has rate limits. The client includes:
- Automatic retry logic for rate limit (429) responses
- Exponential backoff to avoid overwhelming the API
- Connection pooling to minimize overhead

### Best Practices
1. **Cache results in your application** if you query the same terms frequently
2. **Batch requests** when possible using `verify_multiple_relationships()`
3. **Handle rate limits gracefully** - the client will retry automatically
4. **Close sessions** when done:
   ```python
   client = UMLSClient()
   # ... do work ...
   client.close()
   ```

## Behavioral Constraints

The agent is instructed:

1. **Verification First**
   > "If a medical relationship is not explicitly verified by the query_umls_ontology tool, you MUST state that you cannot confirm the clinical relationship."

2. **Prioritize Medical Ontology**
   > "When discussing medical relationships or treatments, prioritize using query_umls_ontology to verify facts."

3. **Uncertainty Statement**
   > If UMLS query fails or returns no results, agent must say: "I cannot confirm this relationship based on verified medical ontologies."

## Testing

Run the included demo to verify the integration:

```bash
# Without API key (shows structure and examples)
python demo_umls_ontology.py

# With API key (runs actual UMLS queries)
export UMLS_API_KEY='your-key'
python demo_umls_ontology.py
```

## Troubleshooting

### API Key Issues
```
UMLSClientError: UMLS_API_KEY not found
```
→ Set: `export UMLS_API_KEY='your-key'`

### Rate Limiting
```
WARNING: Rate limited. Retrying...
```
→ Normal behavior; client automatically retries. Reduce query frequency if persistent.

### Timeouts
```
WARNING: Request timeout (attempt 1/3)
```
→ Normal for slow networks; client retries automatically.

### No Results Found
```
result.found == False
result.error == "Term not found in UMLS database"
```
→ Try searching for a more specific or alternative medical term.

## API References

- **UMLS REST API Documentation**: https://documentation.uts.nlm.nih.gov/rest/home.html
- **Get API Key**: https://uts.nlm.nih.gov/uts/
- **UMLS Search Examples**: https://documentation.uts.nlm.nih.gov/rest/search/index.html
- **Relations Endpoint**: https://documentation.uts.nlm.nih.gov/rest/relations/index.html

## Migration from Mock Ontology

If you were using the old mock ontology (`data/mock_ontology.json`):

**Before** (LLM guessing with mock data):
```python
result = ontology_rag.query_medical_ontology("Lutetium Lu 177 dotatate")
# Hardcoded mock relationships
```

**After** (Verified UMLS relationships):
```python
result = verify_clinical_relationship("Lutetium Lu 177 dotatate")
# Real relationships from NIH UMLS
```

The new system provides:
- ✅ Real, verified medical relationships
- ✅ Consistent with clinical standards
- ✅ Comprehensive coverage of medical concepts
- ✅ Automatic error handling and retries
- ✅ Deterministic, not LLM-guessed

## Summary

The UMLS ontology integration transforms the clinical AI assistant from relying on static mock data or LLM guesses to using verified medical relationships from the NIH's authoritative UMLS database. This ensures clinical accuracy and traceability.
