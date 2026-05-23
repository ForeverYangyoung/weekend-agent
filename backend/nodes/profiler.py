"""Profiler 节点：从用户一句话中抽取群体画像。

薄适配层：业务在 `weekend_agent.agents.profiler.analyze_profile`。
保留 `_heuristic_profile` 名字给老测试 / 文档使用。
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.agents import analyze_profile
from backend.roles import trace_line
from backend.schemas import GroupProfile
from backend.state import AgentState


def _heuristic_profile(
    text: str,
    history_context: Mapping[str, Any] | None = None,
) -> GroupProfile:
    """向后兼容入口（旧代码/文档以此名调用）。"""
    return analyze_profile(text, history_context=history_context)


def profiler_node(state: AgentState) -> dict:
    """节点入口：返回的 dict 会被合并进 AgentState。"""
    text = state.get("user_input", "")
    history_context = state.get("history_context") or {}  # type: ignore[arg-type]
    profile = analyze_profile(text, history_context=history_context)

    scene_conf = profile.confidence.get("scene", 0.0)
    tags_preview = [t.label for t in profile.editable_tags[:6]]
    start = profile.start_time or "—"

    return {
        "group_profile": profile,
        "plan_iteration": 0,
        "trace": [
            trace_line(
                "Profiler",
                f"scene={profile.scene}(conf={scene_conf:.2f}) people={profile.people_count} "
                f"start={start} dietary={profile.dietary} interests={profile.interests} "
                f"tags={tags_preview}",
            )
        ],
    }
