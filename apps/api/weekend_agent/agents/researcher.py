"""Researcher Agent：按画像走 HTTP 调 Mock 美团搜索 POI，再五维加权打分。

P0：候选数据由 `mock_meituan` 子服务通过 `GET /poi/search` 返回；本模块只做
打分、排序、过滤。
P1：把 `MOCK_MEITUAN_BASE_URL` 指到真美团 / 公司 mock server 即可零改动切换。

评分维度（见 03.细节实现.md · Researcher 五维）：
  preference 35%  软偏好命中
  history    20%  GroupProfile.history_weights 命中
  rating     20%  POICandidate.score
  distance   15%  距离衰减
  budget     10%  人均价格 vs 预算
"""
from __future__ import annotations

from typing import Any

from weekend_agent.schemas import (
    GroupProfile,
    POICandidate,
    ResearchResult,
    ResearchStageResult,
    ScoreBreakdown,
)
from weekend_agent.tools.errors import ToolError
from weekend_agent.tools.http_client import search_poi

_TOP_K = 3
_STAGES: tuple[str, ...] = ("玩", "吃", "加餐")

# 五维权重（对齐设计文档）；上层不直接传入，常量定义在此便于评委追问
_WEIGHTS: dict[str, float] = {
    "preference": 0.35,
    "history": 0.20,
    "rating": 0.20,
    "distance": 0.15,
    "budget": 0.10,
}


def _to_candidate(item: dict[str, Any]) -> POICandidate:
    return POICandidate(
        poi_id=item.get("poi_id", ""),
        name=item.get("name", ""),
        category=item.get("category", ""),
        score=float(item.get("score", 0.0) or 0.0),
        reason=item.get("reason", ""),
        metadata=dict(item.get("metadata") or {}),
    )


def run_research(profile: GroupProfile | None) -> ResearchResult:
    if profile is None:
        return ResearchResult(stages=[], tool_trace=["skip: no profile"])

    scene_key = profile.scene if profile.scene != "unknown" else "family"
    stages: list[ResearchStageResult] = []
    trace: list[str] = []
    for stage_name in _STAGES:
        try:
            raw = search_poi(scene=scene_key, stage=stage_name, limit=10)
        except ToolError as e:
            trace.append(f"GET /poi/search(stage={stage_name}) → {e.code} {e.message}")
            continue

        candidates = [_to_candidate(it) for it in raw]
        if not candidates:
            trace.append(f"GET /poi/search(stage={stage_name}) → 0")
            continue

        ranked = _rank_and_filter(candidates, profile, stage_name)
        if not ranked:
            trace.append(
                f"GET /poi/search(stage={stage_name}) → {len(candidates)}，"
                f"过滤后 0（distance_limit={profile.distance_limit_km}）"
            )
            continue
        top = ranked[0]
        stages.append(
            ResearchStageResult(stage_name=stage_name, candidates=ranked, selected=top)
        )
        bd = top.breakdown
        bd_str = (
            f" total={bd.total:.2f} pref={bd.preference:.2f} hist={bd.history:.2f}"
            f" dist={bd.distance:.2f}"
            if bd
            else ""
        )
        trace.append(
            f"GET /poi/search(stage={stage_name}) → {len(ranked)} top={top.name}{bd_str}"
        )

    return ResearchResult(stages=stages, tool_trace=trace)


# ─────────────────────────── 五维打分 ───────────────────────────


def _hit_in_text(text_lower: str, candidates) -> int:
    return sum(1 for t in candidates if t and t.lower() in text_lower)


def _score_preference(c: POICandidate, profile: GroupProfile) -> float:
    """软偏好命中率：interests + dietary + 场景标签。"""
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
    """玩/加餐通常不在预算考核内；只有「吃」严格按预算扣分。"""
    avg_price = float(c.metadata.get("avg_price", 0) or 0)
    budget = profile.budget_per_person
    if stage_name != "吃" or budget is None or avg_price <= 0:
        return 0.7
    if avg_price <= budget:
        return 1.0
    over_ratio = (avg_price - budget) / max(budget, 1)
    return max(0.0, 1.0 - over_ratio)


def _score_one(c: POICandidate, profile: GroupProfile, stage_name: str) -> ScoreBreakdown:
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
    """1) 距离硬过滤；2) 五维加权打分；3) 按 total 降序取 Top_K。

    打分明细写回 candidate.breakdown，下游 Planner / Critic 可直接读。
    软偏好不命中也不剔除，避免阶段被砍空。
    """
    kept: list[POICandidate] = []
    for c in candidates:
        if float(c.metadata.get("distance_km", 0) or 0) > profile.distance_limit_km:
            continue
        scored = c.model_copy(update={"breakdown": _score_one(c, profile, stage_name)})
        kept.append(scored)

    if not kept:
        return []

    kept.sort(key=lambda x: (x.breakdown.total if x.breakdown else 0.0), reverse=True)
    return kept[:_TOP_K]
