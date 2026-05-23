"""Critic 节点：LLM 自我反思方案是否覆盖所有约束。

Stub 版本：用规则检查 dietary / interests / distance，凑齐就 approved。
真版本会让 LLM 输出 CriticFeedback JSON。
"""
from __future__ import annotations

from backend.roles import trace_line
from backend.schemas import CriticFeedback, CriticIssue
from backend.state import AgentState


def critic_node(state: AgentState) -> dict:
    profile = state.get("group_profile")
    plan = state.get("plan")
    issues: list[CriticIssue] = []

    if profile and plan:
        # 1. 饮食约束覆盖
        if "低卡" in profile.dietary:
            eats = [s for s in plan.stages if s.name == "吃"]
            if eats and "轻食" not in eats[0].primary.name and "沙拉" not in eats[0].primary.name:
                issues.append(
                    CriticIssue(
                        severity="warn",
                        field="stages[吃].primary",
                        message="餐厅未明显覆盖低卡需求",
                    )
                )

        # 2. 亲子兴趣覆盖
        if "亲子" in profile.interests:
            plays = [s for s in plan.stages if s.name == "玩"]
            if plays and "亲子" not in plays[0].primary.category and "公园" not in plays[0].primary.name:
                issues.append(
                    CriticIssue(
                        severity="block",
                        field="stages[玩].primary",
                        message="家庭场景下未给出亲子友好活动",
                    )
                )

        # 3. 阶段完整性
        if len(plan.stages) < 2:
            issues.append(
                CriticIssue(
                    severity="block",
                    field="stages",
                    message="方案阶段过少（至少应包含 玩 + 吃）",
                )
            )

    approved = not any(i.severity == "block" for i in issues)
    feedback = CriticFeedback(approved=approved, issues=issues)

    return {
        "critic_feedback": feedback,
        "trace": [
            trace_line(
                "Planner",
                f"approved={approved} issues={len(issues)} "
                + ("✓" if approved else "✗ 触发重规划"),
                phase="校验",
            )
        ],
    }
