"""Mock UMLS API client for testing without API key.

This module provides a mock implementation of the UMLS REST API client
that returns realistic test data. Use this for development and testing
when you don't have an API key yet.

Switch to the real client by changing the import:
  FROM: from umls_client_mock import UMLSClient
  TO:   from umls_client import UMLSClient
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class UMLSClientError(Exception):
    """Custom exception for UMLS client errors."""
    pass


# Mock UMLS database with realistic nuclear medicine/theranostics data
MOCK_UMLS_DB = {
    # Radioisotopes and Therapeutics
    "Lutetium Lu 177 dotatate": {
        "cui": "C4050279",
        "relations": [
            {
                "relatedId": "C2348916",
                "relationLabel": "used_for",
                "relatedConceptName": "Peptide Receptor Radionuclide Therapy"
            },
            {
                "relatedId": "C0022646",
                "relationLabel": "has_adverse_effect",
                "relatedConceptName": "Renal Toxicity"
            },
            {
                "relatedId": "C0015967",
                "relationLabel": "has_adverse_effect",
                "relatedConceptName": "Fever"
            },
            {
                "relatedId": "C0015672",
                "relationLabel": "has_adverse_effect",
                "relatedConceptName": "Fatigue"
            },
            {
                "relatedId": "C0004134",
                "relationLabel": "has_mechanism",
                "relatedConceptName": "Beta Decay"
            }
        ]
    },
    "Lutetium-177": {
        "cui": "C4050279",  # Same as above
        "relations": []  # Alias, reuse parent
    },
    "Lu-177": {
        "cui": "C4050279",
        "relations": []
    },
    "Pluvicto": {
        "cui": "C4050279",
        "relations": []
    },
    "Lutathera": {
        "cui": "C4050279",
        "relations": []
    },
    
    # Therapies
    "Peptide Receptor Radionuclide Therapy": {
        "cui": "C2348916",
        "relations": [
            {
                "relatedId": "C4050279",
                "relationLabel": "uses_agent",
                "relatedConceptName": "Lutetium Lu 177 dotatate"
            },
            {
                "relatedId": "C0031809",
                "relationLabel": "type_of",
                "relatedConceptName": "Radiotherapy"
            },
            {
                "relatedId": "C0006271",
                "relationLabel": "used_for",
                "relatedConceptName": "Breast Neoplasms"
            }
        ]
    },
    "PRRT": {
        "cui": "C2348916",
        "relations": []  # Alias
    },
    
    # Side Effects
    "Renal Toxicity": {
        "cui": "C0022646",
        "relations": [
            {
                "relatedId": "C0020538",
                "relationLabel": "affects",
                "relatedConceptName": "Hypertension"
            },
            {
                "relatedId": "C0020557",
                "relationLabel": "affects",
                "relatedConceptName": "Hyperkalemia"
            }
        ]
    },
    "Kidney Damage": {
        "cui": "C0022646",
        "relations": []
    },
    "Nephrotoxicity": {
        "cui": "C0022646",
        "relations": []
    },
    
    # Organs
    "Kidney": {
        "cui": "C0022646",
        "relations": [
            {
                "relatedId": "C0020557",
                "relationLabel": "has_function",
                "relatedConceptName": "Filtration"
            },
            {
                "relatedId": "C0011570",
                "relationLabel": "produces",
                "relatedConceptName": "Urine"
            }
        ]
    },
    
    # Imaging
    "Positron Emission Tomography": {
        "cui": "C0162565",
        "relations": [
            {
                "relatedId": "C0025078",
                "relationLabel": "uses",
                "relatedConceptName": "Positron"
            },
            {
                "relatedId": "C0040808",
                "relationLabel": "type_of",
                "relatedConceptName": "Tomography"
            }
        ]
    },
    "PET": {
        "cui": "C0162565",
        "relations": []
    },
    "PET Scan": {
        "cui": "C0162565",
        "relations": []
    },
    
    # General symptoms
    "Fatigue": {
        "cui": "C0015672",
        "relations": [
            {
                "relatedId": "C0020538",
                "relationLabel": "causes",
                "relatedConceptName": "Hypertension"
            }
        ]
    },
    "Nausea": {
        "cui": "C0027497",
        "relations": []
    },
    
    # Dosimetry
    "Dosimetry": {
        "cui": "C0012749",
        "relations": [
            {
                "relatedId": "C0020538",
                "relationLabel": "used_for",
                "relatedConceptName": "Personalized Medicine"
            }
        ]
    },
    "Personalized Medicine": {
        "cui": "C2718059",
        "relations": [
            {
                "relatedId": "C0180686",
                "relationLabel": "involves",
                "relatedConceptName": "Genetic Testing"
            }
        ]
    }
}


class UMLSClient:
    """Mock UMLS client for testing without API key."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the mock UMLS client.
        
        Args:
            api_key: Ignored in mock version (no API key needed)
        """
        logger.info("Initialized mock UMLS client (no API key required)")
    
    def search_concept(self, query: str) -> Optional[str]:
        """
        Search for a medical concept and return its mock CUI.
        
        Args:
            query: Medical term to search for
            
        Returns:
            Mock CUI if found, None otherwise
        """
        if not query or not query.strip():
            logger.debug("Empty search query provided")
            return None
        
        query_normalized = query.strip()
        logger.debug(f"[MOCK] Searching for concept: {query_normalized}")
        
        # Try exact match first
        if query_normalized in MOCK_UMLS_DB:
            cui = MOCK_UMLS_DB[query_normalized]["cui"]
            logger.debug(f"[MOCK] Found CUI '{cui}' for '{query_normalized}'")
            return cui
        
        # Try case-insensitive match
        for term, data in MOCK_UMLS_DB.items():
            if term.lower() == query_normalized.lower():
                cui = data["cui"]
                logger.debug(f"[MOCK] Found CUI '{cui}' for '{query_normalized}' (case-insensitive)")
                return cui
        
        logger.debug(f"[MOCK] No concept found for query: {query_normalized}")
        return None
    
    def get_concept_relations(self, cui: str) -> list[dict[str, Any]]:
        """
        Retrieve the relationships for a given CUI from mock database.
        
        Args:
            cui: Concept Unique Identifier
            
        Returns:
            List of relationship dictionaries
        """
        if not cui or not cui.strip():
            logger.debug("Empty CUI provided to get_concept_relations")
            return []
        
        cui_str = cui.strip()
        logger.debug(f"[MOCK] Fetching relations for CUI: {cui_str}")
        
        # Find concept by CUI in mock database
        for term, data in MOCK_UMLS_DB.items():
            if data["cui"] == cui_str:
                relations = data.get("relations", [])
                logger.debug(f"[MOCK] Found {len(relations)} relations for CUI {cui_str}")
                return relations
        
        logger.debug(f"[MOCK] No relations found for CUI: {cui_str}")
        return []
    
    def close(self):
        """Close the client (no-op for mock)."""
        logger.debug("[MOCK] Client closed")


# Module-level convenience functions using a shared client instance
_client_instance: Optional[UMLSClient] = None


def _get_client() -> UMLSClient:
    """Get or create the shared client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = UMLSClient()
    return _client_instance


def search_concept(query: str) -> Optional[str]:
    """
    Search for a medical concept and return its CUI.
    
    Args:
        query: Medical term or concept to search for.
        
    Returns:
        The CUI of the top matching concept, or None if not found.
    """
    try:
        return _get_client().search_concept(query)
    except UMLSClientError as e:
        logger.error(f"UMLS client error: {e}")
        return None


def get_concept_relations(cui: str) -> list[dict[str, Any]]:
    """
    Retrieve the relationships for a given CUI.
    
    Args:
        cui: Concept Unique Identifier.
        
    Returns:
        List of relationship dictionaries.
    """
    try:
        return _get_client().get_concept_relations(cui)
    except UMLSClientError as e:
        logger.error(f"UMLS client error: {e}")
        return []
