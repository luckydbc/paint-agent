"""图流程集成测试（mock LLM，验证 clarify/interrupt/resume 接线）。"""
from __future__ import annotations

import os

import pytest
from langgraph.types import Command

from agent import extractor
from agent.config import load_config
from agent.graph import build_graph
from agent.schemas import BoolParameter, Document, Extraction, IntParameter, Intent


def _fake_intent(history, llm):
    return Intent(intents=["print", "binding"], summary="打印合同并装订")


def _fake_extract(history, llm):
    text = " ".join(m.get("content", "") for m in history if m.get("role") == "user")
    has_pages = "10页" in text or "10 页" in text
    pages = 10 if has_pages else None
    doc = Document(
        document_type="contract",
        name="合同",
        source_pages=IntParameter(
            value=pages, source_text="一共10页" if has_pages else None,
            source_type="explicit" if has_pages else None,
        ),
        print_copies=IntParameter(value=1, source_text="打一份", source_type="explicit"),
        needs_layout=BoolParameter(value=None),
    )
    return Extraction(
        documents=[doc],
        binding_required=BoolParameter(value=True, source_text="装订成1本", source_type="explicit"),
        binding_count=IntParameter(value=1, source_text="装订成1本", source_type="explicit"),
        ambiguities=[] if has_pages else ["合同有多少页？"],
    )


def _fake_review(history, extraction, llm):
    return []


@pytest.fixture
def graph(monkeypatch):
    os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-not-real")
    monkeypatch.setattr(extractor, "parse_intent", _fake_intent)
    monkeypatch.setattr(extractor, "extract_parameters", _fake_extract)
    monkeypatch.setattr(extractor, "review_evidence", _fake_review)
    return build_graph(load_config())


def test_complete_order_produces_quote(graph):
    r = graph.invoke(
        {"messages": [{"role": "user", "content": "帮我打一份合同，一共10页，装订成1本"}]},
        config={"configurable": {"thread_id": "a"}},
    )
    assert not r.get("__interrupt__")
    assert "¥25.00" in r["result"]


def test_missing_pages_clarifies_then_resumes(graph):
    r = graph.invoke(
        {"messages": [{"role": "user", "content": "帮我打一份合同"}]},
        config={"configurable": {"thread_id": "b"}},
    )
    questions = r["__interrupt__"][0].value["questions"]
    assert len(questions) == 1

    r2 = graph.invoke(
        Command(resume="一共10页，装订成1本"),
        config={"configurable": {"thread_id": "b"}},
    )
    assert not r2.get("__interrupt__")
    assert "¥25.00" in r2["result"]
