"""业务规则校验 + 默认值应用的断言。"""
from __future__ import annotations

from agent.schemas import Extraction
from agent.validator import validate_business_rules, validate_schema

from tests.fixtures import boolp, ext_doc, intp, make_config


def test_defaults_applied_when_unmentioned():
    ext = Extraction(
        documents=[ext_doc("合同", "contract", pages=10, copies=1)],
        binding_required=boolp(None),
        binding_count=intp(None),
    )
    order, report = validate_business_rules(ext, [], [], make_config())
    assert report.ok is True
    assert order is not None
    assert order.documents[0].needs_layout.value is False
    assert order.documents[0].needs_layout.source_type == "default"
    assert order.binding_required is False
    assert order.binding_count == 0
    assert any("排版" in d for d in order.applied_defaults)


def test_missing_pages_triggers_clarification():
    ext = Extraction(
        documents=[ext_doc("合同", "contract", pages=None, copies=1)],
        binding_required=boolp(None),
    )
    order, report = validate_business_rules(ext, [], [], make_config())
    assert order is None
    assert report.ok is False
    assert any("多少页" in q for q in report.clarification_questions)


def test_binding_without_count_triggers_clarification():
    ext = Extraction(
        documents=[ext_doc("合同", "contract", pages=10, copies=1)],
        binding_required=boolp(True, source_text="装订", source_type="explicit"),
        binding_count=intp(None),
    )
    order, report = validate_business_rules(ext, [], [], make_config())
    assert order is None
    assert any("几册" in q for q in report.clarification_questions)


def test_explicit_layout_is_kept():
    ext = Extraction(
        documents=[ext_doc("正文", "body", pages=30, copies=2, layout=True)],
        binding_required=boolp(None),
    )
    order, report = validate_business_rules(ext, [], [], make_config())
    assert report.ok is True
    assert order.documents[0].needs_layout.value is True
    assert order.documents[0].needs_layout.source_type != "default"


def test_negative_pages_flagged_by_schema():
    ext = Extraction(documents=[ext_doc("合同", "contract", pages=-1, copies=1)])
    issues = validate_schema(ext)
    assert any("正整数" in i for i in issues)
