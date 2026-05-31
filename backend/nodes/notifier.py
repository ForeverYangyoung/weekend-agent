"""Notifier 节点：生成最终的行程卡 + 给亲友的可分享文案。

LLM 优先：用 LLM 生成自然的展示文案和分享语。
规则兜底：LLM 不可用时回退到模板渲染。
"""
from __future__ import annotations

from backend.llm_client import chat_json, get_llm_client
from backend.prompts import (
    notifier_summary_card_system,
    notifier_summary_card_user,
    plan_to_text,
    profile_to_text,
)
from backend.roles import trace_line
from backend.schemas import SummaryCard
from backend.state import AgentState


def _render_fallback(plan, profile, executed, alternatives) -> SummaryCard:
    """规则模板渲染 — LLM 不可用时的兜底。"""
    lines = [f"## {plan.summary}", ""]
    head = f"- 人数：{profile.people_count}　预计花费：约 ¥{plan.total_cost_estimate}"
    if plan.score:
        head += f"　综合评分：{plan.score:.2f}"
    lines.append(head)
    lines.append("")
    lines.append("| 时间 | 阶段 | 地点 | 订单 |")
    lines.append("|---|---|---|---|")

    order_by_stage: dict[str, str] = {}
    for c in executed:
        if c.result and "order_id" in c.result:
            order_by_stage[c.stage_name] = c.result["order_id"]

    for s in plan.stages:
        order = order_by_stage.get(s.name, "—")
        lines.append(
            f"| {s.start_time}–{s.end_time} | {s.name} | {s.primary.name} | `{order}` |"
        )

    if alternatives:
        lines.append("")
        lines.append("### 备选方案")
        for i, alt in enumerate(alternatives, start=1):
            order_label = alt.order_label or " → ".join(s.name for s in alt.stages)
            names = " → ".join(s.primary.name for s in alt.stages)
            lines.append(
                f"- 方案 {i}（{order_label}，score={alt.score:.2f}，约 ¥{alt.total_cost_estimate}）：{names}"
            )

    share = _render_share_fallback(plan)
    return SummaryCard(
        title=plan.summary,
        body_markdown="\n".join(lines),
        share_text=share,
    )


def _render_share_fallback(plan) -> str:
    if not plan.stages:
        return "搞定了，下午出发～"
    first = plan.stages[0]
    food = next((s for s in plan.stages if s.name == "吃"), None)
    food_name = food.primary.name if food else "一家轻食店"
    return (
        f"搞定了，下午 {first.start_time} 出发，先去 {first.primary.name}，"
        f"之后吃饭定在 {food_name}，美团已经下好单啦～"
    )


def _llm_summary_card(profile, plan) -> SummaryCard | None:
    """LLM 生成摘要卡片。"""
    client = get_llm_client()
    if client is None:
        return None

    result = chat_json(
        notifier_summary_card_system,
        notifier_summary_card_user.format(
            profile_text=profile_to_text(profile),
            plan_text=plan_to_text(plan),
        ),
        temperature=0.6,
        max_tokens=600,
    )

    if not isinstance(result, dict):
        return None

    return SummaryCard(
        title=result.get("title", plan.summary),
        body_markdown=result.get("body_markdown", ""),
        share_text=result.get("share_text", ""),
    )


def notifier_node(state: AgentState) -> dict:
    plan = state.get("plan")
    profile = state.get("group_profile")
    executed = state.get("executed_calls", []) or []
    alternatives = state.get("plan_alternatives") or []

    if not plan or not profile:
        return {"trace": [trace_line("Executor", "跳过：缺 plan/profile", phase="交付")]}

    # LLM 优先
    card = _llm_summary_card(profile, plan)

    # 规则兜底
    if card is None:
        card = _render_fallback(plan, profile, executed, alternatives)

    llm_tag = " (LLM)" if get_llm_client() else ""
    return {
        "summary_card": card,
        "trace": [
            trace_line(
                "Executor",
                f"行程卡已生成{llm_tag} ✓，{card.share_text[:40]}...",
                phase="交付",
            )
        ],
    }
