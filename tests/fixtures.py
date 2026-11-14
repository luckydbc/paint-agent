"""测试共享的构造器与价目。"""
from __future__ import annotations

from agent.config import Config, Defaults, Prices, Rules
from agent.schemas import BoolParameter, Document, IntParameter, ResolvedDocument

PRICES = Prices(
    typesetting_per_source_page=3.0,
    printing_per_page=0.5,
    binding_per_volume=20.0,
)


def make_config(**overrides) -> Config:
    data = dict(model="gpt-4o-mini", temperature=0, prices=PRICES,
                defaults=Defaults(default_needs_layout=False, default_needs_binding=False),
                rules=Rules(evidence_critic_enabled=False, max_clarify_rounds=5))
    data.update(overrides)
    return Config(**data)


def rdoc(doc_id, name, doc_type, pages, copies, layout) -> ResolvedDocument:
    return ResolvedDocument(
        document_id=doc_id,
        document_type=doc_type,
        name=name,
        source_pages=IntParameter(value=pages, source_text="t", source_type="explicit", status="confirmed"),
        print_copies=IntParameter(value=copies, source_text="t", source_type="explicit", status="confirmed"),
        needs_layout=BoolParameter(value=layout, source_text=None,
                                   source_type="explicit" if layout else "default", status="confirmed"),
    )


def intp(value, source_text=None, source_type=None) -> IntParameter:
    return IntParameter(value=value, source_text=source_text, source_type=source_type)


def boolp(value, source_text=None, source_type=None) -> BoolParameter:
    return BoolParameter(value=value, source_text=source_text, source_type=source_type)


def ext_doc(name, doc_type="other", pages=None, copies=None, layout=None) -> Document:
    return Document(
        document_type=doc_type,
        name=name,
        source_pages=intp(pages),
        print_copies=intp(copies),
        needs_layout=boolp(layout),
    )
