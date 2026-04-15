"""Empathic framing for clinical UMLS information.

This module provides ways to present verified medical information
with emotional support and compassionate language.
"""

from rules import detect_language


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
