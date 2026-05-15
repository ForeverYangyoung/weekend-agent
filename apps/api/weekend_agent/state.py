"""LangGraph 的全局 State。所有节点读/写同一份 State。"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from weekend_agent.schemas import (
    CriticFeedback,
    GroupProfile,
    Plan,
    SummaryCard,
    ToolCall,
)


class AgentState(TypedDict, total=False):
    # ── 输入 ──
    user_input: str

    # ── Profiler 输出 ──
    group_profile: GroupProfile | None

    # ── Planner 输出 ──
    plan: Plan | None
    plan_iteration: int  # 已重规划次数，触发 max_plan_iterations 兜底

    # ── Critic 输出 ──
    critic_feedback: CriticFeedback | None

    # ── DryRun / Executor ──
    dry_run_calls: list[ToolCall]
    executed_calls: list[ToolCall]
    failed_calls: list[ToolCall]

    # ── 用户在 HIL 节点的确认结果 ──
    user_confirmed: bool

    # ── Notifier 最终交付 ──
    summary_card: SummaryCard | None

    # ── 追踪日志：每个节点 append 一条，answer 答辩时直接展示 ──
    trace: Annotated[list[str], operator.add]

    # ── Demo 专用：注入某阶段下单失败，用于演示补偿链 ──
    force_failure: str | None
