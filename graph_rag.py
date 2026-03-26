import networkx as nx
import requests
import json

# Clinical knowledge graph for GraphRAG
def create_clinical_graph():
    G = nx.Graph()
    # Adding nodes
    G.add_node("Nuclear Medicine", type="Medical Field", description="Uses small amounts of radioactive material to diagnose or treat disease.")
    G.add_node("Theranostics", type="Medical Approach", description="A personalized approach combining diagnostics to identify targets and therapeutics to treat them.")
    G.add_node("Dosimetry", type="Measurement", description="The calculation and assessment of the radiation dose absorbed by the patient's body and tumors.")
    G.add_node("Radioisotope", type="Substance", description="A radioactive form of an element used for imaging or treatment.")
    G.add_node("PRRT", type="Therapy", description="Peptide Receptor Radionuclide Therapy, a type of targeted radioligand therapy.")
    G.add_node("Lutetium-177", type="Radioisotope", description="A beta-emitting isotope commonly used in therapeutic nuclear medicine.")

    # Adding edges
    G.add_edge("Theranostics", "Nuclear Medicine", relation="is a modern approach within")
    G.add_edge("Theranostics", "Radioisotope", relation="uses specifically targeted")
    G.add_edge("Dosimetry", "Nuclear Medicine", relation="ensures safe and effective treatment in")
    G.add_edge("Dosimetry", "Radioisotope", relation="measures the absorbed dose from")
    G.add_edge("Lutetium-177", "PRRT", relation="is the radiation source for")
    G.add_edge("PRRT", "Theranostics", relation="is a prime example of")
    G.add_edge("Dosimetry", "PRRT", relation="helps personalize the treatment cycles for")

    return G

# Initialize graph
knowledge_graph = create_clinical_graph()

def extract_entities(user_message: str, model: str = "gpt-oss:20b", ollama_url: str = "http://localhost:11434/api/chat") -> list:
    """
    Uses an LLM to extract key entities from the user message.
    """
    system_prompt = (
        "You are an entity extraction system. Extract the core entities from the user's message. "
        "Return ONLY a comma-separated list of entities. Do not add any conversational text. "
        "Example: 'What is the capital of Switzerland?' -> 'Switzerland'"
    )
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "stream": False # Require non-streaming response for easier parsing
    }
    
    try:
        response = requests.post(ollama_url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        reply = data.get('message', {}).get('content', '')
        # Clean up the reply to a list of entities (handle case where LLM gives a full sentence by mistake)
        entities = [e.strip() for e in reply.split(',') if e.strip() and len(e.strip()) < 30]
        return entities
    except Exception as e:
        print(f"Error extracting entities: {e}")
        return []

def retrieve_context(entities: list, graph: nx.Graph = knowledge_graph) -> str:
    """
    Searches the graph for the entities and returns their 1-hop neighborhood context.
    """
    context_lines = []
    # Make lookup case-insensitive
    node_lookup = {str(n).lower(): n for n in graph.nodes()}
    
    for entity in entities:
        ent_lower = entity.lower()
        if ent_lower in node_lookup:
            actual_node = node_lookup[ent_lower]
            # Get node attributes
            attrs = graph.nodes[actual_node]
            if attrs:
                # Format attributes nicely
                attr_str = ", ".join(f"{k}: {v}" for k, v in attrs.items())
                context_lines.append(f"Entity '{actual_node}' has attributes: {attr_str}")
            
            # Get edges
            for neighbor in graph.neighbors(actual_node):
                edge_data = graph.get_edge_data(actual_node, neighbor)
                relation = edge_data.get('relation', 'connected to')
                context_lines.append(f"'{actual_node}' is {relation} '{neighbor}'")
                
    if not context_lines:
        return ""
    
    return "Knowledge Graph Context:\n" + "\n".join(context_lines)
