"""Revision 节点：薄适配层，业务在 `backend.agents.revision`。

解析用户反馈 → PlanPatch 列表。
"""
from __future__ import annotations

from backend.agents.revision import parse_feedback_to_patches
from backend.roles import trace_line
from backend.state import AgentState


def revision_node(state: AgentState) -> dict:
    feedback = state.get("user_feedback", "").strip()
    plan = state.get("plan")
    current_round = state.get("revision_round", 0)

    if not feedback or not plan:
        return {
            "revision_patches": [],
            "trace": [
                trace_line("Planner", "跳过：无反馈或无方案", phase="修订")
            ],
        }

    patches = parse_feedback_to_patches(feedback, plan)
    new_round = current_round + 1

    patch_summary = "; ".join(
        f"{p.target}/{p.action}" + (f"({p.category})" if p.category else "")
        for p in patches
    ) if patches else "无匹配规则"

    return {
        "revision_patches": [p.model_dump(mode="json") for p in patches],
        "revision_round": new_round,
        "trace": [
            trace_line(
                "Planner",
                f"解析反馈 (round {new_round}): \"{feedback[:50]}\" → [{patch_summary}]",
                phase="修订",
            )
        ],
    }
