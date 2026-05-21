"""Planner Agent：把 Researcher 候选拼成可执行 `Plan` 列表（Top-K）。

主要能力（对齐 02.架构 §4 + 03.细节实现.md）：
  1. 硬过滤：场景硬要求（亲子需亲子活动、低卡需轻食/沙拉）；不通过即剔除。
  2. 顺序枚举：玩→吃→加餐 vs 吃→玩→加餐，各排时间轴。
  3. 主选：按候选自带的 breakdown.total 倒序取首位（已五维加权打分）。
  4. 方案打分：取各阶段 primary 的 breakdown.total 算均值，得到 Plan.score。
  5. Top-K：返回排序后的前 K 个 Plan，由 node 写入 plan + plan_alternatives。
  6. 兜底：若 research 为空或被硬过滤砍空，回退到硬编码 family/friends stub。

节点 `nodes/planner.py` 只做 state 适配；业务逻辑全部在这里。
"""
from __future__ import annotations

from weekend_agent.schemas import (
    GroupProfile,
    Plan,
    PlanStage,
    POICandidate,
    ResearchResult,
    ResearchStageResult,
)

# ─────────────────────────── 时间轴工具 ───────────────────────────


_DURATION_PLAY = 150  # 玩 2.5h
_DURATION_TRANSIT = 30  # 通勤 30min
_DURATION_EAT = 120  # 吃 2h
_ADDON_AFTER_EAT_START = 90  # 加餐相对「吃」开始的偏移
_ADDON_DURATION = 15


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


# ─────────────────────────── 硬过滤 ───────────────────────────


_KIDS_KEYS = ("亲子", "儿童", "公园", "童", "宝宝", "海洋馆")
_LOW_CAL_KEYS = ("轻食", "沙拉", "健康", "低卡", "蔬食")


def _candidate_text(c: POICandidate) -> str:
    return f"{c.name} {c.category} {c.reason}".lower()


def _passes_hard_filter(
    c: POICandidate, stage_name: str, profile: GroupProfile
) -> bool:
    """命中硬约束 = 不通过，整条砍掉。

    softer 的约束（如「人均偏贵」「评分稍低」）已在 Researcher 五维打分里降分，
    这里只挑「典型不可接受」的几条，保证规则可解释。
    """
    text = _candidate_text(c)

    # 1) 家庭场景 + 玩阶段：必须亲子友好
    if stage_name == "玩" and profile.scene == "family" and profile.kids_ages:
        if not any(k.lower() in text for k in _KIDS_KEYS):
            return False

    # 2) 低卡需求 + 吃阶段：餐厅名/类目必须含轻食/沙拉等
    if stage_name == "吃" and "低卡" in profile.dietary:
        if not any(k.lower() in text for k in _LOW_CAL_KEYS):
            return False

    # 3) 距离上限（researcher 已过滤一次；planner 再保险，防 stub 进来）
    d = float(c.metadata.get("distance_km", 0) or 0)
    if d > profile.distance_limit_km + 1e-6:
        return False

    return True


def _filter_stage_candidates(
    stage: ResearchStageResult,
    profile: GroupProfile,
    blocked: set[str],
) -> list[POICandidate]:
    """硬过滤 + 黑名单。若全砍光则回退为原始顺序（不报错，让 planner 仍能成图）。"""
    kept = [
        c
        for c in stage.candidates
        if c.poi_id not in blocked and _passes_hard_filter(c, stage.stage_name, profile)
    ]
    if kept:
        return kept
    # 全被砍光：用未硬过滤但避开 blocked 的，保证 demo 不挂
    fallback = [c for c in stage.candidates if c.poi_id not in blocked]
    return fallback or list(stage.candidates)


# ─────────────────────────── 阶段顺序枚举 ───────────────────────────


_ORDER_VARIANTS: tuple[tuple[str, ...], ...] = (
    ("玩", "吃"),
    ("吃", "玩"),
)


def _build_plan_with_order(
    profile: GroupProfile,
    research_by_name: dict[str, ResearchStageResult],
    blocked: set[str],
    order: tuple[str, ...],
) -> Plan | None:
    """按给定阶段顺序构建一个完整 Plan；缺关键阶段则返回 None。"""
    play_stage = research_by_name.get("玩")
    eat_stage = research_by_name.get("吃")
    if play_stage is None or eat_stage is None:
        return None

    play_pool = _filter_stage_candidates(play_stage, profile, blocked)
    eat_pool = _filter_stage_candidates(eat_stage, profile, blocked)
    if not play_pool or not eat_pool:
        return None

    play = play_pool[0]
    eat = eat_pool[0]

    start = profile.start_time or "14:00"
    cursor = start
    stage_objs: dict[str, PlanStage] = {}

    for name in order:
        if name == "玩":
            seg_start = cursor
            seg_end = _shift(seg_start, _DURATION_PLAY)
            stage_objs["玩"] = PlanStage(
                name="玩",
                start_time=seg_start,
                end_time=seg_end,
                primary=play,
                backups=[c for c in play_pool if c.poi_id != play.poi_id],
                notes=play.reason,
            )
            cursor = _shift(seg_end, _DURATION_TRANSIT)
        elif name == "吃":
            seg_start = cursor
            seg_end = _shift(seg_start, _DURATION_EAT)
            stage_objs["吃"] = PlanStage(
                name="吃",
                start_time=seg_start,
                end_time=seg_end,
                primary=eat,
                backups=[c for c in eat_pool if c.poi_id != eat.poi_id],
                notes=eat.reason,
            )
            cursor = _shift(seg_end, _DURATION_TRANSIT)

    # 加餐附在「吃」开始的 +90min（与 nodes/planner 旧逻辑一致）
    addon_stage = research_by_name.get("加餐")
    if addon_stage is not None and "吃" in stage_objs:
        addon_pool = _filter_stage_candidates(addon_stage, profile, blocked)
        if addon_pool:
            addon = addon_pool[0]
            addon_start = _shift(stage_objs["吃"].start_time, _ADDON_AFTER_EAT_START)
            stage_objs["加餐"] = PlanStage(
                name="加餐",
                start_time=addon_start,
                end_time=_shift(addon_start, _ADDON_DURATION),
                primary=addon,
                notes=addon.reason,
            )

    # 按时间排序成 stages 列表
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
    """方案总分 = 各 stage.primary.breakdown.total 的均值，缺失视为 0.5。"""
    if not plan.stages:
        return 0.0
    parts: list[float] = []
    for s in plan.stages:
        bd = s.primary.breakdown
        parts.append(bd.total if bd else 0.5)
    return round(sum(parts) / len(parts), 3)


# ─────────────────────────── Top-K 入口 ───────────────────────────


def build_plans(
    profile: GroupProfile,
    research: ResearchResult,
    blocked: set[str] | None = None,
    *,
    top_k: int = 2,
) -> list[Plan]:
    """枚举顺序 → 硬过滤 → 选 primary → 总分排序 → 返回前 top_k 个方案。

    返回空列表表示 research 不够生成任何 Plan，调用方应回退到 stub。
    """
    blocked = blocked or set()
    by_name = {s.stage_name: s for s in research.stages}
    plans: list[Plan] = []
    seen_signatures: set[tuple[str, str]] = set()
    for order in _ORDER_VARIANTS:
        plan = _build_plan_with_order(profile, by_name, blocked, order)
        if plan is None:
            continue
        sig = (plan.order_label, plan.stages[0].primary.poi_id if plan.stages else "")
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)
        plans.append(plan)

    plans.sort(key=lambda p: p.score, reverse=True)
    return plans[:top_k]


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
