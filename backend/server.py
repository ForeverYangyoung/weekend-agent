"""FastAPI：SSE 流式推送 Agent 状态 + HIL 确认/重规划 + 前端静态资源。"""
from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.graph import (
    dry_run_recovery_graph,
    execution_graph,
    planning_graph,
    replan_graph,
)
from backend.schemas import ToolStatus
from backend.hil import (
    BUILD_VERSION,
    build_plans_payload,
    create_session,
    get_session,
    profile_chips,
    save_session,
    select_plan,
)
from backend.mock_meituan import mock_router
from backend.state import AgentState
from backend.tools.http_client import current_mode

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_DIST = _PROJECT_ROOT / "frontend-v2" / "dist"
_FRONTEND_ASSETS = _FRONTEND_DIST / "assets"

FRONTEND_AVAILABLE = _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").is_file()

_BUILD_HINT = (
    "前端未构建。请在项目根目录执行：\n"
    "  cd frontend-v2 && npm install && npm run build\n"
    "或直接运行 python app.py（会自动尝试构建）。"
)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    mode, base = current_mode()
    url = "http://127.0.0.1:8000"
    frontend_line = f"  前端页面:     {url}/" if FRONTEND_AVAILABLE else f"  前端页面:     （未构建，见 README）"
    print(
        f"\n  {'─' * 45}\n"
        f"  Weekend Agent 启动成功\n"
        f"  {'─' * 45}\n"
        f"{frontend_line}\n"
        f"  API 文档:     {url}/docs\n"
        f"  HIL 确认:     POST /v1/agent/confirm\n"
        f"  HIL 重规划:   POST /v1/agent/replan\n"
        f"  {'─' * 45}\n"
        f"  Mock 美团: mode={mode} base_url={base}\n",
        flush=True,
    )
    yield


app = FastAPI(
    title="Weekend Agent API",
    version="0.1.0",
    lifespan=_lifespan,
    description="周末活动规划 Agent：SSE + HIL 人机协同。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mock_router, prefix="/mock-meituan")


def _json_safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, str | int | float | bool):
        return obj
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_json_safe(v) for v in obj]
    return str(obj)


def _sse_line(payload: dict[str, Any]) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


class ProfileOverrideItem(BaseModel):
    key: str
    value: str = ""
    action: Literal["add", "remove", "set"] = "set"


class StreamAgentRequest(BaseModel):
    user_input: str = Field(..., min_length=1, max_length=8000)
    force_failure: Literal["玩", "吃", "加餐"] | None = None


class ReplanAgentRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=32)
    overrides: list[ProfileOverrideItem] = Field(default_factory=list)
    note: str | None = None


class ConfirmAgentRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=32)
    plan_id: str = "primary"


def _run_planning_stream(
    graph,
    initial: AgentState,
    *,
    session_id: str | None = None,
    is_replan: bool = False,
) -> Iterator[str]:
    yield _sse_line(
        {
            "event": "start",
            "user_input": initial.get("user_input", ""),
            "session_id": session_id,
            "replan": is_replan,
        }
    )

    try:
        last: AgentState | None = None
        for state in graph.stream(initial, stream_mode="values"):  # type: ignore[arg-type]
            last = state  # type: ignore[assignment]
            yield _sse_line(
                {
                    "event": "state",
                    "state": _json_safe(dict(state)),
                }
            )

        if last is None:
            yield _sse_line({"event": "error", "message": "未产生任何状态更新"})
            return

        # 预检满座等失败 → 自动从 Planner 换备选（HIL 展示前静默恢复）
        max_recover = get_settings().max_plan_iterations
        for _ in range(max_recover):
            dry_failed = any(
                c.status == ToolStatus.FAILED for c in (last.get("dry_run_calls") or [])
            )
            if not dry_failed:
                break
            last = dry_run_recovery_graph.invoke(last)  # type: ignore[arg-type]
            yield _sse_line(
                {
                    "event": "state",
                    "state": _json_safe(dict(last)),
                    "note": "dry_run_recovery",
                }
            )

        sid = session_id or create_session(last)
        save_session(sid, last)

        gp = last.get("group_profile")
        dry_runs = last.get("dry_run_calls") or []

        yield _sse_line(
            {
                "event": "awaiting_confirm",
                "session_id": sid,
                "summary": {
                    "scene": gp.scene if gp else None,
                    "plan_iteration": last.get("plan_iteration"),
                    "dry_run_ok": len(dry_runs),
                },
                "profile_chips": profile_chips(gp),
                "plans": build_plans_payload(last),
                "dry_run_calls": _json_safe(dry_runs),
                "message": "预检完成，请确认方案或点改偏好后重规划",
            }
        )
        yield _sse_line({"event": "done"})
    except Exception as e:  # noqa: BLE001
        yield _sse_line({"event": "error", "message": str(e)})


