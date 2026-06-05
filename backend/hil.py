"""HIL 会话：规划暂停、画像覆盖、从 Researcher 重跑。"""
from __future__ import annotations

import uuid
from typing import Any

from backend.agents.planner import (
    _HEAVY_FOOD_KEYS,
    _LOW_CAL_KEYS,
    _candidate_text,
    _explicit_cuisines,
    _matches_cuisine,
    _wants_light_meal,
)

BUILD_VERSION = "2026-06-06-constraint-v3"
from backend.schemas import GroupProfile, Plan
from backend.state import AgentState

_sessions: dict[str, AgentState] = {}


def create_session(state: AgentState) -> str:
    session_id = uuid.uuid4().hex[:12]
    _sessions[session_id] = dict(state)
    return session_id


def get_session(session_id: str) -> AgentState | None:
    return _sessions.get(session_id)


def save_session(session_id: str, state: AgentState) -> None:
    _sessions[session_id] = dict(state)


def clear_planning_artifacts() -> dict[str, Any]:
    """重规划前清空下游产物，保留 user_input / group_profile。"""
    return {
        "research_result": None,
        "targeted_search_requests": [],
        "targeted_research_result": None,
        "plan": None,
        "plan_alternatives": [],
        "critic_feedback": None,
        "dry_run_calls": [],
        "executed_calls": [],
        "failed_calls": [],
        "summary_card": None,
        "user_confirmed": False,
        "force_failure": None,
    }


def select_plan(state: AgentState, plan_id: str) -> AgentState:
    """确认前切换主方案（primary / alt_0 / alt_1 …）。"""
    updated = dict(state)
    plan = updated.get("plan")
    alts = list(updated.get("plan_alternatives") or [])

    if plan_id == "primary" or not plan:
        return updated

    if not plan_id.startswith("alt_"):
        return updated

    try:
        idx = int(plan_id.split("_", 1)[1])
    except (IndexError, ValueError):
        return updated

    if idx < 0 or idx >= len(alts):
        return updated

    chosen = alts[idx]
    rest = [plan] + [a for i, a in enumerate(alts) if i != idx]
    updated["plan"] = chosen
    updated["plan_alternatives"] = rest
    return updated


def _stage_by_name(plan: Plan, name: str):
    return next((s for s in plan.stages if s.name == name), None)


def _short_poi_name(name: str) -> str:
    return name.split("（")[0].strip()


def _venue_extras(stage_name: str, meta: dict) -> dict[str, str]:
    avg = int(meta.get("avg_price", 0) or 0)
    dist = float(meta.get("distance_km", 0) or 0)
    price_label = ""
    if avg:
        price_label = f"约¥{avg}" if stage_name == "加餐" else f"约¥{avg}/人"
    distance_label = f"距家 {dist:g} km" if dist else ""
    return {"priceLabel": price_label, "distanceLabel": distance_label}


def _build_match_reasons(plan: Plan, profile: GroupProfile | None) -> list[str]:
    """把 Profiler / Planner / Critic 命中的约束翻成可展示文案。"""
    if profile is None:
        return []

    reasons: list[str] = []
    play = _stage_by_name(plan, "玩")
    eat = _stage_by_name(plan, "吃")

    scene_labels = {
        "family": "家庭出游",
        "friends": "朋友聚会",
        "couple": "情侣约会",
        "solo": "独自放松",
    }
    if profile.scene in scene_labels:
        reasons.append(f"场景·{scene_labels[profile.scene]}")

    if profile.people_count:
        reasons.append(f"人数·{profile.people_count} 人")

    if eat is not None:
        eat_text = _candidate_text(eat.primary)
        if _wants_light_meal(profile):
            if any(k.lower() in eat_text for k in _LOW_CAL_KEYS):
                reasons.append("饮食·轻食/低卡（已匹配餐厅）")
            elif any(k.lower() in eat_text for k in _HEAVY_FOOD_KEYS):
                reasons.append("未满足·轻食约束（当前餐厅为重口味）")
        elif "重口味" in profile.dietary:
            if any(k in eat_text for k in ("烤肉", "火锅", "重口味")):
                reasons.append("口味·重口味（烤肉/火锅）")
        for tag in _explicit_cuisines(profile):
            if tag not in ("轻食",) and _matches_cuisine(eat.primary, {tag}):
                reasons.append(f"菜系·{tag}（已匹配）")

    if profile.kids_ages and play is not None:
        reasons.append(f"亲子·适合 {profile.kids_ages[0]} 岁娃")

    if play is not None and eat is not None:
        d_play = float(play.primary.metadata.get("distance_km", 0) or 0)
        d_eat = float(eat.primary.metadata.get("distance_km", 0) or 0)
        if abs(d_play - d_eat) <= 3.0:
            reasons.append("顺路·玩/吃相距 ≤3km")

    if eat is not None and profile.people_count >= 4:
        table_types = eat.primary.metadata.get("table_type") or []
        reason_text = eat.primary.reason or ""
        if "4 人" in reason_text or "4人" in reason_text or "4人桌" in table_types:
            reasons.append("订座·支持 4 人桌")

    if profile.scene == "friends" and eat is not None:
        eat_tags = eat.primary.metadata.get("tags") or []
        if "社交" in eat_tags:
            reasons.append("氛围·适合朋友社交")

    if profile.distance_limit_km and play is not None and eat is not None:
        d_play = float(play.primary.metadata.get("distance_km", 0) or 0)
        d_eat = float(eat.primary.metadata.get("distance_km", 0) or 0)
        if max(d_play, d_eat) <= profile.distance_limit_km:
            reasons.append(f"距离·≤{profile.distance_limit_km:.0f}km")

    return reasons


