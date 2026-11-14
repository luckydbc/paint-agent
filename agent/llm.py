"""LLM 模型工厂：通过 OpenAI 兼容接口调用 DeepSeek。"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from .config import Config

# DeepSeek 提供 OpenAI 兼容的 API 端点
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

load_dotenv()


def make_llm(config: Config) -> ChatOpenAI:
    return ChatOpenAI(
        model=config.model,
        temperature=config.temperature,
        base_url=config.base_url or os.getenv("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL,
        api_key=config.api_key or os.getenv("DEEPSEEK_API_KEY"),
    )
