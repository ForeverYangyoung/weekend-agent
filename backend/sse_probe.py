"""本地 SSE 探针：调 /v1/agent/stream 并把每一帧漂亮地打出来。

用途：
- 演示 FastAPI 流式接口，避免 PowerShell 的 curl 别名和 GBK 乱码坑。
- 也方便接前端前，先在终端看到完整 event 时序。

用法：
    python -m weekend_agent.sse_probe --input "下午两个人随便逛逛"
    python -m weekend_agent.sse_probe --input "下午带老婆孩子出去玩" --fail 吃
    python -m weekend_agent.sse_probe --url http://127.0.0.1:8000/v1/agent/stream --input "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.request import Request, urlopen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.rule import Rule

console = Console(legacy_windows=False, force_terminal=True)


DEFAULT_URL = "http://127.0.0.1:8000/v1/agent/stream"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--input", required=True, help="一句话用户输入")
    p.add_argument(
        "--fail",
        choices=["玩", "吃", "加餐"],
        default=None,
        help="模拟某阶段下单失败，演示补偿链",
    )
    p.add_argument(
        "--show-state",
        action="store_true",
        help="逐帧打印完整 state（默认只打印 trace 增量）",
    )
    return p.parse_args()


def _iter_sse(resp: Any):
    """从 HTTP 响应里按 SSE 协议（空行分隔）拆出每条 data。"""
    buf = ""
    for chunk in iter(lambda: resp.read(1024), b""):
        if not chunk:
            break
        buf += chunk.decode("utf-8", errors="replace")
        while "\n\n" in buf:
            block, buf = buf.split("\n\n", 1)
            for line in block.splitlines():
                if line.startswith("data: "):
                    yield line[6:]


def main() -> None:
    args = parse_args()

    body = {"user_input": args.input}
    if args.fail:
        body["force_failure"] = args.fail

    console.print(Rule("[bold cyan]SSE Probe"))
    console.print(Panel.fit(args.url, title="endpoint", border_style="cyan"))
    console.print(Panel.fit(args.input, title="user_input", border_style="cyan"))
    if args.fail:
        console.print(f"[yellow]⚠ 注入失败开关：{args.fail}\n")

    req = Request(
        args.url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )

    seen_trace = 0
    try:
        with urlopen(req, timeout=120) as resp:
            for raw in _iter_sse(resp):
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    console.print(f"[red]非 JSON 帧：{raw}")
                    continue

                ev = msg.get("event", "?")
                if ev == "start":
                    console.print(f"[bold green]▶ start[/]  input={msg.get('user_input')!r}")
                elif ev == "state":
                    state = msg.get("state", {}) or {}
                    trace = state.get("trace", []) or []
                    for line in trace[seen_trace:]:
                        console.print(f"  [dim]·[/] {line}")
                    seen_trace = len(trace)
                    if args.show_state:
                        console.print(Rule("[dim]full state"))
                        console.print(JSON.from_data(state))
                elif ev == "final":
                    console.print(Rule("[bold]final"))
                    console.print(JSON.from_data(msg.get("summary", {})))
                    card = msg.get("summary_card")
                    if card:
                        console.print(Panel(card.get("share_text", ""), title=card.get("title", ""), border_style="green"))
                elif ev == "done":
                    console.print("[bold green]✓ done")
                elif ev == "error":
                    console.print(f"[bold red]✗ error[/] {msg.get('message')}")
                else:
                    console.print(f"[magenta]{ev}[/] {msg}")
    except (ConnectionRefusedError, OSError) as e:
        console.print(f"[red]连不上 {args.url}：{e}")
        console.print("提示：先在另一个终端启动 [bold]python -m weekend_agent[/]。")
        sys.exit(2)


if __name__ == "__main__":
    main()
