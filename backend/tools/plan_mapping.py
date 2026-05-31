"""把 Planner 产出的 Plan 翻译成 DryRun 要「打听」的 Tool 列表。"""
from __future__ import annotations

from uuid import uuid4

from backend.planner.constants import READ_TOOL, READ_TO_WRITE
from backend.schemas import Plan, ToolCall


def plan_to_dry_run_calls(plan: Plan, *, people: int = 4) -> list[ToolCall]:
    """根据方案每个阶段，生成对应的「只查询、不下单」Tool。"""
    calls: list[ToolCall] = []
    for stage in plan.stages:
        tool_name = READ_TOOL.get(stage.name)
        if tool_name is None:
            continue

        args: dict = {"poi_id": stage.primary.poi_id}
        if stage.name == "玩":
            args["start"] = stage.start_time
        elif stage.name == "吃":
            args["people"] = people
            args["time"] = stage.start_time

        calls.append(ToolCall(
            id=f"tc_{uuid4().hex[:8]}",
            stage_name=stage.name,
            tool_name=tool_name,
            args=args,
        ))
    return calls
