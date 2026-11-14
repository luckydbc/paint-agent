"""确定性计费与独立复核（纯函数，不依赖 LLM）。"""
from __future__ import annotations

from .config import Prices
from .schemas import Order, Quote


def calculate_quote(order: Order, prices: Prices) -> Quote:
    typesetting_pages = sum(
        d.source_pages.value for d in order.documents if d.needs_layout.value
    )
    printing_pages = sum(
        d.source_pages.value * d.print_copies.value for d in order.documents
    )
    binding_count = order.binding_count if order.binding_required else 0

    typesetting_fee = round(typesetting_pages * prices.typesetting_per_source_page, 2)
    printing_fee = round(printing_pages * prices.printing_per_page, 2)
    binding_fee = round(binding_count * prices.binding_per_volume, 2)
    total = round(typesetting_fee + printing_fee + binding_fee, 2)

    detail = [
        {
            "document_id": d.document_id,
            "name": d.name,
            "document_type": d.document_type,
            "source_pages": d.source_pages.value,
            "print_copies": d.print_copies.value,
            "printed_pages": d.source_pages.value * d.print_copies.value,
            "needs_layout": d.needs_layout.value,
        }
        for d in order.documents
    ]

    return Quote(
        typesetting_pages=typesetting_pages,
        typesetting_fee=typesetting_fee,
        printing_pages=printing_pages,
        printing_fee=printing_fee,
        binding_count=binding_count,
        binding_fee=binding_fee,
        total=total,
        detail=detail,
        applied_defaults=list(order.applied_defaults),
        summary=order.summary,
    )


def validate_quote(quote: Quote, order: Order, prices: Prices) -> list[str]:
    """独立复核：用订单反推各分项，与 Quote 逐项比对。"""
    issues: list[str] = []

    expected_printing_pages = sum(
        d.source_pages.value * d.print_copies.value for d in order.documents
    )
    expected_ts_pages = sum(
        d.source_pages.value for d in order.documents if d.needs_layout.value
    )
    expected_binding_count = order.binding_count if order.binding_required else 0

    if quote.printing_pages != expected_printing_pages:
        issues.append(f"打印页数复核不一致：{quote.printing_pages} != {expected_printing_pages}")
    if quote.typesetting_pages != expected_ts_pages:
        issues.append(f"排版页数复核不一致：{quote.typesetting_pages} != {expected_ts_pages}")
    if quote.binding_count != expected_binding_count:
        issues.append(f"装订册数复核不一致：{quote.binding_count} != {expected_binding_count}")

    if abs(quote.total - (quote.typesetting_fee + quote.printing_fee + quote.binding_fee)) > 0.01:
        issues.append("总价不等于各分项之和")
    if abs(quote.typesetting_fee - round(quote.typesetting_pages * prices.typesetting_per_source_page, 2)) > 0.01:
        issues.append("排版费与价目不符")
    if abs(quote.printing_fee - round(quote.printing_pages * prices.printing_per_page, 2)) > 0.01:
        issues.append("打印费与价目不符")
    if abs(quote.binding_fee - round(quote.binding_count * prices.binding_per_volume, 2)) > 0.01:
        issues.append("装订费与价目不符")

    return issues
