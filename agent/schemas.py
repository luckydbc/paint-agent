"""订单数据模型：值 + 状态分离，关键参数带原文证据。"""
from __future__ import annotations

from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field

SourceType = Literal["explicit", "inferred", "default"]
ParamStatus = Literal["missing", "pending", "confirmed", "conflict"]
DocumentType = Literal["cover", "catalog", "body", "ppt", "contract", "manual", "paper", "other"]
IntentType = Literal["print", "layout", "binding", "modify", "clarify"]


class IntParameter(BaseModel):
    """整数参数（页数/份数/册数）：value 未知用 null，绝不用 0 代替。"""

    value: Optional[int] = None
    source_text: Optional[str] = None
    source_type: Optional[SourceType] = None
    status: ParamStatus = "missing"


class BoolParameter(BaseModel):
    """布尔参数（是否排版/是否装订）：value 未知用 null。"""

    value: Optional[bool] = None
    source_text: Optional[str] = None
    source_type: Optional[SourceType] = None
    status: ParamStatus = "missing"


class Document(BaseModel):
    """一个文档（或文档组成部分），如封面/目录/正文。"""

    document_type: DocumentType = "other"
    name: str
    source_pages: IntParameter = Field(default_factory=IntParameter)
    print_copies: IntParameter = Field(default_factory=IntParameter)
    needs_layout: BoolParameter = Field(default_factory=BoolParameter)


class Extraction(BaseModel):
    """LLM 提取的原始结果（尚未套默认值、尚未校验完整性）。"""

    documents: list[Document] = Field(default_factory=list)
    binding_required: BoolParameter = Field(default_factory=BoolParameter)
    binding_count: IntParameter = Field(default_factory=IntParameter)
    ambiguities: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class Intent(BaseModel):
    intents: list[IntentType] = Field(default_factory=list)
    summary: str = ""


class EvidenceIssue(BaseModel):
    category: Literal[
        "omission", "hallucination", "misbinding", "conflict", "scope", "negation", "reference"
    ]
    description: str
    source_text: str = ""


class EvidenceReview(BaseModel):
    issues: list[EvidenceIssue] = Field(default_factory=list)


class ResolvedDocument(BaseModel):
    """校验 + 默认值应用后的文档，各字段 value 已确认为非空。"""

    document_id: str
    document_type: DocumentType
    name: str
    source_pages: IntParameter
    print_copies: IntParameter
    needs_layout: BoolParameter


class Order(BaseModel):
    """最终订单：所有影响报价的参数已明确。"""

    documents: list[ResolvedDocument] = Field(default_factory=list)
    binding_required: bool = False
    binding_count: int = 0
    summary: str = ""
    applied_defaults: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    missing_fields: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    ok: bool = True


class Quote(BaseModel):
    typesetting_pages: int = 0
    typesetting_fee: float = 0.0
    printing_pages: int = 0
    printing_fee: float = 0.0
    binding_count: int = 0
    binding_fee: float = 0.0
    total: float = 0.0
    detail: list[dict] = Field(default_factory=list)
    applied_defaults: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    summary: str = ""


class OrderState(TypedDict, total=False):
    messages: list
    intent: dict
    extraction: Optional[Extraction]
    schema_issues: list[str]
    evidence_issues: list[str]
    order: Optional[Order]
    validation: Optional[ValidationReport]
    quote: Optional[Quote]
    quote_issues: list[str]
    clarify_rounds: int
    give_up: bool
    result: str
