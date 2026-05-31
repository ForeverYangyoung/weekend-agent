"""Revision Agent：把用户自然语言反馈转成结构化的 PlanPatch 列表。

P0：关键词 + 正则；规则命中直接返回。
P1：零命中时 LLM fallback（用 revision_agent_system prompt）。

与 profiler.py 对齐：规则优先，LLM 只兜底。
"""

from __future__ import annotations

import re

from backend.planner.constants import ADDON_AFTER, ADDON_BETWEEN
from backend.schemas import Plan, PlanPatch

# ── 动作关键词 ──

_REPLACE_KEYS = ("换", "换成", "改成", "改", "换一个", "换一下", "换个")
_INSERT_KEYS = ("加个", "再加", "加一杯", "加个", "顺路", "顺道", "买杯", "买", "多一个", "多来")
_REMOVE_KEYS = ("不要", "删", "去掉", "取消", "不去", "算了", "别要")
_LOCK_KEYS = ("别动", "保留", "很好", "不动", "不用改", "不用换", "留下", "挺好的")
_REORDER_PATTERN = re.compile(r"先\s*(吃|玩)\s*后\s*(吃|玩)")

# ── 目标关键词 ──

_PLAY_KEYS = ("玩", "活动", "地方", "景点", "公园")
_FOOD_KEYS = ("吃", "餐厅", "饭", "馆", "火锅", "日料", "烤肉", "料理")
_ADDON_KEYS: dict[str, str] = {
    "奶茶": "奶茶",
    "咖啡": "咖啡",
    "蛋糕": "蛋糕",
    "花": "花",
    "冰淇淋": "冰淇淋",
    "甜品": "甜品",
    "小吃": "小吃",
}

_ADDON_TARGET_KEYS = ("加餐",) + tuple(ADDON_BETWEEN | ADDON_AFTER)

# ── 约束提取 ──

_CONSTRAINT_NEG = re.compile(r"(?:不要|避免|别去|别吃|不吃|排除)\s*(\S+)")
_CONSTRAINT_POS = re.compile(r"(?:(?<!不)要|想要|想吃|改成)\s*(\S+)")


def _hit_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(k in text for k in keywords)


def _find_target(text: str) -> str | None:
    """从文本中识别目标阶段。"""
    # addon 优先（品类词 / "加餐" 更具体）
    if _hit_any(text, _ADDON_TARGET_KEYS):
        return "addon"
    if _hit_any(text, _FOOD_KEYS):
        return "food"
    if _hit_any(text, _PLAY_KEYS):
        return "play"
    return None


def _find_action(text: str) -> str | None:
    """从文本中识别动作类型。优先级：reorder > replace > insert > lock > remove。"""
    if _REORDER_PATTERN.search(text):
        return "reorder"
    if _hit_any(text, _REPLACE_KEYS):
        return "replace"
    if _hit_any(text, _INSERT_KEYS):
        return "insert"
    if _hit_any(text, _LOCK_KEYS):
        return "lock"
    if _hit_any(text, _REMOVE_KEYS):
        return "remove"
    return None


def _extract_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    for m in _CONSTRAINT_NEG.finditer(text):
        constraints.append(f"不要{m.group(1)}")
    for m in _CONSTRAINT_POS.finditer(text):
        constraints.append(f"要{m.group(1)}")
    return constraints


def _find_category(text: str) -> str | None:
    for kw, cat in _ADDON_KEYS.items():
        if kw in text:
            return cat
    return None


def _split_clauses(text: str) -> list[str]:
    """按逗号/句号/分号拆分子句，每句独立解析。"""
    return [s.strip() for s in re.split(r"[，,。；;、]", text) if s.strip()]


def parse_feedback_to_patches(
    feedback: str,
    plan: Plan | None = None,
) -> list[PlanPatch]:
    """将用户自然语言反馈解析为 PlanPatch 列表。

    规则优先：关键词命中直接返回。零命中时走 LLM fallback。
    """
    feedback = feedback.strip()
    if not feedback:
        return []

    clauses = _split_clauses(feedback)
    patches: list[PlanPatch] = []

    for clause in clauses:
        action = _find_action(clause)
        target = _find_target(clause)

        if action is None and target is None:
            # 无关键词命中 — 整句尝试整体解析
            action = _find_action(feedback)
            target = _find_target(feedback)
            if action is None:
                # LLM fallback would go here, but for P0: skip
                continue

        if action is None:
            action = "replace"  # 默认：提到目标但没说动作 = 想换

        if target is None:
            target = "food"  # 默认：提到动作但没指目标 = 大概率在说餐厅

        constraints = _extract_constraints(clause)
        category = _find_category(clause) if action == "insert" else None

        patches.append(
            PlanPatch(
                target=target,
                action=action,
                constraints=constraints,
                category=category,
            )
        )

    # 去重
    seen: set[tuple[str, str]] = set()
    unique: list[PlanPatch] = []
    for p in patches:
        key = (p.target, p.action)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique
