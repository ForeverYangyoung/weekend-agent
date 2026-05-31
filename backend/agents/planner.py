"""Planner Agent：检索 + 过滤 + 打分 + 组合 → Top-K 方案。

职责（重构后）：
  1. 根据 UserProfile.search_strategy 检索候选（内部调 http_client.search_poi）
  2. 硬约束过滤
  3. 五维打分
  4. 阶段顺序枚举 + 时间轴构建
  5. 顺路活动（加餐）补全
  6. Top-K 排序输出
  7. 兜底：检索为空时回退到硬编码 stub

节点 `nodes/planner.py` 只做 state 适配；业务逻辑全部在这里。
"""
from __future__ import annotations

from copy import deepcopy

from backend.planner.constants import (
    ADDON_AFTER,
    ADDON_AFTER_EAT_OFFSET,
    ADDON_BETWEEN,
    DURATION_ADDON,
    DURATION_EAT,
    DURATION_PLAY,
    DURATION_TRANSIT,
    STAGE_CN2EN,
    STAGE_EN2CN,
)
from backend.planner.route_insertion import find_insertion_slot
from backend.planner.validator import validate_plan
from backend.schemas import (
    GroupProfile,
    Plan,
    PlanEvent,
    PlanPatch,
    PlanStage,
    POICandidate,
    ScoreBreakdown,
)
from backend.tools.errors import ToolError
from backend.tools.http_client import search_poi

# ─────────────────────────── 时间轴工具 ───────────────────────────

_TOP_K = 3

_WEIGHTS: dict[str, float] = {
    "preference": 0.35,
    "history": 0.20,
    "rating": 0.20,
    "distance": 0.15,
    "budget": 0.10,
}


