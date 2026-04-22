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
from typing import Optional

import networkx as nx
import requests
from pydantic import BaseModel, Field
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

BASE_DIR = Path(__file__).resolve().parent
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
EXTRACTION_MODEL = os.getenv("GRAPH_RAG_EXTRACTION_MODEL", "hf.co/unsloth/medgemma-27b-it-GGUF:Q4_K_M")
ANSWER_MODEL = os.getenv("GRAPH_RAG_ANSWER_MODEL", EXTRACTION_MODEL)
DOCUMENT_ROOTS = [
    Path(path.strip())
    for path in os.getenv("GRAPH_RAG_DOCUMENT_ROOTS", "").split(",")
    if path.strip()
]
if not DOCUMENT_ROOTS:
    DOCUMENT_ROOTS = [BASE_DIR / "context", BASE_DIR / "docs", BASE_DIR / "data"]
VECTOR_STORE_DIR = Path(os.getenv("GRAPH_RAG_VECTOR_STORE", BASE_DIR / "data" / "vector_store"))
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".markdown"}
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250

_knowledge_graph: nx.Graph | None = None


class KnowledgeGraphFactResult(BaseModel):
    """Structured output for graph-based fact verification."""

    query: str
    entities: list[str] = Field(default_factory=list)
    verified: bool = False
    subject: str = ""
    relation: str = ""
    object: str = ""
    answer: str = ""
    evidence: list[str] = Field(default_factory=list)
    fallback: str = (
        "I want to keep this safe and only share what I can confirm from the provided document. "
        "If you want, I can explain the confirmed parts more simply or focus on one question at a time."
    )


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
    response = requests.post(ollama_url, json=payload, timeout=300)
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

    print(f"🔍 Found {len(document_paths)} documents. Building clinical knowledge graph...")
    for i, document_path in enumerate(document_paths, 1):
        print(f"📄 [{i}/{len(document_paths)}] Processing: {document_path.name}...")
        try:
            text = load_document_text(document_path)
        except Exception as exc:
            print(f"Skipping {document_path}: {exc}")
            continue

        chunks = chunk_text(text)
        print(f"   - Document has {len(chunks)} chunks.")
        for index, chunk in enumerate(chunks, start=1):
            if index % 5 == 1:
                print(f"   - Extracting facts from chunk {index}/{len(chunks)}...")
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


def _find_verified_relation(graph: nx.Graph, entities: list[str]) -> tuple[str, str, str, list[str]]:
    """Find a supported edge between extracted entities."""
    normalized_entities = [entity.lower().strip() for entity in entities if entity and entity.strip()]
    if len(normalized_entities) < 2:
        return "", "", "", []

    graph_nodes = list(graph.nodes())
    for left in graph_nodes:
        left_lower = str(left).lower()
        if not any(entity == left_lower or entity in left_lower or left_lower in entity for entity in normalized_entities):
            continue
        for right in graph.neighbors(left):
            right_lower = str(right).lower()
            if not any(entity == right_lower or entity in right_lower or right_lower in entity for entity in normalized_entities):
                continue
            edge_data = graph.get_edge_data(left, right) or {}
            relation = str(edge_data.get("relation", "connected to")).strip() or "connected to"
            evidence = [f"{left} -- {relation} -- {right}"]
            return str(left), relation, str(right), evidence
    return "", "", "", []


def get_knowledge_graph_fact(query: str, graph: Optional[nx.Graph] = None) -> KnowledgeGraphFactResult:
    """Tool for verifying a clinical relationship against the knowledge graph."""
    graph = graph or get_knowledge_graph()
    entities = extract_entities(query)

    subject, relation, object_, evidence = _find_verified_relation(graph, entities)
    if subject and relation and object_:
        answer = f"Yes. The graph supports that {subject} {relation} {object_}."
        return KnowledgeGraphFactResult(
            query=query,
            entities=entities,
            verified=True,
            subject=subject,
            relation=relation,
            object=object_,
            answer=answer,
            evidence=evidence,
        )

    context = retrieve_context(entities, graph=graph)
    # If graph didn't confirm relation, try RAG vector store retrieval for supporting context
    rag_contexts = []
    try:
        rag_contexts = retrieve_similar_documents(" ".join(entities) or query, top_k=3)
    except Exception:
        rag_contexts = []
    answer = (
        "I could not verify that relationship directly from the current knowledge graph. "
        "I can only provide high-level, document-grounded information."
    )
    if context:
        answer = f"{answer} Relevant context is available from the graph, but the exact relationship is not confirmed."

    return KnowledgeGraphFactResult(
        query=query,
        entities=entities,
        verified=False,
        answer=answer,
        evidence=([context] if context else []) + rag_contexts,
    )


