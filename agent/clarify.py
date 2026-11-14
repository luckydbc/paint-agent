"""追问节点：interrupt 挂起，恢复后把问答追加进对话。"""
from __future__ import annotations

from langgraph.types import interrupt

GIVE_UP_TEXT = (
    "抱歉，多次补充后信息仍不完整。请重新下单，并明确：各文档的页数、打印份数、"
    "是否需要排版、装订册数。"
)


def format_clarification(questions: list[str]) -> str:
    if not questions:
        return ""
    return "好的，还差一点信息，请补充：\n" + "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))


def clarify_order_node(state: dict, max_rounds: int) -> dict:
    rounds = int(state.get("clarify_rounds", 0) or 0) + 1
    if rounds > max_rounds:
        return {"give_up": True, "clarify_rounds": rounds, "result": GIVE_UP_TEXT}

    questions = state["validation"].clarification_questions
    answer = interrupt({"questions": questions})

    messages = list(state.get("messages") or [])
    messages.append({"role": "assistant", "content": format_clarification(questions)})
    messages.append({"role": "user", "content": str(answer)})
    return {"messages": messages, "clarify_rounds": rounds}
