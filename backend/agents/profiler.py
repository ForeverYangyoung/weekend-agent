"""Profiler Agent：把一句自然语言转成结构化 GroupProfile。

P0：规则 + 正则；为每个字段给出置信度 + 可编辑标签 + 证据链，对齐 02.架构 §3。
P1：可在调用方按 `use_llm` 切到 LLM Function Calling，输出仍是 GroupProfile。

节点 `nodes/profiler.py` 只做 state 适配，业务全部在这里。
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from backend.planner.strategy_builder import build_search_strategy
from backend.schemas import EditableTag, GroupProfile, PlanningPreferences, ProfileEvidence

# ─────────────────────────── 关键词表 ───────────────────────────

_FAMILY_KEYWORDS = (
    "老婆", "老公", "孩子", "娃", "宝宝", "孩", "一家", "亲子",
    "儿子", "女儿", "妈妈", "爸爸",
)
_FRIENDS_KEYWORDS = ("朋友", "哥们", "闺蜜", "同事", "同学", "搭子")
_COUPLE_KEYWORDS = ("对象", "女朋友", "男朋友", "约会", "情侣", "二人世界")

_LOW_CAL_KEYWORDS = ("减肥", "低卡", "轻食", "沙拉", "控糖", "减脂", "健康餐")
_NO_SPICY_KEYWORDS = ("不辣", "微辣", "清淡")

# 兴趣标签 → 命中关键词
_INTEREST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "亲子": ("亲子", "儿童", "宝宝", "娃"),
    "展览": ("展览", "美术馆", "博物馆", "艺术展"),
    "citywalk": ("citywalk", "逛街", "散步", "随便逛"),
    "剧本杀": ("剧本杀", "密室"),
    "户外": ("公园", "户外", "露营", "骑行"),
}

_NEAR_HINTS = ("别太远", "不要远", "近点", "别离家太远", "附近", "周边")
_AFTERNOON_HINTS = ("下午", "饭后", "下午茶")
_EVENING_HINTS = ("晚上", "晚饭", "夜里", "晚餐")
_MORNING_HINTS = ("上午", "早上", "早饭")

# 中文小数字 → 阿拉伯数字
_CN_DIGIT: dict[str, int] = {
    "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

# 中文常见「人数说法」短语 → (人数, 触发词)
_PEOPLE_PHRASES: tuple[tuple[str, int], ...] = (
    ("一家三口", 3),
    ("一家四口", 4),
    ("一家五口", 5),
    ("两口子", 2),
    ("两口", 2),
    ("我们俩", 2),
    ("俩人", 2),
    ("我俩", 2),
    ("我们三个", 3),
    ("三人行", 3),
    ("我们四个", 4),
)

# 预算正则：「人均 200」「预算 300」「300 元/人」
_BUDGET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"人均\s*(\d+)"), "人均"),
    (re.compile(r"预算\s*(?:每人)?\s*(\d+)"), "预算"),
    (re.compile(r"(\d+)\s*(?:元|块)?\s*/\s*人"), "元/人"),
)


# ── 群体行为特征：场景 → 风格偏好默认值 ──

_SCENE_STYLE_DEFAULTS: dict[str, dict[str, list[str]]] = {
    "family": {
        "restaurant_style": ["family_friendly", "value_for_money", "low_wait_time", "safe_dining"],
        "activity_style": ["kid_friendly", "safe", "educational", "hands_on"],
        "route_style": ["efficient", "minimal_walking", "rest_stops_available"],
    },
    "friends": {
        "restaurant_style": ["social_gathering", "casual", "trendy", "value_for_money"],
        "activity_style": ["social", "immersive", "group_friendly", "fun_oriented"],
        "route_style": ["flexible", "clustered", "transit_friendly"],
    },
    "couple": {
        "restaurant_style": ["romantic", "photogenic", "private", "fine_dining"],
        "activity_style": ["romantic", "photogenic", "immersive", "ritual_oriented"],
        "route_style": ["scenic", "leisurely", "photogenic", "walkable"],
    },
    "solo": {
        "restaurant_style": ["casual", "quick", "value_for_money", "solo_friendly"],
        "activity_style": ["relaxed", "self_paced", "contemplative", "flexible"],
        "route_style": ["efficient", "flexible", "walkable"],
    },
}

# ── 文本关键词增强：在场景默认值之上追加的风格标签 ──

_STYLE_HINTS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "restaurant_style": (
        ("低卡", ("healthy", "light_fare")),
        ("减肥", ("healthy", "light_fare")),
        ("小资", ("trendy", "photogenic")),
        ("网红", ("trendy", "photogenic")),
        ("安静", ("quiet", "private")),
        ("包间", ("private",)),
        ("快餐", ("quick", "casual")),
    ),
    "activity_style": (
        ("拍照", ("photogenic",)),
        ("打卡", ("photogenic", "trendy")),
        ("安静", ("contemplative", "relaxed")),
        ("刺激", ("adventurous",)),
        ("学习", ("educational",)),
        ("动手", ("hands_on",)),
        ("出片", ("photogenic",)),
        ("仪式感", ("ritual_oriented",)),
    ),
    "route_style": (
        ("随便逛", ("flexible", "walkable")),
        ("不赶时间", ("leisurely",)),
        ("一条线", ("efficient", "clustered")),
        ("不绕", ("efficient", "clustered")),
        ("风景", ("scenic",)),
        ("拍照", ("photogenic", "scenic")),
    ),
}

# ─────────────────────────── 工具函数 ───────────────────────────


def _hits(text: str, keywords) -> list[str]:
    return [k for k in keywords if k in text]


def _conf_by_hits(n: int, *, low: float = 0.55, mid: float = 0.82, high: float = 0.92) -> float:
    if n >= 2:
        return high
    if n == 1:
        return mid
    return low


# ─────────────────────────── 各维度推理 ───────────────────────────


def _infer_scene(text: str) -> tuple[str, float, list[str]]:
    """返回 (scene, confidence, 触发词列表)。"""
    cpl = _hits(text, _COUPLE_KEYWORDS)
    text_for_friends = text
    for kw in cpl:
        text_for_friends = text_for_friends.replace(kw, "")
    fam = _hits(text, _FAMILY_KEYWORDS)
    fri = _hits(text_for_friends, _FRIENDS_KEYWORDS)

    priority = {"family": 3, "couple": 2, "friends": 1}
    ranked = sorted(
        [
            ("family", len(fam), fam),
            ("couple", len(cpl), cpl),
            ("friends", len(fri), fri),
        ],
        key=lambda x: (x[1], priority[x[0]]),
        reverse=True,
    )
    scene, n, terms = ranked[0]
    if n == 0:
        return "solo", 0.55, []
    return scene, _conf_by_hits(n), terms


def _infer_people(text: str, scene: str) -> tuple[int, float, str]:
    """优先级：阿拉伯数字 > 短语表 > 单字中文 > 场景默认。返回 (n, conf, term)。"""
    m = re.search(r"(\d+)\s*(?:个人|人)", text)
    if m:
        return int(m.group(1)), 0.95, m.group(0)

    for phrase, n in _PEOPLE_PHRASES:
        if phrase in text:
            return n, 0.92, phrase

    for ch, n in _CN_DIGIT.items():
        if f"{ch}个人" in text or f"{ch}人" in text:
            return n, 0.85, f"{ch}人"

    defaults = {"family": (3, 0.6, "default-family"), "friends": (4, 0.6, "default-friends"),
                "couple": (2, 0.7, "default-couple")}
    return defaults.get(scene, (1, 0.5, "default-solo"))


def _infer_kids_ages(text: str, scene: str) -> tuple[list[int], list[str]]:
    if scene != "family":
        return [], []
    matches = list(re.finditer(r"(\d+)\s*岁", text))
    if not matches:
        return [], []
    return [int(m.group(1)) for m in matches[:3]], [m.group(0) for m in matches[:3]]


def _infer_start_time(text: str) -> tuple[str | None, float, str]:
    m = re.search(r"(下午|晚上|早上|中午|上午)\s*(\d+)\s*点", text)
    if m:
        period, hour = m.group(1), int(m.group(2))
        if period in ("下午", "晚上") and hour < 12:
            hour += 12
        return f"{hour:02d}:00", 0.9, m.group(0)

    m = re.search(r"(\d+)\s*点", text)
    if m:
        return f"{int(m.group(1)):02d}:00", 0.75, m.group(0)

    aft = _hits(text, _AFTERNOON_HINTS)
    if aft:
        return "14:00", 0.7, aft[0]
    eve = _hits(text, _EVENING_HINTS)
    if eve:
        return "18:00", 0.7, eve[0]
    mor = _hits(text, _MORNING_HINTS)
    if mor:
        return "09:00", 0.7, mor[0]
    return None, 0.4, ""


def _infer_duration(text: str) -> tuple[float, float, str]:
    m = re.search(r"(\d+)\s*小时", text)
    if m:
        return float(m.group(1)), 0.9, m.group(0)
    if "几个小时" in text:
        return 5.0, 0.75, "几个小时"
    if "下午" in text:
        return 5.0, 0.65, "下午"
    return 4.0, 0.5, "default"


def _infer_distance(text: str) -> tuple[float, float, str]:
    near = _hits(text, _NEAR_HINTS)
    if near:
        return 8.0, 0.85, near[0]
    return 10.0, 0.5, "default"


def _infer_dietary(text: str) -> tuple[list[str], list[tuple[str, str, float]]]:
    """返回 (tags, evidence_tuples)；evidence_tuples = (value, term, conf)。"""
    tags: list[str] = []
    ev: list[tuple[str, str, float]] = []
    low_hits = _hits(text, _LOW_CAL_KEYWORDS)
    if low_hits:
        tags.append("低卡")
        ev.append(("低卡", low_hits[0], 0.85))
    no_spicy = _hits(text, _NO_SPICY_KEYWORDS)
    if no_spicy:
        tags.append("不辣")
        ev.append(("不辣", no_spicy[0], 0.85))
    return tags, ev


def _infer_interests(
    text: str, scene: str, kids_ages: list[int]
) -> tuple[list[str], list[tuple[str, str, float]]]:
    text_low = text.lower()
    tags: list[str] = []
    ev: list[tuple[str, str, float]] = []
    if scene == "family" and kids_ages:
        tags.append("亲子")
        ev.append(("亲子", f"scene=family+kids={kids_ages}", 0.85))
    for tag, kws in _INTEREST_KEYWORDS.items():
        if tag in tags:
            continue
        for k in kws:
            if k.lower() in text_low:
                tags.append(tag)
                ev.append((tag, k, 0.8))
                break
    return tags, ev


def _infer_budget(text: str) -> tuple[int | None, float, str]:
    for pat, label in _BUDGET_PATTERNS:
        m = pat.search(text)
        if m:
            return int(m.group(1)), 0.9, f"{label}={m.group(0)}"
    return None, 0.4, ""


def _infer_planning_preferences(
    text: str,
    scene: str,
    kids_ages: list[int],
    dietary: list[str],
    interests: list[str],
) -> PlanningPreferences:
    """场景默认值 + 文本关键词增强 → PlanningPreferences。

    不涉及具体搜索类别；只描述群体的行为风格偏好。
    """
    defaults = _SCENE_STYLE_DEFAULTS.get(scene, _SCENE_STYLE_DEFAULTS["solo"])
    result: dict[str, list[str]] = {
        k: list(v) for k, v in defaults.items()
    }

    # 文本关键词增强
    for dim in ("restaurant_style", "activity_style", "route_style"):
        for kw, tags in _STYLE_HINTS.get(dim, ()):
            if kw in text:
                for t in tags:
                    if t not in result[dim]:
                        result[dim].append(t)

    # 幼儿增强：有 ≤5 岁孩子 → 强化安全/低等待/休息站
    if kids_ages and min(kids_ages) <= 5:
        for tag, dim in [
            ("safe_dining", "restaurant_style"),
            ("low_wait_time", "restaurant_style"),
            ("safe", "activity_style"),
            ("rest_stops_available", "route_style"),
        ]:
            if tag not in result[dim]:
                result[dim].append(tag)

    # 饮食偏好增强
    if "低卡" in dietary:
        for tag in ("healthy", "light_fare"):
            if tag not in result["restaurant_style"]:
                result["restaurant_style"].append(tag)

    # 兴趣增强
    if "亲子" in interests:
        for tag in ("kid_friendly", "educational"):
            if tag not in result["activity_style"]:
                result["activity_style"].append(tag)
    if "户外" in interests:
        for tag in ("outdoor", "scenic"):
            if tag not in result["activity_style"]:
                result["activity_style"].append(tag)

    return PlanningPreferences(
        restaurant_style=result["restaurant_style"],
        activity_style=result["activity_style"],
        route_style=result["route_style"],
    )


# ─────────────────────────── 历史偏好融合 ───────────────────────────


def _build_history_weights(history: Mapping[str, Any]) -> dict[str, float]:
    """把历史 dict 汇总成 {tag: weight}，weight 归一化到 [0,1]，top-5。"""
    counter: dict[str, float] = {}
    for src in ("tag_counts", "cuisine_counts", "category_counts"):
        for k, v in (history.get(src) or {}).items():
            if not isinstance(k, str) or not isinstance(v, (int, float)) or v <= 0:
                continue
            counter[k] = counter.get(k, 0.0) + float(v)
    # favorite_tags 视作命中 3 次（明示偏好权重最高）
    for t in history.get("favorite_tags") or []:
        if isinstance(t, str):
            counter[t] = counter.get(t, 0.0) + 3.0

    if not counter:
        return {}
    top = sorted(counter.items(), key=lambda x: -x[1])[:5]
    max_v = top[0][1] or 1.0
    return {k: round(v / max_v, 3) for k, v in top}


def _merge_history(
    profile: GroupProfile, history: Mapping[str, Any], evidence: list[ProfileEvidence]
) -> None:
    weights = _build_history_weights(history)
    profile.history_weights = weights
    for tag, w in weights.items():
        if w >= 0.55 and tag not in profile.interests:
            profile.interests.append(tag)
            evidence.append(
                ProfileEvidence(
                    field="interests",
                    value=tag,
                    term=f"history(w={w:.2f})",
                    confidence=min(0.9, 0.5 + w / 2),
                    source="history",
                )
            )


# ─────────────────────────── 可编辑标签 ───────────────────────────


_SCENE_LABEL = {
    "family": "家庭",
    "friends": "朋友",
    "couple": "情侣",
    "solo": "独自",
    "unknown": "未识别",
}


def _build_editable_tags(profile: GroupProfile, has_history: bool) -> list[EditableTag]:
    tags: list[EditableTag] = [
        EditableTag(
            key="scene",
            label=_SCENE_LABEL.get(profile.scene, profile.scene),
            value=profile.scene,
            confidence=profile.confidence.get("scene", 0.5),
            source="utterance",
        ),
        EditableTag(
            key="people_count",
            label=f"{profile.people_count} 人",
            value=str(profile.people_count),
            confidence=profile.confidence.get("people_count", 0.5),
            source="utterance",
        ),
        EditableTag(
            key="distance_limit_km",
            label=f"≤ {profile.distance_limit_km:.0f} km",
            value=f"{profile.distance_limit_km}",
            confidence=profile.confidence.get("distance_limit_km", 0.5),
            source="utterance",
        ),
        EditableTag(
            key="duration_hours",
            label=f"约 {profile.duration_hours:.0f} 小时",
            value=f"{profile.duration_hours}",
            confidence=profile.confidence.get("duration_hours", 0.5),
            source="utterance",
        ),
    ]
    if profile.kids_ages:
        tags.append(
            EditableTag(
                key="kids_ages",
                label="孩子 " + "、".join(f"{a}岁" for a in profile.kids_ages),
                value=",".join(str(a) for a in profile.kids_ages),
                confidence=0.9,
                source="utterance",
            )
        )
    if profile.start_time:
        tags.append(
            EditableTag(
                key="start_time",
                label=f"{profile.start_time} 出发",
                value=profile.start_time,
                confidence=profile.confidence.get("start_time", 0.5),
                source="utterance",
            )
        )
    if profile.budget_per_person is not None:
        tags.append(
            EditableTag(
                key="budget_per_person",
                label=f"约 ¥{profile.budget_per_person}/人",
                value=str(profile.budget_per_person),
                confidence=profile.confidence.get("budget_per_person", 0.5),
                source="utterance",
            )
        )
    for d in profile.dietary:
        tags.append(
            EditableTag(
                key="dietary",
                label=d,
                value=d,
                confidence=profile.confidence.get("dietary", 0.7),
                source="utterance",
            )
        )
    for i in profile.interests:
        is_from_history = has_history and i in profile.history_weights
        tags.append(
            EditableTag(
                key="interests",
                label=i + ("（历史）" if is_from_history else ""),
                value=i,
                confidence=profile.confidence.get("interests", 0.7),
                source="history" if is_from_history else "utterance",
            )
        )
    return tags


# ─────────────────────────── 入口 ───────────────────────────


def analyze_profile(
    text: str,
    *,
    history_context: Mapping[str, Any] | None = None,
) -> GroupProfile:
    """规则引擎抽取群体画像。

    Args:
        text: 用户一句话。
        history_context: 可选历史上下文（`favorite_tags` / `tag_counts` /
            `cuisine_counts` / `category_counts`）。
    """
    text = text or ""
    profile = GroupProfile(raw_text=text)
    evidence: list[ProfileEvidence] = []

    scene, scene_conf, scene_terms = _infer_scene(text)
    profile.scene = scene
    profile.confidence["scene"] = scene_conf
    if scene_terms or scene != "solo":
        evidence.append(
            ProfileEvidence(
                field="scene",
                value=scene,
                term="/".join(scene_terms) if scene_terms else "default",
                confidence=scene_conf,
                source="utterance" if scene_terms else "rule",
            )
        )

    people, people_conf, people_term = _infer_people(text, scene)
    profile.people_count = people
    profile.confidence["people_count"] = people_conf
    evidence.append(
        ProfileEvidence(
            field="people_count",
            value=str(people),
            term=people_term,
            confidence=people_conf,
            source="utterance" if not people_term.startswith("default") else "rule",
        )
    )

    kids_ages, kids_terms = _infer_kids_ages(text, scene)
    profile.kids_ages = kids_ages
    if kids_ages:
        evidence.append(
            ProfileEvidence(
                field="kids_ages",
                value=",".join(str(a) for a in kids_ages),
                term="/".join(kids_terms),
                confidence=0.9,
                source="utterance",
            )
        )

    start_time, st_conf, st_term = _infer_start_time(text)
    profile.start_time = start_time
    profile.confidence["start_time"] = st_conf
    if start_time:
        evidence.append(
            ProfileEvidence(
                field="start_time",
                value=start_time,
                term=st_term,
                confidence=st_conf,
                source="utterance",
            )
        )

    duration, du_conf, du_term = _infer_duration(text)
    profile.duration_hours = duration
    profile.confidence["duration_hours"] = du_conf
    evidence.append(
        ProfileEvidence(
            field="duration_hours",
            value=f"{duration}",
            term=du_term,
            confidence=du_conf,
            source="utterance" if du_term != "default" else "rule",
        )
    )

    distance, dist_conf, dist_term = _infer_distance(text)
    profile.distance_limit_km = distance
    profile.confidence["distance_limit_km"] = dist_conf
    evidence.append(
        ProfileEvidence(
            field="distance_limit_km",
            value=f"{distance}",
            term=dist_term,
            confidence=dist_conf,
            source="utterance" if dist_term != "default" else "rule",
        )
    )

    dietary, diet_ev = _infer_dietary(text)
    profile.dietary = dietary
    profile.confidence["dietary"] = 0.85 if dietary else 0.5
    for value, term, conf in diet_ev:
        evidence.append(
            ProfileEvidence(
                field="dietary", value=value, term=term,
                confidence=conf, source="utterance",
            )
        )

    interests, int_ev = _infer_interests(text, scene, profile.kids_ages)
    profile.interests = interests
    profile.confidence["interests"] = 0.8 if interests else 0.5
    for value, term, conf in int_ev:
        evidence.append(
            ProfileEvidence(
                field="interests", value=value, term=term,
                confidence=conf, source="utterance",
            )
        )

    budget, bud_conf, bud_term = _infer_budget(text)
    profile.budget_per_person = budget
    profile.confidence["budget_per_person"] = bud_conf
    if budget is not None:
        evidence.append(
            ProfileEvidence(
                field="budget_per_person", value=str(budget), term=bud_term,
                confidence=bud_conf, source="utterance",
            )
        )

    planning_prefs = _infer_planning_preferences(
        text, scene, profile.kids_ages, profile.dietary, profile.interests,
    )
    profile.planning_preferences = planning_prefs

    profile.search_strategy = build_search_strategy(profile)

    has_history = bool(history_context)
    if has_history:
        _merge_history(profile, history_context, evidence)

    profile.evidence = evidence
    profile.editable_tags = _build_editable_tags(profile, has_history=has_history)
    return profile
