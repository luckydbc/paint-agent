"""LLM 调用：意图识别、参数提取、证据复核。"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from . import prompts
from .schemas import EvidenceReview, Extraction, Intent


def _to_messages(system_prompt: str, history: list[dict]) -> list:
    msgs = [SystemMessage(content=system_prompt)]
    for m in history or []:
        role = m.get("role")
        content = m.get("content", "")
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            msgs.append(AIMessage(content=content))
    return msgs


def _invoke_structured(structured_llm, messages, fallback: BaseModel) -> BaseModel:
    try:
        result = structured_llm.invoke(messages)
    except Exception:
        result = None
    if result is None:
        return fallback
    if isinstance(result, dict):
        return type(fallback).model_validate(result)
    return result


def parse_intent(history: list[dict], intent_llm) -> Intent:
    result = _invoke_structured(
        intent_llm, _to_messages(prompts.PARSE_INTENT_PROMPT, history), Intent()
    )
    return result  # type: ignore[return-value]


def extract_parameters(history: list[dict], extract_llm) -> Extraction:
    result = _invoke_structured(
        extract_llm,
        _to_messages(prompts.EXTRACT_PROMPT, history),
        Extraction(documents=[], ambiguities=["未能理解需求，请补充页码、份数、装订等信息。"]),
    )
    return result  # type: ignore[return-value]


def review_evidence(history: list[dict], extraction: Extraction, critic_llm) -> list[str]:
    """LLM 证据复核：参照原文，返回问题描述列表。"""
    user_text = "\n".join(m.get("content", "") for m in history if m.get("role") == "user")
    prompt = prompts.EVIDENCE_CRITIC_PROMPT.format(
        user_text=user_text or "(空)",
        extraction_json=extraction.model_dump_json(exclude_none=False),
    )
    review = _invoke_structured(critic_llm, [SystemMessage(content=prompt)], EvidenceReview())
    if review is None:
        return []
    return [f"[{i.category}] {i.description}" for i in review.issues]
