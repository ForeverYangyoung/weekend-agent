"""DryRun 节点：根据 Plan 生成 Tool 调用清单并做"占位调用"。

占位 = 只查询 / 占座 / 校验库存，不真扣款不真锁定。
真实 Tool 调用在 Executor 节点。下一步会接 tools/registry.py。
"""
from __future__ import annotations

from uuid import uuid4

from weekend_agent.schemas import ToolCall, ToolStatus
from weekend_agent.state import AgentState


def _plan_to_calls(plan) -> list[ToolCall]:
    """Plan → ToolCall 列表的简单映射。"""
    calls: list[ToolCall] = []
    for stage in plan.stages:
        if stage.name == "玩":
            calls.append(
                ToolCall(
                    id=f"tc_{uuid4().hex[:8]}",
                    stage_name=stage.name,
                    tool_name="check_activity_availability",
                    args={"poi_id": stage.primary.poi_id, "start": stage.start_time},
                )
            )
        elif stage.name == "吃":
            calls.append(
                ToolCall(
                    id=f"tc_{uuid4().hex[:8]}",
                    stage_name=stage.name,
                    tool_name="check_table_availability",
                    args={
                        "poi_id": stage.primary.poi_id,
                        "ppl": 4,
                        "time": stage.start_time,
                    },
                )
            )
        elif stage.name == "加餐":
            calls.append(
                ToolCall(
                    id=f"tc_{uuid4().hex[:8]}",
                    stage_name=stage.name,
                    tool_name="check_addon_stock",
                    args={"poi_id": stage.primary.poi_id},
                )
            )
    return calls


def dry_run_node(state: AgentState) -> dict:
    plan = state.get("plan")
    if not plan:
        return {"dry_run_calls": [], "trace": ["[DryRun] 跳过：无 plan"]}

    calls = _plan_to_calls(plan)
    # Stub：默认全部 OK；下一步 registry 接入后会真调用 Mock Tool
    for c in calls:
        c.status = ToolStatus.OK
        c.result = {"ok": True, "stub": True}

    return {
        "dry_run_calls": calls,
        "trace": [f"[DryRun] 占位调用 {len(calls)} 个 Tool，全部可执行 ✓"],
    }
