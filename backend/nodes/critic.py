"""Critic 节点：规则检查 + LLM 体验评审。

规则层检查硬约束（dietary / interests / 阶段完整性）。
LLM 从"人的感受"角度审查（节奏/衔接/场景匹配）。
"""
from __future__ import annotations

from backend.llm_client import chat_json, get_llm_client
from backend.prompts import (
    critic_feedback_system,
    critic_feedback_user,
    plan_to_text,
    profile_to_text,
)
from backend.roles import trace_line
from backend.schemas import CriticFeedback, CriticIssue
from backend.state import AgentState


def _rule_checks(profile, plan) -> list[CriticIssue]:
    """硬约束规则检查 — 确定性，零延迟。"""
    issues: list[CriticIssue] = []

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

    return issues


def _llm_review(profile, plan) -> list[CriticIssue]:
    """LLM 体验评审 — 从人的感受角度审查方案。"""
    client = get_llm_client()
    if client is None:
        return []

    result = chat_json(
        critic_feedback_system,
        critic_feedback_user.format(
            profile_text=profile_to_text(profile),
            plan_text=plan_to_text(plan),
        ),
        temperature=0.3,
        max_tokens=500,
    )

    if not isinstance(result, dict):
        return []

    raw_issues = result.get("issues", [])
    if not isinstance(raw_issues, list):
        return []

    issues: list[CriticIssue] = []
    for ri in raw_issues:
        if not isinstance(ri, dict):
            continue
        issues.append(
            CriticIssue(
                severity=ri.get("severity", "warn"),
                field=ri.get("field", "stages"),
                message=ri.get("message", ""),
            )
        )
    return issues


def critic_node(state: AgentState) -> dict:
    profile = state.get("group_profile")
    plan = state.get("plan")
    issues: list[CriticIssue] = []

    if profile and plan:
        # 规则层（硬约束）
        issues.extend(_rule_checks(profile, plan))

        # LLM 层（体验评审）
        llm_issues = _llm_review(profile, plan)
        if llm_issues:
            issues.extend(llm_issues)

    approved = not any(i.severity == "block" for i in issues)
    feedback = CriticFeedback(approved=approved, issues=issues)

    llm_tag = " +LLM" if get_llm_client() else ""
    return {
        "critic_feedback": feedback,
        "trace": [
            trace_line(
                "Planner",
                f"approved={approved} issues={len(issues)}{llm_tag} "
                + ("✓" if approved else "✗ 触发重规划"),
                phase="校验",
            )
        ],
    }
