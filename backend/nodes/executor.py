"""Executor 节点：在 DryRun 通过后「真下单」（走假后台 Mock）。

- 读 Tool（DryRun）→ 写 Tool（Executor）的对应关系见 `tools/plan_mapping.READ_TO_WRITE_TOOL`
- `state["force_failure"]` = 阶段名（如 "吃"）时，该阶段写操作返回满座/售罄
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from backend.roles import trace_line
from backend.schemas import ToolCall, ToolStatus
from backend.state import AgentState
from backend.tools import ToolContext, ToolError, invoke
from backend.tools.plan_mapping import READ_TO_WRITE_TOOL


def _run_write_call(
    dry: ToolCall,
    *,
    ctx: ToolContext,
    idempotency_key: str,
) -> ToolCall:
    write_name = READ_TO_WRITE_TOOL.get(dry.tool_name, dry.tool_name)
    args = dict(dry.args)
    args["idempotency_key"] = idempotency_key
    if write_name == "buy_ticket":
        args.setdefault("count", args.get("people", 2))

    call = ToolCall(
        id=f"tc_{uuid4().hex[:8]}",
        stage_name=dry.stage_name,
        tool_name=write_name,
        args=args,
        started_at=datetime.utcnow(),
    )
    try:
        call.result = invoke(
            write_name,
            args,
            ctx=ToolContext(
                force_failure_stage=ctx.force_failure_stage,
                idempotency_key=idempotency_key,
            ),
            stage_name=dry.stage_name,
        )
        call.status = ToolStatus.OK
    except ToolError as e:
        call.status = ToolStatus.FAILED
        call.error = e.message
        call.result = {"code": e.code, **e.details}
    call.finished_at = datetime.utcnow()
    return call


def executor_node(state: AgentState) -> dict:
    dry_calls = state.get("dry_run_calls", [])
    if not dry_calls:
        return {
            "executed_calls": [],
            "failed_calls": [],
            "trace": [trace_line("Executor", "无可执行项", phase="提交")],
        }

    # 只执行 DryRun 里已经打听成功的项
    runnable = [c for c in dry_calls if c.status == ToolStatus.OK]
    skipped = len(dry_calls) - len(runnable)

    ctx = ToolContext(force_failure_stage=state.get("force_failure"))
    run_id = uuid4().hex[:8]

    executed: list[ToolCall] = []
    failed: list[ToolCall] = []

    for dry in runnable:
        idem = f"run_{run_id}_{dry.stage_name}_{dry.tool_name}"
        call = _run_write_call(dry, ctx=ctx, idempotency_key=idem)
        if call.status == ToolStatus.OK:
            executed.append(call)
        else:
            failed.append(call)

    msg = f"成功 {len(executed)} 笔"
    if failed:
        msg += f"，失败 {len(failed)} 笔 ✗"
    if skipped:
        msg += f"，跳过预检未通过 {skipped} 项"
    elif not failed:
        msg += " ✓"

    return {
        "executed_calls": executed,
        "failed_calls": failed,
        "trace": [trace_line("Executor", msg, phase="提交")],
    }
