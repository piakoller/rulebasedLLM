"""Agentic orchestration for the clinical GraphRAG chatbot.

This module implements a lightweight Thought-Action-Observation loop around
the existing frame prompt, graph-based fact verification, and static patient
context lookup.
"""

from __future__ import annotations

import ast
import csv
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import requests
from pydantic import BaseModel, Field, ValidationError

import graph_rag
import ontology_rag
from ontology_tool import verify_clinical_relationship, UMLSVerificationResult
from rules import DISTRESS_KEYWORDS, apply_rules, sentiment_analyzer, detect_language
from empathy_framing import (
    create_empathic_response_to_umls_result,
    classify_emotional_state,
    get_nurse_instruction,
)

BASE_DIR = Path(__file__).resolve().parent
FRAME_PROMPT_PATH = BASE_DIR / "frame_prompt.txt"
STATIC_PATIENT_DATA_PATH = BASE_DIR / "context" / "static_patient_records.json"
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "hf.co/unsloth/medgemma-1.5-4b-it-GGUF:BF16")
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
DEFAULT_DOCUMENT_ROOT = BASE_DIR / "context"
MAX_REASONING_STEPS = 2

FORBIDDEN_TOPICS = {
    "dose",
    "dosing",
    "dosimetry",
    "numerical dosimetry",
    "prognosis",
    "survival rate",
    "life expectancy",
    "treatment planning",
}

SUPPORTIVE_MARKERS = {
    "i understand",
    "i’m sorry",
    "i'm sorry",
    "that sounds difficult",
    "you are not alone",
    "we can take this step by step",
    "i want to help",
    "i will keep this simple",
}


class StaticPatientRecord(BaseModel):
    patient_id: str
    therapy: str = ""
    scheduled_date: str = ""
    perception: str = ""
    concerns: list[str] = Field(default_factory=list)
    notes: str = ""


class StaticPatientContextResult(BaseModel):
    query: str
    matched: bool
    records: list[StaticPatientRecord] = Field(default_factory=list)
    summary: str = ""


class EmpathyComplianceResult(BaseModel):
    compliant: bool
    score: float
    issues: list[str] = Field(default_factory=list)
    recommended_prefix: str = ""


class FrameResponse(BaseModel):
    active_frame: str
    filled_slots: dict[str, str] = Field(default_factory=dict)
    agent_response: str
    next_frame: str


class ToolCall(BaseModel):
    """Represents a single tool call extracted from LLM output."""
    function_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    raw_call: str = ""


class ToolResult(BaseModel):
    """Represents the result of executing a tool call."""
    tool_name: str
    success: bool
    result: Any = None
    error: str = ""


class DraftComparison(BaseModel):
    """Container for comparing original and final drafts (for DPO studies)."""
    original_draft: FrameResponse
    final_response: FrameResponse
    revision_occurred: bool
    revision_reason: str = ""


@dataclass
class FrameSpec:
    goal: str
    required_slots: list[str]
    optional_slots: list[str]
    forbidden: list[str]
    next_frames: list[str]


def load_frame_prompt(prompt_path: Path = FRAME_PROMPT_PATH) -> str:
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return "You are a helpful clinical assistant."


def parse_tool_call(line: str) -> Optional[ToolCall]:
    """
    Parse a single line that may contain a tool call in the format:
    ACTION: function_name(arg1="value1", arg2="value2", ...)
    
    Returns a ToolCall object if a valid tool call is found, None otherwise.
    """
    line = line.strip()
    if not line.startswith("ACTION:"):
        return None
    
    action_part = line[7:].strip()  # Remove "ACTION:"
    
    # Match pattern: function_name(args)
    match = re.match(r"(\w+)\s*\((.*)\)", action_part)
    if not match:
        return None
    
    function_name = match.group(1)
    args_str = match.group(2)
    
    arguments: dict[str, Any] = {}
    if args_str.strip():
        try:
            # Parse arguments using ast.literal_eval for safety
            # Convert the argument string to a dict-like format
            args_pairs = []
            current_key = None
            current_val = []
            
            # Simple parser for key="value" pairs
            for part in re.findall(r'(\w+)\s*=\s*(["\'][^"\']*["\']|[^,]+)(?:,|$)', args_str):
                key = part[0].strip()
                val = part[1].strip()
                
                # Remove quotes if present
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                
                arguments[key] = val
        except Exception:
            # If parsing fails, return None
            return None
    
    return ToolCall(
        function_name=function_name,
        arguments=arguments,
        raw_call=line
    )


