"""FastAPI：SSE 流式推送 Agent 状态 + 前端静态资源（python app.py 一把启动）。"""
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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.graph import agent_graph
from backend.mock_meituan import mock_router
from backend.state import AgentState
from backend.tools.http_client import current_mode

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PLAYGROUND_HTML = _PROJECT_ROOT / "frontend" / "playground.html"
_FRONTEND_DIST = _PROJECT_ROOT / "frontend-v2" / "dist"
_FRONTEND_ASSETS = _FRONTEND_DIST / "assets"


FRONTEND_AVAILABLE = _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").is_file()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """启动时在终端打印访问地址。"""
    mode, base = current_mode()
    url = "http://127.0.0.1:8000"
    print(
        f"\n  {'─' * 45}\n"
        f"  Weekend Agent 启动成功\n"
        f"  {'─' * 45}\n"
        f"  前端页面:     {url}/\n"
        f"  API 文档:     {url}/docs\n"
        f"  旧版测试页:   {url}/playground\n"
        f"  {'─' * 45}\n"
        f"  前端来源: {'frontend-v2/dist/' if FRONTEND_AVAILABLE else 'frontend/playground.html'}\n"
        f"  Mock 美团: mode={mode} base_url={base}\n",
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


@app.get("/", response_model=None)
def root() -> FileResponse | RedirectResponse:
    """根路径 → 新版前端（若有构建产物），否则回退到旧版测试页。"""
    if FRONTEND_AVAILABLE:
        return FileResponse(
            str(_FRONTEND_DIST / "index.html"),
            media_type="text/html; charset=utf-8",
        )
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
        str(_PLAYGROUND_HTML),
        media_type="text/html; charset=utf-8",
    )


@app.get("/health")
def health() -> dict[str, object]:
    """健康检查。"""
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


if FRONTEND_AVAILABLE:
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_ASSETS)), name="assets")

    @app.get("/favicon.svg")
    def favicon() -> FileResponse:
        return FileResponse(str(_FRONTEND_DIST / "favicon.svg"))