"""Compensator 节点：发生失败时回滚已成功的 Tool，并清空方案触发重规划。

设计原则：
- 已成功的 ToolCall 调用对应 cancel_* Tool 进行幂等回滚
- 把 failed 阶段记入 plan_iteration，回到 Planner 用备选/重规划
"""
from __future__ import annotations

from weekend_agent.schemas import ToolStatus
from weekend_agent.state import AgentState


def compensator_node(state: AgentState) -> dict:
    executed = state.get("executed_calls", []) or []
    failed = state.get("failed_calls", []) or []

    rolled_back = 0
    for call in executed:
        # Stub：把已成功的标记为已回滚（生产版会真调用 cancel_* Tool）
        if call.status == ToolStatus.OK:
            call.status = ToolStatus.ROLLED_BACK
            rolled_back += 1

    return {
        # 回滚完成后清空，让重规划干净
        "executed_calls": [],
        "dry_run_calls": [],
        "failed_calls": failed,  # 保留失败信息让 Planner 知道避开哪些 POI
        "trace": [
            f"[Compensator] 回滚 {rolled_back} 笔成功订单 ↩，失败原因: "
            + "; ".join(f.error or "?" for f in failed)
        ],
    }
