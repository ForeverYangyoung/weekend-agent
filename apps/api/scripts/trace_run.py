"""按节点打印 LangGraph 每步的 state 增量（写 04 展示文档用）。

用法（在 apps/api 目录）：
    python scripts/trace_run.py
    python scripts/trace_run.py --fail 吃
"""
from __future__ import annotations

import argparse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

from weekend_agent.graph import agent_graph
from weekend_agent.state import AgentState

DEFAULT_INPUT = (
    "今天下午是空的，想和老婆孩子出去玩几个小时，"
    "别离家太远，老婆最近在减肥，孩子 5 岁，帮我安排一下。"
)


def _brief(obj, max_len: int = 800) -> str:
    if obj is None:
        return "null"
    if isinstance(obj, list):
        obj = [
            x.model_dump(mode="json") if hasattr(x, "model_dump") else x
            for x in obj
        ]
    elif hasattr(obj, "model_dump"):
        obj = obj.model_dump(mode="json")
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= max_len else s[:max_len] + "..."


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--fail", choices=["玩", "吃", "加餐"], default=None)
    p.add_argument("--input", default=DEFAULT_INPUT)
    args = p.parse_args()

    initial: AgentState = {"user_input": args.input, "trace": []}
    if args.fail:
        initial["force_failure"] = args.fail

    print("=== 全局输入 ===")
    print(json.dumps({"user_input": args.input, "force_failure": args.fail}, ensure_ascii=False, indent=2))
    print()

    for chunk in agent_graph.stream(initial, stream_mode="updates"):  # type: ignore[arg-type]
        for node, update in chunk.items():
            print(f"--- 节点: {node} ---")
            for k in sorted(update.keys()):
                if k == "trace":
                    for line in update.get("trace") or []:
                        print(f"  [trace] {line}")
                else:
                    print(f"  {k}: {_brief(update[k])}")
            print()


if __name__ == "__main__":
    main()