def _run_stream(req: StreamAgentRequest) -> Iterator[str]:
    initial: AgentState = {
        "user_input": req.user_input.strip(),
        "trace": [],
    }
    if req.force_failure:
        initial["force_failure"] = req.force_failure

    yield from _run_planning_stream(planning_graph, initial)


def _run_replan(req: ReplanAgentRequest) -> Iterator[str]:
    base = get_session(req.session_id)
    if base is None:
        yield _sse_line({"event": "error", "message": f"会话不存在: {req.session_id}"})
        return

    overrides = [o.model_dump() for o in req.overrides]
    if req.note and req.note.strip():
        base = dict(base)
        base["user_input"] = f"{base.get('user_input', '')}；{req.note.strip()}"

    initial: AgentState = {
        **base,
        "profile_overrides": overrides,
        "user_confirmed": False,
        "trace": list(base.get("trace") or []),
    }

    yield from _run_planning_stream(
        replan_graph,
        initial,
        session_id=req.session_id,
        is_replan=True,
    )


@app.get("/", response_model=None)
def root() -> FileResponse | HTMLResponse:
    if FRONTEND_AVAILABLE:
        return FileResponse(
            str(_FRONTEND_DIST / "index.html"),
            media_type="text/html; charset=utf-8",
        )
    return HTMLResponse(content=f"<pre>{_BUILD_HINT}</pre>", status_code=503)


@app.get("/health")
def health() -> dict[str, object]:
    mode, base = current_mode()
    return {
        "status": "ok",
        "build": BUILD_VERSION,
        "frontend": "/" if FRONTEND_AVAILABLE else "not_built",
        "stream": "/v1/agent/stream",
        "replan": "/v1/agent/replan",
        "confirm": "/v1/agent/confirm",
        "mock_meituan_mode": mode,
        "mock_meituan_base_url": base,
    }


@app.post("/v1/agent/confirm")
def confirm_agent(req: ConfirmAgentRequest) -> dict[str, object]:
    state = get_session(req.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"会话不存在: {req.session_id}")

    state = select_plan(state, req.plan_id)
    state = dict(state)
    state["user_confirmed"] = True

    try:
        final: AgentState = execution_graph.invoke(state)  # type: ignore[arg-type]
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e

    save_session(req.session_id, final)

    executed = final.get("executed_calls") or []
    orders = [
        {
            "stage": c.stage_name,
            "order_id": (c.result or {}).get("order_id"),
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
        }
        for c in executed
        if c.result and c.result.get("order_id")
    ]

    return {
        "status": "ok",
        "session_id": req.session_id,
        "plan_id": req.plan_id,
        "executed": len(executed),
        "failed": len(final.get("failed_calls") or []),
        "orders": orders,
        "summary_card": _json_safe(final.get("summary_card")),
        "trace_tail": (final.get("trace") or [])[-6:],
    }


def _stream_response(iterator: Iterator[str]) -> StreamingResponse:
    return StreamingResponse(
        iterator,
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/v1/agent/stream")
def stream_agent(req: StreamAgentRequest) -> StreamingResponse:
    if not req.user_input.strip():
        raise HTTPException(status_code=400, detail="user_input 不能为空")
    return _stream_response(_run_stream(req))


@app.post("/agent/stream")
def stream_agent_short_path(req: StreamAgentRequest) -> StreamingResponse:
    return stream_agent(req)


@app.post("/v1/agent/replan")
def replan_agent(req: ReplanAgentRequest) -> StreamingResponse:
    return _stream_response(_run_replan(req))


@app.post("/agent/replan")
def replan_agent_short_path(req: ReplanAgentRequest) -> StreamingResponse:
    return replan_agent(req)


if FRONTEND_AVAILABLE:
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_ASSETS)), name="assets")

    @app.get("/favicon.svg")
    def favicon() -> FileResponse:
        return FileResponse(str(_FRONTEND_DIST / "favicon.svg"))
