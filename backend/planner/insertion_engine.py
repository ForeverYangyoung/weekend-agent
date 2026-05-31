"""顺路插入过滤器 — 纯规则，不调用 LLM。

规则筛选：场景匹配 / 时长 ≤ 15min / 预算允许 / 路线绕路 ≤ 10min。
筛完后只送 LLM 生成 display 文案。
"""

from backend.planner.state import InsertableBehavior, RouteInsertion

# ── 场景 → 可接受的行为 ID ──

_SCENE_ACCEPT: dict[str, set[str]] = {
    "family": {"bubble_tea", "cake", "photo", "restroom", "snack", "souvenir"},
    "friends": {"bubble_tea", "coffee", "snack", "photo", "souvenir"},
    "couple": {"bubble_tea", "coffee", "flower", "photo", "snack"},
    "solo": {"coffee", "snack", "photo", "souvenir"},
}

# ── 预算下限：低于此则不允许加（单位：元/人）──

_MIN_BUDGET_FOR_INSERTION = 50


def filter_insertions(
    catalog: list[InsertableBehavior],
    scene: str,
    budget_per_person: int | None = None,
) -> list[InsertableBehavior]:
    """规则初筛可插入行为。

    返回通过筛选的行为列表（未通过的直接丢弃）。
    剩余行为由 LLM 仅负责生成 display / reason 文案。

    筛选规则：
      1. 场景不匹配 → 丢弃（如 family 不送 flower）
      2. 时长 > 15min → 丢弃
      3. 预算不足 → 丢弃（人均预算 < 行为成本 × 2）
    """
    accepted_ids = _SCENE_ACCEPT.get(scene, set())
    if not accepted_ids:
        accepted_ids = _SCENE_ACCEPT["family"]

    passed: list[InsertableBehavior] = []
    for b in catalog:
        # 1. 场景匹配
        if b.id not in accepted_ids:
            continue

        # 2. 时长限制
        if b.duration_min > 15:
            continue

        # 3. 预算检查（行为成本不应超过人均预算的一半）
        if budget_per_person is not None and budget_per_person > 0:
            if b.cost > budget_per_person * 0.5:
                continue

        passed.append(b)

    return passed


def _find_position(
    behavior: InsertableBehavior,
    stage_names: list[str],
) -> str:
    """根据行为类型推断最佳插入位置。"""
    category = behavior.category

    # 餐饮小食 → 玩和吃之间
    if category == "餐饮小食":
        if "吃" in stage_names:
            return "吃之前"
        return "玩和吃之间"

    # 礼物 → 吃之前（如取蛋糕）/ 结束后（如取花）
    if category == "礼物":
        return "吃之前" if "吃" in stage_names else "结束后"

    # 纪念 → 结束后
    if category == "纪念":
        return "结束后"

    # 休闲 → 玩和吃之间
    return "玩和吃之间"


def build_insertion_display(
    behavior: InsertableBehavior,
    stage_names: list[str],
) -> str:
    """生成默认 display 文案（规则兜底，LLM 开启时会被覆盖）。"""
    templates: dict[str, str] = {
        "bubble_tea": "顺路买杯奶茶解渴",
        "coffee": "顺路带杯咖啡提神",
        "flower": "取一束鲜花，增添仪式感",
        "cake": "取预定的蛋糕",
        "photo": "拍张合照留个纪念",
        "souvenir": "顺路逛逛文创店",
        "snack": "路过小吃摊随手买点",
        "restroom": "找个洗手间稍作休整",
    }
    return templates.get(behavior.id, f"顺路{behavior.name}")