def _parse_list_value(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_frame_specs(prompt_text: str) -> dict[str, FrameSpec]:
    specs: dict[str, FrameSpec] = {}
    current_frame: Optional[str] = None
    current_field: Optional[str] = None

    for raw_line in prompt_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("FRAME:"):
            current_frame = line.split(":", 1)[1].strip()
            specs[current_frame] = FrameSpec(goal="", required_slots=[], optional_slots=[], forbidden=[], next_frames=[])
            current_field = None
            continue

        if current_frame is None:
            continue

        if line.startswith("goal:"):
            specs[current_frame].goal = line.split(":", 1)[1].strip()
            current_field = None
            continue

        if line.startswith("required_slots:"):
            current_field = "required_slots"
            continue
        if line.startswith("optional_slots:"):
            value = line.split(":", 1)[1].strip()
            specs[current_frame].optional_slots = _parse_list_value(value)
            current_field = None
            continue
        if line.startswith("forbidden:"):
            value = line.split(":", 1)[1].strip()
            specs[current_frame].forbidden = _parse_list_value(value)
            current_field = None
            continue
        if line.startswith("next_frames:"):
            value = line.split(":", 1)[1].strip()
            specs[current_frame].next_frames = _parse_list_value(value)
            current_field = None
            continue

        if current_field == "required_slots" and line.startswith("-"):
            specs[current_frame].required_slots.append(line.split("-", 1)[1].strip())

    return specs


def _load_json_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        records = payload.get("records", [])
        return [item for item in records if isinstance(item, dict)]
    return []


def _load_csv_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle)]


def load_static_patient_records(data_path: Path = STATIC_PATIENT_DATA_PATH) -> list[StaticPatientRecord]:
    if not data_path.exists():
        return []

    raw_records: list[dict[str, Any]] = []
    if data_path.suffix.lower() == ".json":
        raw_records = _load_json_records(data_path)
    elif data_path.suffix.lower() == ".csv":
        raw_records = _load_csv_records(data_path)

    records: list[StaticPatientRecord] = []
    for raw in raw_records:
        try:
            records.append(StaticPatientRecord.model_validate(raw))
        except ValidationError:
            continue
    return records


def get_static_patient_context(query: str, data_path: Path = STATIC_PATIENT_DATA_PATH) -> StaticPatientContextResult:
    """Return de-identified static patient context from a local file."""
    records = load_static_patient_records(data_path)
    lowered_query = query.lower()
    scored: list[tuple[int, StaticPatientRecord]] = []

    for record in records:
        score = 0
        record_text = " ".join(
            [
                record.patient_id,
                record.therapy,
                record.scheduled_date,
                record.perception,
                record.notes,
                " ".join(record.concerns),
            ]
        ).lower()

        if record.patient_id.lower() in lowered_query:
            score += 5
        if record.therapy and record.therapy.lower() in lowered_query:
            score += 3
        if record.scheduled_date and record.scheduled_date.lower() in lowered_query:
            score += 4
        for concern in record.concerns:
            if concern.lower() in lowered_query:
                score += 2
        for token in lowered_query.split():
            if token and token in record_text:
                score += 1

        if score > 0:
            scored.append((score, record))

    scored.sort(key=lambda item: item[0], reverse=True)
    top_records = [item[1] for item in scored[:2]]
    matched = bool(top_records)

    if not matched:
        return StaticPatientContextResult(
            query=query,
            matched=False,
            records=[],
            summary="No matching de-identified patient context was found in the local file.",
        )

    summary_lines = []
    for record in top_records:
        summary_lines.append(
            f"{record.patient_id}: therapy={record.therapy or 'n/a'}, scheduled_date={record.scheduled_date or 'n/a'}"
        )
        if record.perception:
            summary_lines.append(f"Perception: {record.perception}")
        if record.concerns:
            summary_lines.append(f"Concerns: {', '.join(record.concerns)}")
    return StaticPatientContextResult(
        query=query,
        matched=True,
        records=top_records,
        summary="; ".join(summary_lines),
    )


def _sentence_count(text: str) -> int:
    sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    return len(sentences)


