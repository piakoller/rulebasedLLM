# UMLS Ontology Integration - Quick Start

## 5-Minute Setup

### Step 1: Get UMLS API Key
1. Visit https://uts.nlm.nih.gov/uts/
2. Click "Sign up" if you don't have an account
3. Create free account
4. Go to "My Profile" → "API Key"
5. Generate or retrieve your API key

### Step 2: Set Environment Variable

```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
export UMLS_API_KEY='your-api-key-here'

# Or set for current session only
export UMLS_API_KEY='your-api-key-here'

# Verify it's set
echo $UMLS_API_KEY
```

### Step 3: Test the Integration

```bash
cd /home/pia/projects/rulebasedLLM
export UMLS_API_KEY='your-api-key-here'
python demo_umls_ontology.py
```

## How It Works

### User Asks Clinical Question
```
"What are the side effects of Lutetium Lu 177 dotatate?"
```

### Agent Triggered Actions
```
THOUGHT: "I need verified clinical information"

ACTION: query_umls_ontology(term="Lutetium Lu 177 dotatate")

OBSERVATION: 
{
  "found": true,
  "cui": "C4050279",
  "relationships": [
    {
      "relationLabel": "has_adverse_effect",
      "relatedConceptName": "Renal Toxicity"
    },
    ...
  ]
}

RESPONSE: "According to the verified UMLS ontology, 
Lutetium Lu 177 dotatate is associated with the following 
adverse effects: Renal Toxicity, ..."
```

## Core Files

| File | Purpose |
|------|---------|
| `core/umls_client.py` | Low-level UMLS REST API client |
| `core/ontology_tool.py` | High-level wrapper for clinical verification |
| `core/agent_engine.py` | Agent orchestrator (updated to use UMLS tool) |
| `demo_umls_ontology.py` | Interactive demo and examples |
| `UMLS_INTEGRATION.md` | Complete integration documentation |

## Using the Tool in Code

### Direct Client Usage
```python
from umls_client import search_concept, get_concept_relations

# Search for a concept
cui = search_concept("Lutetium Lu 177 dotatate")
print(f"CUI: {cui}")  # C4050279

# Get relationships
relations = get_concept_relations(cui)
for rel in relations[:3]:
    print(f"  {rel['relationLabel']}: {rel['relatedConceptName']}")
```

### Ontology Tool Wrapper
```python
from ontology_tool import verify_clinical_relationship

result = verify_clinical_relationship("Lutetium Lu 177 dotatate")

if result.found:
    print(f"CUI: {result.cui}")
    print(f"Relations: {len(result.relationships)}")
    print(result.summary)
```

### Agent Tool Call (Automatic)
The agent automatically uses this when the LLM calls:
```
ACTION: query_umls_ontology(term="medical_term")
```

## Common Medical Terms to Test

| Term | Use Case |
|------|----------|
| "Lutetium Lu 177 dotatate" | Radiotracers |
| "Renal Toxicity" | Adverse effects |
| "Positron Emission Tomography" | Diagnostic imaging |
| "Peptide Receptor Radionuclide Therapy" | Theranostics |
| "Kidney" | Organs |
| "Fatigue" | Side effects |

## Troubleshooting

### API Key Not Found
```
ERROR: UMLS_API_KEY not found
```
**Fix**: Must set in shell before running:
```bash
export UMLS_API_KEY='your-actual-key'
```

### Rate Limited (429 errors)
```
WARNING: Rate limited. Retrying after 1s...
```
**What's happening**: UMLS API has rate limits; client automatically retries
**Fix**: Wait a moment or adjust query frequency

### Concept Not Found
```
result.found == False
result.error == "Term not found in UMLS database"
```
**Fix**: Try alternative term names or check spelling

### Network Timeout
```
WARNING: Request timeout (attempt 1/3)
```
**What's happening**: Network delay; client retries automatically
**Fix**: Verify internet connection

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│  Clinical AI Assistant (Agent Engine)           │
│                                                 │
│  "What are side effects of Lu-177?"            │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
      ┌──────────────────────────┐
      │  LLM (Gemma 3)           │
      │  - Decides to query tool │
      └─────────┬────────────────┘
                │
                ↓
      ┌──────────────────────────┐
      │  ACTION: query_umls_ontology()
      │  (Extracted by Agent)    │
      └─────────┬────────────────┘
                │
                ↓
      ┌──────────────────────────────────────┐
      │  Ontology Tool (ontology_tool.py)    │
      │  verify_clinical_relationship()      │
      └─────────┬──────────────────────────┬─┘
                │                          │
   ┌────────────▼─────────────┐   Creates │
   │  UMLS API Client         │   client  │
   │  (umls_client.py)        │           │
   │                          │           │
   │  search_concept()        │           │
   │  get_concept_relations() │           │
   └────────────┬─────────────┘           │
                │                          │
                │ HTTP GET                 │
                ↓                          │
      ┌──────────────────────────────────┐│
      │  NIH UMLS REST API               ││
      │  (https://uts-ws.nlm.nih.gov)    ││
      └────────────┬─────────────────────┘│
                   │                       │
                   ↓ JSON Response         │
      ┌────────────────────────────────────
      │  CUIs, Relationships, Metadata
      └────────────┬─────────────────────────
                   │
                   ↓
      ┌──────────────────────────────────┐
      │  Format for LLM                  │
      │  (result.summary)                │
      └─────────┬────────────────────────┘
                │
                ↓
      ┌──────────────────────────────────┐
      │  Return ToolResult to Agent      │
      └─────────┬────────────────────────┘
                │
                ↓
      ┌──────────────────────────────────┐
      │  LLM uses verified results       │
      │  to generate response            │
      └──────────────────────────────────┘
```

## Next Steps

1. **Set your API key** (see Step 2 above)
2. **Run the demo** to test
3. **Check logs** to see tool calls:
   ```bash
   export UMLS_API_KEY='...'
   python -c "from ontology_tool import verify_clinical_relationship; verify_clinical_relationship('Lutetium Lu 177 dotatate')"
   ```
4. **Integrate with agent** - already integrated! The agent will auto-use the tool
5. **Monitor queries** - check logs for rate limiting or errors

## API Documentation Links

- **UMLS REST API**: https://documentation.uts.nlm.nih.gov/rest/home.html
- **Search Endpoint**: https://documentation.uts.nlm.nih.gov/rest/search/index.html
- **Relations Endpoint**: https://documentation.uts.nlm.nih.gov/rest/relations/index.html
- **CUI Format**: https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/definitions.html

## Support

| Issue | Resource |
|-------|----------|
| API Key issues | https://uts.nlm.nih.gov/uts/ |
| UMLS API questions | https://documentation.uts.nlm.nih.gov/ |
| Integration questions | See `UMLS_INTEGRATION.md` |
| Code issues | Check logs in `core/umls_client.py` |

---

**Ready to use UMLS-verified clinical ontologies!** 🔬
