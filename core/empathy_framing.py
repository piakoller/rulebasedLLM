"""Dynamic NURSE protocol-based empathy system for clinical conversations.

Maps emotional states to NURSE protocol instructions (Name, Understand, Respect, 
Support, Explore) and uses the LLM to classify emotional state and apply appropriate 
empathic strategies.
"""

import json
from typing import Optional, Literal
from rules import detect_language

# Emotional State Context: Gives the LLM awareness of patient's emotional state
# The LLM has full freedom to generate empathy naturally, not follow a rigid script
EMOTIONAL_STATE_CONTEXT = {
    "anxiety": {
        "state_description": "Patient is worried or nervous about treatment/condition",
        "context_for_llm": (
            "The patient is experiencing anxiety/worry about their treatment. "
            "They need reassurance grounded in facts, acknowledgment that their concern is legitimate, "
            "and understanding of what will be monitored or managed. "
            "Generate a natural, conversational response that addresses their worry—you choose the best way to do this."
        ),
    },
    "frustration": {
        "state_description": "Patient is irritated, feels unheard, or impatient",
        "context_for_llm": (
            "The patient is frustrated or impatient. They likely feel unheard or are experiencing delays. "
            "Acknowledge their frustration directly and naturally, explain why it makes sense, "
            "and provide clear next steps or concrete information. Be action-oriented. "
            "Choose how best to address their frustration in your response."
        ),
    },
    "fear": {
        "state_description": "Patient is experiencing fear, terror, or feeling unsafe",
        "context_for_llm": (
            "The patient is experiencing fear or feeling unsafe. Use calm, steady language. "
            "Address their specific fear directly and naturally. Emphasize what will protect them, "
            "what will be monitored, and why safety measures are in place. "
            "Normalize their fear—it's a rational response to medical situations. "
            "Generate your own empathic approach based on what you think will best address their fear."
        ),
    },
    "overwhelm": {
        "state_description": "Patient has too much information or too many decisions",
        "context_for_llm": (
            "The patient is feeling overwhelmed. They may have received too much information, "
            "have too many decisions to make, or feel lost. "
            "Respond with simplicity and respect for their pace. Focus on the most important thing first. "
            "Use shorter responses and let them guide what they want to understand next. "
            "How you structure and pace your response matters more than specific phrases."
        ),
    },
    "neutral": {
        "state_description": "Patient shows no clear emotional distress",
        "context_for_llm": (
            "The patient is asking straightforward questions without apparent emotional distress. "
            "Respond clearly and professionally. Answer their question, offer context, and be honest. "
            "No need for extra reassurance or emotional language—clarity and accuracy are what they need."
        ),
    },
}


def classify_emotional_state(
    user_message: str,
    conversation_history: Optional[list[dict]] = None,
    llm_classifier=None,
) -> Literal["anxiety", "frustration", "fear", "overwhelm", "neutral"]:
    """
    Classify the user's emotional state using the LLM.
    
    Falls back to keyword heuristics if LLM is unavailable.
    
    Args:
        user_message: The user's current message
        conversation_history: Optional previous messages for context
        llm_classifier: Optional LLM function for classification
        
    Returns:
        One of: "anxiety", "frustration", "fear", "overwhelm", "neutral"
    """
    if llm_classifier:
        try:
            classification_prompt = f"""Classify the emotional state of this patient message. 
Only respond with the emotion classification (no explanation).

Emotional states:
- anxiety: worry, nervousness, concern about treatment
- frustration: irritation, feeling unheard, impatience
- fear: terror, extreme worry, feeling unsafe
- overwhelm: too much information, too many decisions
- neutral: no clear emotional distress

Message: {user_message}

Classification (one word only):"""
            
            result = llm_classifier(classification_prompt)
            emotion = result.strip().lower()
            
            # Validate the result
            if emotion in EMOTIONAL_STATE_CONTEXT:
                return emotion
        except Exception:
            pass
    
    # Fallback to keyword heuristics
    lowered = user_message.lower()
    
    # Fear keywords (English + German)
    fear_keywords = [
        "terrified", "terrify", "petrified", "scared stiff", "freeze", "panic",
        "terror", "afraid", "beängstigt", "furchtbar", "panik"
    ]
    if any(word in lowered for word in fear_keywords):
        return "fear"
    
    # Overwhelm keywords (English + German)
    overwhelm_keywords = [
        "overwhelm", "too much", "can't think", "confused", "dizzy", "too many",
        "zuviel", "zu viel", "überfordert", "verwirrt", "durcheinander", "kopf raucht",
        "so much information", "don't know where to start", "information overload"
    ]
    if any(word in lowered for word in overwhelm_keywords):
        return "overwhelm"
    
    # Frustration keywords (English + German)
    frustration_keywords = [
        "frustrated", "irritated", "annoyed", "tired of", "enough", "impatient",
        "frustriert", "genervt", "ungeduldig", "reicht mir", "zu lange",
        "taking forever", "why can't you", "wait", "waiting", "weeks"
    ]
    if any(word in lowered for word in frustration_keywords):
        return "frustration"
    
    # Anxiety keywords (English + German)
    anxiety_keywords = [
        "nervous", "worried", "anxious", "concerned", "apprehensive", "uneasy",
        "sorge", "sorgen", "nervös", "angespannt", "besorg", "besorgnis",
        "side effects", "will it", "what if"
    ]
    if any(word in lowered for word in anxiety_keywords):
        return "anxiety"
    
    return "neutral"


