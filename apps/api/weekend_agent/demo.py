"""CLI 演示入口。

用法：
    python -m weekend_agent.demo                       # 默认家庭场景
    python -m weekend_agent.demo --scene friends       # 朋友场景
    python -m weekend_agent.demo --fail 吃              # 注入"吃"阶段失败，演示补偿链
"""
from __future__ import annotations

import argparse
import json
import sys

# Windows 默认 GBK 码页对 ¥ 等字符会崩溃，统一切到 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from weekend_agent.graph import agent_graph
from weekend_agent.state import AgentState


# legacy_windows=False 让 rich 走 ANSI/VT 序列，配合 PowerShell 7 / Windows Terminal 显示中文
console = Console(legacy_windows=False, force_terminal=True)


SCENES = {
    "family": (
        "今天下午是空的，想和老婆孩子出去玩几个小时，"
        "别离家太远，老婆最近在减肥，孩子 5 岁，帮我安排一下。"
    ),
    "friends": (
        "下午想和 4 个朋友（2 男 2 女）一起出去玩几个小时，"
        "找点有意思的活动配个晚饭，帮我安排一下。"
    ),
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--scene", choices=list(SCENES), default="family")
    p.add_argument(
        "--fail",
        choices=["玩", "吃", "加餐"],
        default=None,
        help="模拟某阶段下单失败，演示补偿链",
    )
    p.add_argument("--input", default=None, help="自定义用户输入，覆盖 --scene")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    user_input = args.input or SCENES[args.scene]

    console.print(Rule("[bold cyan]Weekend Agent · 周末活动规划"))
    console.print(Panel(user_input, title="用户输入", border_style="cyan"))
    if args.fail:
        console.print(f"[yellow]⚠ 已注入失败开关：'{args.fail}' 阶段会下单失败\n")

    initial_state: AgentState = {
        "user_input": user_input,
        "trace": [],
    }
    if args.fail:
        initial_state["force_failure"] = args.fail

    final_state: AgentState = agent_graph.invoke(initial_state)  # type: ignore[arg-type]

    # ── 打印追踪链路 ──
    console.print(Rule("[bold]执行链路"))
    for line in final_state.get("trace", []):
        console.print(f"  {line}")

    # ── 打印行程卡 ──
    card = final_state.get("summary_card")
    if card:
        console.print(Rule("[bold]最终行程卡"))
        console.print(Markdown(card.body_markdown))
        console.print()
        console.print(Panel(card.share_text, title="可分享文案", border_style="green"))

    # ── 调试用：dump 关键状态 ──
    console.print(Rule("[dim]State 摘要 (debug)"))
    summary = {
        "scene": (final_state.get("group_profile").scene if final_state.get("group_profile") else None),
        "plan_iteration": final_state.get("plan_iteration"),
        "executed": len(final_state.get("executed_calls", []) or []),
        "failed": len(final_state.get("failed_calls", []) or []),
    }
    console.print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
