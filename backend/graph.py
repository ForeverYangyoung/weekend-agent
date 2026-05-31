"""LangGraph 状态机装配。

主路径：

    START → profiler → planner → critic → dry_run → executor → notifier → END
                                          ▲                    │
                                          │   ┌────┴──────────────┐
                                          │ approved           not approved & iter < max
                                          │   ▼                    ▼
                                          │ dry_run              planner（重规划）
                                          │
                                          └── 重规划 ──────────────┘

Profiler 产出 search_strategy，Planner 内部完成检索+打分+组合。
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.config import get_settings
from backend.nodes import (
    compensator_node,
    critic_node,
    dry_run_node,
    executor_node,
    notifier_node,
    plan_patcher_node,
    planner_node,
    profiler_node,
    revision_node,
)
from backend.state import AgentState


def _post_critic_router(state: AgentState) -> str:
    """critic 之后：有用户反馈 → revision，未通过 → 重规划，通过 → dry_run。"""
    fb = state.get("critic_feedback")
    iteration = state.get("plan_iteration", 0)
    max_iter = get_settings().max_plan_iterations
    user_feedback = state.get("user_feedback", "").strip()

    if user_feedback:
        return "revision"

    if fb is None or fb.approved:
        return "dry_run"
    if iteration >= max_iter:
        return "dry_run"
    return "planner"


def _revision_router(state: AgentState) -> str:
    patches = state.get("revision_patches", []) or []
    return "plan_patcher" if patches else "dry_run"


def _executor_router(state: AgentState) -> str:
    failed = state.get("failed_calls", []) or []
    return "compensator" if failed else "notifier"


def _compensator_router(state: AgentState) -> str:
    iteration = state.get("plan_iteration", 0)
    max_iter = get_settings().max_plan_iterations
    return "planner" if iteration < max_iter else "notifier"


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("profiler", profiler_node)
    g.add_node("planner", planner_node)
    g.add_node("critic", critic_node)
    g.add_node("revision", revision_node)
    g.add_node("plan_patcher", plan_patcher_node)
    g.add_node("dry_run", dry_run_node)
    g.add_node("executor", executor_node)
    g.add_node("compensator", compensator_node)
    g.add_node("notifier", notifier_node)

    g.add_edge(START, "profiler")
    g.add_edge("profiler", "planner")
    g.add_edge("planner", "critic")

    g.add_conditional_edges(
        "critic",
        _post_critic_router,
        {"dry_run": "dry_run", "planner": "planner", "revision": "revision"},
    )

    g.add_conditional_edges(
        "revision",
        _revision_router,
        {"plan_patcher": "plan_patcher", "dry_run": "dry_run"},
    )

    g.add_edge("plan_patcher", "critic")

    g.add_edge("dry_run", "executor")

    g.add_conditional_edges(
        "executor",
        _executor_router,
        {"compensator": "compensator", "notifier": "notifier"},
    )

    g.add_conditional_edges(
        "compensator",
        _compensator_router,
        {"planner": "planner", "notifier": "notifier"},
    )

    g.add_edge("notifier", END)

    return g.compile()


agent_graph = build_graph()
