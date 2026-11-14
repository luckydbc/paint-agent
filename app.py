"""Streamlit 入口：打印店自然语言接单 Agent。"""
from __future__ import annotations

import os
import uuid

import streamlit as st
from dotenv import load_dotenv
from langgraph.types import Command

from agent import clarify
from agent.config import load_config
from agent.graph import build_graph

load_dotenv()

st.set_page_config(page_title="打印店接单 Agent", page_icon="🖨️")
st.title("🖨️ 打印店自然语言接单 Agent")

config = load_config()

with st.sidebar:
    st.subheader("当前价目（可配置）")
    st.write(f"- 排版：¥{config.prices.typesetting_per_source_page}/源页面")
    st.write(f"- 打印：¥{config.prices.printing_per_page}/打印页")
    st.write(f"- 装订：¥{config.prices.binding_per_volume}/册")
    st.caption("默认规则：未提及排版/装订时按「不需要」处理，并在报价单中标注。修改 config.json 后重启生效。")


def _get_graph():
    # MemorySaver 随 graph 对象保存，缓存到 session_state 以便中断恢复
    if "graph" not in st.session_state:
        st.session_state.graph = build_graph(config)
    return st.session_state.graph


def _extract_interrupt_questions(result: dict):
    irq = result.get("__interrupt__")
    if not irq:
        return None
    item = irq[0]
    value = item if isinstance(item, dict) else getattr(item, "value", None)
    if isinstance(value, dict):
        return value.get("questions")
    return value


if not (os.getenv("DEEPSEEK_API_KEY") or config.api_key):
    st.error("未检测到 DEEPSEEK_API_KEY，请在 .env 文件中配置后重启。")
    st.stop()

graph = _get_graph()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = False

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("描述您的打印需求，例如：帮我打一份合同，一共10页，装订成1本。"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.pending:
        result = graph.invoke(
            Command(resume=prompt),
            config={"configurable": {"thread_id": st.session_state.thread_id}},
        )
    else:
        st.session_state.thread_id = str(uuid.uuid4())
        result = graph.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": st.session_state.thread_id}},
        )

    questions = _extract_interrupt_questions(result)
    if questions:
        st.session_state.pending = True
        text = clarify.format_clarification(questions)
    else:
        st.session_state.pending = False
        text = result.get("result", "")

    st.session_state.messages.append({"role": "assistant", "content": text})
    with st.chat_message("assistant"):
        st.markdown(text)
