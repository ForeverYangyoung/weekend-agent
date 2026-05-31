"""PlanPatcher 节点：薄适配层，业务在 `backend.agents.planner`。

应用 PlanPatch 列表 → 产出修订后 Plan + PlanSnapshot + PlanEvent。
"""
from __future__ import annotations

from datetime import datetime

from backend.agents.planner import revise_plan
from backend.schemas import PlanPatch, PlanSnapshot
from backend.roles import trace_line
from backend.state import AgentState


def plan_patcher_node(state: AgentState) -> dict:
    plan = state.get("plan")
    profile = state.get("group_profile")
    patches_raw = state.get("revision_patches", []) or []
    feedback = state.get("user_feedback", "")
    revision_round = state.get("revision_round", 0)

    if not patches_raw or not plan or not profile:
        return {
            "trace": [
                trace_line("Planner", "跳过：无补丁可应用", phase="打补丁")
            ],
        }

    patches = [PlanPatch(**p) for p in patches_raw]
    locked = plan.locked_stages

    revised, events = revise_plan(plan, patches, profile, locked_stages=locked)

    now = datetime.utcnow().isoformat()
    snapshot = PlanSnapshot(
        version=plan.version,
        plan=plan.model_copy(deep=True),
        created_at=now,
        parent_version=None,
        event_summary=feedback,
    )

    result: dict = {
        "plan_snapshots": [snapshot.model_dump(mode="json")],
        "user_feedback": "",
    }

    if revised:
        revised_snapshot = PlanSnapshot(
            version=revised.version,
            plan=revised.model_copy(deep=True),
            created_at=now,
            parent_version=plan.version,
            event_summary="; ".join(e.summary for e in events),
        )
        result["plan"] = revised
        result["plan_snapshots"] = [
            snapshot.model_dump(mode="json"),
            revised_snapshot.model_dump(mode="json"),
        ]
        result["plan_events"] = [e.model_dump(mode="json") for e in events]

        event_text = " | ".join(e.summary for e in events)
        result["trace"] = [
            trace_line(
                "Planner",
                f"应用补丁成功 (v{revised.version}): {event_text}",
                phase="打补丁",
            )
        ]
    else:
        result["plan_snapshots"] = [snapshot.model_dump(mode="json")]
        result["plan_events"] = [e.model_dump(mode="json") for e in events]
        result["trace"] = [
            trace_line(
                "Planner",
                "应用补丁失败：校验不通过，保持原方案",
                phase="打补丁",
            )
        ]

    return result