def check_empathy_compliance(draft_response: str, user_message: str = "") -> EmpathyComplianceResult:
    """Evaluate whether the draft response sounds supportive and patient-centered."""
    lowered = draft_response.lower()
    issues: list[str] = []
    score = 1.0

    if any(keyword in lowered for keyword in ["dose", "dosing", "prognosis", "survival", "guarantee"]):
        issues.append("Contains prohibited clinical detail.")
        score -= 0.6

    if any(keyword in user_message.lower() for keyword in DISTRESS_KEYWORDS):
        if not any(marker in lowered for marker in SUPPORTIVE_MARKERS):
            issues.append("Missing explicit supportive or validating language for distress.")
            score -= 0.3

    if _sentence_count(draft_response) > 2 and any(term in lowered for term in ["therapy", "treatment", "radiation"]):
        issues.append("Contains more than two sentences of medical facts in a clinical explanation.")
        score -= 0.2

    if not any(marker in lowered for marker in SUPPORTIVE_MARKERS):
        issues.append("Could be warmer and more patient-centered.")
        score -= 0.1

    score = max(0.0, min(1.0, score))
    recommended_prefix = ""
    if any(keyword in user_message.lower() for keyword in DISTRESS_KEYWORDS):
        recommended_prefix = "I’m sorry you’re going through this. I want to respond carefully and supportively. "

    return EmpathyComplianceResult(
        compliant=score >= 0.6 and not any("prohibited" in issue.lower() for issue in issues),
        score=score,
        issues=issues,
        recommended_prefix=recommended_prefix,
    )


