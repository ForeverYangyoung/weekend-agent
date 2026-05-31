"""Planner + Scorer 模块入口。

用法:
    from backend.planner import PlannerEngine, LLMClient, UserProfile
    from backend.planner.state import TimeWindow, Geo, BudgetRange

    profile = UserProfile(
        mode="family", party_size=3,
        time_window=TimeWindow(start="14:00", end="18:00", duration_hours=4),
        geo=Geo(anchor="北京朝阳", radius_km=5),
        budget_per_person=BudgetRange(min=100, max=300),
        hard_filters=["needs_kid_friendly"],
        soft_preferences=["公园"],
    )
    engine = PlannerEngine(llm_client=LLMClient(api_key="..."))
    result = engine.run(profile, "下午带家人出去玩")
    for plan in result.scored_plans:
        print(f"#{plan.rank} {plan.score:.2f} {plan.summary}")

打分功能已独立为 peer package，请直接导入:
    from scoring import ScoringAgent
    from scoring.rules import compute_total_score, rank_plans
"""

from backend.planner.graph import PlannerEngine, build_planner_graph
from backend.planner.insertion_engine import (
    build_insertion_display,
    filter_insertions,
)
from backend.planner.llm_wrapper import LLMClient
from backend.planner.state import (
    INSERTABLE_CATALOG,
    Combo,
    InsertableBehavior,
    PlannerState,
    RouteInsertion,
    ScoreBreakdown,
    ScoredPlan,
    UserProfile,
    create_initial_state,
)
from backend.planner.strategy_builder import build_search_strategy
from backend.planner.timeline import build_skeleton_from_order, enumerate_candidate_orders
from backend.planner.tool_hub import ToolHub
from backend.planner.trace import TraceLogger, TraceSpan
from backend.planner.validator import ValidationResult, validate_plan

__all__ = [
    "PlannerEngine",
    "build_planner_graph",
    "build_search_strategy",
    "ToolHub",
    "TraceLogger",
    "TraceSpan",
    "LLMClient",
    "UserProfile",
    "PlannerState",
    "ScoredPlan",
    "ScoreBreakdown",
    "Combo",
    "InsertableBehavior",
    "RouteInsertion",
    "INSERTABLE_CATALOG",
    "create_initial_state",
    "enumerate_candidate_orders",
    "build_skeleton_from_order",
    "filter_insertions",
    "build_insertion_display",
    "validate_plan",
    "ValidationResult",
]