def _validate_plan_constraints(plan: Plan, profile: GroupProfile | None) -> list[str]:
    """最后一道闸：任何硬约束不满足，都不能包装成可确认方案。"""
    if profile is None:
        return []

    issues: list[str] = []
    play = _stage_by_name(plan, "玩")
    eat = _stage_by_name(plan, "吃")

    if eat is not None:
        eat_text = _candidate_text(eat.primary)
        eat_name = eat.primary.name
        if _wants_light_meal(profile):
            if any(k.lower() in eat_text for k in _HEAVY_FOOD_KEYS):
                issues.append(f"轻食约束冲突：{eat_name} 属于重口味/烤肉类")
            elif not any(k.lower() in eat_text for k in _LOW_CAL_KEYS):
                issues.append(f"轻食约束未满足：{eat_name} 缺少轻食/低卡标签")
        for cuisine in _explicit_cuisines(profile):
            if cuisine == "轻食" and _wants_light_meal(profile):
                continue
            if not _matches_cuisine(eat.primary, {cuisine}):
                issues.append(f"菜系约束未满足：{eat_name} 不匹配 {cuisine}")

    if play is not None and eat is not None:
        d_play = float(play.primary.metadata.get("distance_km", 0) or 0)
        d_eat = float(eat.primary.metadata.get("distance_km", 0) or 0)
        if abs(d_play - d_eat) > 3.0:
            issues.append("顺路约束未满足：玩/吃距离差超过 3km")
        if max(d_play, d_eat) > profile.distance_limit_km:
            issues.append(f"距离约束未满足：超出 {profile.distance_limit_km:.0f}km")

    return issues


def _diff_summary(primary: Plan | None, alt: Plan) -> str:
    if primary is None:
        return "备选方案"

    p_play = _stage_by_name(primary, "玩")
    a_play = _stage_by_name(alt, "玩")
    p_eat = _stage_by_name(primary, "吃")
    a_eat = _stage_by_name(alt, "吃")

    parts: list[str] = []
    if p_play and a_play and p_play.primary.poi_id != a_play.primary.poi_id:
        parts.append(f"玩法改为「{_short_poi_name(a_play.primary.name)}」")
    if p_eat and a_eat and p_eat.primary.poi_id != a_eat.primary.poi_id:
        parts.append(f"餐厅改为「{_short_poi_name(a_eat.primary.name)}」")

    return "；".join(parts) if parts else "同路线备选"


def plan_to_display(
    plan: Plan,
    plan_id: str,
    people_count: int,
    *,
    profile: GroupProfile | None = None,
    primary: Plan | None = None,
) -> dict[str, Any]:
    """前端行程卡 JSON。"""
    stage_map = {"玩": "play", "吃": "eat", "加餐": "addon"}
    match_reasons = _build_match_reasons(plan, profile)
    constraint_issues = _validate_plan_constraints(plan, profile)
    payload: dict[str, Any] = {
        "id": plan_id,
        "title": plan.summary,
        "order_label": plan.order_label,
        "score": int(round(plan.score * 100)) if plan.score <= 1 else int(plan.score),
        "totalPrice": f"¥{max(plan.total_cost_estimate // max(people_count, 1), 0)}/人",
        "highlights": match_reasons,
        "matchReasons": match_reasons,
        "constraintIssues": constraint_issues,
        "isValid": not constraint_issues,
    }

    if plan_id != "primary" and primary is not None:
        payload["diffSummary"] = _diff_summary(primary, plan)
    elif plan_id == "primary":
        payload["diffSummary"] = "综合评分最高"

    for stage in plan.stages:
        key = stage_map.get(stage.name, stage.name)
        meta = stage.primary.metadata or {}
        tags = meta.get("tags") or []
        if not tags and stage.primary.category:
            tags = [stage.primary.category]
        extras = _venue_extras(stage.name, meta)
        payload[key] = {
            "name": stage.primary.name,
            "time": f"{stage.start_time}–{stage.end_time}",
            "desc": stage.primary.reason or "",
            "tags": list(tags),
            **extras,
        }

    return payload


def build_plans_payload(state: AgentState) -> list[dict[str, Any]]:
    profile = state.get("group_profile")
    people = profile.people_count if profile else 1
    items: list[dict[str, Any]] = []

    plan = state.get("plan")
    if plan:
        items.append(
            plan_to_display(plan, "primary", people, profile=profile, primary=None)
        )

    for i, alt in enumerate(state.get("plan_alternatives") or []):
        items.append(
            plan_to_display(alt, f"alt_{i}", people, profile=profile, primary=plan)
        )

    return items


def profile_chips(profile: GroupProfile | None) -> list[dict[str, Any]]:
    if profile is None:
        return []
    return [t.model_dump(mode="json") for t in profile.editable_tags]
