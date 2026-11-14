"""5 个验收样例 + 边界的计费断言。"""
from __future__ import annotations

from agent.pricing import calculate_quote, validate_quote
from agent.schemas import Order

from tests.fixtures import PRICES, rdoc


def _order(docs, binding=False, count=0, applied_defaults=None) -> Order:
    return Order(documents=docs, binding_required=binding, binding_count=count,
                 applied_defaults=applied_defaults or [])


def test_sample1():
    o = _order([rdoc("doc_1", "合同", "contract", 10, 1, False)], True, 1)
    q = calculate_quote(o, PRICES)
    assert q.printing_fee == 5.0
    assert q.binding_fee == 20.0
    assert q.typesetting_fee == 0.0
    assert q.total == 25.0


def test_sample2():
    o = _order([rdoc("doc_1", "PPT", "ppt", 20, 3, False)], True, 2)
    q = calculate_quote(o, PRICES)
    assert q.printing_pages == 60
    assert q.printing_fee == 30.0
    assert q.binding_fee == 40.0
    assert q.total == 70.0


def test_sample3():
    o = _order([rdoc("doc_1", "论文", "paper", 80, 2, False)], True, 2)
    q = calculate_quote(o, PRICES)
    assert q.printing_pages == 160
    assert q.printing_fee == 80.0
    assert q.binding_fee == 40.0
    assert q.total == 120.0


def test_sample4():
    o = _order([rdoc("doc_1", "手册", "manual", 15, 1, False)], False, 0)
    q = calculate_quote(o, PRICES)
    assert q.printing_pages == 15
    assert q.printing_fee == 7.5
    assert q.binding_fee == 0.0
    assert q.typesetting_fee == 0.0
    assert q.total == 7.5


def test_sample5():
    docs = [
        rdoc("doc_1", "封面", "cover", 1, 1, True),
        rdoc("doc_2", "目录", "catalog", 1, 1, True),
        rdoc("doc_3", "正文", "body", 30, 2, False),
    ]
    o = _order(docs, True, 1)
    q = calculate_quote(o, PRICES)
    assert q.printing_pages == 62
    assert q.printing_fee == 31.0
    assert q.typesetting_pages == 2
    assert q.typesetting_fee == 6.0
    assert q.binding_fee == 20.0
    assert q.total == 57.0


def test_typesetting_dedupes_per_document():
    # 同一文档打印多份，排版只按源页计一次
    o = _order([rdoc("doc_1", "正文", "body", 30, 5, True)], False, 0)
    q = calculate_quote(o, PRICES)
    assert q.typesetting_pages == 30
    assert q.typesetting_fee == 90.0
    assert q.printing_pages == 150


def test_quote_validation_passes_on_consistent_quote():
    o = _order([rdoc("doc_1", "正文", "body", 30, 2, True)], True, 1)
    q = calculate_quote(o, PRICES)
    assert validate_quote(q, o, PRICES) == []
