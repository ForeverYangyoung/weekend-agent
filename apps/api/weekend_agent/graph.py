"""LangGraph 状态机装配。

主路径（4 个逻辑 Agent，8 个 node）：

    START → profiler → researcher → planner → critic
                                       ▲        │
                                       │   ┌────┴──────────────────┐
                                       │ approved              not approved & iter < max
                                       │   ▼                       │
                                       │ dry_run                   │
                                       │   ▼                       │
                                       │ executor                  │
                                       │   ├── all ok ──→ notifier → END
                                       │   └── any fail ──→ compensator
                                       │                        │
                                       └────── 重规划 ──────────┘

逻辑角色 ↔ node 对照见 `roles.py` 与 `02.架构和agent.md §7`。
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from weekend_agent.config import get_settings
from weekend_agent.nodes import (
    compensator_node,
    critic_node,
    dry_run_node,
    executor_node,
    notifier_node,
    planner_node,
    profiler_node,
    researcher_node,
)
from weekend_agent.state import AgentState


# ─────────────────────────── 条件分支函数 ───────────────────────────


def _critic_router(state: AgentState) -> str:
    fb = state.get("critic_feedback")
    iteration = state.get("plan_iteration", 0)
    max_iter = get_settings().max_plan_iterations

    if fb is None or fb.approved:
        return "dry_run"
    if iteration >= max_iter:
        return "dry_run"
    return "planner"


def _executor_router(state: AgentState) -> str:
    failed = state.get("failed_calls", []) or []
    return "compensator" if failed else "notifier"


def _compensator_router(state: AgentState) -> str:
    iteration = state.get("plan_iteration", 0)
    max_iter = get_settings().max_plan_iterations
    return "planner" if iteration < max_iter else "notifier"


# ─────────────────────────── 装配 ───────────────────────────


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("profiler", profiler_node)
    g.add_node("researcher", researcher_node)
    g.add_node("planner", planner_node)
    g.add_node("critic", critic_node)
    g.add_node("dry_run", dry_run_node)
    g.add_node("executor", executor_node)
    g.add_node("compensator", compensator_node)
    g.add_node("notifier", notifier_node)

    g.add_edge(START, "profiler")
    g.add_edge("profiler", "researcher")
    g.add_edge("researcher", "planner")
    g.add_edge("planner", "critic")

    g.add_conditional_edges(
        "critic",
        _critic_router,
        {"dry_run": "dry_run", "planner": "planner"},
    )

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
