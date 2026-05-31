"""Route Insertion Engine — 判断新需求是否顺路。

给定当前 plan 路线 + 新意图（品类），估算：
  - 绕路时间（分钟）
  - 最佳插入位置（stage 下标）

规则优先，不调用 LLM。
"""

from __future__ import annotations

from backend.planner.constants import ADDON_AFTER, ADDON_BETWEEN, MAX_DETOUR_MIN
from backend.schemas import Plan


def find_insertion_slot(plan: Plan, category: str) -> int:
    """返回新 stage 应插入的下标位置。

    ADDON_BETWEEN（奶茶/咖啡/小吃/冰淇淋）→ 玩和吃之间
    ADDON_AFTER（蛋糕/甜品/花）→ 吃之后
    其余 → 玩和吃之间（有玩和吃）或末尾
    """
    has_play = any(s.name == "玩" for s in plan.stages)
    has_food = any(s.name == "吃" for s in plan.stages)

    if category in ADDON_AFTER and has_food:
        for i, s in enumerate(plan.stages):
            if s.name == "吃":
                return i + 1
        return len(plan.stages)

    if has_play and has_food:
        play_idx = next(i for i, s in enumerate(plan.stages) if s.name == "玩")
        food_idx = next(i for i, s in enumerate(plan.stages) if s.name == "吃")
        return min(play_idx, food_idx) + 1

    if has_play:
        play_idx = next(i for i, s in enumerate(plan.stages) if s.name == "玩")
        return play_idx + 1

    return len(plan.stages)


def estimate_detour(plan: Plan, category: str) -> float:
    """估算插入一个品类后的绕路时间（分钟）。"""
    if category in ADDON_BETWEEN:
        return 3.0
    if category in ADDON_AFTER:
        return 7.0 if category != "花" else 8.0
    return 8.0


def is_on_route(plan: Plan, category: str, max_detour_min: float = MAX_DETOUR_MIN) -> bool:
    """判断品类是否可顺路插入。"""
    return estimate_detour(plan, category) <= max_detour_min
