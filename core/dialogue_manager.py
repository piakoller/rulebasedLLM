# dialogue_manager.py
"""
Dialogue State Manager for rule-based chatbot.
Manages conversation state and applies rules based on state and user input.
"""

class DialogueStateManager:
    """
    Finite-State Dialogue Manager for rule-based chatbot.
    Manages conversation state using a finite-state machine (FSM) approach.
    """
    def __init__(self):
        self.state = "START"  # Initial state
        self.context = {}
        # Define the FSM transition table: (current_state, input_type) -> next_state
        self.transitions = {
            ("START", "greet"): "GREETED",
            ("START", "bye"): "ENDED",
            ("GREETED", "bye"): "ENDED",
            ("GREETED", "question"): "ANSWERING",
            ("ANSWERING", "bye"): "ENDED",
            ("ANSWERING", "question"): "ANSWERING",
            ("ANSWERING", "greet"): "GREETED",
            # Add more transitions as needed
        }

    def reset(self):
        self.state = "START"
        self.context = {}

    def get_state(self):
        return self.state

    def classify_input(self, user_message, rule_response=None):
        """
        Classifies the user input into types for FSM transitions.
        Extend this for more sophisticated input classification.
        """
        msg = user_message.lower()
        if any(greet in msg for greet in ["hello", "hi", "hey"]):
            return "greet"
        if msg in ["bye", "goodbye"]:
            return "bye"
        if msg.endswith("?"):
            return "question"
        return "other"

    def update_state(self, user_message, rule_response=None):
        input_type = self.classify_input(user_message, rule_response)
        key = (self.state, input_type)
        if key in self.transitions:
            self.state = self.transitions[key]
        # else, remain in current state

    def handle_message(self, user_message, apply_rules_func):
        """
        Handles a user message, applies rules, updates state, and returns response.
        """
        rule_response = apply_rules_func(user_message, state=self.state, context=self.context)
        self.update_state(user_message, rule_response)
        return rule_response