def _load_vector_store(outdir: Path | None = None) -> tuple[np.ndarray, list[dict]]:
    outdir = Path(outdir or VECTOR_STORE_DIR)
    emb_path = outdir / "embeddings.npy"
    meta_path = outdir / "metadata.json"
    if not emb_path.exists() or not meta_path.exists():
        return np.zeros((0, 1), dtype=np.float32), []
    embs = np.load(str(emb_path))
    with meta_path.open("r", encoding="utf-8") as fh:
        metadata = json.load(fh)
    return embs, metadata


def _embed_query_text(text: str, model_name: str | None = None) -> np.ndarray:
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is required for RAG retrieval. Install with: pip install sentence-transformers")
    model = SentenceTransformer(model_name or "all-MiniLM-L6-v2")
    emb = model.encode([text], convert_to_numpy=True, show_progress_bar=False)
    return np.array(emb, dtype=np.float32)


def retrieve_similar_documents(text: str, top_k: int = 5, model_name: str | None = None, outdir: Path | None = None) -> list[dict]:
    """Return top_k metadata entries from the vector store similar to `text`.

    Each returned item is a dict with keys: `score` (cosine), and the original metadata fields.
    """
    embs, metadata = _load_vector_store(outdir=outdir)
    if embs.size == 0 or not metadata:
        return []

    try:
        q_emb = _embed_query_text(text, model_name=model_name)
    except Exception:
        return []

    # Normalize for cosine similarity
    def _norm(x: np.ndarray) -> np.ndarray:
        denom = np.linalg.norm(x, axis=1, keepdims=True)
        denom[denom == 0] = 1.0
        return x / denom

    embs_norm = _norm(embs)
    q_norm = q_emb / (np.linalg.norm(q_emb) or 1.0)
    scores = (embs_norm @ q_norm.reshape(-1)).astype(float)
    top_idx = list(np.argsort(scores)[-top_k:][::-1])
    results = []
    for i in top_idx:
        item = dict(metadata[i]) if i < len(metadata) else {"id": i}
        item["score"] = float(scores[i])
        results.append(item)
    return results


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


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _graph_has_relation(graph: nx.Graph, source: str, target: str) -> bool:
    if graph.has_edge(source, target):
        return True

    source_lower = source.lower()
    target_lower = target.lower()
    for left, right, data in graph.edges(data=True):
        left_lower = str(left).lower()
        right_lower = str(right).lower()
        relation_text = str(data.get("relation", "")).lower()
        if {source_lower, target_lower} == {left_lower, right_lower}:
            return True
        if source_lower in left_lower and target_lower in right_lower:
            return True
        if source_lower in relation_text and target_lower in relation_text:
            return True
    return False


def verify_llm_response(response: str, entities: list[str], graph: nx.Graph | None = None) -> dict:
    """Verify whether response-level medical relationships exist in the graph.

    Returns a dictionary with:
      - verified: bool
      - flagged_relations: list[str]
      - safe_fallback: str
    """
    graph = graph or get_knowledge_graph()
    normalized_response = _normalize_text(response)
    flagged_relations = []
    verified_relations = []

    if not normalized_response:
        return {
            "verified": False,
            "flagged_relations": ["empty response"],
            "safe_fallback": (
                "I want to keep this safe and only share what I can confirm from the provided document. "
                "If you want, I can explain the confirmed parts more simply or focus on one question at a time."
            ),
            "verified_relations": [],
        }

    for entity in entities:
        entity_lower = entity.lower().strip()
        if not entity_lower:
            continue

        matched_node = None
        for node in graph.nodes():
            node_lower = str(node).lower()
            if entity_lower == node_lower or entity_lower in node_lower or node_lower in entity_lower:
                matched_node = node
                break

        if matched_node is None:
            continue

        neighbor_mentions = []
        for neighbor in graph.neighbors(matched_node):
            neighbor_mentions.append(str(neighbor))

        if neighbor_mentions and not any(neighbor.lower() in normalized_response for neighbor in neighbor_mentions):
            continue

    graph_nodes = list(graph.nodes())
    for i, left in enumerate(graph_nodes):
        left_lower = str(left).lower()
        if left_lower not in normalized_response:
            continue
        for right in graph_nodes[i + 1 :]:
            right_lower = str(right).lower()
            if right_lower not in normalized_response:
                continue
            if not _graph_has_relation(graph, str(left), str(right)):
                flagged_relations.append(f"{left} <-> {right}")
            else:
                verified_relations.append(f"{left} <-> {right}")

    verified = len(flagged_relations) == 0
    safe_fallback = (
        "I want to keep this safe and only share what I can confirm from the provided document. "
        "If you want, I can explain the confirmed parts more simply or focus on one question at a time."
    )

    return {
        "verified": verified,
        "flagged_relations": flagged_relations,
        "safe_fallback": safe_fallback,
        "verified_relations": verified_relations,
    }
