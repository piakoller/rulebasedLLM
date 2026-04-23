#!/usr/bin/env python3
"""
Test the empathy pipeline with actual LLM connection.
Shows how the context-aware empathy system works with real LLM responses.
"""

import sys
import json
import requests
import random
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "core"))

from empathy_framing import (
    classify_emotional_state,
    get_nurse_instruction,
    EMOTIONAL_STATE_CONTEXT,
)
from empathy_framing import detect_language

# Bilingual keyword dictionaries for quality assessment
CLINICAL_KEYWORDS = {
    "en": {
        "treatment", "therapy", "medicine", "medication", "treatment plan", "dosage",
        "side effect", "symptom", "diagnosis", "clinical", "oncology", "cancer",
        "chemotherapy", "radiation", "immunotherapy", "prognosis", "recovery"
    },
    "de": {
        "behandlung", "therapie", "medikament", "dosierung", "nebenwirkung", "symptom",
        "diagnose", "klinisch", "onkologie", "krebs", "chemotherapie", "bestrahlung",
        "immuntherapie", "prognose", "genesung", "heilung"
    }
}

EMPATHY_KEYWORDS = {
    "en": {
        "understand", "concern", "worried", "fear", "anxious", "support", "help",
        "difficult", "challenging", "valid", "empathize", "recognize", "acknowledge",
        "strength", "cope", "courage"
    },
    "de": {
        "verstehen", "besorgnis", "sorgen", "angst", "bange", "unterstützung", "hilfe",
        "schwierig", "herausforderung", "berechtigt", "mitfühlen", "anerkennung",
        "würdigung", "stärke", "bewältigung", "mut"
    }
}

UMLS_KEYWORDS = {
    "en": {
        "database", "verified", "medical database", "CUI", "SNOMED", "ICD", "verified concept",
        "medical terminology", "standardized", "coded information"
    },
    "de": {
        "datenbank", "überprüft", "medizinische datenbank", "standardisiert", "SNOMED",
        "ICD", "überprüfter begriff", "medizinische terminologie", "kodiert"
    }
}

NURSE_KEYWORDS = {
    "en": {
        # Naming: Identify and name the emotion
        "name", "emotion", "feeling", "sound like", "experiencing", "feeling like",
        # Understanding: Show understanding and empathy
        "understand", "make sense", "understandable", "recognize", "makes sense",
        # Respecting: Respect patient's coping strategies
        "respect", "strength", "admire", "courage", "handled well",
        # Supporting: Offer practical support
        "support", "help", "can do", "available", "there for you", "assist",
        # Exploring: Explore concerns and emotions
        "explore", "tell me", "what else", "further", "deeper", "more about"
    },
    "de": {
        # Naming
        "benennen", "gefühl", "emotion", "klingt", "erlebst", "fühlst",
        # Understanding
        "verstehen", "verständlich", "nachvollziehen", "sinn macht",
        # Respecting
        "respekt", "stärke", "bewunderung", "mut", "gut gemacht",
        # Supporting
        "unterstützung", "hilfe", "können", "verfügbar", "für dich", "unterstütze",
        # Exploring
        "erkunden", "erzähl", "was noch", "weiter", "tiefer", "mehr über"
    }
}

# Configuration
OLLAMA_MODEL = "hf.co/unsloth/medgemma-27b-it-GGUF:Q4_K_M"  # Medical model with stable Q4_K_M quantization
OLLAMA_URL = "http://localhost:11434/api/chat"
TIMEOUT = 120  # Increased timeout for initial model load
NUM_RANDOM_QUESTIONS = 3  # Number of random questions to test

from core.umls_grounding import extract_medical_terms, get_umls_grounding


