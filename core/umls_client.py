"""UMLS REST API client for clinical ontology integration.

This module provides a robust interface to the NIH UMLS (Unified Medical Language System)
REST API for retrieving Concept Unique Identifiers (CUIs) and their verified relationships.
It also includes a mock mode for testing without an API key.

The UMLS API requires a valid API key set in the UMLS_API_KEY environment variable.
"""

import logging
import os
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# UMLS API endpoints
UMLS_SEARCH_URL = "https://uts-ws.nlm.nih.gov/rest/search/current"
UMLS_RELATIONS_URL = "https://uts-ws.nlm.nih.gov/rest/content/current/CUI/{cui}/relations"

# Configurable retry parameters
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
REQUEST_TIMEOUT = 30  # seconds


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
        "cui": "C4050279",
        "relations": []
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
        "relations": []
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
    """Client for interacting with the NIH UMLS REST API or a mock database."""
    
    def __init__(self, api_key: Optional[str] = None, mock: bool = False):
        """
        Initialize the UMLS client.
        
        Args:
            api_key: UMLS API key. If None, reads from UMLS_API_KEY environment variable.
            mock: If True, uses the local mock database instead of hitting the API.
            
        Raises:
            UMLSClientError: If no API key is found and mock is False.
        """
        self.mock = mock or os.getenv("UMLS_USE_MOCK", "false").lower() == "true"
        
        if self.mock:
            logger.info("Initialized UMLS client in MOCK mode (no API key required)")
            self.api_key = "MOCK_KEY"
            self.session = None
        else:
            self.api_key = api_key or os.getenv("UMLS_API_KEY")
            if not self.api_key:
                raise UMLSClientError(
                    "UMLS_API_KEY not found. Set it as an environment variable, "
                    "pass it to the constructor, or enable mock mode."
                )
            self.session = requests.Session()
            logger.debug("Initialized UMLS client for production API")
    
    def _make_request(
        self,
        url: str,
        params: dict[str, Any],
        description: str = "UMLS API request"
    ) -> Optional[dict[str, Any]]:
        """Make an HTTP GET request to UMLS API with retry logic."""
        if self.mock:
            return None
            
        params["apiKey"] = self.api_key
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 429:
                    logger.warning(f"{description}: Rate limited. Retrying after {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                    continue
                
                response.raise_for_status()
                return response.json()
            
            except requests.exceptions.RequestException as e:
                logger.error(f"{description}: Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    return None
        return None
    
    def search_concept(self, query: str) -> Optional[str]:
        """Search for a medical concept and return its CUI."""
        if not query or not query.strip():
            return None
        
        query_normalized = query.strip()
        
        if self.mock:
            logger.debug(f"[MOCK] Searching for concept: {query_normalized}")
            # Try exact match
            if query_normalized in MOCK_UMLS_DB:
                return MOCK_UMLS_DB[query_normalized]["cui"]
            # Try case-insensitive
            for term, data in MOCK_UMLS_DB.items():
                if term.lower() == query_normalized.lower():
                    return data["cui"]
            return None
        
        # Real API logic
        params = {"string": query_normalized, "searchType": "exact", "pageNumber": 1, "pageSize": 1}
        response = self._make_request(UMLS_SEARCH_URL, params, f"Searching for '{query_normalized}'")
        
        if not response:
            params["searchType"] = "approximate"
            response = self._make_request(UMLS_SEARCH_URL, params, f"Approximate search for '{query_normalized}'")
            
        if response:
            results = response.get("result", {}).get("results", [])
            if results:
                return results[0].get("ui")
        return None
    
    def get_concept_relations(self, cui: str) -> list[dict[str, Any]]:
        """Retrieve relationships for a given CUI."""
        if not cui or not cui.strip():
            return []
            
        cui_str = cui.strip()
        
        if self.mock:
            logger.debug(f"[MOCK] Fetching relations for CUI: {cui_str}")
            for term, data in MOCK_UMLS_DB.items():
                if data["cui"] == cui_str:
                    return data.get("relations", [])
            return []
            
        # Real API logic
        url = UMLS_RELATIONS_URL.format(cui=cui_str)
        response = self._make_request(url, {}, f"Fetching relations for {cui_str}")
        
        if not response:
            return []
            
        relations = []
        for item in response.get("result", []):
            relation_label = item.get("relationLabel", "")
            related_name = item.get("relatedIdName", "")
            if relation_label and related_name:
                relations.append({
                    "relationLabel": relation_label,
                    "relatedConceptName": related_name,
                    "additionalLabel": item.get("additionalRelationLabel", "")
                })
        return relations
    
    def close(self):
        """Close the session and clean up resources."""
        if self.session:
            self.session.close()


# Shared client functionality
_client_instance: Optional[UMLSClient] = None

def _get_client() -> UMLSClient:
    global _client_instance
    if _client_instance is None:
        # Check if we should default to mock
        use_mock = not os.getenv("UMLS_API_KEY")
        _client_instance = UMLSClient(mock=use_mock)
    return _client_instance

def search_concept(query: str) -> Optional[str]:
    try:
        return _get_client().search_concept(query)
    except Exception as e:
        logger.error(f"UMLS search error: {e}")
        return None

def get_concept_relations(cui: str) -> list[dict[str, Any]]:
    try:
        return _get_client().get_concept_relations(cui)
    except Exception as e:
        logger.error(f"UMLS relations error: {e}")
        return []
