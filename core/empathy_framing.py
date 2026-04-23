"""Dynamic NURSE protocol-based empathy system for clinical conversations.

Maps emotional states to NURSE protocol instructions (Name, Understand, Respect, 
Support, Explore) and uses the LLM to classify emotional state and apply appropriate 
empathic strategies.
"""

import json
from typing import Optional, Literal
import os
import requests

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
    "emotional_overwhelm": {
        "state_description": "Patient feels they can't cope with the situation (emotional overwhelm)",
        "context_for_llm": (
            "The patient is emotionally overwhelmed. They are struggling to cope with the reality of their situation. "
            "Respond with deep empathy and respect. Focus on being present and supportive. "
            "Do not rush into technical details. Acknowledge the weight of what they are experiencing."
        ),
    },
    "technical_overwhelm": {
        "state_description": "Patient is confused by technical information or logistics",
        "context_for_llm": (
            "The patient is overwhelmed by technical information, medical jargon, or complex logistics. "
            "Simplify your language immediately. Break down concepts into clear, manageable steps. "
            "Focus on the most important 'next thing' to know. Avoid all non-essential medical detail."
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


# NURSE Strategy Sentence Starters to guide the LLM's empathy integration (English)
STRATEGY_SENTENCE_STARTERS_EN = {
    "naming": [
        "It sounds like you're feeling {emotion}...",
        "I can hear the {emotion} in your voice...",
        "Many patients feel {emotion} when faced with this...",
    ],
    "understanding": [
        "I can understand why that would be {emotion} for you...",
        "It makes sense that you would feel {emotion} given what you've been through...",
        "I can see how that would feel overwhelming...",
    ],
    "respecting": [
        "I'm impressed by how you're handling this...",
        "You've clearly put a lot of thought into your care...",
        "It takes a lot of strength to ask these questions...",
    ],
    "supporting": [
        "I want to help you through this step by step...",
        "Your medical team and I are here to support you...",
        "We will make sure you have everything you need...",
    ],
    "exploring": [
        "Can you tell me more about what's worrying you most?",
        "What have you heard so far about this?",
        "What would be most helpful for you to understand right now?",
    ],
}

# NURSE Strategy Sentence Starters to guide the LLM's empathy integration (German)
STRATEGY_SENTENCE_STARTERS_DE = {
    "naming": [
        "Es hört sich so an, als ob Sie {emotion} fühlen...",
        "Ich kann die {emotion} in Ihren Worten heraushören...",
        "Viele Patienten fühlen sich {emotion}, wenn sie damit konfrontiert werden...",
    ],
    "understanding": [
        "Ich kann gut verstehen, warum das für Sie {emotion} ist...",
        "Es ergibt absolut Sinn, dass Sie sich so {emotion} fühlen, nach all dem, was Sie durchgemacht haben...",
        "Ich sehe, wie überwältigend das für Sie sein muss...",
    ],
    "respecting": [
        "Ich bin beeindruckt davon, wie Sie mit dieser Situation umgehen...",
        "Sie haben sich offensichtlich sehr viele Gedanken über Ihre Behandlung gemacht...",
        "Es erfordert viel Kraft, diese Fragen so offen zu stellen...",
    ],
    "supporting": [
        "Ich möchte Sie Schritt für Schritt dabei unterstützen...",
        "Ihr medizinisches Team und ich sind hier, um Ihnen Rückhalt zu geben...",
        "Wir werden sicherstellen, dass Sie alles haben, was Sie brauchen...",
    ],
    "exploring": [
        "Können Sie mir mehr darüber erzählen, was Ihnen am meisten Sorgen bereitet?",
        "Was haben Sie bisher darüber gehört?",
        "Was wäre im Moment am hilfreichsten für Sie zu verstehen?",
    ],
}

# Legacy alias for backward compatibility (defaults to English)
STRATEGY_SENTENCE_STARTERS = STRATEGY_SENTENCE_STARTERS_EN


# --- Lightweight replacements for the previous `rules` module ---
# Distress keywords used across the pipeline (English + German samples)
DISTRESS_KEYWORDS = [
    "nervous", "worried", "anxious", "sorge", "sorgen", "ängst", "angst", "panik",
    "überfordert", "überfordert", "frustriert", "genervt", "scared", "afraid",
    "terrified", "nervös", "besorgt", "besorgnis", "sorgen"
]


def detect_language(text: str) -> str:
    """Simple language heuristic: returns 'de' for German-like text else 'en'."""
    if not text:
        return "en"
    lowered = text.lower()
    german_markers = ["ich", "sie", "nicht", "nebenwirkung", "nebenwirkungen", "therapie", "behandlung", "dass", "ist", "sind"]
    if any(marker in lowered for marker in german_markers):
        return "de"
    return "en"


def sentiment_analyzer(text: str) -> dict | None:
    """Very small sentiment helper: returns a mandatory prefix when distress keywords present."""
    if not text:
        return None
    lowered = text.lower()
    if any(kw in lowered for kw in DISTRESS_KEYWORDS):
        return {"mandatory_prefix": "I’m sorry you’re going through this. "}
    return None


def apply_rules(user_message: str, state: str = "start", context: dict | None = None) -> dict:
    """Minimal rule replacement used by the agent.

    Returns a dict that may contain keys: direct_response, stop_chat, mandatory_prefix
    """
    if not user_message:
        return {}
    lowered = user_message.lower()
    # Simple terminal rule
    if any(term in lowered for term in ["bye", "goodbye", "quit", "exit"]):
        return {"direct_response": "Goodbye.", "stop_chat": True}
    # No other rules by default
    return {}


# --- LLM-based classifier helper ---
DEFAULT_OLLAMA_MODEL_EMPATHY = os.getenv("OLLAMA_MODEL", "hf.co/unsloth/medgemma-1.5-4b-it-GGUF:BF16")
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")


def make_ollama_classifier(model: str | None = None, ollama_url: str | None = None, timeout: int = 30):
    """Return a function that calls an Ollama-compatible chat endpoint.

    The returned function accepts a single `prompt` string and returns the
    assistant's text. On any network/error it returns an empty string so callers
    can fall back to heuristics.
    """
    model = model or DEFAULT_OLLAMA_MODEL_EMPATHY
    ollama_url = ollama_url or DEFAULT_OLLAMA_URL

    def classifier(prompt: str) -> str:
        try:
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}
            resp = requests.post(ollama_url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "") or ""
        except Exception:
            return ""

    return classifier



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
            # Increased sensitivity to implied anxiety: include guidance for questions
            # that ask about probabilities, risks, or personal outcomes.
            classification_prompt = f"""
You are a clinical conversation emotion classifier. Read the patient's message and pick exactly one label from this closed set: anxiety, frustration, fear, emotional_overwhelm, technical_overwhelm, neutral.

Rules (must follow exactly):
- Output exactly one of: anxiety, frustration, fear, emotional_overwhelm, technical_overwhelm, neutral (lowercase), and nothing else.

Interpretation guidance:
- anxiety: the patient expresses or implies worry about outcomes, risks, uncertainty, or personal impact.
- fear: explicit, intense fear or statements about danger to life/safety.
- frustration: irritation, complaints, feeling ignored, or impatience.
- emotional_overwhelm: patient expresses being unable to cope, feeling lost, or emotionally saturated ("I can't take this anymore", "I'm falling apart").
- technical_overwhelm: patient expresses confusion about medical terms, data, or complex steps ("This is too much information", "I don't understand these results", "Explain it simply").
- neutral: informational, logistical, or clinical questions without emotional content or implied worry.

Important heuristics:
- If they complain about complexity or "too much info", use *technical_overwhelm*.
- If they express deep emotional struggle, use *emotional_overwhelm*.

Examples (input -> output):
"I'm nervous about the treatment" -> anxiety
"Will I die from this?" -> fear
"I've been waiting for weeks and nobody answers" -> frustration
"I can't cope with all this bad news" -> emotional_overwhelm
"This is all too complicated, I don't understand the PSA graph" -> technical_overwhelm
"When is my next scan scheduled?" -> neutral

Message: {user_message}

Classification (one word only):
"""

            result = llm_classifier(classification_prompt)
            emotion = result.strip().lower()
            # Validate the result strictly against allowed labels
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
    technical_overwhelm_keywords = [
        "too much information", "so much information", "don't know where to start",
        "information overload", "complicated", "confused", "don't understand",
        "too technical", "explain it simply", "zu viele informationen", "verwirrt",
        "zu kompliziert", "einfach erklären"
    ]
    if any(word in lowered for word in technical_overwhelm_keywords):
        return "technical_overwhelm"

    emotional_overwhelm_keywords = [
        "can't cope", "too much to handle", "falling apart", "can't take it",
        "overwhelm", "zuviel", "zu viel", "überfordert", "kopf raucht"
    ]
    if any(word in lowered for word in emotional_overwhelm_keywords):
        return "emotional_overwhelm"
    
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