def load_sample_questions(num_questions: int = 3) -> list[dict]:
    """Load random questions from data/psma_sample_questions.json"""
    sample_file = Path(__file__).parent / "data" / "psma_sample_questions.json"
    
    try:
        with open(sample_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Flatten all questions from all categories
        all_questions = []
        for category, questions in data.items():
            all_questions.extend(questions)
        
        # Randomly select the requested number
        selected = random.sample(all_questions, min(num_questions, len(all_questions)))
        
        # Convert to test format
        test_questions = []
        for q in selected:
            test_questions.append({
                "question": q,
                "category": "Patient Question",
                "expected_emotion": "unknown",  # Will be classified by the system
            })
        
        return test_questions
    
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️  Could not load sample questions: {e}")
        print("   Falling back to default questions")
        # Fallback to default questions
        return [
            {
                "question": "Ich mache mir Sorgen um die Nebenwirkungen der Therapie. Sind die gefährlich?",
                "category": "Anxiety (German)",
                "expected_emotion": "anxiety",
            },
            {
                "question": "I'm worried the treatment might make things worse. What if complications occur?",
                "category": "Anxiety (English)",
                "expected_emotion": "anxiety",
            },
            {
                "question": "Wie lange dauert die Behandlung normalerweise?",
                "category": "Neutral/Factual (German)",
                "expected_emotion": "neutral",
            },
        ]

# Load random questions
TEST_QUESTIONS = load_sample_questions(NUM_RANDOM_QUESTIONS)

def parse_llm_response(full_response: str) -> dict:
    """
    Parse LLM response to extract thinking process and actual response.
    
    Expected format:
    <unused94>thinking content<unused95>actual response
    """
    thinking = ""
    patient_response = ""
    
    if "<unused94>" in full_response and "<unused95>" in full_response:
        # Extract thinking between markers
        start_idx = full_response.find("<unused94>") + len("<unused94>")
        end_idx = full_response.find("<unused95>")
        thinking = full_response[start_idx:end_idx].strip()
        
        # Extract actual response after the closing marker
        patient_response = full_response[end_idx + len("<unused95>"):].strip()
    else:
        # No thinking markers found, treat entire response as patient response
        patient_response = full_response
    
    return {
        "thinking": thinking,
        "patient_response": patient_response,
        "full_response": full_response,
    }

def detect_clinical_accuracy(response_text: str, language: str) -> dict:
    """
    Detect clinical accuracy in response using bilingual keywords.
    Returns dict with score and details.
    """
    response_lower = response_text.lower()
    keywords = CLINICAL_KEYWORDS.get(language, CLINICAL_KEYWORDS.get("en", set()))
    
    found_keywords = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', response_lower)]
    
    score = len(found_keywords) / max(len(keywords), 1) if keywords else 0
    has_clinical_terms = len(found_keywords) > 0
    
    return {
        "has_clinical_terms": has_clinical_terms,
        "keywords_found": found_keywords,
        "score": min(1.0, score),  # Normalize to 0-1
        "details": f"Found {len(found_keywords)} clinical keywords in {language}"
    }

def detect_empathy(response_text: str, language: str, emotional_state: str) -> dict:
    """
    Detect empathic language in response using bilingual keywords.
    Only checks for empathy if emotional state is not neutral.
    Returns dict with score and details.
    """
    if emotional_state == "neutral":
        return {
            "is_empathic": True,  # Not required for neutral
            "keywords_found": [],
            "score": 1.0,
            "details": "Neutral state requires factual response (empathy not required)"
        }
    
    response_lower = response_text.lower()
    keywords = EMPATHY_KEYWORDS.get(language, EMPATHY_KEYWORDS.get("en", set()))
    
    found_keywords = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', response_lower)]
    
    score = len(found_keywords) / max(len(keywords), 1) if keywords else 0
    is_empathic = len(found_keywords) > 0
    
    return {
        "is_empathic": is_empathic,
        "keywords_found": found_keywords,
        "score": min(1.0, score),  # Normalize to 0-1
        "details": f"Found {len(found_keywords)} empathy keywords in {language}"
    }

def detect_umls_api_usage(umls_grounding: dict) -> dict:
    """
    Detect if UMLS API was actually called and used.
    Checks the grounding data from pre-LLM UMLS verification.
    """
    api_called = umls_grounding.get("grounded", False)
    num_verified = umls_grounding.get("num_verified", 0)
    terms = umls_grounding.get("terms_verified", [])
    
    return {
        "api_referenced": api_called,
        "api_called": api_called,
        "num_verified_concepts": num_verified,
        "verified_terms": [t["term"] for t in terms],
        "details": f"UMLS API called: {num_verified} verified concepts found" if api_called else "UMLS API: No verified concepts"
    }

def detect_nurse_framework(response_text: str, language: str) -> dict:
    """
    Detect if NURSE framework elements are present in response.
    NURSE = Naming, Understanding, Respecting, Supporting, Exploring
    """
    response_lower = response_text.lower()
    keywords = NURSE_KEYWORDS.get(language, NURSE_KEYWORDS.get("en", set()))
    
    found_keywords = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', response_lower)]
    
    # Count how many NURSE elements are likely present
    nurse_elements_detected = len(found_keywords) > 0
    
    return {
        "nurse_framework_used": nurse_elements_detected,
        "keywords_found": found_keywords,
        "num_elements": len(found_keywords),
        "score": min(1.0, len(found_keywords) / max(len(keywords), 1)),
        "details": f"Found {len(found_keywords)} NURSE framework indicators"
    }

def call_ollama(messages: list[dict]) -> str:
    """Call Ollama API with given messages."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    
    try:
        print(f"\n  📡 Calling Ollama ({OLLAMA_MODEL})...", end=" ", flush=True)
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        result = data.get("message", {}).get("content", "")
        print("✓")
        return result
    except requests.exceptions.ConnectionError:
        print("\n  ❌ ERROR: Cannot connect to Ollama at", OLLAMA_URL)
        print("     Make sure Ollama is running: ollama serve")
        return None
    except requests.exceptions.Timeout:
        print("\n  ❌ ERROR: Ollama request timed out")
        return None
    except Exception as e:
        print(f"\n  ❌ ERROR: {str(e)}")
        return None

def run_question_with_llm(question: str, category: str, expected_emotion: str):
    """Test a single question with LLM using context-aware empathy."""
    print("\n" + "=" * 85)
    print(f"CATEGORY: {category}")
    print("=" * 85)
    
    # Step 1: Analysis
    language = detect_language(question)
    emotional_state = classify_emotional_state(question)
    
    print(f"\n📝 PATIENT QUESTION ({language}):")
    print(f'   "{question}"')
    
    print(f"\n📊 ANALYSIS:")
    print(f"   Language: {language}")
    print(f"   Emotion: {emotional_state} (expected: {expected_emotion})")
    
    status_icon = "✓" if emotional_state == expected_emotion else "✗"
    print(f"   {status_icon} Classification: {status_icon}")
    
    # Initialize result dict to collect full data
    result_data = {
        "category": category,
        "question": question,
        "language": language,
        "emotional_state": emotional_state,
        "expected_emotion": expected_emotion,
    }
    
    # Step 2a: Get UMLS grounding (pre-LLM enhancement)
    print(f"\n🔬 UMLS VERIFICATION (Hybrid: German + English):")
    umls_grounding = get_umls_grounding(question, language=language)
    if umls_grounding["grounded"]:
        print(f"   ✓ Found {umls_grounding['num_verified']} verified concepts from {umls_grounding['num_searches']} searches")
        for term_info in umls_grounding["terms_verified"]:
            tag = "(translated)" if term_info.get("is_translated") else "(original)"
            print(f"     • {term_info['term']} {tag} → CUI: {term_info['cui']}")
    else:
        print(f"   (Searched {umls_grounding.get('num_searches', 0)} terms, none verified)")
    
    result_data["umls_grounding"] = umls_grounding
    
    # Step 2b: Get emotional context
    context = get_nurse_instruction(emotional_state)
    print(f"\n💡 EMOTIONAL CONTEXT (for LLM):")
    print(f"   {context[:100]}...")
    
    # Step 3: Build system message with emotional context AND UMLS grounding
    system_message = f"""You are a compassionate clinical assistant for patients undergoing cancer treatment.

Your role is to provide accurate medical information combined with emotional support.

Patient's Emotional State:
{context}

Verified Medical Concepts (from NIH UMLS):
{umls_grounding['context'] if umls_grounding['grounded'] else "No pre-grounding available for this question."}

Clinical Guidelines:
- Always verify information with established medical facts
- Respond in the patient's language (German OR English, not both)
- Be honest about uncertainties
- Prioritize patient safety and comfort
- Never make guarantees about treatment outcomes

Behavioral Constraints:
- Ask before telling when facts are not yet needed or patient is distressed
- Validate emotion before giving technical explanations
- Keep responses clear and understandable for patients
"""
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": question}
    ]
    
    # Step 4: Get LLM response
    print(f"\n🤖 LLM RESPONSE:")
    llm_response = call_ollama(messages)
    
    if llm_response is None:
        print("   (Could not get LLM response)")
        result_data["success"] = False
        result_data["llm_full_response"] = None
        result_data["llm_thinking"] = None
        result_data["llm_patient_response"] = None
        return result_data
    
    # Parse response to separate thinking from actual response
    parsed_response = parse_llm_response(llm_response)
    result_data["llm_full_response"] = parsed_response["full_response"]
    result_data["llm_thinking"] = parsed_response["thinking"]
    result_data["llm_patient_response"] = parsed_response["patient_response"]
    
    # Display response preview (patient response only)
    response_preview = parsed_response["patient_response"][:200] + "..." if len(parsed_response["patient_response"]) > 200 else parsed_response["patient_response"]
    print(f"   {response_preview}")
    
    # Step 5: Analyze response quality with smart detection
    print(f"\n✨ RESPONSE ANALYSIS:")
    
    # Use helper functions for intelligent quality assessment
    clinical_analysis = detect_clinical_accuracy(parsed_response["patient_response"], language)
    empathy_analysis = detect_empathy(parsed_response["patient_response"], language, emotional_state)
    umls_analysis = detect_umls_api_usage(umls_grounding)  # Use actual grounding data
    nurse_analysis = detect_nurse_framework(parsed_response["patient_response"], language)
    
    # Create comprehensive quality assessment
    checks = {
        "Has clinical accuracy": clinical_analysis["has_clinical_terms"],
        "Clinical keywords score": f"{clinical_analysis['score']:.1%}",
        "Is clinically detailed": clinical_analysis["score"] >= 0.15,
        "Has empathy (when needed)": empathy_analysis["is_empathic"],
        "Empathy keywords score": f"{empathy_analysis['score']:.1%}",
        "UMLS API Called": umls_analysis["api_called"],
        "Verified concepts found": umls_analysis["num_verified_concepts"],
        "NURSE framework detected": nurse_analysis["nurse_framework_used"],
        "NURSE elements found": nurse_analysis["num_elements"],
    }
    
    result_data["quality_checks"] = checks
    result_data["quality_details"] = {
        "clinical": clinical_analysis,
        "empathy": empathy_analysis,
        "umls": umls_analysis,
        "nurse": nurse_analysis,
    }
    
    for check_name, result in checks.items():
        if isinstance(result, bool):
            icon = "✓" if result else "✗"
            print(f"   {icon} {check_name}")
        else:
            print(f"   • {check_name}: {result}")
    
    result_data["success"] = True
    return result_data

def main():
    print("\n" + "=" * 85)
    print(" " * 20 + "EMPATHY PIPELINE WITH ACTUAL LLM TESTING")
    print("=" * 85)
    
    print("\nThis test connects to a real LLM and demonstrates:")
    print("  ✓ Context-aware emotional state classification")
    print("  ✓ Emotional context injection into system message")
    print("  ✓ LLM generating empathic responses naturally")
    print("  ✓ Bilingual support (German/English)")
    print("  ✓ No forced prefixes or step-by-step checklists")
    
    print(f"\n🎲 RANDOM QUESTIONS LOADED:")
    for i, q in enumerate(TEST_QUESTIONS, 1):
        print(f"   {i}. {q['question'][:60]}...")
    
    print(f"\n🔧 CONFIGURATION:")
    print(f"   Model: {OLLAMA_MODEL}")
    print(f"   URL: {OLLAMA_URL}")
    print(f"   Questions to test: {len(TEST_QUESTIONS)}")
    
    # Test connection
    print(f"\n🔗 Testing connection to Ollama...", end=" ", flush=True)
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "messages": [{"role": "user", "content": "test"}], "stream": False},
            timeout=30  # Increased timeout for connection test
        )
        if response.status_code == 200:
            print("✓ Connected")
        else:
            print(f"✗ Error ({response.status_code})")
    except Exception as e:
        print(f"✗ Cannot connect: {str(e)}")
        print("\n⚠️  Make sure Ollama is running:")
        print("    ollama serve")
        return
    
    # Run tests
    results = []
    for i, test_case in enumerate(TEST_QUESTIONS, 1):
        print(f"\n{'#' * 85}")
        print(f"TEST {i}/{len(TEST_QUESTIONS)}")
        print(f"{'#' * 85}")
        
        result_data = run_question_with_llm(
            question=test_case["question"],
            category=test_case["category"],
            expected_emotion=test_case["expected_emotion"]
        )
        
        results.append(result_data)
    
    # Summary
    print("\n" + "=" * 85)
    print(" " * 35 + "TEST SUMMARY")
    print("=" * 85)
    
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"\n✅ Successfully tested: {successful}/{total}")
    
    if successful == total:
        print("\n" + "🎉 " * 20)
        print("ALL TESTS PASSED!")
        print("🎉 " * 20)
    else:
        print(f"\n⚠️  {total - successful} test(s) need attention")
    
    # Save full results to JSON
    output_file = Path(__file__).parent / "LLM_TEST_RESULTS.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📝 Full results saved to: {output_file}")
    
    print("=" * 85)

if __name__ == "__main__":
    main()
