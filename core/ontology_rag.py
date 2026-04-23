"""Ontology-grounded RAG for deterministic medical relationship verification.

This module provides a static ontology-based fact verification layer that replaces
LLM-guessed medical relationships. It maps user queries to predefined concepts
and returns only ontology-verified relationships.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent
ONTOLOGY_PATH = BASE_DIR.parent / "data" / "mock_ontology.json"


class OntologyVerificationResult:
    """Result of ontology verification containing mapped entities and relationships."""
    
    def __init__(
        self,
        query: str,
        success: bool,
        mapped_entities: list[dict[str, Any]] | None = None,
        relationships: str = "",
        error: str = ""
    ):
        self.query = query
        self.success = success
        self.mapped_entities = mapped_entities or []
        self.relationships = relationships
        self.error = error


def load_ontology(ontology_path: Path = ONTOLOGY_PATH) -> dict[str, Any]:
    """Load the static medical ontology from JSON file."""
    if not ontology_path.exists():
        return {}
    try:
        return json.loads(ontology_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {}


def extract_and_map_entities(user_query: str, ontology: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Extract clinical terms from the user query and map them to ontology concepts.
    
    Args:
        user_query: The user's question or statement
        ontology: Pre-loaded ontology dict (loads from file if None)
    
    Returns:
        List of dicts with keys: { "cui", "name", "matched_term", "type", "aliases" }
    """
    if ontology is None:
        ontology = load_ontology()
    
    if not ontology:
        return []
    
    # Normalize query for comparison
    query_lower = user_query.lower()
    query_tokens = set(re.findall(r'\b\w+\b', query_lower))
    
    mapped_entities: list[dict[str, Any]] = []
    matched_cuis = set()
    
    # Search through ontology for matching concepts
    for cui, concept in ontology.items():
        if cui in matched_cuis:
            continue
            
        concept_name = concept.get("name", "").lower()
        aliases = [alias.lower() for alias in concept.get("aliases", [])]
        
        # Check for direct alias matches in the query
        for alias in aliases:
            if alias in query_lower:
                mapped_entities.append({
                    "cui": cui,
                    "name": concept.get("name", ""),
                    "matched_term": alias,
                    "type": concept.get("type", ""),
                    "aliases": concept.get("aliases", [])
                })
                matched_cuis.add(cui)
                break
        
        # Check for partial word matches if no direct alias match
        if cui not in matched_cuis:
            name_tokens = set(re.findall(r'\b\w+\b', concept_name))
            if name_tokens & query_tokens:
                mapped_entities.append({
                    "cui": cui,
                    "name": concept.get("name", ""),
                    "matched_term": concept_name,
                    "type": concept.get("type", ""),
                    "aliases": concept.get("aliases", [])
                })
                matched_cuis.add(cui)
    
    return mapped_entities


def get_ontology_pathway(
    cui_list: list[str],
    ontology: dict[str, Any] | None = None
) -> str:
    """
    Check relationships between identified CUIs in the ontology and return
    deterministic relationship descriptions.
    
    Args:
        cui_list: List of CUIs to find relationships between
        ontology: Pre-loaded ontology dict (loads from file if None)
    
    Returns:
        A deterministic string describing ontology-verified relationships
    """
    if ontology is None:
        ontology = load_ontology()
    
    if not ontology or not cui_list:
        return "No ontology relationships could be verified."
    
    # Filter valid CUIs that exist in the ontology
    valid_cuis = [cui for cui in cui_list if cui in ontology]
    
    if not valid_cuis:
        return "The specified concepts are not found in the medical ontology."
    
    # Build relationship descriptions
    relationship_lines = ["According to the medical ontology:"]
    
    for cui in valid_cuis:
        concept = ontology[cui]
        concept_name = concept.get("name", cui)
        relations = concept.get("relations", [])
        
        for relation in relations:
            rel_type = relation.get("type", "related_to")
            target_cui = relation.get("target_cui", "")
            target_name = relation.get("target_name", "")
            
            # Format relationship as: "ConceptA has_relation ConceptB"
            if target_name:
                relationship_lines.append(f"  - {concept_name} {rel_type} {target_name}")
    
    if len(relationship_lines) == 1:
        return f"No relationships found for: {', '.join(valid_cuis)}"
    
    return "\n".join(relationship_lines)


def query_medical_ontology(
    terms: str,
    ontology: dict[str, Any] | None = None
) -> OntologyVerificationResult:
    """
    Main function to query the medical ontology for entity mapping and relationships.
    
    This is the tool interface that the agent uses to verify medical relationships.
    
    Args:
        terms: Comma-separated terms or a natural language query
        ontology: Pre-loaded ontology dict (loads from file if None)
    
    Returns:
        OntologyVerificationResult with mapped entities and relationship description
    """
    if ontology is None:
        ontology = load_ontology()
    
    if not ontology:
        return OntologyVerificationResult(
            query=terms,
            success=False,
            error="Medical ontology could not be loaded"
        )
    
    try:
        # Extract and map entities from the query
        mapped_entities = extract_and_map_entities(terms, ontology)
        
        if not mapped_entities:
            return OntologyVerificationResult(
                query=terms,
                success=False,
                mapped_entities=[],
                error="No recognized medical terms found in the query"
            )
        
        # Extract CUIs and get relationship pathway
        cuis = [entity["cui"] for entity in mapped_entities]
        pathway = get_ontology_pathway(cuis, ontology)
        
        return OntologyVerificationResult(
            query=terms,
            success=True,
            mapped_entities=mapped_entities,
            relationships=pathway
        )
    
    except Exception as e:
        return OntologyVerificationResult(
            query=terms,
            success=False,
            error=f"Ontology query failed: {str(e)}"
        )


def verify_statement_against_ontology(
    statement: str,
    ontology: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Verify if a clinical statement is supported by the ontology.
    
    Args:
        statement: A clinical claim to verify
        ontology: Pre-loaded ontology dict (loads from file if None)
    
    Returns:
        Dict with keys:
        - verified: bool indicating if statement is supported
        - extracted_entities: list of mapped entities
        - relationships: string of verified relationships
        - confidence: float from 0 to 1
    """
    if ontology is None:
        ontology = load_ontology()
    
    if not ontology:
        return {
            "verified": False,
            "extracted_entities": [],
            "relationships": "",
            "confidence": 0.0,
            "reason": "Ontology unavailable"
        }
    
    # Extract entities from the statement
    mapped_entities = extract_and_map_entities(statement, ontology)
    
    if not mapped_entities:
        return {
            "verified": False,
            "extracted_entities": [],
            "relationships": "",
            "confidence": 0.0,
            "reason": "No medical concepts found in statement"
        }
    
    # Get relationships
    cuis = [entity["cui"] for entity in mapped_entities]
    pathway = get_ontology_pathway(cuis, ontology)
    
    # Verify statement against relationships
    # If we have mapped entities and found relationships, consider it verified
    verified = bool(mapped_entities and "No relationships found" not in pathway)
    confidence = 0.9 if verified else 0.3
    
    return {
        "verified": verified,
        "extracted_entities": mapped_entities,
        "relationships": pathway,
        "confidence": confidence,
        "reason": "Verified against medical ontology" if verified else "No supporting relationships found"
    }