def get_nurse_instruction(emotional_state: str) -> str:
    """
    Get context about patient's emotional state to inform LLM response generation.
    
    This provides the LLM with awareness of what the patient needs, WITHOUT prescribing
    HOW to respond. The LLM has full freedom to generate empathy naturally.
    
    Args:
        emotional_state: One of "anxiety", "frustration", "fear", "overwhelm", "neutral"
        
    Returns:
        Context guidance for the LLM to use as it sees fit
    """
    if emotional_state not in EMOTIONAL_STATE_CONTEXT:
        return EMOTIONAL_STATE_CONTEXT["neutral"]["context_for_llm"]
    
    return EMOTIONAL_STATE_CONTEXT[emotional_state]["context_for_llm"]


def get_nurse_protocol_details(emotional_state: str) -> dict:
    """
    Get details about an emotional state and what the patient likely needs.
    
    Args:
        emotional_state: One of "anxiety", "frustration", "fear", "overwhelm", "neutral"
        
    Returns:
        Dictionary with state description and context for LLM
    """
    return EMOTIONAL_STATE_CONTEXT.get(
        emotional_state, 
        EMOTIONAL_STATE_CONTEXT["neutral"]
    )


def frame_clinical_information_empathically(
    clinical_info: str,
    context: str = "",
    user_distressed: bool = False,
) -> str:
    """
    Wrap clinical information with empathic framing.
    
    Args:
        clinical_info: The clinical fact (e.g., from UMLS)
        context: Additional context about the patient's question
        user_distressed: Whether the user expressed distress
        
    Returns:
        Clinical info wrapped in empathic language
    """
    language = detect_language(clinical_info + " " + context)
    
    if language == "de":
        return _frame_german(clinical_info, context, user_distressed)
    else:
        return _frame_english(clinical_info, context, user_distressed)


def _frame_english(clinical_info: str, context: str, distressed: bool) -> str:
    """Frame clinical information with English empathy."""
    
    frames = {
        "side_effect": (
            "Based on verified medical data, I want to be honest about what patients "
            "typically experience so we can plan together. {clinical_info} "
            "These side effects are manageable, and we have strategies to help you through them."
        ),
        "therapy_purpose": (
            "Let me explain what this treatment is designed to do. {clinical_info} "
            "Your medical team chose this because they believe it's the best option for you."
        ),
        "relationship": (
            "According to verified medical records, {clinical_info} "
            "I know this might sound technical, but I want you to understand your condition."
        ),
    }
    
    if distressed:
        frames["side_effect"] = (
            "I understand this is a lot to think about. Here's what the research shows: "
            "{clinical_info} The important thing is that your team is watching closely "
            "and we can adjust your care if needed. You won't go through this alone."
        )
        frames["therapy_purpose"] = (
            "I know you might feel worried about this treatment. Let me explain why it's recommended: "
            "{clinical_info} Your safety is our top priority, and your doctors chose this "
            "because they believe it gives you the best chance."
        )
    
    # Determine category (simple heuristic)
    if any(word in clinical_info.lower() for word in ["side effect", "adverse", "toxicity", "nausea", "fatigue"]):
        template = frames.get("side_effect", frames["relationship"])
    elif any(word in clinical_info.lower() for word in ["therapy", "treatment", "purpose", "designed"]):
        template = frames.get("therapy_purpose", frames["relationship"])
    else:
        template = frames.get("relationship", frames["relationship"])
    
    return template.format(clinical_info=clinical_info)


