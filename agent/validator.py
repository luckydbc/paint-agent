"""确定性校验：Schema、证据（规则部分）、业务规则 + 默认值应用。"""
from __future__ import annotations

import re

from .config import Config
from .schemas import (
    BoolParameter,
    Document,
    Extraction,
    IntParameter,
    Order,
    ResolvedDocument,
    ValidationReport,
)

_NEGATION_BINDING_WORDS = ["不要装订", "不装订", "无需装订", "不用装订", "只要打印", "只打印"]


def _norm(s: str) -> str:
    return re.sub(r"[「」『』（）()。？?！!、\s]", "", s)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if not x:
            continue
        k = _norm(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def validate_schema(extraction: Extraction) -> list[str]:
    """类型已由 Pydantic 保证，这里做正整数等业务性 schema 约束。"""
    issues: list[str] = []
    if not extraction.documents:
        issues.append("未提取到任何文档")
    for doc in extraction.documents:
        if doc.source_pages.value is not None and doc.source_pages.value <= 0:
            issues.append(f"文档「{doc.name}」源页数不是正整数：{doc.source_pages.value}")
        if doc.print_copies.value is not None and doc.print_copies.value <= 0:
            issues.append(f"文档「{doc.name}」打印份数不是正整数：{doc.print_copies.value}")
    if extraction.binding_count.value is not None and extraction.binding_count.value <= 0:
        issues.append(f"装订册数不是正整数：{extraction.binding_count.value}")
    return issues


def validate_evidence_deterministic(history: list[dict], extraction: Extraction) -> list[str]:
    """确定性证据规则：否定词、同参数冲突。"""
    issues: list[str] = []
    user_text = " ".join(m.get("content", "") for m in history or [] if m.get("role") == "user")

    if any(w in user_text for w in _NEGATION_BINDING_WORDS):
        if extraction.binding_required.value is True:
            issues.append("原文明确“不要装订/只要打印”，但提取为需要装订（否定错误）")
        if extraction.binding_count.value not in (None, 0):
            issues.append("原文明确不要装订，但提取了装订册数（否定错误）")

    # 同参数冲突：binding_required 与 binding_count 自相矛盾
    if extraction.binding_required.value is False and extraction.binding_count.value:
        issues.append("是否需要装订与装订册数互相矛盾")

    return issues


def _resolve_bool(param: BoolParameter, default: bool, label: str, applied_defaults: list[str]) -> BoolParameter:
    if param.value is None:
        applied_defaults.append(f"{label} → 默认{'需要' if default else '不需要'}")
        return BoolParameter(value=default, source_text=None, source_type="default", status="confirmed")
    return BoolParameter(
        value=param.value,
        source_text=param.source_text,
        source_type=param.source_type or "explicit",
        status="confirmed",
    )


def validate_business_rules(
    extraction: Extraction,
    schema_issues: list[str],
    evidence_issues: list[str],
    config: Config,
) -> tuple[Order | None, ValidationReport]:
    """套默认值 + 检查计费前置条件，产出最终 Order 与校验报告。"""
    missing: list[str] = []
    ambiguities: list[str] = list(extraction.ambiguities)
    conflicts: list[str] = list(extraction.conflicts) + list(schema_issues) + list(evidence_issues)
    applied_defaults: list[str] = []

    if not extraction.documents:
        missing.append("请问需要打印什么内容？一共有多少页、打印几份？")

    resolved_docs: list[ResolvedDocument] = []
    for i, doc in enumerate(extraction.documents):
        sp_value = doc.source_pages.value
        pc_value = doc.print_copies.value
        if sp_value is None:
            missing.append(f"「{doc.name}」有多少页？")
        if pc_value is None:
            missing.append(f"「{doc.name}」需要打印几份？")

        needs_layout = _resolve_bool(
            doc.needs_layout, config.defaults.default_needs_layout, f"{doc.name} 排版", applied_defaults
        )

        resolved_docs.append(
            ResolvedDocument(
                document_id=f"doc_{i + 1}",
                document_type=doc.document_type,
                name=doc.name,
                source_pages=IntParameter(
                    value=sp_value,
                    source_text=doc.source_pages.source_text,
                    source_type=doc.source_pages.source_type,
                    status="confirmed" if sp_value is not None else "missing",
                ),
                print_copies=IntParameter(
                    value=pc_value,
                    source_text=doc.print_copies.source_text,
                    source_type=doc.print_copies.source_type,
                    status="confirmed" if pc_value is not None else "missing",
                ),
                needs_layout=needs_layout,
            )
        )

    br = extraction.binding_required
    bc = extraction.binding_count
    if br.value is None and bc.value is not None and bc.value > 0:
        # 册数已给出，说明需要装订（推断），避免漏掉装订费
        br = BoolParameter(value=True, source_text=bc.source_text, source_type="inferred", status="confirmed")
    binding_required = _resolve_bool(br, config.defaults.default_needs_binding, "装订", applied_defaults).value
    binding_count = bc.value
    if binding_required and binding_count is None:
        missing.append("需要装订成几册？（例如：每份单独装订，还是合并装订）")

    questions = _dedupe(missing + ambiguities + conflicts)

    if questions:
        report = ValidationReport(
            missing_fields=_dedupe(missing),
            ambiguities=_dedupe(ambiguities),
            conflicts=_dedupe(conflicts),
            clarification_questions=questions,
            ok=False,
        )
        return None, report

    order = Order(
        documents=resolved_docs,
        binding_required=binding_required,
        binding_count=binding_count if binding_required else 0,
        applied_defaults=_dedupe(applied_defaults),
    )
    report = ValidationReport(ok=True)
    return order, report
