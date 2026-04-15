"""Rule-based logic for the hybrid empathy layer.

Supports both English and German-speaking patients.
"""


DISTRESS_KEYWORDS = {
    # English
    "scared",
    "terrified",
    "fear",
    "afraid",
    "anxious",
    "worried",
    "panic",
    "panicked",
    "pain",
    "suffering",
    "overwhelmed",
    "distressed",
    "depressed",
    "desperate",
    "hopeless",
    # German
    "angst",
    "angespannt",
    "nervös",
    "besorg",
    "panik",
    "schmerz",
    "leid",
    "überfordert",
    "verzweifelt",
    "hoffnung",
    "depressiv",
    "hilflos",
    "traurig",
    "ängstlich",
}

SUPPORTIVE_MARKERS = {
    # English
    "i understand",
    "i'm sorry",
    "that sounds difficult",
    "you are not alone",
    "we can take this step by step",
    "i want to help",
    "i will keep this simple",
    "let me explain",
    "together we can",
    "don't worry",
    # German
    "ich verstehe",
    "es tut mir leid",
    "das klingt schwierig",
    "sie sind nicht allein",
    "wir können das schritt für schritt",
    "ich möchte helfen",
    "ich halte es einfach",
    "lassen sie mich erklären",
    "zusammen können wir",
    "machen sie sich keine sorgen",
    "das ist völlig normal",
    "es ist ok",
}


def detect_language(text: str) -> str:
    """
    Detect if text is German or English.
    Returns 'de' for German, 'en' for English.
    Uses word boundaries and common German characteristics.
    """
    text_lower = text.lower()
    
    # German-specific patterns and words (expanded)
    german_indicators = {
        # Common German words
        "der", "die", "das", "ist", "und", "ich", "mich", "mir", "den", "dem",
        # German question words
        "was", "wie", "wann", "wo", "warum", "welch", "wer",
        # Common German verbs (present tense)
        "bin", "bist", "seid", "sind", "haben", "habe", "hast", "habt",
        "werden", "werde", "wirst", "werdet", "kann", "könnt", "muss", "musst",
        "geben", "gibt", "gebt", "sage", "sagst", "sagen", "sagt",
        # German adjectives/articles
        "ein", "eine", "einen", "einem", "eines", "einer",
        "kein", "keine", "keinen", "keinem", "keines", "keiner",
        # German pronouns and possessives
        "sie", "ihr", "euch", "uns", "unser", "meinen", "seinen", "dein",
        # Medical/common German words
        "angst", "angespannt", "nervös", "besorg", "panik", "schmerz",
        "nebenwirkung", "behandlung", "therapie", "medikament", "krankheit",
        "arzt", "doktor", "patient", "symptom", "krankenhaus",
        "sie", "wir", "nicht", "nur", "auch", "noch", "mehr",
        # German suffixes that often indicate German
        "ung", "heit", "keit", "lich", "isch",
    }
    
    # English-specific patterns and words
    english_indicators = {
        # Common English words
        "the", "is", "and", "a", "of", "to", "for", "in", "with",
        # English question words
        "what", "how", "when", "where", "why", "which", "who",
        # Common English verbs
        "am", "are", "be", "been", "being", "have", "has", "do", "does",
        "will", "would", "could", "should", "may", "might", "must", "can",
        # Common English medical words
        "symptom", "treatment", "therapy", "side", "effect", "drug", "medicine",
        "disease", "doctor", "patient", "hospital", "pain", "worry", "fear",
        # English pronouns
        "you", "your", "he", "his", "she", "her", "they", "their",
        "i", "me", "my", "we", "us", "our",
        # Common English words
        "that", "this", "not", "only", "also", "more", "some",
    }
    
    # Count word occurrences
    german_score = sum(1 for word in german_indicators if word in text_lower)
    english_score = sum(1 for word in english_indicators if word in text_lower)
    
    # If one is clearly higher, use that
    if german_score > english_score:
        return "de"
    elif english_score > german_score:
        return "en"
    else:
        # Fallback: check for German umlauts and special characters
        if any(char in text for char in ["ä", "ö", "ü", "ß"]):
            return "de"
        # Default to English
        return "en"


def sentiment_analyzer(user_message):
    """Return empathy prefix when distress is detected (English or German)."""
    lowered = user_message.lower()
    language = detect_language(user_message)
    
    if any(keyword in lowered for keyword in DISTRESS_KEYWORDS):
        if language == "de":
            prefix = (
                "Es tut mir leid, dass Sie das durchmachen. "
                "Ich möchte sorgfältig und unterstützend antworten. "
            )
        else:
            prefix = (
                "I'm sorry you're going through this. I want to respond carefully and supportively. "
            )
        
        return {
            "rule": "sentiment_analyzer",
            "mandatory_prefix": prefix,
        }
    return None


def apply_rules(user_message, state=None, context=None):
    """
    Checks user_message against rules, optionally using state/context.
    Returns response or rule payload if matched, otherwise None.
    Supports both English and German.
    """
    language = detect_language(user_message)
    sentiment_rule = sentiment_analyzer(user_message)
    
    if sentiment_rule:
        return sentiment_rule

    # Greeting rules
    if str(state).lower() == "start":
        if language == "de":
            if any(greet in user_message.lower() for greet in ["hallo", "hallo!", "hi", "guten"]):
                return {
                    "rule": "greeting",
                    "direct_response": "Hallo! Wie kann ich Ihnen heute helfen?",
                }
        else:
            if any(greet in user_message.lower() for greet in ["hello", "hi", "hey"]):
                return {
                    "rule": "greeting",
                    "direct_response": "Hello! How can I help you today?",
                }
    
    # Farewell rules
    if language == "de":
        if user_message.lower() in ["auf wiedersehen", "tschüss", "bye"]:
            return {
                "rule": "farewell",
                "direct_response": "Auf Wiedersehen! Alles Gute für Sie.",
                "stop_chat": True,
            }
    else:
        if user_message.lower() in ["bye", "goodbye"]:
            return {
                "rule": "farewell",
                "direct_response": "Goodbye! Have a nice day.",
                "stop_chat": True,
            }
    
    return None
