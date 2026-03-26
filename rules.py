# rules.py
# Define your rule-based logic here as functions or classes

def apply_rules(user_message, state=None, context=None):
    """
    Checks user_message against a set of rules, optionally using state/context.
    Returns a response string if a rule matches, otherwise None.
    """
    # Example: Greet only if not already greeted
    if state == "start" and any(greet in user_message.lower() for greet in ["hello", "hi", "hey"]):
        return "Hello! How can I help you today?"
    # Example: End conversation
    if user_message.lower() in ["bye", "goodbye"]:
        return "Goodbye! Have a nice day."
    # Add more rules below, using state/context as needed
    return None  # No rule matched
