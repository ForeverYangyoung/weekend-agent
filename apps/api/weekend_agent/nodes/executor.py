"""Executor 节点：用户确认后，真实并行触发下单/订位/送花。

Stub：把 DryRun 的 ToolCall 拷一份当作"已执行"，标 OK；
注入一个可控失败开关用于演示补偿链（state["force_failure"]）。
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from weekend_agent.schemas import ToolCall, ToolStatus
from weekend_agent.state import AgentState


def executor_node(state: AgentState) -> dict:
    dry_calls = state.get("dry_run_calls", [])
    if not dry_calls:
        return {"executed_calls": [], "failed_calls": [], "trace": ["[Executor] 无可执行项"]}

    # 演示用：开关一打开，模拟"吃"阶段下单失败，触发补偿链
    force_failure: str | None = state.get("force_failure")  # type: ignore[assignment]

    executed: list[ToolCall] = []
    failed: list[ToolCall] = []

    real_tool_map = {
        "check_activity_availability": "buy_ticket",
        "check_table_availability": "book_table",
        "check_addon_stock": "order_addon",
    }

    for dc in dry_calls:
        call = ToolCall(
            id=f"tc_{uuid4().hex[:8]}",
            stage_name=dc.stage_name,
            tool_name=real_tool_map.get(dc.tool_name, dc.tool_name),
            args=dc.args,
            started_at=datetime.utcnow(),
        )

        if force_failure and dc.stage_name == force_failure:
            call.status = ToolStatus.FAILED
            call.error = f"模拟失败：{dc.stage_name} 阶段商家无库存"
            call.finished_at = datetime.utcnow()
            failed.append(call)
        else:
            call.status = ToolStatus.OK
            call.result = {"order_id": f"M{uuid4().hex[:10].upper()}", "stub": True}
            call.finished_at = datetime.utcnow()
            executed.append(call)

    return {
        "executed_calls": executed,
        "failed_calls": failed,
        "trace": [
            f"[Executor] 成功 {len(executed)} 笔 ✓"
            + (f"，失败 {len(failed)} 笔 ✗" if failed else "")
        ],
    }
