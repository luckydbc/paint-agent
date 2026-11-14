"""确定性证据规则的断言（否定、冲突）。"""
from __future__ import annotations

from agent.schemas import Extraction
from agent.validator import validate_evidence_deterministic

from tests.fixtures import boolp, ext_doc, intp


def _hist(*user_texts):
    return [{"role": "user", "content": t} for t in user_texts]


def test_negation_binding_conflict():
    ext = Extraction(
        documents=[ext_doc("手册", "manual", pages=15, copies=1)],
        binding_required=boolp(True, source_text="装订", source_type="explicit"),
    )
    issues = validate_evidence_deterministic(_hist("只要打印，不要装订：手册15页，印1份"), ext)
    assert any("否定" in i for i in issues)


def test_binding_false_with_count_is_conflict():
    ext = Extraction(
        documents=[ext_doc("手册", "manual", pages=15, copies=1)],
        binding_required=boolp(False, source_text="不要装订", source_type="explicit"),
        binding_count=intp(2),
    )
    issues = validate_evidence_deterministic(_hist("手册15页印1份"), ext)
    assert any("矛盾" in i for i in issues)


def test_no_negation_means_no_issue():
    ext = Extraction(
        documents=[ext_doc("合同", "contract", pages=10, copies=1)],
        binding_required=boolp(True, source_text="装订成1本", source_type="explicit"),
        binding_count=intp(1),
    )
    issues = validate_evidence_deterministic(_hist("帮我打一份合同，一共10页，装订成1本"), ext)
    assert issues == []
