#!/usr/bin/env python3
"""
Baseline MedGemma runner for PSMA sample questions.

Produces concise, clinically-correct answers without any empathic phrasing
or additional background information. Intended to compare against the
empathic pipeline in `test_empathy_with_llm.py`.
"""

import sys
import json
import requests
from pathlib import Path

# Reuse sample question loader and config constants from the empathy test file
sys.path.insert(0, str(Path(__file__).parent))
from tests.test_empathy_with_llm import load_sample_questions, OLLAMA_MODEL, OLLAMA_URL, TIMEOUT


def call_ollama(messages: list[dict]) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")
    except Exception:
        return None


SYSTEM_PROMPT = """
You are a clinical assistant providing concise, clinically-correct answers
to patient questions about cancer treatment.

Instructions:
- Provide a direct, factual answer to the user's question and only the
  information requested.
- Do not provide additional background, extra recommendations, or any
  empathic language or emotional support statements.
- If you are uncertain about a factual detail, state that you don't know
  and recommend the patient consult their treating clinician.
- Respond in the patient's language (German or English) and be as brief
  and precise as possible.
"""


def test_baseline_question(question: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    llm_response = call_ollama(messages)

    result = {
        "question": question,
        "llm_response": llm_response,
        "success": llm_response is not None,
    }

    # Print concise output for quick inspection
    print("\n" + "=" * 70)
    print(question)
    print("-" * 70)
    if llm_response is None:
        print("(No response from Ollama)")
    else:
        print(llm_response)

    return result


def main():
    # Request all 11 sample questions for a full baseline run
    questions = load_sample_questions(11)
    results = []

    for q in questions:
        res = test_baseline_question(q["question"])
        results.append(res)

    out_file = Path(__file__).parent / "LLM_TEST_RESULTS_BASELINE.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved baseline results to: {out_file}")


if __name__ == "__main__":
    main()
