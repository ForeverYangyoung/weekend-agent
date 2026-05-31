"""搜索策略生成器 — 纯规则，不调用 LLM。

根据 Profiler 产出的画像字段（scene / interests / dietary / duration）
推导应搜哪些品类、避开哪些品类。

这是业务规则层，不应放在 Prompt 里。
"""

from backend.schemas import GroupProfile, SearchStrategy

# ── 场景 → 玩品类 ──

_SCENE_PLAY_MAP: dict[str, list[str]] = {
    "family": ["亲子", "儿童乐园", "动物体验馆", "儿童科学馆", "公园"],
    "friends": ["活动", "剧本杀", "密室", "展览", "citywalk", "酒吧"],
    "couple": ["展览", "citywalk", "景点", "公园"],
    "solo": ["景点", "展览", "citywalk", "活动"],
    "unknown": ["景点", "活动", "亲子"],
}

# ── 场景 → 吃品类 ──

_SCENE_FOOD_MAP: dict[str, list[str]] = {
    "family": ["餐厅", "亲子餐厅"],
    "friends": ["餐厅", "火锅", "烤肉"],
    "couple": ["餐厅"],
    "solo": ["餐厅", "轻食"],
    "unknown": ["餐厅"],
}

# ── 兴趣 → 品类映射 ──

_INTEREST_TO_CATEGORY: dict[str, str] = {
    "亲子": "亲子",
    "展览": "展览",
    "citywalk": "citywalk",
    "剧本杀": "剧本杀",
    "户外": "公园",
}

# ── 饮食偏好 → 吃品类 ──

_DIETARY_TO_FOOD: dict[str, str] = {
    "低卡": "轻食",
    "不辣": "清淡餐厅",
    "素食": "素食",
}


def build_search_strategy(profile: GroupProfile) -> SearchStrategy:
    """根据画像生成搜索策略 — 纯规则，零 LLM 调用。

    推导逻辑：
      玩品类 = 场景默认 + 兴趣命中前置
      吃品类 = 场景默认 + 饮食偏好命中前置
      可选   = 时长 ≥ 4h 则加「加餐」
      避开   = 与场景冲突的品类（如 family 避开酒吧）
    """
    scene = profile.scene

    # ── 玩 ──
    play = list(_SCENE_PLAY_MAP.get(scene, ["景点"]))
    for interest in profile.interests:
        cat = _INTEREST_TO_CATEGORY.get(interest)
        if cat and cat not in play:
            play.insert(0, cat)

    # ── 吃 ──
    food = list(_SCENE_FOOD_MAP.get(scene, ["餐厅"]))
    for d in profile.dietary:
        cat = _DIETARY_TO_FOOD.get(d)
        if cat and cat not in food:
            food.insert(0, cat)

    # ── 可选加餐 ──
    optional: list[str] = []
    if profile.duration_hours >= 4:
        optional = ["加餐"]

    # ── 避开 ──
    avoid: list[str] = []
    if scene == "family":
        avoid.extend(["酒吧", "剧本杀", "密室"])
    elif scene == "couple":
        avoid.extend(["亲子", "儿童乐园"])

    return SearchStrategy(
        play_categories=play,
        food_categories=food,
        optional_categories=optional,
        avoid_categories=avoid,
    )
