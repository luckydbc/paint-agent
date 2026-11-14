"""配置加载：模型、价目、默认策略、业务规则。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


@dataclass
class Prices:
    typesetting_per_source_page: float
    printing_per_page: float
    binding_per_volume: float


@dataclass
class Defaults:
    default_needs_layout: bool
    default_needs_binding: bool


@dataclass
class Rules:
    evidence_critic_enabled: bool = True
    max_clarify_rounds: int = 5


@dataclass
class Config:
    model: str
    temperature: float
    prices: Prices
    defaults: Defaults
    rules: Rules
    base_url: str | None = None
    api_key: str | None = None


def load_config(path: str | Path | None = None) -> Config:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    return Config(
        model=data["model"],
        temperature=data.get("temperature", 0),
        prices=Prices(**data["prices"]),
        defaults=Defaults(**data["defaults"]),
        rules=Rules(**data.get("rules", {})),
        base_url=data.get("base_url"),
        api_key=data.get("api_key"),
    )
