"""UMLS REST API client for clinical ontology integration.

This module provides a robust interface to the NIH UMLS (Unified Medical Language System)
REST API for retrieving Concept Unique Identifiers (CUIs) and their verified relationships.

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


class UMLSClient:
    """Client for interacting with the NIH UMLS REST API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the UMLS client with an API key.
        
        Args:
            api_key: UMLS API key. If None, reads from UMLS_API_KEY environment variable.
            
        Raises:
            UMLSClientError: If no API key is found.
        """
        self.api_key = api_key or os.getenv("UMLS_API_KEY")
        if not self.api_key:
            raise UMLSClientError(
                "UMLS_API_KEY not found. Set it as an environment variable or pass it to the constructor."
            )
        self.session = requests.Session()
    
    def _make_request(
        self,
        url: str,
        params: dict[str, Any],
        description: str = "UMLS API request"
    ) -> Optional[dict[str, Any]]:
        """
        Make an HTTP GET request to UMLS API with retry logic.
        
        Args:
            url: The API endpoint URL.
            params: Query parameters.
            description: Friendly description for logging.
            
        Returns:
            Parsed JSON response, or None if request fails after retries.
        """
        params["apiKey"] = self.api_key
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 429:
                    # Rate limit hit
                    logger.warning(f"{description}: Rate limited. Retrying after {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                    continue
                
                response.raise_for_status()
                return response.json()
            
            except requests.exceptions.Timeout:
                logger.warning(f"{description}: Request timeout (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
            
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"{description}: Connection error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
            
            except requests.exceptions.HTTPError as e:
                if response.status_code == 404:
                    logger.debug(f"{description}: Not found (404)")
                    return None
                logger.error(f"{description}: HTTP error {response.status_code}: {e}")
                return None
            
            except requests.exceptions.RequestException as e:
                logger.error(f"{description}: Request failed: {e}")
                return None
        
        logger.error(f"{description}: Failed after {MAX_RETRIES} retries")
        return None
    
    def search_concept(self, query: str) -> Optional[str]:
        """
        Search for a medical concept and return its CUI (Concept Unique Identifier).
        
        Args:
            query: Medical term or concept to search for (e.g., "Lutetium Lu 177 dotatate").
            
        Returns:
            The CUI of the top matching concept, or None if not found.
            
        Example:
            >>> client = UMLSClient()
            >>> cui = client.search_concept("Lutetium Lu 177 dotatate")
            >>> print(cui)
            C4050279
        """
        if not query or not query.strip():
            logger.debug("Empty search query provided")
            return None
        
        logger.debug(f"Searching for concept: {query}")
        
        params = {
            "string": query.strip(),
            "searchType": "exact",  # Try exact match first
            "pageNumber": 1,
            "pageSize": 1
        }
        
        response = self._make_request(UMLS_SEARCH_URL, params, f"Searching for '{query}'")
        
        if not response:
            # Fall back to approximate search
            logger.debug(f"Exact search failed for '{query}', trying approximate search...")
            params["searchType"] = "approximate"
            response = self._make_request(UMLS_SEARCH_URL, params, f"Approximate search for '{query}'")
        
        if not response:
            logger.debug(f"No concept found for query: {query}")
            return None
        
        # Extract the top result
        results = response.get("result", {}).get("results", [])
        if not results:
            logger.debug(f"No results returned for query: {query}")
            return None
        
        cui = results[0].get("ui")
        concept_name = results[0].get("name")
        
        if cui:
            logger.debug(f"Found CUI '{cui}' for '{query}' (concept: '{concept_name}')")
        
        return cui
    
    def get_concept_relations(self, cui: str) -> list[dict[str, Any]]:
        """
        Retrieve the relationships for a given CUI, filtered to English terms only.
        
        Args:
            cui: Concept Unique Identifier (e.g., "C4050279").
            
        Returns:
            List of relationship dictionaries with keys:
                - relatedId: CUI of related concept
                - relationLabel: Type of relationship (e.g., "has_part_or_component")
                - relatedConceptName: Name of the related concept (English only)
            
        Example:
            >>> client = UMLSClient()
            >>> relations = client.get_concept_relations("C4050279")
            >>> for rel in relations:
            ...     print(f"{rel['relationLabel']}: {rel['relatedConceptName']}")
        """
        if not cui or not cui.strip():
            logger.debug("Empty CUI provided to get_concept_relations")
            return []
        
        logger.debug(f"Fetching relations for CUI: {cui}")
        
        url = UMLS_RELATIONS_URL.format(cui=cui.strip())
        response = self._make_request(url, {}, f"Fetching relations for {cui}")
        
        if not response:
            logger.debug(f"No relations found for CUI: {cui}")
            return []
        
        relations: list[dict[str, Any]] = []
        results = response.get("result", [])
        
        for item in results:
            # Get the relationship label
            relation_label = item.get("relationLabel", "")
            
            # Get the related concept info
            related_id = item.get("relatedIdInverted")  # Target CUI
            
            # Extract related concept details from nested structure
            related_name = None
            if isinstance(item.get("relatedId"), dict):
                related_name = item["relatedId"].get("name")
            else:
                # Try to get from relatedIdInverted
                if isinstance(item.get("relatedIdInverted"), dict):
                    related_name = item["relatedIdInverted"].get("name")
            
            # Filter for English terms only
            language = item.get("relatedId", {}).get("language", "")
            if language and language != "ENG":
                continue
            
            if related_id and related_name:
                relations.append({
                    "relatedId": related_id,
                    "relationLabel": relation_label,
                    "relatedConceptName": related_name
                })
        
        logger.debug(f"Found {len(relations)} relations for CUI {cui}")
        return relations
    
    def close(self):
        """Close the session and clean up resources."""
        if self.session:
            self.session.close()
            logger.debug("UMLS client session closed")


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
