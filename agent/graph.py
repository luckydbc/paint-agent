"""LangGraph 工作流组装。"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from . import clarify, extractor, pricing, quotation, schemas, validator
from .config import Config
from .llm import make_llm
from .schemas import EvidenceReview, Extraction, Intent, OrderState


def _build_checkpointer() -> MemorySaver:
    """注册 state 中会存放的 Pydantic 模型，避免 checkpointer 序列化告警。"""
    models = [
        schemas.IntParameter,
        schemas.BoolParameter,
        schemas.Document,
        schemas.Extraction,
        schemas.ResolvedDocument,
        schemas.Order,
        schemas.ValidationReport,
        schemas.Quote,
        schemas.Intent,
        schemas.EvidenceReview,
    ]
    allowed = [(m.__module__, m.__name__) for m in models]
    serde = JsonPlusSerializer(allowed_msgpack_modules=allowed)
    return MemorySaver(serde=serde)


def build_graph(config: Config):
    llm = make_llm(config)
    # DeepSeek 不支持 response_format=json_schema（langchain 默认 method），
    # 而 function_calling 会与提示词里的「输出 JSON」冲突（模型常返回文本而非工具调用，导致解析为空）。
    # json_mode 使用 response_format=json_object，与提示词一致且 DeepSeek 支持，最稳定。
    intent_llm = llm.with_structured_output(Intent, method="json_mode")
    extract_llm = llm.with_structured_output(Extraction, method="json_mode")
    critic_llm = llm.with_structured_output(EvidenceReview, method="json_mode")

    def parse_intent_node(state: OrderState) -> dict:
        intent = extractor.parse_intent(state.get("messages") or [], intent_llm)
        return {"intent": intent.model_dump()}

    def extract_node(state: OrderState) -> dict:
        extraction = extractor.extract_parameters(state.get("messages") or [], extract_llm)
        return {"extraction": extraction}

    def validate_schema_node(state: OrderState) -> dict:
        issues = validator.validate_schema(state["extraction"])
        return {"schema_issues": issues}

    def validate_evidence_node(state: OrderState) -> dict:
        issues = validator.validate_evidence_deterministic(
            state.get("messages") or [], state["extraction"]
        )
        if config.rules.evidence_critic_enabled:
            issues += extractor.review_evidence(
                state.get("messages") or [], state["extraction"], critic_llm
            )
        return {"evidence_issues": issues}

    def validate_business_node(state: OrderState) -> dict:
        order, report = validator.validate_business_rules(
            state["extraction"],
            state.get("schema_issues") or [],
            state.get("evidence_issues") or [],
            config,
        )
        if order is not None:
            order.summary = (state.get("intent") or {}).get("summary", "")
        return {"order": order, "validation": report}

    def calculate_quote_node(state: OrderState) -> dict:
        quote = pricing.calculate_quote(state["order"], config.prices)
        return {"quote": quote}

    def validate_quote_node(state: OrderState) -> dict:
        issues = pricing.validate_quote(state["quote"], state["order"], config.prices)
        return {"quote_issues": issues}

    def render_node(state: OrderState) -> dict:
        if state.get("give_up"):
            return {}
        if state.get("quote_issues"):
            body = "\n".join(f"- {x}" for x in state["quote_issues"])
            return {"result": f"【系统错误】报价复核未通过：\n{body}"}
        return {"result": quotation.render_quote(state["quote"], config.prices)}

    def clarify_node(state: OrderState) -> dict:
        return clarify.clarify_order_node(state, config.rules.max_clarify_rounds)

    def route_after_business(state: OrderState) -> str:
        if state["validation"].ok:
            return "calculate_quote"
        return "clarify_order"

    def route_after_clarify(state: OrderState) -> str:
        if state.get("give_up"):
            return END
        return "extract_parameters"

    g = StateGraph(OrderState)
    g.add_node("parse_intent", parse_intent_node)
    g.add_node("extract_parameters", extract_node)
    g.add_node("validate_schema", validate_schema_node)
    g.add_node("validate_evidence", validate_evidence_node)
    g.add_node("validate_business_rules", validate_business_node)
    g.add_node("clarify_order", clarify_node)
    g.add_node("calculate_quote", calculate_quote_node)
    g.add_node("validate_quote", validate_quote_node)
    g.add_node("render_result", render_node)

    g.add_edge(START, "parse_intent")
    g.add_edge("parse_intent", "extract_parameters")
    g.add_edge("extract_parameters", "validate_schema")
    g.add_edge("validate_schema", "validate_evidence")
    g.add_edge("validate_evidence", "validate_business_rules")
    g.add_conditional_edges(
        "validate_business_rules",
        route_after_business,
        {"calculate_quote": "calculate_quote", "clarify_order": "clarify_order"},
    )
    g.add_conditional_edges(
        "clarify_order",
        route_after_clarify,
        {"extract_parameters": "extract_parameters", END: END},
    )
    g.add_edge("calculate_quote", "validate_quote")
    g.add_edge("validate_quote", "render_result")
    g.add_edge("render_result", END)

    return g.compile(checkpointer=_build_checkpointer())
