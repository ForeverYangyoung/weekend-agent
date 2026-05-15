"""Notifier 节点：生成最终的行程卡 + 给亲友的可分享文案。"""
from __future__ import annotations

from weekend_agent.schemas import SummaryCard
from weekend_agent.state import AgentState


def _render_markdown(plan, profile, executed) -> str:
    lines = [f"## {plan.summary}", ""]
    lines.append(f"- 人数：{profile.people_count}　预计花费：约 ¥{plan.total_cost_estimate}")
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
    return "\n".join(lines)


def _render_share(plan) -> str:
    first = plan.stages[0] if plan.stages else None
    if not first:
        return "搞定了，下午出发～"
    return (
        f"搞定了，下午 {first.start_time} 出发，先去 {first.primary.name}，"
        f"之后吃饭定在 {plan.stages[1].primary.name if len(plan.stages) > 1 else '一家轻食店'}，"
        "美团已经下好单啦～"
    )


def notifier_node(state: AgentState) -> dict:
    plan = state.get("plan")
    profile = state.get("group_profile")
    executed = state.get("executed_calls", []) or []

    if not plan or not profile:
        return {"trace": ["[Notifier] 跳过：缺 plan/profile"]}

    card = SummaryCard(
        title=plan.summary,
        body_markdown=_render_markdown(plan, profile, executed),
        share_text=_render_share(plan),
    )

    return {
        "summary_card": card,
        "trace": [f"[Notifier] 行程卡已生成 ✓，分享文案: {card.share_text[:30]}..."],
    }