class AgentEngine:
    """Agentic orchestrator that performs a Thought-Action-Observation loop."""

    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        document_roots: Optional[list[Path]] = None,
        patient_data_path: Path = STATIC_PATIENT_DATA_PATH,
        prompt_path: Path = FRAME_PROMPT_PATH,
        max_reasoning_steps: int = MAX_REASONING_STEPS,
    ) -> None:
        self.model = model
        self.ollama_url = ollama_url
        self.patient_data_path = patient_data_path
        self.max_reasoning_steps = max_reasoning_steps
        self.system_prompt = load_frame_prompt(prompt_path)
        self.frame_specs = parse_frame_specs(self.system_prompt)
        self.current_frame = "greeting"
        self.frame_memory: dict[str, dict[str, str]] = {}
        self.conversation_history: list[dict[str, str]] = [{"role": "system", "content": self.system_prompt}]
        self.document_roots = document_roots or [DEFAULT_DOCUMENT_ROOT]
        self.knowledge_graph = graph_rag.get_knowledge_graph(self.document_roots)

    def _execute_tool(self, tool_call: ToolCall, user_message: str = "") -> ToolResult:
        """Execute a tool call and return the result."""
        try:
            if tool_call.function_name == "get_patient_context":
                # Extract patient_id or use query from arguments
                patient_id = tool_call.arguments.get("patient_id") or tool_call.arguments.get("query", "")
                result = get_static_patient_context(patient_id, data_path=self.patient_data_path)
                return ToolResult(
                    tool_name=tool_call.function_name,
                    success=True,
                    result={
                        "matched": result.matched,
                        "summary": result.summary,
                        "records": [r.model_dump() for r in result.records]
                    }
                )
            
            elif tool_call.function_name == "search_knowledge_graph":
                # Search the knowledge graph for facts
                query = tool_call.arguments.get("query", "")
                if not query:
                    return ToolResult(
                        tool_name=tool_call.function_name,
                        success=False,
                        error="Missing 'query' argument"
                    )
                result = graph_rag.get_knowledge_graph_fact(query, graph=self.knowledge_graph)
                return ToolResult(
                    tool_name=tool_call.function_name,
                    success=True,
                    result={
                        "answer": result.answer,
                        "verified": result.verified,
                        "entities": result.entities
                    }
                )
            
            elif tool_call.function_name == "verify_fact":
                # Verify if a statement is supported by the knowledge graph
                statement = tool_call.arguments.get("statement", "")
                if not statement:
                    return ToolResult(
                        tool_name=tool_call.function_name,
                        success=False,
                        error="Missing 'statement' argument"
                    )
                verification = graph_rag.verify_llm_response(statement, entities=[], graph=self.knowledge_graph)
                return ToolResult(
                    tool_name=tool_call.function_name,
                    success=True,
                    result={
                        "verified": verification.get("verified", False),
                        "flagged_relations": verification.get("flagged_relations", [])
                    }
                )
            
            elif tool_call.function_name == "query_medical_ontology":
                # Query the medical ontology for deterministic entity mapping and relationships
                terms = tool_call.arguments.get("terms", "")
                if not terms:
                    return ToolResult(
                        tool_name=tool_call.function_name,
                        success=False,
                        error="Missing 'terms' argument"
                    )
                result = ontology_rag.query_medical_ontology(terms)
                return ToolResult(
                    tool_name=tool_call.function_name,
                    success=result.success,
                    result={
                        "mapped_entities": result.mapped_entities,
                        "relationships": result.relationships,
                        "success": result.success
                    } if result.success else None,
                    error=result.error if not result.success else ""
                )
            
            elif tool_call.function_name == "query_umls_ontology":
                # Query the UMLS ontology for verified clinical relationships
                term = tool_call.arguments.get("term", "")
                if not term:
                    return ToolResult(
                        tool_name=tool_call.function_name,
                        success=False,
                        error="Missing 'term' argument"
                    )
                result = verify_clinical_relationship(term)
                
                # Check if user is distressed
                user_distressed = any(kw in user_message.lower() for kw in DISTRESS_KEYWORDS) if user_message else False
                
                # Create empathic response if available
                tool_result = {
                    "term": result.term,
                    "cui": result.cui,
                    "found": result.found,
                    "relationships": result.relationships,
                    "summary": result.summary
                }
                
                # Add empathic framing if we have user message
                if user_message and result.found:
                    empathic_response = create_empathic_response_to_umls_result(
                        tool_result,
                        user_message,
                        user_distressed
                    )
                    tool_result["empathic_framing"] = empathic_response
                
                return ToolResult(
                    tool_name=tool_call.function_name,
                    success=result.found,
                    result=tool_result,
                    error=result.error if not result.found else ""
                )
            
            else:
                return ToolResult(
                    tool_name=tool_call.function_name,
                    success=False,
                    error=f"Unknown tool: {tool_call.function_name}"
                )
        
        except Exception as e:
            return ToolResult(
                tool_name=tool_call.function_name,
                success=False,
                error=str(e)
            )

    def _extract_tool_calls(self, text: str) -> list[ToolCall]:
        """Extract all ACTION: lines from text and parse them as tool calls."""
        tool_calls: list[ToolCall] = []
        for line in text.split("\n"):
            tool_call = parse_tool_call(line)
            if tool_call:
                tool_calls.append(tool_call)
        return tool_calls

    def _call_ollama(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
        }
        response = requests.post(self.ollama_url, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    def _analyze_input(self, user_message: str) -> dict[str, Any]:
        lowered = user_message.lower()
        emotion_hit = next((keyword for keyword in DISTRESS_KEYWORDS if keyword in lowered), "")
        forbidden_hit = next((topic for topic in FORBIDDEN_TOPICS if topic in lowered), "")
        
        # Classify emotional state using NURSE protocol
        emotional_state = classify_emotional_state(user_message)
        
        if any(marker in lowered for marker in ["bye", "goodbye", "quit", "exit"]):
            intent = "farewell"
        elif "?" in user_message or lowered.startswith(("what", "how", "why", "when", "is ", "are ")):
            intent = "question"
        elif emotion_hit:
            intent = "emotion"
        else:
            intent = "conversation"
        return {
            "intent": intent,
            "emotion_detected": emotion_hit,
            "emotional_state": emotional_state,
            "forbidden_topic": forbidden_hit,
        }

    def _select_next_frame(self, analysis: dict[str, Any], patient_context: StaticPatientContextResult, graph_fact: graph_rag.KnowledgeGraphFactResult) -> str:
        if self.current_frame == "greeting":
            return "emotion_check"
        if self.current_frame == "emotion_check":
            if analysis["forbidden_topic"]:
                return "safety_instructions"
            if graph_fact.verified or patient_context.matched:
                return "therapy_explanation"
            return "emotion_check"
        if self.current_frame == "therapy_explanation":
            if any(topic in analysis["forbidden_topic"] for topic in ["dose", "dosimetry", "numerical dosimetry"]):
                return "safety_instructions"
            return "safety_instructions"
        if self.current_frame == "safety_instructions":
            return "dosimetry_explanation" if "dosimetry" in analysis["intent"] else "closing"
        if self.current_frame == "dosimetry_explanation":
            return "closing"
        return self.current_frame

    def _build_observation_summary(
        self,
        user_message: str,
        patient_context: StaticPatientContextResult,
        graph_fact: graph_rag.KnowledgeGraphFactResult,
        empathy: EmpathyComplianceResult,
        analysis: dict[str, Any],
    ) -> str:
        return "\n".join(
            [
                f"User message: {user_message}",
                f"Intent: {analysis['intent']}",
                f"Emotional state: {analysis.get('emotional_state', 'neutral')}",
                f"Emotion detected: {analysis['emotion_detected'] or 'none'}",
                f"Forbidden topic: {analysis['forbidden_topic'] or 'none'}",
                f"Patient context: {patient_context.summary or 'none'}",
                f"Graph fact: {graph_fact.answer or 'none'}",
                f"Graph verified: {graph_fact.verified}",
                f"Empathy compliance score: {empathy.score:.2f}",
                f"Empathy issues: {', '.join(empathy.issues) if empathy.issues else 'none'}",
            ]
        )

    def _build_prompt(self, user_message: str, observation_summary: str, emotional_state: str = "neutral", revised: bool = False) -> list[dict[str, str]]:
        spec = self.frame_specs.get(self.current_frame)
        required_slots = ", ".join(spec.required_slots) if spec else ""
        optional_slots = ", ".join(spec.optional_slots) if spec else ""
        allowed_next = ", ".join(spec.next_frames) if spec else ""
        goal = spec.goal if spec else ""
        filled_slots = self.frame_memory.get(self.current_frame, {})
        missing_slots = []
        if spec:
            missing_slots = [slot for slot in spec.required_slots if slot not in filled_slots]

        # Get emotional context to inform LLM (not prescriptive rules)
        emotional_context = get_nurse_instruction(emotional_state)

        system_message = (
            f"{self.system_prompt}\n\n"
            f"Current active frame: {self.current_frame}\n"
            f"Frame goal: {goal}\n"
            f"Required slots: {required_slots}\n"
            f"Optional slots: {optional_slots}\n"
            f"Allowed next frames: {allowed_next}\n"
            f"Already filled slots: {json.dumps(filled_slots, ensure_ascii=False)}\n"
            f"Missing slots: {', '.join(missing_slots) if missing_slots else 'none'}\n\n"
            "Patient's Emotional State:\n"
            f"{emotional_context}\n\n"
            "Behavioral constraints:\n"
            "- Ask before telling when facts are not yet needed or the patient is distressed.\n"
            "- Validate emotion before giving technical explanations.\n"
            "- Never mention dosing, prognosis, or numerical dosimetry.\n"
            "- In therapy_explanation, use at most two sentences of medical facts before checking understanding.\n"
            "- CRITICAL: If a medical relationship is not explicitly verified by the query_umls_ontology or query_medical_ontology tool, you MUST state that you cannot confirm the clinical relationship.\n"
            "- LANGUAGE: Always respond to the user in the language they used (German, English, etc.), even though your tool calls and observations are in English.\n"
            "- Output valid JSON only and follow this schema exactly:\n"
            '{"active_frame":"...","filled_slots":{...},"agent_response":"...","next_frame":"..."}\n\n'
            "Available Tools (optional):\n"
            "You may call tools by outputting lines like: ACTION: function_name(arg1=\"value1\", arg2=\"value2\")\n"
            "Available tools:\n"
            "- ACTION: get_patient_context(patient_id=\"Patient_ID\") - Retrieve static patient context from the local database\n"
            "- ACTION: search_knowledge_graph(query=\"your_query\") - Search the knowledge graph for clinical facts\n"
            "- ACTION: verify_fact(statement=\"your_statement\") - Verify if a statement is supported by the knowledge graph\n"
            "- ACTION: query_umls_ontology(term=\"english_medical_term\") - You MUST translate any German or Swiss-German medical terms into standard English before calling this tool. Use this to retrieve medically verified relationships for a specific drug, therapy, or side effect from the NIH UMLS database. Returns CUI and verified relationships.\n"
            "- ACTION: query_medical_ontology(terms=\"term1, term2\") - Deterministically verify medical relationships using the static medical ontology. Use this to confirm any clinical relationships before making statements about them.\n"
            "Each tool call will be executed and the result will be added to observations for the next iteration.\n"
            "Only use tools when you need additional information to answer the user's question accurately.\n"
            "When discussing medical relationships or treatments, prioritize using query_umls_ontology to verify facts from the official medical ontology.\n"
        )
        if revised:
            system_message += "\nThe previous draft did not comply with empathy or safety requirements. Revise it carefully."

        user_message_block = (
            f"User message: {user_message}\n\n"
            f"Observations:\n{observation_summary}\n\n"
            "Draft the final frame response now."
        )
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message_block},
        ]

    def _fallback_response(
        self,
        user_message: str,
        analysis: dict[str, Any],
        patient_context: StaticPatientContextResult,
        graph_fact: graph_rag.KnowledgeGraphFactResult,
    ) -> FrameResponse:
        # Note: Empathy is now handled via system_message injection in _build_prompt(),
        # not through hardcoded prefixes. This keeps fallback responses clear and lets
        # the LLM integrate empathy naturally when needed.
        
        if analysis["forbidden_topic"]:
            response_text = (
                f"I can keep this at a high level, but I should not provide {analysis['forbidden_topic']} details. "
                "If you would like, I can explain the general purpose of the treatment or what patients usually experience."
            ).strip()
            next_frame = "safety_instructions"
        elif self.current_frame == "emotion_check":
            response_text = (
                "It sounds like this may feel difficult. Before I explain more, what have you been told so far about the treatment?"
            ).strip()
            next_frame = "emotion_check"
        else:
            response_text = (
                "I want to stay careful and only share what I can confirm. "
                "If you want, I can give a simple high-level explanation or focus on your immediate concerns."
            ).strip()
            next_frame = self._select_next_frame(analysis, patient_context, graph_fact)

        filled_slots: dict[str, str] = {}
        if self.current_frame == "greeting":
            filled_slots["greeting_message"] = response_text
        elif self.current_frame == "emotion_check":
            filled_slots["emotion_detected"] = analysis["emotion_detected"] or "not explicitly stated"
            filled_slots["patient_perception"] = patient_context.records[0].perception if patient_context.records else "not yet clarified"
            filled_slots["validation_statement"] = "Your feelings make sense, and I want to help carefully."
        elif self.current_frame == "therapy_explanation":
            filled_slots["purpose_of_therapy"] = "high-level therapy purpose based on the available context"
            filled_slots["high_level_mechanism"] = "a simple explanation of how the therapy works"
            filled_slots["what_to_expect"] = "what patients usually experience at a general level"
        elif self.current_frame == "safety_instructions":
            filled_slots["general_safety_principles"] = "general guideline-aligned safety information"
            filled_slots["reassurance_statement"] = "I will keep this focused on safe, high-level information."
        elif self.current_frame == "dosimetry_explanation":
            filled_slots["purpose_of_dosimetry"] = "to personalize treatment in a general sense"
            filled_slots["why_multiple_timepoints"] = "to observe how the body changes over time"
            filled_slots["personalization_concept"] = "to support individualized care"
        else:
            filled_slots["closing_message"] = response_text

        return FrameResponse(
            active_frame=self.current_frame,
            filled_slots=filled_slots,
            agent_response=response_text,
            next_frame=next_frame,
        )

    def _parse_frame_response(self, raw_content: str) -> FrameResponse:
        try:
            payload = json.loads(raw_content)
            return FrameResponse.model_validate(payload)
        except Exception:
            return FrameResponse(
                active_frame=self.current_frame,
                filled_slots={},
                agent_response=raw_content.strip() or "I want to keep this safe and simple.",
                next_frame=self.current_frame,
            )

    def handle_message(self, user_message: str) -> FrameResponse:
        """Process one user turn through the agentic reasoning loop."""
        self.conversation_history.append({"role": "user", "content": user_message})
        analysis = self._analyze_input(user_message)

        rule_state = "start" if self.current_frame == "greeting" else self.current_frame
        rule_result = apply_rules(user_message, state=rule_state, context=self.frame_memory)
        direct_response = ""
        if isinstance(rule_result, dict):
            direct_response = rule_result.get("direct_response", "")
            if rule_result.get("stop_chat"):
                response_text = direct_response.strip()
                output = FrameResponse(
                    active_frame="closing",
                    filled_slots={"closing_message": response_text},
                    agent_response=response_text,
                    next_frame="closing",
                )
                self.conversation_history.append({"role": "assistant", "content": output.model_dump_json()})
                self.current_frame = "closing"
                return output

        patient_context = get_static_patient_context(user_message, data_path=self.patient_data_path)
        graph_fact = graph_rag.get_knowledge_graph_fact(user_message, graph=self.knowledge_graph)
        # Empathy compliance check is now based on NURSE instructions in the prompt
        empathy = check_empathy_compliance(direct_response, user_message=user_message)

        observation_summary = self._build_observation_summary(user_message, patient_context, graph_fact, empathy, analysis)
        
        # Get emotional state from analysis
        emotional_state = analysis.get("emotional_state", "neutral")

        draft_response: Optional[FrameResponse] = None
        for attempt in range(self.max_reasoning_steps):
            messages = self._build_prompt(user_message, observation_summary, emotional_state=emotional_state, revised=attempt > 0)
            raw_content = self._call_ollama(messages)
            
            # Extract and execute tool calls from the response
            tool_calls = self._extract_tool_calls(raw_content)
            tool_results: list[ToolResult] = []
            if tool_calls:
                for tool_call in tool_calls:
                    tool_result = self._execute_tool(tool_call, user_message=user_message)
                    tool_results.append(tool_result)
                
                # Add tool results to observation summary for the next reasoning step
                if tool_results and attempt < self.max_reasoning_steps - 1:
                    observation_summary += "\n\nTool Execution Results:\n"
                    for tool_result in tool_results:
                        observation_summary += f"- {tool_result.tool_name}: {'Success' if tool_result.success else 'Error'}\n"
                        if tool_result.success and tool_result.result:
                            result_str = json.dumps(tool_result.result, indent=2)
                            observation_summary += f"  Result: {result_str}\n"
                        elif not tool_result.success:
                            observation_summary += f"  Error: {tool_result.error}\n"
            
            candidate = self._parse_frame_response(raw_content)

            if direct_response and candidate.agent_response:
                candidate.agent_response = f"{direct_response} {candidate.agent_response}".strip()

            compliance = check_empathy_compliance(candidate.agent_response, user_message=user_message)
            graph_verification = graph_rag.verify_llm_response(candidate.agent_response, graph_fact.entities, graph=self.knowledge_graph)

            if analysis["forbidden_topic"]:
                candidate = self._fallback_response(user_message, analysis, patient_context, graph_fact)
                draft_response = candidate
                break

            if compliance.compliant and graph_verification.get("verified", True):
                draft_response = candidate
                break

            observation_summary += (
                "\n\nRevision notes:\n"
                f"- Empathy compliance issues: {', '.join(compliance.issues) if compliance.issues else 'none'}\n"
                f"- Graph verification issues: {', '.join(graph_verification.get('flagged_relations', [])) if graph_verification.get('flagged_relations') else 'none'}\n"
            )

        if draft_response is None:
            draft_response = self._fallback_response(user_message, analysis, patient_context, graph_fact)

        required_slots = self.frame_specs.get(self.current_frame).required_slots if self.current_frame in self.frame_specs else []
        current_memory = self.frame_memory.setdefault(self.current_frame, {})
        current_memory.update(draft_response.filled_slots)

        if self.current_frame == "emotion_check" and patient_context.records:
            current_memory.setdefault("patient_perception", patient_context.records[0].perception or "not yet clarified")

        missing_required = [slot for slot in required_slots if slot not in current_memory]
        if missing_required:
            draft_response.next_frame = self.current_frame
        else:
            allowed = self.frame_specs.get(self.current_frame).next_frames if self.current_frame in self.frame_specs else []
            if allowed and draft_response.next_frame not in allowed:
                draft_response.next_frame = allowed[0]

        self.current_frame = draft_response.next_frame or self.current_frame
        self.conversation_history.append({"role": "assistant", "content": draft_response.model_dump_json()})
        return draft_response

    def handle_message_for_study(self, user_message: str) -> DraftComparison:
        """
        Process a user message and return both the original draft and final response
        for DPO (Direct Preference Optimization) study comparison.
        
        Returns DraftComparison with original_draft (first iteration) and final_response.
        """
        self.conversation_history.append({"role": "user", "content": user_message})
        analysis = self._analyze_input(user_message)

        rule_state = "start" if self.current_frame == "greeting" else self.current_frame
        rule_result = apply_rules(user_message, state=rule_state, context=self.frame_memory)
        direct_response = ""
        mandatory_prefix = ""
        if isinstance(rule_result, dict):
            direct_response = rule_result.get("direct_response", "")
            mandatory_prefix = rule_result.get("mandatory_prefix", "")
            if rule_result.get("stop_chat"):
                response_text = f"{mandatory_prefix}{direct_response}".strip()
                output = FrameResponse(
                    active_frame="closing",
                    filled_slots={"closing_message": response_text},
                    agent_response=response_text,
                    next_frame="closing",
                )
                self.conversation_history.append({"role": "assistant", "content": output.model_dump_json()})
                self.current_frame = "closing"
                return DraftComparison(
                    original_draft=output,
                    final_response=output,
                    revision_occurred=False,
                    revision_reason="Rule-based termination"
                )

        patient_context = get_static_patient_context(user_message, data_path=self.patient_data_path)
        graph_fact = graph_rag.get_knowledge_graph_fact(user_message, graph=self.knowledge_graph)
        empathy_seed = mandatory_prefix or direct_response or ""
        empathy = check_empathy_compliance(empathy_seed, user_message=user_message)

        observation_summary = self._build_observation_summary(user_message, patient_context, graph_fact, empathy, analysis)

        original_draft: Optional[FrameResponse] = None
        draft_response: Optional[FrameResponse] = None
        revision_occurred = False
        revision_reason = ""
        
        for attempt in range(self.max_reasoning_steps):
            messages = self._build_prompt(user_message, observation_summary, revised=attempt > 0)
            raw_content = self._call_ollama(messages)
            
            # Extract and execute tool calls from the response
            tool_calls = self._extract_tool_calls(raw_content)
            tool_results: list[ToolResult] = []
            if tool_calls:
                for tool_call in tool_calls:
                    tool_result = self._execute_tool(tool_call)
                    tool_results.append(tool_result)
                
                # Add tool results to observation summary for the next reasoning step
                if tool_results and attempt < self.max_reasoning_steps - 1:
                    observation_summary += "\n\nTool Execution Results:\n"
                    for tool_result in tool_results:
                        observation_summary += f"- {tool_result.tool_name}: {'Success' if tool_result.success else 'Error'}\n"
                        if tool_result.success and tool_result.result:
                            result_str = json.dumps(tool_result.result, indent=2)
                            observation_summary += f"  Result: {result_str}\n"
                        elif not tool_result.success:
                            observation_summary += f"  Error: {tool_result.error}\n"
            
            candidate = self._parse_frame_response(raw_content)

            if direct_response and candidate.agent_response:
                candidate.agent_response = f"{direct_response} {candidate.agent_response}".strip()

            if mandatory_prefix and not candidate.agent_response.startswith(mandatory_prefix):
                candidate.agent_response = f"{mandatory_prefix}{candidate.agent_response}".strip()

            # Capture the original draft from first iteration
            if original_draft is None:
                original_draft = FrameResponse(
                    active_frame=candidate.active_frame,
                    filled_slots=candidate.filled_slots.copy(),
                    agent_response=candidate.agent_response,
                    next_frame=candidate.next_frame
                )

            compliance = check_empathy_compliance(candidate.agent_response, user_message=user_message)
            graph_verification = graph_rag.verify_llm_response(candidate.agent_response, graph_fact.entities, graph=self.knowledge_graph)

            if analysis["forbidden_topic"]:
                candidate = self._fallback_response(user_message, analysis, patient_context, graph_fact)
                draft_response = candidate
                if original_draft.agent_response != candidate.agent_response:
                    revision_occurred = True
                    revision_reason = "Forbidden topic detected; fallback response applied"
                break

            if compliance.compliant and graph_verification.get("verified", True):
                draft_response = candidate
                if original_draft.agent_response != candidate.agent_response:
                    revision_occurred = True
                    revision_reason = "Original draft did not pass compliance/verification checks"
                break

            observation_summary += (
                "\n\nRevision notes:\n"
                f"- Empathy compliance issues: {', '.join(compliance.issues) if compliance.issues else 'none'}\n"
                f"- Graph verification issues: {', '.join(graph_verification.get('flagged_relations', [])) if graph_verification.get('flagged_relations') else 'none'}\n"
            )

        if draft_response is None:
            draft_response = self._fallback_response(user_message, analysis, patient_context, graph_fact)
            if original_draft and original_draft.agent_response != draft_response.agent_response:
                revision_occurred = True
                revision_reason = "All iterations failed compliance; fallback response applied"

        required_slots = self.frame_specs.get(self.current_frame).required_slots if self.current_frame in self.frame_specs else []
        current_memory = self.frame_memory.setdefault(self.current_frame, {})
        current_memory.update(draft_response.filled_slots)

        if self.current_frame == "emotion_check" and patient_context.records:
            current_memory.setdefault("patient_perception", patient_context.records[0].perception or "not yet clarified")

        missing_required = [slot for slot in required_slots if slot not in current_memory]
        if missing_required:
            draft_response.next_frame = self.current_frame
        else:
            allowed = self.frame_specs.get(self.current_frame).next_frames if self.current_frame in self.frame_specs else []
            if allowed and draft_response.next_frame not in allowed:
                draft_response.next_frame = allowed[0]

        self.current_frame = draft_response.next_frame or self.current_frame
        self.conversation_history.append({"role": "assistant", "content": draft_response.model_dump_json()})
        
        # Ensure we have valid drafts to return
        if original_draft is None:
            original_draft = draft_response
        
        return DraftComparison(
            original_draft=original_draft,
            final_response=draft_response,
            revision_occurred=revision_occurred,
            revision_reason=revision_reason
        )
