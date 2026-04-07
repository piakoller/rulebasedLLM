"""Rule-based logic for the hybrid empathy layer."""


DISTRESS_KEYWORDS = {
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
}


def sentiment_analyzer(user_message):
    """Return a mandatory empathy prefix when distress is detected."""
    lowered = user_message.lower()
    if any(keyword in lowered for keyword in DISTRESS_KEYWORDS):
        return {
            "rule": "sentiment_analyzer",
            "mandatory_prefix": (
                "I’m sorry you’re going through this. I want to respond carefully and supportively. "
            ),
        }
    return None

def apply_rules(user_message, state=None, context=None):
    """
    Checks user_message against a set of rules, optionally using state/context.
    Returns a response string or rule payload if a rule matches, otherwise None.
    """
    sentiment_rule = sentiment_analyzer(user_message)
    if sentiment_rule:
        return sentiment_rule

    # Example: Greet only if not already greeted
    if str(state).lower() == "start" and any(greet in user_message.lower() for greet in ["hello", "hi", "hey"]):
        return {
            "rule": "greeting",
            "direct_response": "Hello! How can I help you today?",
        }
    # Example: End conversation
    if user_message.lower() in ["bye", "goodbye"]:
        return {
            "rule": "farewell",
            "direct_response": "Goodbye! Have a nice day.",
            "stop_chat": True,
        }
    # Add more rules below, using state/context as needed
    return None  # No rule matched
