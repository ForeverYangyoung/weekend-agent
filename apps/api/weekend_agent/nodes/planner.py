"""Planner 节点：薄适配层，业务在 `weekend_agent.agents.planner`。

主路径：调 `build_plans` 枚举两种阶段顺序 → 五维分排序 → 写 plan + plan_alternatives。
降级：研究无产出/全被硬过滤砍光 → 回退到 stub（家庭/朋友）。
"""
from __future__ import annotations

from weekend_agent.agents import build_family_stub, build_friends_stub, build_plans
from weekend_agent.roles import trace_line
from weekend_agent.schemas import Plan
from weekend_agent.state import AgentState


def planner_node(state: AgentState) -> dict:
    profile = state.get("group_profile")
    iteration = state.get("plan_iteration", 0)
    research = state.get("research_result")

    blocked = {
        (call.args or {}).get("poi_id")
        for call in state.get("failed_calls", []) or []
        if (call.args or {}).get("poi_id")
    }
    blocked.discard(None)

    plans: list[Plan] = []
    source = "stub"
    if profile is not None and research is not None and research.stages:
        plans = build_plans(profile, research, blocked, top_k=2)
        if plans:
            source = "research"

    if not plans:
        stub = (
            build_friends_stub()
            if profile and profile.scene == "friends"
            else build_family_stub()
        )
        plans = [stub]

    primary = plans[0]
    alternatives = plans[1:]

    alt_brief = (
        "；备选 " + "; ".join(f"{p.order_label} score={p.score:.2f}" for p in alternatives)
        if alternatives
        else ""
    )
    detail = (
        f"{primary.summary}（来源={source}，{len(primary.stages)} 阶段，"
        f"预计 ¥{primary.total_cost_estimate}，score={primary.score:.2f}{alt_brief}）"
    )
    if iteration > 0:
        line = trace_line("Planner", detail, phase="重规划", suffix=f"#{iteration}")
    else:
        line = trace_line("Planner", f"首次规划：{detail}")

    return {
        "plan": primary,
        "plan_alternatives": alternatives,
        "plan_iteration": iteration + 1,
        "trace": [line],
    }
