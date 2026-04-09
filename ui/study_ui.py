#!/usr/bin/env python3
"""
Minimalist Streamlit UI for DPO (Direct Preference Optimization) data collection.

This app allows researchers to gather preference data between original and revised
LLM responses for clinical question answering.
"""

import json
import random
from pathlib import Path
from datetime import datetime

import streamlit as st
from agent_engine import AgentEngine

# Configuration
STUDY_DATA_PATH = Path("study_data.jsonl")
DEFAULT_MODEL = "gemma3:27b"


@st.cache_resource
def load_engine():
    """Initialize and cache the AgentEngine instance."""
    return AgentEngine(model=DEFAULT_MODEL)


def log_preference(
    question: str,
    answer_a: str,
    answer_b: str,
    original_draft: str,
    user_preference: str,
) -> None:
    """
    Log the preference data to study_data.jsonl.
    
    Args:
        question: The clinical question
        answer_a: Content of Answer A
        answer_b: Content of Answer B
        original_draft: Which answer was the original draft ("A" or "B")
        user_preference: Which answer was preferred ("A" or "B")
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer_a": answer_a,
        "answer_b": answer_b,
        "original_draft": original_draft,
        "user_preference": user_preference,
        "preference_matches_original": original_draft == user_preference,
    }
    
    with open(STUDY_DATA_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def reset_session_state() -> None:
    """Reset the session state after a preference is logged."""
    st.session_state.question = ""
    st.session_state.draft_comparison = None
    st.session_state.answer_assignments = None


def main():
    """Main Streamlit app for DPO data collection."""
    st.set_page_config(
        page_title="Clinical Response Study",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    # Hide the sidebar
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Title and instructions
    st.title("Clinical Question Response Study")
    st.markdown(
        """
        This study compares different versions of responses to clinical questions.
        Please read both responses carefully and indicate your preference.
        """
    )
    
    # Initialize session state
    if "draft_comparison" not in st.session_state:
        st.session_state.draft_comparison = None
    if "answer_assignments" not in st.session_state:
        st.session_state.answer_assignments = None
    if "question" not in st.session_state:
        st.session_state.question = ""
    
    # Load engine
    engine = load_engine()
    
    # Question input section
    st.markdown("---")
    st.subheader("Step 1: Enter a Clinical Question")
    
    question = st.text_area(
        "Enter your clinical question:",
        value=st.session_state.question,
        height=100,
        placeholder="Example: What are the common side effects of targeted therapy?",
        key="question_input",
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        generate_button = st.button(
            "Generate Answers",
            type="primary",
            use_container_width=True,
        )
    
    if generate_button and question.strip():
        with st.spinner("Generating responses..."):
            try:
                st.session_state.draft_comparison = engine.handle_message_for_study(
                    question.strip()
                )
                
                # Randomly assign original/revised to A/B
                if random.random() < 0.5:
                    st.session_state.answer_assignments = {
                        "A": "original",
                        "B": "final",
                    }
                else:
                    st.session_state.answer_assignments = {
                        "A": "final",
                        "B": "original",
                    }
                
                st.session_state.question = question.strip()
                st.rerun()
            except Exception as e:
                st.error(f"Error generating responses: {str(e)}")
    elif generate_button:
        st.warning("Please enter a question first.")
    
    # Display comparison if available
    if st.session_state.draft_comparison and st.session_state.answer_assignments:
        st.markdown("---")
        st.subheader("Step 2: Compare Responses")
        
        comparison = st.session_state.draft_comparison
        assignments = st.session_state.answer_assignments
        
        # Display question
        st.markdown(f"**Question:** {st.session_state.question}")
        
        # Get the responses
        original_response = comparison.original_draft.agent_response
        final_response = comparison.final_response.agent_response
        
        # Assign to A/B based on random assignment
        answer_a = (
            original_response
            if assignments["A"] == "original"
            else final_response
        )
        answer_b = (
            original_response
            if assignments["B"] == "original"
            else final_response
        )
        
        original_is_a = assignments["A"] == "original"
        
        # Display in two columns
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("### Answer A")
            st.markdown(f"{answer_a}")
            
            if st.button(
                "👍 Prefer Answer A",
                type="primary",
                use_container_width=True,
                key="prefer_a",
            ):
                log_preference(
                    question=st.session_state.question,
                    answer_a=answer_a,
                    answer_b=answer_b,
                    original_draft="A" if original_is_a else "B",
                    user_preference="A",
                )
                st.success("✓ Preference recorded. Loading next question...")
                reset_session_state()
                st.rerun()
        
        with col_b:
            st.markdown("### Answer B")
            st.markdown(f"{answer_b}")
            
            if st.button(
                "👍 Prefer Answer B",
                type="primary",
                use_container_width=True,
                key="prefer_b",
            ):
                log_preference(
                    question=st.session_state.question,
                    answer_a=answer_a,
                    answer_b=answer_b,
                    original_draft="A" if original_is_a else "B",
                    user_preference="B",
                )
                st.success("✓ Preference recorded. Loading next question...")
                reset_session_state()
                st.rerun()
        
        # Show study progress
        st.markdown("---")
        if STUDY_DATA_PATH.exists():
            num_responses = sum(1 for _ in open(STUDY_DATA_PATH))
            st.info(f"📊 Responses recorded so far: {num_responses}")


if __name__ == "__main__":
    main()