def _frame_german(clinical_info: str, context: str, distressed: bool) -> str:
    """Frame clinical information with German empathy."""
    
    frames = {
        "side_effect": (
            "Basierend auf überprüften Daten möchte ich ehrlich sein, was Patienten "
            "typischerweise erleben, damit wir gemeinsam planen können. {clinical_info} "
            "Diese Nebenwirkungen sind handhabbar, und wir haben Strategien, um Ihnen zu helfen."
        ),
        "therapy_purpose": (
            "Lassen Sie mich erklären, wozu diese Behandlung gedacht ist. {clinical_info} "
            "Ihr Arzteam hat sich dafür entschieden, weil es die beste Option für Sie ist."
        ),
        "relationship": (
            "Nach überprüften medizinischen Daten: {clinical_info} "
            "Ich weiß, das klingt technisch, aber ich möchte, dass Sie Ihren Zustand verstehen."
        ),
    }
    
    if distressed:
        frames["side_effect"] = (
            "Ich verstehe, dass das viel ist. Hier ist, was die Forschung zeigt: "
            "{clinical_info} Das Wichtigste ist, dass Ihr Team aufmerksam ist "
            "und wir Ihre Behandlung anpassen können. Sie gehen das nicht alleine durch."
        )
        frames["therapy_purpose"] = (
            "Ich weiß, dass Ihnen vor dieser Behandlung nervös sein können. Lassen Sie mich "
            "erklären, warum sie empfohlen wird: {clinical_info} Ihre Sicherheit ist unsere "
            "höchste Priorität, und Ihre Ärzte haben sich dafür entschieden, weil sie "
            "Ihnen die beste Chance geben."
        )
    
    # Determine category
    if any(word in clinical_info.lower() for word in ["nebenwirkung", "schädlich", "toxizität", "übelkeit", "müdigkeit"]):
        template = frames.get("side_effect", frames["relationship"])
    elif any(word in clinical_info.lower() for word in ["therapie", "behandlung", "zweck", "bestimmt"]):
        template = frames.get("therapy_purpose", frames["relationship"])
    else:
        template = frames.get("relationship", frames["relationship"])
    
    return template.format(clinical_info=clinical_info)


def create_empathic_response_to_umls_result(
    umls_result: dict,
    user_message: str,
    user_distressed: bool = False,
) -> str:
    """
    Create an empathic response to UMLS ontology query results.
    
    Args:
        umls_result: The tool result from query_umls_ontology
        user_message: The original user message
        user_distressed: Whether user expressed distress
        
    Returns:
        Empathic response ready for the LLM
    """
    language = detect_language(user_message)
    
    if not umls_result.get("found"):
        if language == "de":
            return (
                f"Ich konnte keinen Eintrag für '{umls_result.get('term')}' "
                f"in der überprüften Datenbank finden. "
                f"Aber ich kann über das allgemein Bekannte darüber sprechen."
            )
        else:
            return (
                f"I couldn't find '{umls_result.get('term')}' in the verified database. "
                f"But I can tell you what is generally known about it."
            )
    
    # Format relationships empathically
    relationships = umls_result.get("relationships", [])
    
    if language == "de":
        if relationships:
            rel_text = ", ".join(
                f"{rel['relationLabel']}: {rel['relatedConceptName']}"
                for rel in relationships[:3]
            )
            intro = "Die überprüfte Datenbank zeigt folgende wichtige Informationen:\n\n"
            outro = "\n\nLassen Sie mich erklären, was das für Sie bedeutet..."
            return intro + rel_text + outro
        else:
            return (
                "Die überprüfte Datenbank bestätigt, dass dies ein anerkannter "
                "medizinischer Begriff ist."
            )
    else:
        if relationships:
            rel_text = ", ".join(
                f"{rel['relationLabel']}: {rel['relatedConceptName']}"
                for rel in relationships[:3]
            )
            intro = "The verified database shows these important relationships:\n\n"
            outro = "\n\nLet me help you understand what this means for you..."
            return intro + rel_text + outro
        else:
            return (
                "The verified database confirms this is a recognized medical term."
            )
