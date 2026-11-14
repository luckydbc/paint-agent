"""报价单渲染（确定性）。"""
from __future__ import annotations

from .config import Prices
from .schemas import Quote

_DOC_TYPE_LABELS = {
    "cover": "封面",
    "catalog": "目录",
    "body": "正文",
    "ppt": "PPT",
    "contract": "合同",
    "manual": "手册",
    "paper": "论文",
    "other": "其他",
}


def _money(amount: float) -> str:
    return f"¥{amount:.2f}"


def render_quote(quote: Quote, prices: Prices) -> str:
    lines: list[str] = []
    lines.append("### 📋 报价单")
    lines.append("")

    if quote.summary:
        lines.append(f"**需求摘要**：{quote.summary}")
        lines.append("")

    lines.append("**文档清单**")
    lines.append("")
    lines.append("| 文档 | 类型 | 源页数 | 份数 | 打印页数 | 排版 |")
    lines.append("| --- | --- | ---: | ---: | ---: | --- |")
    for d in quote.detail:
        layout = "需要" if d["needs_layout"] else "不需要"
        doc_type = _DOC_TYPE_LABELS.get(d["document_type"], d["document_type"])
        lines.append(
            f"| {d['name']} | {doc_type} | {d['source_pages']} | {d['print_copies']} "
            f"| {d['printed_pages']} | {layout} |"
        )
    lines.append("")

    lines.append("**费用明细**")
    lines.append("")
    lines.append("| 费用项 | 计算 | 金额 |")
    lines.append("| --- | --- | ---: |")
    lines.append(
        f"| 排版费 | {quote.typesetting_pages} 源页 × {_money(prices.typesetting_per_source_page)} "
        f"| {_money(quote.typesetting_fee)} |"
    )
    lines.append(
        f"| 打印费 | {quote.printing_pages} 页 × {_money(prices.printing_per_page)} "
        f"| {_money(quote.printing_fee)} |"
    )
    lines.append(
        f"| 装订费 | {quote.binding_count} 册 × {_money(prices.binding_per_volume)} "
        f"| {_money(quote.binding_fee)} |"
    )
    lines.append("")
    lines.append(f"**合计：{_money(quote.total)}**")
    lines.append("")

    if quote.applied_defaults:
        lines.append("**计费说明（默认规则）**")
        lines.append("")
        for ad in quote.applied_defaults:
            lines.append(f"- {ad}")
        lines.append("")

    if quote.notes:
        lines.append("**备注**")
        lines.append("")
        for n in quote.notes:
            lines.append(f"- {n}")
        lines.append("")

    return "\n".join(lines).rstrip()
