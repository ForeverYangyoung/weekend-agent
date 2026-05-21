"""FastAPI：SSE 流式推送 Agent 状态（供前端 fetch 流式读取）。"""
from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from weekend_agent.graph import agent_graph
from weekend_agent.mock_meituan import mock_router
from weekend_agent.state import AgentState
from weekend_agent.tools.http_client import current_mode

_PLAYGROUND_HTML = Path(__file__).resolve().parent / "static" / "playground.html"


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """启动时在终端打印测试页地址，避免只打开 `/` 却以为没有网页。"""
    mode, base = current_mode()
    print(
        "\n[weekend-agent] 浏览器流式测试: http://127.0.0.1:8000/playground\n"
        "[weekend-agent] API 文档: http://127.0.0.1:8000/docs\n"
        f"[weekend-agent] Mock 美团: mode={mode} base_url={base} "
        "(同进程也挂在 /mock-meituan/*, curl http://127.0.0.1:8000/mock-meituan/health 验证)\n",
        flush=True,
    )
    yield


app = FastAPI(
    title="Weekend Agent API",
    version="0.1.0",
    lifespan=_lifespan,
    description="含浏览器测试页：`GET /playground`；根路径 `GET /` 会重定向到测试页。",
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

# 把假美团 API 同时挂在主服务下，方便评委直接 `curl http://127.0.0.1:8000/mock-meituan/...`
app.include_router(mock_router, prefix="/mock-meituan")


def _json_safe(obj: Any) -> Any:
    """把 State / Pydantic / Enum 等转成可 JSON 序列化的结构。"""
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


class StreamAgentRequest(BaseModel):
    user_input: str = Field(..., min_length=1, max_length=8000)
    force_failure: Literal["玩", "吃", "加餐"] | None = None


def _run_stream(req: StreamAgentRequest) -> Iterator[str]:
    initial: AgentState = {
        "user_input": req.user_input.strip(),
        "trace": [],
    }
    if req.force_failure:
        initial["force_failure"] = req.force_failure

    yield _sse_line(
        {
            "event": "start",
            "user_input": initial["user_input"],
            "force_failure": req.force_failure,
        }
    )

    try:
        last: AgentState | None = None
        for state in agent_graph.stream(initial, stream_mode="values"):  # type: ignore[arg-type]
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

        gp = last.get("group_profile")
        scene = gp.scene if gp is not None else None
        yield _sse_line(
            {
                "event": "final",
                "summary": {
                    "scene": scene,
                    "plan_iteration": last.get("plan_iteration"),
                    "executed": len(last.get("executed_calls", []) or []),
                    "failed": len(last.get("failed_calls", []) or []),
                },
                "summary_card": _json_safe(last.get("summary_card")),
            }
        )
        yield _sse_line({"event": "done"})
    except Exception as e:  # noqa: BLE001 —— 流式接口需把异常写入 SSE
        yield _sse_line({"event": "error", "message": str(e)})


@app.get("/")
def root() -> RedirectResponse:
    """浏览器打开服务根路径即可进入流式测试页。"""
    return RedirectResponse(url="/playground", status_code=307)


@app.get("/ui")
def ui_shortcut() -> RedirectResponse:
    """短路径，等价于 `/playground`。"""
    return RedirectResponse(url="/playground", status_code=307)


@app.get("/ground")
def ground_typo_redirect() -> RedirectResponse:
    """常见笔误 `/ground` → 自动跳到测试页 `/playground`。"""
    return RedirectResponse(url="/playground", status_code=307)


@app.get("/playground")
def playground() -> FileResponse:
    """单页：输入一句话 + 可选失败注入，实时看 SSE trace。"""
    if not _PLAYGROUND_HTML.is_file():
        raise HTTPException(status_code=404, detail="playground.html 缺失")
    return FileResponse(
        _PLAYGROUND_HTML,
        media_type="text/html; charset=utf-8",
        filename="playground.html",
    )


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查；若响应里没有 `playground` 字段，说明进程加载的是旧代码，请重启服务并 `pip install -e .`。"""
    mode, base = current_mode()
    return {
        "status": "ok",
        "playground": "/playground",
        "playground_shortcuts": "/ui,/ground",
        "stream": "/v1/agent/stream",
        "stream_alt": "/agent/stream",
        "mock_meituan_mode": mode,
        "mock_meituan_base_url": base,
        "mock_meituan_mounted": "/mock-meituan",
    }


def _stream_agent_response(req: StreamAgentRequest) -> StreamingResponse:
    if not req.user_input.strip():
        raise HTTPException(status_code=400, detail="user_input 不能为空")

    return StreamingResponse(
        _run_stream(req),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/v1/agent/stream")
def stream_agent(req: StreamAgentRequest) -> StreamingResponse:
    return _stream_agent_response(req)


@app.post("/agent/stream")
def stream_agent_short_path(req: StreamAgentRequest) -> StreamingResponse:
    """与 `POST /v1/agent/stream` 行为完全一致；兼容 Swagger/前端里未带 `v1` 的路径。"""
    return _stream_agent_response(req)
