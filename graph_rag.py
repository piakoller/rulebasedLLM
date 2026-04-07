"""Document-driven GraphRAG for theranostics.

The graph can be built from provided PDF/text documents through Ollama-based
entity and relation extraction. If no documents are available, a small fallback
clinical graph is used so the module still works out of the box.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import networkx as nx
import requests

BASE_DIR = Path(__file__).resolve().parent
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
EXTRACTION_MODEL = os.getenv("GRAPH_RAG_EXTRACTION_MODEL", "gemma3:latest")
ANSWER_MODEL = os.getenv("GRAPH_RAG_ANSWER_MODEL", EXTRACTION_MODEL)
DOCUMENT_ROOTS = [
    Path(path.strip())
    for path in os.getenv("GRAPH_RAG_DOCUMENT_ROOTS", "").split(",")
    if path.strip()
]
if not DOCUMENT_ROOTS:
    DOCUMENT_ROOTS = [BASE_DIR / "context", BASE_DIR / "docs", BASE_DIR / "data"]
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".markdown"}
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250

_knowledge_graph: nx.Graph | None = None


def create_clinical_graph() -> nx.Graph:
    """Fallback graph used when no documents are available."""
    graph = nx.Graph()
    graph.add_node(
        "Nuclear Medicine",
        type="Medical Field",
        description="Uses small amounts of radioactive material to diagnose or treat disease.",
        sources=["fallback"],
    )
    graph.add_node(
        "Theranostics",
        type="Medical Approach",
        description="A personalized approach combining diagnostics to identify targets and therapeutics to treat them.",
        sources=["fallback"],
    )
    graph.add_node(
        "Dosimetry",
        type="Measurement",
        description="The calculation and assessment of the radiation dose absorbed by the patient's body and tumors.",
        sources=["fallback"],
    )
    graph.add_node(
        "Radioisotope",
        type="Substance",
        description="A radioactive form of an element used for imaging or treatment.",
        sources=["fallback"],
    )
    graph.add_node(
        "PRRT",
        type="Therapy",
        description="Peptide Receptor Radionuclide Therapy, a type of targeted radioligand therapy.",
        sources=["fallback"],
    )
    graph.add_node(
        "Lutetium-177",
        type="Radioisotope",
        description="A beta-emitting isotope commonly used in therapeutic nuclear medicine.",
        sources=["fallback"],
    )

    graph.add_edge("Theranostics", "Nuclear Medicine", relation="is a modern approach within", sources=["fallback"])
    graph.add_edge("Theranostics", "Radioisotope", relation="uses specifically targeted", sources=["fallback"])
    graph.add_edge("Dosimetry", "Nuclear Medicine", relation="ensures safe and effective treatment in", sources=["fallback"])
    graph.add_edge("Dosimetry", "Radioisotope", relation="measures the absorbed dose from", sources=["fallback"])
    graph.add_edge("Lutetium-177", "PRRT", relation="is the radiation source for", sources=["fallback"])
    graph.add_edge("PRRT", "Theranostics", relation="is a prime example of", sources=["fallback"])
    graph.add_edge("Dosimetry", "PRRT", relation="helps personalize the treatment cycles for", sources=["fallback"])
    return graph


def _discover_document_paths(roots: list[Path]) -> list[Path]:
    document_paths = []
    for root in roots:
        if root.is_file() and root.suffix.lower() in SUPPORTED_SUFFIXES:
            document_paths.append(root)
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                document_paths.append(path)
    return document_paths


def _load_text_from_pdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError(
            "Reading PDF files requires 'pypdf'. Install it with: pip install pypdf"
        ) from exc

    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def load_document_text(document_path: Path) -> str:
    suffix = document_path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return document_path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        return _load_text_from_pdf(document_path)
    raise ValueError(f"Unsupported document type: {document_path}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _ollama_chat(messages: list[dict], model: str = EXTRACTION_MODEL, ollama_url: str = OLLAMA_URL) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    response = requests.post(ollama_url, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("message", {}).get("content", "")


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}

    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return {}


def extract_entities(user_message: str, model: str = EXTRACTION_MODEL, ollama_url: str = OLLAMA_URL) -> list[str]:
    """Extract core entities from the user message."""
    system_prompt = (
        "You are an entity extraction system. Extract the core entities from the user's message. "
        "Return ONLY a comma-separated list of entities. Do not add any conversational text."
    )

    try:
        reply = _ollama_chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            model=model,
            ollama_url=ollama_url,
        )
        return [entity.strip() for entity in reply.split(",") if entity.strip() and len(entity.strip()) < 80]
    except Exception as exc:
        print(f"Error extracting entities: {exc}")
        return []


def extract_graph_facts(document_chunk: str, model: str = EXTRACTION_MODEL, ollama_url: str = OLLAMA_URL) -> dict:
    """Extract entity and relation facts from a document chunk as JSON."""
    system_prompt = (
        "You extract structured knowledge from clinical documents. "
        "Return valid JSON only with this schema: "
        '{"entities":[{"name":"...","type":"...","description":"..."}],'
        '"relations":[{"source":"...","target":"...","relation":"..."}]}. '
        "Use only facts supported by the provided text. Do not invent relationships."
    )
    user_prompt = f"Document chunk:\n{document_chunk}\n\nExtract graph facts now."

    try:
        reply = _ollama_chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
            ollama_url=ollama_url,
        )
        payload = _extract_json_object(reply)
        if not isinstance(payload, dict):
            return {"entities": [], "relations": []}
        entities = payload.get("entities", [])
        relations = payload.get("relations", [])
        return {
            "entities": entities if isinstance(entities, list) else [],
            "relations": relations if isinstance(relations, list) else [],
        }
    except Exception as exc:
        print(f"Error extracting graph facts: {exc}")
        return {"entities": [], "relations": []}


def _upsert_entity(graph: nx.Graph, entity: dict, source_label: str) -> None:
    name = str(entity.get("name", "")).strip()
    if not name:
        return

    node_type = str(entity.get("type", "Entity")).strip() or "Entity"
    description = str(entity.get("description", "")).strip()
    sources = list(graph.nodes[name].get("sources", [])) if graph.has_node(name) else []
    if source_label not in sources:
        sources.append(source_label)

    if not graph.has_node(name):
        graph.add_node(name, type=node_type, description=description, sources=sources)
        return

    node_data = graph.nodes[name]
    if not node_data.get("description") and description:
        node_data["description"] = description
    if not node_data.get("type") and node_type:
        node_data["type"] = node_type
    node_data["sources"] = sources


def _add_relation(graph: nx.Graph, relation: dict, source_label: str) -> None:
    source = str(relation.get("source", "")).strip()
    target = str(relation.get("target", "")).strip()
    relation_text = str(relation.get("relation", "connected to")).strip() or "connected to"
    if not source or not target:
        return

    if not graph.has_edge(source, target):
        graph.add_edge(source, target, relation=relation_text, sources=[source_label])
        return

    edge_data = graph.get_edge_data(source, target)
    if not edge_data.get("relation"):
        edge_data["relation"] = relation_text
    edge_sources = list(edge_data.get("sources", []))
    if source_label not in edge_sources:
        edge_sources.append(source_label)
    edge_data["sources"] = edge_sources


def create_graph_from_documents(document_roots: list[Path] | None = None, model: str = EXTRACTION_MODEL) -> nx.Graph:
    """Build a graph from provided documents."""
    graph = nx.Graph()
    roots = document_roots or DOCUMENT_ROOTS
    document_paths = _discover_document_paths(roots)

    if not document_paths:
        return create_clinical_graph()

    for document_path in document_paths:
        try:
            text = load_document_text(document_path)
        except Exception as exc:
            print(f"Skipping {document_path}: {exc}")
            continue

        chunks = chunk_text(text)
        for index, chunk in enumerate(chunks, start=1):
            source_label = f"{document_path.name}#chunk-{index}"
            facts = extract_graph_facts(chunk, model=model)
            for entity in facts.get("entities", []):
                if isinstance(entity, dict):
                    _upsert_entity(graph, entity, source_label)
            for relation in facts.get("relations", []):
                if isinstance(relation, dict):
                    _add_relation(graph, relation, source_label)

    if graph.number_of_nodes() == 0:
        return create_clinical_graph()
    return graph


def get_knowledge_graph(document_roots: list[Path] | None = None) -> nx.Graph:
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = create_graph_from_documents(document_roots=document_roots)
    return _knowledge_graph


def retrieve_context(entities: list[str], graph: nx.Graph | None = None) -> str:
    """Search the graph for the entities and return their local neighborhood."""
    graph = graph or get_knowledge_graph()
    context_lines = []
    node_lookup = {str(node).lower(): node for node in graph.nodes()}

    for entity in entities:
        ent_lower = entity.lower().strip()
        matched_nodes = []
        if ent_lower in node_lookup:
            matched_nodes.append(node_lookup[ent_lower])
        else:
            matched_nodes.extend(
                node for key, node in node_lookup.items() if ent_lower and (ent_lower in key or key in ent_lower)
            )

        for actual_node in dict.fromkeys(matched_nodes):
            attrs = graph.nodes[actual_node]
            if attrs:
                attr_bits = []
                if attrs.get("type"):
                    attr_bits.append(f"type: {attrs['type']}")
                if attrs.get("description"):
                    attr_bits.append(f"description: {attrs['description']}")
                if attrs.get("sources"):
                    attr_bits.append(f"sources: {', '.join(attrs['sources'])}")
                context_lines.append(f"Entity '{actual_node}' has attributes: {', '.join(attr_bits)}")

            for neighbor in graph.neighbors(actual_node):
                edge_data = graph.get_edge_data(actual_node, neighbor)
                relation = edge_data.get("relation", "connected to")
                source_info = edge_data.get("sources", [])
                suffix = f" [sources: {', '.join(source_info)}]" if source_info else ""
                context_lines.append(f"'{actual_node}' is {relation} '{neighbor}'{suffix}")

    if not context_lines:
        return ""
    return "Knowledge Graph Context:\n" + "\n".join(context_lines)