def _shift(time_str: str, minutes: int) -> str:
    h, m = (int(x) for x in time_str.split(":", 1))
    total = (h * 60 + m + minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def _estimate_cost(people: int, stages: list[PlanStage]) -> int:
    total = 0
    for s in stages:
        price = int(s.primary.metadata.get("avg_price", 0) or 0)
        total += price if s.name == "加餐" else price * max(people, 1)
    return total


def _summary(scene: str, stages: list[PlanStage], order_label: str) -> str:
    names = " → ".join(s.primary.name for s in stages)
    label = {
        "family": "家庭周末",
        "friends": "朋友周末",
        "couple": "约会周末",
        "solo": "个人放松",
    }.get(scene, "周末安排")
    return f"{label}（{order_label}）：{names}"


# ─────────────────────────── 候选转换 ───────────────────────────


def _to_candidate(item: dict) -> POICandidate:
    return POICandidate(
        poi_id=item.get("poi_id", ""),
        name=item.get("name", ""),
        category=item.get("category", ""),
        score=float(item.get("score", 0.0) or 0.0),
        reason=item.get("reason", ""),
        metadata=dict(item.get("metadata") or {}),
    )


# ─────────────────────────── 五维打分 ───────────────────────────


def _hit_in_text(text_lower: str, candidates) -> int:
    return sum(1 for t in candidates if t and t.lower() in text_lower)


def _score_preference(c: POICandidate, profile: GroupProfile) -> float:
    target = set(profile.interests) | set(profile.dietary)
    if profile.scene == "family":
        target |= {"亲子", "儿童"}
    if profile.scene == "friends":
        target |= {"朋友", "聚餐"}
    if not target:
        return 0.5
    haystack = f"{c.name} {c.category} {c.reason}".lower()
    hits = _hit_in_text(haystack, target)
    return min(1.0, hits / max(len(target), 1) * 2)


def _score_history(c: POICandidate, profile: GroupProfile) -> float:
    if not profile.history_weights:
        return 0.5
    haystack = f"{c.name} {c.category} {c.reason}".lower()
    values = [
        w
        for tag, w in profile.history_weights.items()
        if tag and tag.lower() in haystack
    ]
    return max(values) if values else 0.3


def _score_rating(c: POICandidate) -> float:
    return max(0.0, min(c.score, 1.0))


def _score_distance(c: POICandidate, profile: GroupProfile) -> float:
    d = float(c.metadata.get("distance_km", 0) or 0)
    limit = max(profile.distance_limit_km, 1.0)
    return max(0.0, 1.0 - d / limit)


def _score_budget(c: POICandidate, profile: GroupProfile, stage_name: str) -> float:
    avg_price = float(c.metadata.get("avg_price", 0) or 0)
    budget = profile.budget_per_person
    if stage_name != "吃" or budget is None or avg_price <= 0:
        return 0.7
    if avg_price <= budget:
        return 1.0
    over_ratio = (avg_price - budget) / max(budget, 1)
    return max(0.0, 1.0 - over_ratio)


def _score_one(
    c: POICandidate, profile: GroupProfile, stage_name: str
) -> ScoreBreakdown:
    pref = _score_preference(c, profile)
    hist = _score_history(c, profile)
    rating = _score_rating(c)
    dist = _score_distance(c, profile)
    budget = _score_budget(c, profile, stage_name)
    total = (
        _WEIGHTS["preference"] * pref
        + _WEIGHTS["history"] * hist
        + _WEIGHTS["rating"] * rating
        + _WEIGHTS["distance"] * dist
        + _WEIGHTS["budget"] * budget
    )
    return ScoreBreakdown(
        preference=round(pref, 3),
        history=round(hist, 3),
        rating=round(rating, 3),
        distance=round(dist, 3),
        budget=round(budget, 3),
        total=round(total, 3),
    )


def _rank_and_filter(
    candidates: list[POICandidate], profile: GroupProfile, stage_name: str
) -> list[POICandidate]:
    kept: list[POICandidate] = []
    for c in candidates:
        if float(c.metadata.get("distance_km", 0) or 0) > profile.distance_limit_km:
            continue
        scored = c.model_copy(
            update={"breakdown": _score_one(c, profile, stage_name)}
        )
        kept.append(scored)

    if not kept:
        return []

    kept.sort(
        key=lambda x: (x.breakdown.total if x.breakdown else 0.0), reverse=True
    )
    return kept[:_TOP_K]


# ─────────────────────────── 硬过滤 ───────────────────────────

_KIDS_KEYS = ("亲子", "儿童", "公园", "童", "宝宝", "海洋馆")
_LOW_CAL_KEYS = ("轻食", "沙拉", "健康", "低卡", "蔬食")


def _candidate_text(c: POICandidate) -> str:
    return f"{c.name} {c.category} {c.reason}".lower()


def _passes_hard_filter(
    c: POICandidate, stage_name: str, profile: GroupProfile
) -> bool:
    text = _candidate_text(c)

    if stage_name == "玩" and profile.scene == "family" and profile.kids_ages:
        if not any(k.lower() in text for k in _KIDS_KEYS):
            return False

    if stage_name == "吃" and "低卡" in profile.dietary:
        if not any(k.lower() in text for k in _LOW_CAL_KEYS):
            return False

    d = float(c.metadata.get("distance_km", 0) or 0)
    if d > profile.distance_limit_km + 1e-6:
        return False

    return True


def _apply_hard_filters(
    candidates: list[POICandidate],
    profile: GroupProfile,
    stage_name: str,
    blocked: set[str],
) -> list[POICandidate]:
    kept = [
        c
        for c in candidates
        if c.poi_id not in blocked and _passes_hard_filter(c, stage_name, profile)
    ]
    if kept:
        return kept
    fallback = [c for c in candidates if c.poi_id not in blocked]
    return fallback or list(candidates)


# ─────────────────────────── 阶段顺序枚举 ───────────────────────────


def _determine_orders(profile: GroupProfile) -> list[tuple[str, ...]]:
    if not profile.start_time:
        return [("玩", "吃"), ("吃", "玩")]

    try:
        start_h = int(profile.start_time.split(":")[0])
    except (ValueError, IndexError):
        return [("玩", "吃"), ("吃", "玩")]

    # 基础规则排序
    if 11 <= start_h <= 13 or 17 <= start_h <= 19:
        orders = [("吃", "玩"), ("玩", "吃")]
    else:
        orders = [("玩", "吃"), ("吃", "玩")]

    # LLM 重新排序（基于更丰富的画像上下文）
    return _llm_rank_orders(profile, orders)


def _llm_rank_orders(
    profile: GroupProfile, orders: list[tuple[str, ...]]
) -> list[tuple[str, ...]]:
    """LLM-as-a-Judge：从候选顺序中选出最优。失败时回退到规则排序。"""
    from backend.llm_client import chat_json
    from backend.prompts import (
        profile_to_text,
        rank_timeline_orders_system,
        rank_timeline_orders_user,
    )

    result = chat_json(
        rank_timeline_orders_system,
        rank_timeline_orders_user.format(
            profile_text=profile_to_text(profile),
            candidates_text="\n".join(
                f"  {i+1}. {' → '.join(o)}" for i, o in enumerate(orders)
            ),
        ),
        temperature=0.2,
        max_tokens=200,
    )

    if not isinstance(result, dict):
        return orders

    best = result.get("best_order", [])
    if not isinstance(best, list) or len(best) < 2:
        return orders

    # 将 LLM 选中的顺序放在第一位，其余保持原顺序
    best_tuple = tuple(best)
    reordered = [best_tuple] if best_tuple in orders else []
    for o in orders:
        if o not in reordered:
            reordered.append(o)
    return reordered or orders


def _build_plan_with_order(
    profile: GroupProfile,
    play_pool: list[POICandidate],
    eat_pool: list[POICandidate],
    addon_pool: list[POICandidate] | None,
    blocked: set[str],
    order: tuple[str, ...],
    play_idx: int = 0,
    eat_idx: int = 0,
    addon_idx: int = 0,
) -> Plan | None:
    fp_play = _apply_hard_filters(play_pool, profile, "玩", blocked)
    fp_eat = _apply_hard_filters(eat_pool, profile, "吃", blocked)
    if not fp_play or not fp_eat:
        return None

    if play_idx >= len(fp_play) or eat_idx >= len(fp_eat):
        return None

    play = fp_play[play_idx]
    eat = fp_eat[eat_idx]

    start = profile.start_time or "14:00"
    cursor = start
    stage_objs: dict[str, PlanStage] = {}

    for name in order:
        if name == "玩":
            seg_start = cursor
            seg_end = _shift(seg_start, DURATION_PLAY)
            stage_objs["玩"] = PlanStage(
                name="玩",
                start_time=seg_start,
                end_time=seg_end,
                primary=play,
                backups=[c for c in fp_play if c.poi_id != play.poi_id],
                notes=play.reason,
            )
            cursor = _shift(seg_end, DURATION_TRANSIT)
        elif name == "吃":
            seg_start = cursor
            seg_end = _shift(seg_start, DURATION_EAT)
            stage_objs["吃"] = PlanStage(
                name="吃",
                start_time=seg_start,
                end_time=seg_end,
                primary=eat,
                backups=[c for c in fp_eat if c.poi_id != eat.poi_id],
                notes=eat.reason,
            )
            cursor = _shift(seg_end, DURATION_TRANSIT)

    # 加餐按品类智能定位
    if addon_pool:
        fp_addon = _apply_hard_filters(addon_pool, profile, "加餐", blocked)
        if fp_addon:
            addon = fp_addon[min(addon_idx, len(fp_addon) - 1)]
            category = addon.category
            # 奶茶/咖啡/小吃 → 玩和吃之间；蛋糕/甜品/花 → 吃之后
            if category in ADDON_AFTER and "吃" in stage_objs:
                addon_start = _shift(stage_objs["吃"].start_time, ADDON_AFTER_EAT_OFFSET)
            elif category in ADDON_BETWEEN and "玩" in stage_objs:
                addon_start = _shift(stage_objs["玩"].end_time, 5)
            elif "玩" in stage_objs and "吃" in stage_objs:
                addon_start = _shift(stage_objs["玩"].end_time, 5)  # 默认：玩和吃之间
            elif "玩" in stage_objs:
                addon_start = stage_objs["玩"].end_time
            elif "吃" in stage_objs:
                addon_start = _shift(stage_objs["吃"].start_time, ADDON_AFTER_EAT_OFFSET)
            else:
                addon_start = "14:30"
            stage_objs["加餐"] = PlanStage(
                name="加餐",
                start_time=addon_start,
                end_time=_shift(addon_start, DURATION_ADDON),
                primary=addon,
                notes=addon.reason,
            )

    final_stages = sorted(stage_objs.values(), key=lambda s: s.start_time)
    order_label = " → ".join(s.name for s in final_stages)
    plan = Plan(
        stages=final_stages,
        total_duration_hours=max(profile.duration_hours, 4.0),
        total_cost_estimate=_estimate_cost(profile.people_count, final_stages),
        order_label=order_label,
    )
    plan.summary = _summary(profile.scene, final_stages, order_label)
    plan.score = _plan_score(plan)
    return plan


def _plan_score(plan: Plan) -> float:
    if not plan.stages:
        return 0.0
    parts: list[float] = []
    for s in plan.stages:
        bd = s.primary.breakdown
        parts.append(bd.total if bd else 0.5)
    return round(sum(parts) / len(parts), 3)


# ─────────────────────────── 检索入口 ───────────────────────────


def _search_stage(
    scene: str, stage: str, limit: int = 10, category: str | None = None
) -> list[POICandidate]:
    """调 http_client.search_poi，转为 POICandidate 列表。

    category 非空时，mock 后端优先返回品类匹配的 POI（如「奶茶」→ 喜茶）。
    """
    try:
        raw = search_poi(scene=scene, stage=stage, limit=limit, category=category)
        return [_to_candidate(item) for item in raw]
    except ToolError:
        return []


# ─────────────────────────── Top-K 入口 ───────────────────────────


def build_plans(
    profile: GroupProfile,
    blocked: set[str] | None = None,
    *,
    top_k: int = 2,
) -> list[Plan]:
    """检索 → 打分 → 硬过滤 → 组合 → 排序 → 返回 Top-K 方案。

    Planner 内部完成全部检索与打分，不再依赖外部 Researcher。
    返回空列表时调用方应回退到 stub。
    """
    blocked = blocked or set()
    scene = profile.scene if profile.scene != "unknown" else "family"

    # 1. 检索玩 + 吃候选
    play_raw = _search_stage(scene, "玩")
    eat_raw = _search_stage(scene, "吃")

    if not play_raw or not eat_raw:
        return []

    # 2. 打分 + 距离过滤
    play_pool = _rank_and_filter(play_raw, profile, "玩")
    eat_pool = _rank_and_filter(eat_raw, profile, "吃")

    if not play_pool or not eat_pool:
        return []

    # 3. 检索加餐候选（长时间窗才搜）
    addon_pool: list[POICandidate] | None = None
    strategy = profile.search_strategy
    if strategy and strategy.optional_categories:
        addon_raw = _search_stage(scene, "加餐", limit=5)
        if addon_raw:
            addon_pool = _rank_and_filter(addon_raw, profile, "加餐")

    # 4. 枚举顺序 × 不同 POI 组合 → 构建多样方案
    plans: list[Plan] = []
    seen_signatures: set[tuple[str, str]] = set()
    orders = _determine_orders(profile)

    # 组合：(order_index, play_idx, eat_idx, addon_idx)
    combos: list[tuple[int, int, int, int]] = [
        (0, 0, 0, 0),                           # 主选：最优顺序，最优 POI
    ]
    if len(orders) > 1:
        combos.append((1, 0, 0, 0))             # 备选顺序 + 最优 POI
    if len(orders) > 1 and len(play_pool) > 1:
        combos.append((1, 1, 0, 0))             # 备选顺序 + 换玩
    if len(orders) > 1 and len(play_pool) > 1 and len(eat_pool) > 1:
        combos.append((1, 1, 1, 0))             # 备选顺序 + 全换（最大化差异）
    if len(orders) > 1 and len(eat_pool) > 1:
        combos.append((1, 0, 1, 0))             # 备选顺序 + 换吃
    if len(play_pool) > 1:
        combos.append((0, 1, 0, 0))             # 主顺序 + 换玩
    if len(eat_pool) > 1:
        combos.append((0, 0, 1, 0))             # 主顺序 + 换吃
    if addon_pool and len(addon_pool) > 1:
        combos.append((0, 0, 0, 1))             # 主顺序 + 换加餐

    def _poi_ids(plan: Plan) -> set[str]:
        return {s.primary.poi_id for s in plan.stages}

    for order_i, pi, ei, ai in combos:
        if order_i >= len(orders):
            continue
        if len(plans) >= top_k:
            break
        plan = _build_plan_with_order(
            profile, play_pool, eat_pool, addon_pool, blocked,
            orders[order_i], play_idx=pi, eat_idx=ei, addon_idx=ai,
        )
        if plan is None:
            continue
        sig = (plan.order_label, tuple(s.primary.poi_id for s in plan.stages))
        if sig in seen_signatures:
            continue
        # 跳过与已有方案 POI 完全相同的方案
        new_ids = _poi_ids(plan)
        if plans and any(new_ids == _poi_ids(existing) for existing in plans):
            continue
        # 硬约束校验：block 级问题直接淘汰
        vr = validate_plan(plan, profile)
        if not vr.passed:
            continue
        plan.validation = vr
        seen_signatures.add(sig)
        plans.append(plan)

    plans.sort(key=lambda p: p.score, reverse=True)
    return plans[:top_k]


# ─────────────────────────── 方案修订 ───────────────────────────


def _find_stage_index(plan: Plan, target: str) -> int | None:
    for i, s in enumerate(plan.stages):
        if target == "play" and s.name == "玩":
            return i
        if target == "food" and s.name == "吃":
            return i
        if target == "addon" and s.name == "加餐":
            return i
    return None


def _compact_timeline(stages: list[PlanStage], start_time: str) -> list[PlanStage]:
    """重算时间轴：紧凑排列所有 stage，不留空隙。"""
    cursor = start_time
    result: list[PlanStage] = []
    for s in sorted(stages, key=lambda x: x.start_time):
        dur = _time_diff_minutes(s.start_time, s.end_time)
        new_end = _shift(cursor, int(dur))
        result.append(
            PlanStage(
                name=s.name,
                start_time=cursor,
                end_time=new_end,
                primary=s.primary,
                backups=s.backups,
                notes=s.notes,
            )
        )
        cursor = _shift(new_end, DURATION_TRANSIT)
    return result


def _time_diff_minutes(start: str, end: str) -> float:
    h1, m1 = (int(x) for x in start.split(":", 1))
    h2, m2 = (int(x) for x in end.split(":", 1))
    return (h2 * 60 + m2) - (h1 * 60 + m1)


def replace_stage(
    plan: Plan,
    target: str,
    profile: GroupProfile,
    constraints: list[str] | None = None,
    blocked: set[str] | None = None,
) -> tuple[Plan, PlanEvent]:
    """重搜 target 阶段 POI，替换 primary。保留其余阶段不变。"""
    blocked = blocked or set()
    constraints = constraints or []
    scene = profile.scene if profile.scene != "unknown" else "family"
    stage_name = STAGE_EN2CN.get(target, target)
    idx = _find_stage_index(plan, target)

    if idx is None:
        return plan, PlanEvent(
            event_type="stage_replaced",
            summary=f"未找到 {stage_name} 阶段",
            version=plan.version,
        )

    candidates = _search_stage(scene, stage_name, limit=10)
    if not candidates:
        return plan, PlanEvent(
            event_type="stage_replaced",
            summary=f"未搜索到 {stage_name} 候选",
            version=plan.version,
        )

    # 约束过滤
    for c in constraints:
        neg = c.startswith("不要")
        keyword = c[2:] if neg else c[1:] if c.startswith("要") else c
        if neg:
            candidates = [
                x for x in candidates
                if keyword not in f"{x.name} {x.category}"
            ]
        else:
            # 正向约束：提升匹配 POI 的权重
            for x in candidates:
                if keyword in f"{x.name} {x.category}":
                    x.score = min(1.0, x.score + 0.15)

    if not candidates:
        return plan, PlanEvent(
            event_type="stage_replaced",
            summary=f"约束过滤后无 {stage_name} 候选",
            version=plan.version,
        )

    # 排除当前 POI + blocked
    candidates = [
        c for c in candidates
        if c.poi_id != plan.stages[idx].primary.poi_id and c.poi_id not in blocked
    ]
    if not candidates:
        return plan, PlanEvent(
            event_type="stage_replaced",
            summary=f"无新的 {stage_name} 候选（已排除当前选择）",
            version=plan.version,
        )

    # 打分 + 取最优
    scored = _rank_and_filter(candidates, profile, stage_name)
    if not scored:
        return plan, PlanEvent(
            event_type="stage_replaced",
            summary=f"打分后无合格的 {stage_name} 候选",
            version=plan.version,
        )

    old_name = plan.stages[idx].primary.name
    new_primary = scored[0]
    new_backups = scored[1:3] if len(scored) > 1 else []

    new_stages = list(plan.stages)
    new_stages[idx] = PlanStage(
        name=new_stages[idx].name,
        start_time=new_stages[idx].start_time,
        end_time=new_stages[idx].end_time,
        primary=new_primary,
        backups=new_backups,
        notes=new_primary.reason,
    )

    revised = plan.model_copy(update={"stages": new_stages})
    revised.summary = _summary(profile.scene, new_stages, plan.order_label)
    revised.score = _plan_score(revised)
    revised.total_cost_estimate = _estimate_cost(profile.people_count, new_stages)
    revised.version = plan.version + 1

    event = PlanEvent(
        event_type="stage_replaced",
        summary=f"已替换{stage_name}：{old_name} → {new_primary.name}",
        version=revised.version,
    )
    return revised, event


def insert_stage(
    plan: Plan,
    category: str,
    profile: GroupProfile,
    blocked: set[str] | None = None,
) -> tuple[Plan, PlanEvent]:
    """搜索品类 POI，作为加餐阶段插入路线。"""
    blocked = blocked or set()
    scene = profile.scene if profile.scene != "unknown" else "family"

    candidates = _search_stage(scene, "加餐", limit=10, category=category)
    if not candidates:
        return plan, PlanEvent(
            event_type="stage_inserted",
            summary=f"未搜索到 {category} 相关候选",
            version=plan.version,
        )

    # 按品类关键词过滤
    matched = [
        c for c in candidates
        if category in f"{c.name} {c.category}" and c.poi_id not in blocked
    ]
    if not matched:
        matched = [c for c in candidates if c.poi_id not in blocked]
    if not matched:
        return plan, PlanEvent(
            event_type="stage_inserted",
            summary=f"无可用 {category} 候选",
            version=plan.version,
        )

    scored = _rank_and_filter(matched, profile, "加餐")
    if not scored:
        return plan, PlanEvent(
            event_type="stage_inserted",
            summary=f"打分后无合格的 {category} 候选",
            version=plan.version,
        )

    new_poi = scored[0]

    # 用路由引擎确定插入位置
    insert_at = find_insertion_slot(plan, category)

    # 按品类规则计算时间
    food_idx = _find_stage_index(plan, "food")
    play_idx = _find_stage_index(plan, "play")
    if category in ADDON_AFTER and food_idx is not None:
        addon_start = _shift(plan.stages[food_idx].start_time, ADDON_AFTER_EAT_OFFSET)
    elif play_idx is not None:
        addon_start = _shift(plan.stages[play_idx].end_time, 5)
    else:
        addon_start = plan.stages[-1].end_time if plan.stages else "14:00"

    new_stage = PlanStage(
        name="加餐",
        start_time=addon_start,
        end_time=_shift(addon_start, DURATION_ADDON),
        primary=new_poi,
        notes=new_poi.reason,
    )

    new_stages = list(plan.stages)
    new_stages.insert(insert_at, new_stage)
    new_stages = _compact_timeline(new_stages, plan.stages[0].start_time)

    revised = plan.model_copy(update={"stages": new_stages})
    revised.summary = _summary(profile.scene, new_stages, plan.order_label)
    revised.score = _plan_score(revised)
    revised.total_cost_estimate = _estimate_cost(profile.people_count, new_stages)
    revised.version = plan.version + 1

    event = PlanEvent(
        event_type="stage_inserted",
        summary=f"已加入{category}（{new_poi.name}）",
        version=revised.version,
    )
    return revised, event


def remove_stage(
    plan: Plan,
    target: str,
) -> tuple[Plan, PlanEvent]:
    """删除目标阶段并压缩时间轴。"""
    stage_name = STAGE_EN2CN.get(target, target)
    idx = _find_stage_index(plan, target)

    if idx is None:
        return plan, PlanEvent(
            event_type="stage_removed",
            summary=f"未找到 {stage_name} 阶段",
            version=plan.version,
        )

    removed_name = plan.stages[idx].primary.name
    new_stages = [s for i, s in enumerate(plan.stages) if i != idx]

    if new_stages and plan.stages[0].start_time:
        new_stages = _compact_timeline(new_stages, plan.stages[0].start_time)

    scene = "family"
    revised = plan.model_copy(update={"stages": new_stages})
    revised.summary = _summary(scene, new_stages, plan.order_label)
    revised.score = _plan_score(revised)
    revised.total_cost_estimate = _estimate_cost(1, new_stages)
    revised.version = plan.version + 1

    event = PlanEvent(
        event_type="stage_removed",
        summary=f"已删除{stage_name}（{removed_name}）",
        version=revised.version,
    )
    return revised, event


def reorder_stages(
    plan: Plan,
    new_order: list[str],
    profile: GroupProfile,
) -> tuple[Plan, PlanEvent]:
    """重排阶段顺序并重新计算时间轴。"""
    name_map = STAGE_CN2EN
    stage_by_name: dict[str, PlanStage] = {}
    for s in plan.stages:
        stage_by_name[s.name] = s

    reordered: list[PlanStage] = []
    for n in new_order:
        if n in stage_by_name:
            reordered.append(stage_by_name[n])

    # 把没在 new_order 里提到的 stage 追加到末尾
    for s in plan.stages:
        if s.name not in new_order:
            reordered.append(s)

    if not reordered:
        return plan, PlanEvent(
            event_type="stages_reordered",
            summary="重排后无有效阶段",
            version=plan.version,
        )

    start = profile.start_time or plan.stages[0].start_time
    reordered = _compact_timeline(reordered, start)

    order_label = " → ".join(s.name for s in reordered)
    revised = plan.model_copy(update={"stages": reordered, "order_label": order_label})
    revised.summary = _summary(profile.scene, reordered, order_label)
    revised.score = _plan_score(revised)
    revised.total_cost_estimate = _estimate_cost(profile.people_count, reordered)
    revised.version = plan.version + 1

    event = PlanEvent(
        event_type="stages_reordered",
        summary=f"已调整顺序：{order_label}",
        version=revised.version,
    )
    return revised, event


def revise_plan(
    plan: Plan,
    patches: list[PlanPatch],
    profile: GroupProfile,
    locked_stages: list[str] | None = None,
    blocked: set[str] | None = None,
) -> tuple[Plan | None, list[PlanEvent]]:
    """按序应用一批 patches，全部成功后校验，返回修订后 Plan + 事件列表。

    原子性：任一 patch 失败则返回 (None, events)。
    locked_stages：被锁定的阶段名列表，修订时跳过这些 target。"""
    if profile is None:
        from backend.agents.profiler import analyze_profile
        profile = analyze_profile("周末出去玩")
    locked = set(locked_stages or []) | set(plan.locked_stages)
    current = deepcopy(plan)
    events: list[PlanEvent] = []

    for patch in patches:
        # 锁定检查
        target_stage_name = STAGE_EN2CN.get(
            patch.target, patch.target
        )
        if patch.action != "lock" and target_stage_name in locked:
            events.append(
                PlanEvent(
                    event_type="stage_locked",
                    summary=f"跳过修改 {target_stage_name}（已锁定）",
                    version=current.version,
                )
            )
            continue

        if patch.action == "lock":
            if target_stage_name not in locked:
                locked.add(target_stage_name)
                current.locked_stages = list(locked)
                events.append(
                    PlanEvent(
                        event_type="stage_locked",
                        summary=f"已锁定 {target_stage_name} 阶段",
                        version=current.version,
                    )
                )

        elif patch.action == "replace":
            current, ev = replace_stage(
                current, patch.target, profile, patch.constraints, blocked
            )
            events.append(ev)

        elif patch.action == "insert":
            cat = patch.category or "奶茶"
            current, ev = insert_stage(current, cat, profile, blocked)
            events.append(ev)

        elif patch.action == "remove":
            current, ev = remove_stage(current, patch.target)
            events.append(ev)

        elif patch.action == "reorder":
            # 从 constraints 或文本中提取新顺序
            new_order = _parse_reorder(patch)
            if not new_order:
                new_order = ["吃", "玩"]
            current, ev = reorder_stages(current, new_order, profile)
            events.append(ev)

    # 最终校验
    vr = validate_plan(current, profile)
    if not vr.passed:
        return None, events

    current.validation = vr
    return current, events


def _parse_reorder(patch: PlanPatch) -> list[str] | None:
    """从 patch constraints 中提取顺序 ['玩','吃'] 或 ['吃','玩']。"""
    for c in patch.constraints:
        if "先吃后玩" in c or "吃→玩" in c:
            return ["吃", "玩"]
        if "先玩后吃" in c or "玩→吃" in c:
            return ["玩", "吃"]
    return None


# ─────────────────────────── 兜底 Stub ───────────────────────────


def build_family_stub() -> Plan:
    return Plan(
        summary="亲子下午：奥森公园遛娃 → 轻食午餐 → 北欧蛋糕加餐",
        order_label="玩 → 吃 → 加餐",
        stages=[
            PlanStage(
                name="玩",
                start_time="14:00",
                end_time="16:00",
                primary=POICandidate(
                    poi_id="poi_park_001",
                    name="奥林匹克森林公园",
                    category="亲子活动",
                    score=0.92,
                    reason="离家 6km，有儿童游乐区，5 岁孩子合适",
                ),
            ),
            PlanStage(
                name="吃",
                start_time="16:30",
                end_time="18:00",
                primary=POICandidate(
                    poi_id="poi_rest_021",
                    name="Wagas 沙拉轻食（奥森店）",
                    category="餐厅",
                    score=0.88,
                    reason="低卡符合减肥需求；有儿童椅",
                ),
            ),
            PlanStage(
                name="加餐",
                start_time="17:30",
                end_time="17:45",
                primary=POICandidate(
                    poi_id="poi_cake_007",
                    name="原麦山丘 小蛋糕（送至餐厅）",
                    category="加餐",
                    score=0.81,
                    reason="低糖款，给孩子的小惊喜",
                ),
            ),
        ],
        total_duration_hours=4.0,
        total_cost_estimate=320,
        score=0.0,
    )


def build_friends_stub() -> Plan:
    return Plan(
        summary="朋友下午：剧本杀 → 烤肉聚餐 → 鲜花点缀",
        order_label="玩 → 吃 → 加餐",
        stages=[
            PlanStage(
                name="玩",
                start_time="14:00",
                end_time="16:30",
                primary=POICandidate(
                    poi_id="poi_act_101",
                    name="罪有引力剧本杀（三里屯店）",
                    category="活动",
                    score=0.90,
                    reason="4 人本，2 男 2 女均衡，距离 5km",
                ),
            ),
            PlanStage(
                name="吃",
                start_time="17:00",
                end_time="19:00",
                primary=POICandidate(
                    poi_id="poi_rest_201",
                    name="姜虎东白丁烤肉（三里屯）",
                    category="餐厅",
                    score=0.89,
                    reason="4 人聚餐口碑高",
                ),
            ),
            PlanStage(
                name="加餐",
                start_time="18:30",
                end_time="18:45",
                primary=POICandidate(
                    poi_id="poi_flower_009",
                    name="花点时间 小花束（送至餐厅）",
                    category="加餐",
                    score=0.76,
                    reason="给女生的小惊喜",
                ),
            ),
        ],
        total_duration_hours=5.0,
        total_cost_estimate=680,
        score=0.0,
    )
