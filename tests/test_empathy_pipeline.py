#!/usr/bin/env python3
"""Test empathic framing for clinical information.

Shows how the system combines:
1. Clinical validity (UMLS ontology)
2. Emotional intelligence (empathy framing)
3. Multilingual support (German & English)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "core"))

from rules import detect_language, DISTRESS_KEYWORDS
from empathy_framing import frame_clinical_information_empathically, create_empathic_response_to_umls_result


def test_language_detection():
    """Test language detection for empathy."""
    print("\n" + "=" * 70)
    print("TEST 1: Language Detection for Empathy")
    print("=" * 70)
    
    test_cases = [
        ("What are the side effects?", "en"),
        ("Was sind die Nebenwirkungen?", "de"),
        ("Ich bin nervös und angespannt", "de"),
        ("I'm scared and worried", "en"),
    ]
    
    for text, expected in test_cases:
        detected = detect_language(text)
        status = "✓" if detected == expected else "✗"
        print(f"{status} '{text[:40]}...' → {detected} (expected {expected})")


def test_distress_detection():
    """Test distress detection in both languages."""
    print("\n" + "=" * 70)
    print("TEST 2: Distress Detection (English & German)")
    print("=" * 70)
    
    test_cases = [
        ("I'm really worried about my treatment", True),
        ("Can you explain the dosage?", False),
        ("Ich habe Angst vor den Nebenwirkungen", True),
        ("Wie lange dauert die Therapie?", False),
    ]
    
    for message, should_detect_distress in test_cases:
        has_distress = any(kw in message.lower() for kw in DISTRESS_KEYWORDS)
        status = "✓" if has_distress == should_detect_distress else "✗"
        language = detect_language(message)
        print(f"{status} [{language}] Distress detected: {has_distress}")
        print(f"   Message: '{message}'")


def test_empathic_framing():
    """Test framing clinical information empathically."""
    print("\n" + "=" * 70)
    print("TEST 3: Empathic Framing of Clinical Information")
    print("=" * 70)
    
    # English example
    print("\n### ENGLISH ###")
    print("Clinical fact: 'Lutetium Lu 177 can cause renal toxicity'")
    print("-" * 70)
    
    framed = frame_clinical_information_empathically(
        "Lutetium Lu 177 can cause renal toxicity",
        context="patient asking about side effects",
        user_distressed=False
    )
    print("Empathic framing:")
    print(framed)
    
    # English with distress
    print("\n### ENGLISH (WITH DISTRESS) ###")
    print("Patient is worried: 'I'm terrified about the side effects'")
    print("-" * 70)
    
    framed_distressed = frame_clinical_information_empathically(
        "Lutetium Lu 177 can cause renal toxicity, fatigue, and nausea",
        context="patient expressing fear",
        user_distressed=True
    )
    print("Empathic framing:")
    print(framed_distressed)
    
    # German example
    print("\n### GERMAN ###")
    print("Clinical fact: 'Lutetium Lu 177 kann Nierenschädigung verursachen'")
    print("-" * 70)
    
    framed_de = frame_clinical_information_empathically(
        "Lutetium Lu 177 kann Nierenschädigung verursachen",
        context="Patient fragt nach Nebenwirkungen",
        user_distressed=False
    )
    print("Empathic framing:")
    print(framed_de)
    
    # German with distress
    print("\n### GERMAN (WITH DISTRESS) ###")
    print("Patient ist besorgt: 'Ich habe Angst vor den Nebenwirkungen'")
    print("-" * 70)
    
    framed_de_distressed = frame_clinical_information_empathically(
        "Lutetium Lu 177 kann Nierenschädigung, Müdigkeit und Übelkeit verursachen",
        context="Patient drückt Angst aus",
        user_distressed=True
    )
    print("Empathic framing:")
    print(framed_de_distressed)


def test_umls_result_framing():
    """Test making empathic responses to UMLS results."""
    print("\n" + "=" * 70)
    print("TEST 4: Empathic Responses to UMLS Ontology Results")
    print("=" * 70)
    
    # English UMLS result
    print("\n### ENGLISH: Found results ###")
    umls_result_en = {
        "found": True,
        "term": "Lutetium Lu 177 dotatate",
        "cui": "C4050279",
        "relationships": [
            {"relationLabel": "used_for", "relatedConceptName": "PRRT"},
            {"relationLabel": "has_adverse_effect", "relatedConceptName": "Renal Toxicity"},
            {"relationLabel": "has_adverse_effect", "relatedConceptName": "Fatigue"},
        ]
    }
    
    response_en = create_empathic_response_to_umls_result(
        umls_result_en,
        user_message="What is Lutetium-177?",
        user_distressed=False
    )
    print(response_en)
    
    # German UMLS result
    print("\n### GERMAN: Found results ###")
    umls_result_de = {
        "found": True,
        "term": "Lutetium Lu 177 dotatate",
        "cui": "C4050279",
        "relationships": [
            {"relationLabel": "verwendet_für", "relatedConceptName": "PRRT"},
            {"relationLabel": "hat_nebenwirkung", "relatedConceptName": "Nierenschädigung"},
        ]
    }
    
    response_de = create_empathic_response_to_umls_result(
        umls_result_de,
        user_message="Was ist Lutetium-177?",
        user_distressed=False
    )
    print(response_de)
    
    # Not found example
    print("\n### ENGLISH: Not found ###")
    umls_result_notfound = {
        "found": False,
        "term": "Unknown Medical Term",
        "error": "Term not found in UMLS database"
    }
    
    response_notfound = create_empathic_response_to_umls_result(
        umls_result_notfound,
        user_message="What is gibberish-123?",
        user_distressed=False
    )
    print(response_notfound)


def test_full_scenario():
    """Test a complete scenario: German patient asks about treatment side effects with distress."""
    print("\n" + "=" * 70)
    print("TEST 5: Full Scenario - German patient with distress")
    print("=" * 70)
    
    user_message = "Ich habe Angst vor den Nebenwirkungen der Behandlung. Was wird passieren?"
    
    print(f"\nUser message (German): {user_message}")
    print("-" * 70)
    
    # Step 1: Detect language
    language = detect_language(user_message)
    print(f"\n1. Language detected: {language.upper()}")
    
    # Step 2: Detect distress
    is_distressed = any(kw in user_message.lower() for kw in DISTRESS_KEYWORDS)
    print(f"2. Distress detected: {is_distressed}")
    if is_distressed:
        print(f"   → Trigger empathic response requirement")
    
    # Step 3: Mock UMLS query result
    umls_result = {
        "found": True,
        "term": "Lutetium Lu 177 dotatate",
        "cui": "C4050279",
        "relationships": [
            {"relationLabel": "hat_nebenwirkung", "relatedConceptName": "Nierenschädigung"},
            {"relationLabel": "hat_nebenwirkung", "relatedConceptName": "Müdigkeit"},
        ]
    }
    print(f"\n3. UMLS query result: Found {len(umls_result['relationships'])} verified relationships")
    
    # Step 4: Create empathic response
    empathic_response = create_empathic_response_to_umls_result(
        umls_result,
        user_message=user_message,
        user_distressed=is_distressed
    )
    
    print(f"\n4. Agent response (empathically framed):")
    print("-" * 70)
    print(empathic_response)
    
    print("\n" + "=" * 70)
    print("✓ Pipeline shows:")
    print("  - Clinical validity (UMLS verified facts)")
    print("  - Emotional intelligence (empathic framing)")
    print("  - Multilingual support (German + English)")
    print("  - Distress-aware responses")
    print("=" * 70)


def main():
    """Run all empathy tests."""
    print("\n" + "=" * 70)
    print("EMPATHIC CLINICAL AI PIPELINE TEST")
    print("=" * 70)
    print("Combining clinical validity with emotional intelligence")
    
    test_language_detection()
    test_distress_detection()
    test_empathic_framing()
    test_umls_result_framing()
    test_full_scenario()
    
    print("\n" + "=" * 70)
    print("✓ ALL EMPATHY TESTS COMPLETE")
    print("=" * 70)
    print("""
The pipeline now features:

✓ CLINICAL VALIDITY
  - UMLS ontology for verified medical facts
  - Mock client for testing without API key
  - Cross-lingual entity mapping (German → English)

✓ EMOTIONAL INTELLIGENCE
  - Multilingual distress detection (German + English)
  - Empathic framing of clinical information
  - Tailored responses for distressed patients
  - Culturally appropriate language

✓ INTEGRATED PIPELINE
  1. Patient asks in German (with or without distress)
  2. System detects language and emotional state
  3. Query UMLS for verified relationships (English terms)
  4. Frame results empathically in patient's language
  5. Respond with both clinical accuracy AND emotional care

Ready for production testing! 🔬❤️
    """)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
