"""Ontology tool for verifying clinical relationships against the NIH UMLS.

This module provides a wrapper around the UMLS client to verify medical relationships
and provide formatted summaries for the LLM agent.

Configuration:
  Use the real UMLS API (requires UMLS_API_KEY):
    export UMLS_CLIENT_MODE=real
  
  Use the mock UMLS client (no API key needed):
    export UMLS_CLIENT_MODE=mock  # default
"""

import logging
import os
from typing import Any, Optional

from pydantic import BaseModel, Field

from umls_client import UMLSClient, UMLSClientError, get_concept_relations, search_concept

logger = logging.getLogger(__name__)


class UMLSVerificationResult(BaseModel):
    """Result of verifying a clinical term against UMLS."""
    
    term: str
    cui: Optional[str] = None
    found: bool = False
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    error: str = ""


def verify_clinical_relationship(term: str) -> UMLSVerificationResult:
    """
    Verify a clinical term against UMLS and retrieve its relationships.
    
    This function:
    1. Searches for the term to get its CUI
    2. Fetches the relationships for that CUI
    3. Formats a clear text summary for the LLM
    
    Args:
        term: Medical term to verify (e.g., "Lutetium Lu 177 dotatate", "Renal Toxicity").
        
    Returns:
        UMLSVerificationResult with:
            - cui: Concept Unique Identifier if found
            - found: Whether the term was found in UMLS
            - relationships: List of verified relationships
            - summary: Formatted text summary for the LLM
            
    Example:
        >>> result = verify_clinical_relationship("Lutetium Lu 177 dotatate")
        >>> if result.found:
        ...     print(result.summary)
    """
    if not term or not term.strip():
        return UMLSVerificationResult(
            term=term,
            found=False,
            error="Empty term provided"
        )
    
    logger.info(f"Verifying clinical term: {term}")
    
    try:
        # Step 1: Search for the concept
        cui = search_concept(term)
        
        if not cui:
            logger.debug(f"Term not found in UMLS: {term}")
            return UMLSVerificationResult(
                term=term,
                found=False,
                error=f"Term '{term}' not found in UMLS database"
            )
        
        logger.debug(f"Found CUI {cui} for term: {term}")
        
        # Step 2: Get relationships for this CUI
        relationships = get_concept_relations(cui)
        
        # Step 3: Format summary
        if relationships:
            rel_summary = "\n  ".join(
                f"• {rel['relationLabel']}: {rel['relatedConceptName']}"
                for rel in relationships[:10]  # Limit to first 10 relationships
            )
            summary = (
                f"UMLS Ontology Verification (CUI: {cui})\n"
                f"Concept: {term}\n"
                f"\nVerified Relationships:\n  {rel_summary}"
            )
        else:
            summary = (
                f"UMLS Ontology Verification (CUI: {cui})\n"
                f"Concept: {term}\n"
                f"\nNo relationships found for this concept."
            )
        
        logger.info(f"Successfully verified term '{term}' with CUI {cui}")
        
        return UMLSVerificationResult(
            term=term,
            cui=cui,
            found=True,
            relationships=relationships,
            summary=summary
        )
    
    except UMLSClientError as e:
        logger.error(f"UMLS client error for term '{term}': {e}")
        return UMLSVerificationResult(
            term=term,
            found=False,
            error=f"UMLS client error: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error verifying term '{term}': {e}")
        return UMLSVerificationResult(
            term=term,
            found=False,
            error=f"Unexpected error: {str(e)}"
        )


def verify_multiple_relationships(terms: list[str]) -> dict[str, UMLSVerificationResult]:
    """
    Verify multiple clinical terms and return all results.
    
    Args:
        terms: List of medical terms to verify.
        
    Returns:
        Dictionary mapping term to UMLSVerificationResult.
    """
    results = {}
    for term in terms:
        if term and term.strip():
            results[term.strip()] = verify_clinical_relationship(term)
    return results


def format_umls_verification_for_llm(results: list[UMLSVerificationResult]) -> str:
    """
    Format verification results into a structured prompt for the LLM.
    
    Args:
        results: List of verification results to format.
        
    Returns:
        Formatted string suitable for inclusion in LLM prompt.
    """
    lines = ["UMLS Ontology Query Results:", "=" * 50]
    
    verified_count = sum(1 for r in results if r.found)
    lines.append(f"Verified concepts: {verified_count}/{len(results)}")
    lines.append("")
    
    for result in results:
        if result.found:
            lines.append(f"✓ {result.term} (CUI: {result.cui})")
            if result.relationships:
                for rel in result.relationships[:5]:
                    lines.append(
                        f"  → {rel['relationLabel']}: {rel['relatedConceptName']}"
                    )
        else:
            lines.append(f"✗ {result.term}")
            if result.error:
                lines.append(f"  Error: {result.error}")
        lines.append("")
    
    return "\n".join(lines)
