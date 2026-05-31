"""核心领域模型（Pydantic）。LLM 输出的 JSON 全部通过这些模型校验。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ─────────────────────────── 搜索策略 ───────────────────────────


class SearchStrategy(BaseModel):
    """Profiler 产出的搜索策略，Planner 依此检索 POI。"""

    play_categories: list[str] = Field(default_factory=list)
    food_categories: list[str] = Field(default_factory=list)
    optional_categories: list[str] = Field(default_factory=list)
    avoid_categories: list[str] = Field(default_factory=list)


# ─────────────────────────── 群体行为特征偏好 ───────────────────────────


class PlanningPreferences(BaseModel):
    """群体行为特征 — 纯画像层，描述"怎么选"而非"选什么"。

    不包含具体搜索类别（那是 Strategy Builder 的职责）。
    只描述群体的风格偏好，供 Planner 的打分/过滤/排序使用。
    """

    restaurant_style: list[str] = Field(default_factory=list)
    activity_style: list[str] = Field(default_factory=list)
    route_style: list[str] = Field(default_factory=list)


# ─────────────────────────── 群体画像 ───────────────────────────


class EditableTag(BaseModel):
    """前端可点改的画像标签胶囊（对应 02.架构和agent.md §3.2 ui_chips）。"""

    key: str  # 对应 GroupProfile 的字段名，如 "scene" / "dietary"
    label: str  # 展示文案，如 "家庭" / "约 5 小时"
    value: str = ""  # 序列化后的值，前端编辑后回传
    confidence: float = 0.0  # 0~1，<0.6 视为低置信，UI 可弱化
    editable: bool = True
    source: Literal["utterance", "history", "rule"] = "rule"


class ProfileEvidence(BaseModel):
    """画像字段的证据链：依据哪句关键词、来自哪里。"""

    field: str  # 影响的字段，如 "scene" / "dietary"
    value: str  # 推断值的字符串形态
    term: str = ""  # 触发的原文片段，如 "老婆孩子"
    confidence: float = 0.0
    source: Literal["utterance", "history", "rule"] = "utterance"


class GroupProfile(BaseModel):
    """从用户一句话里抽取出的群体画像。"""

    scene: Literal["family", "friends", "couple", "solo", "unknown"] = "unknown"
    people_count: int = 1
    kids_ages: list[int] = Field(default_factory=list)
    distance_limit_km: float = 10.0
    duration_hours: float = 4.0
    start_time: str | None = None  # ISO 字符串，None 表示尽快出发
    dietary: list[str] = Field(default_factory=list)  # 例 ["低卡", "不辣"]
    interests: list[str] = Field(default_factory=list)  # 例 ["亲子", "展览"]
    budget_per_person: int | None = None
    raw_text: str = ""
    # 每字段置信度（0~1），缺失字段视为 0.5
    confidence: dict[str, float] = Field(default_factory=dict)
    # 给前端的可编辑标签；空表示前端不展示
    editable_tags: list[EditableTag] = Field(default_factory=list)
    # 每个字段的证据链；面试可亮「依据哪句话推出来的」
    evidence: list[ProfileEvidence] = Field(default_factory=list)
    # 历史偏好权重（来自 history_context），0~1，越大越喜欢
    history_weights: dict[str, float] = Field(default_factory=dict)
    # 群体行为特征偏好，供 Planner 的打分/过滤/排序使用
    planning_preferences: PlanningPreferences = Field(default_factory=PlanningPreferences)
    # Profiler 产出的搜索策略，Planner 依此检索 POI
    search_strategy: SearchStrategy | None = None


# ─────────────────────────── 打分明细 ───────────────────────────


class ScoreBreakdown(BaseModel):
    """五维打分明细，附在 POICandidate.breakdown。

    评委追问「为啥选 A 不选 B」时，可亮明细。
    """

    preference: float = 0.0  # 标签匹配 35%
    history: float = 0.0  # 历史偏好 20%
    rating: float = 0.0  # POI 评分 20%
    distance: float = 0.0  # 距离 15%
    budget: float = 0.0  # 预算 10%
    total: float = 0.0


# ─────────────────────────── 方案 ───────────────────────────


class POICandidate(BaseModel):
    poi_id: str
    name: str
    category: str  # 餐厅 / 活动 / 加餐 等
    score: float = 0.0
    reason: str = ""  # 为什么推这家（可解释性）
    metadata: dict = Field(default_factory=dict)  # avg_price / distance_km / open_hours / tags 等
    # 五维加权打分明细，None 表示尚未打分（如 stub 兜底方案）
    breakdown: ScoreBreakdown | None = None


class PlanStage(BaseModel):
    """方案的一个阶段。一个阶段对应一段时间窗口和一个动作。"""

    name: str  # "玩" / "吃" / "加餐" / "通勤"
    start_time: str  # "14:00"
    end_time: str  # "16:00"
    primary: POICandidate
    backups: list[POICandidate] = Field(default_factory=list)
    notes: str = ""


class Plan(BaseModel):
    summary: str = ""
    stages: list[PlanStage] = Field(default_factory=list)
    total_duration_hours: float = 0.0
    total_cost_estimate: int = 0  # 单位：元
    # 方案总分（取所有 stage.primary.breakdown.total 平均）；用于 Top-K 排序
    score: float = 0.0
    # 阶段顺序，例如 "玩→吃→加餐" / "吃→玩→加餐"，给评委展示「试过多种顺序」
    order_label: str = ""
    # 硬约束校验结果（validator 产出），None 表示未校验
    validation: Any | None = Field(default=None, exclude=True)
    # 修订版本号，初始为 1
    version: int = 1
    # 被锁定的阶段名列表，修订时跳过这些阶段
    locked_stages: list[str] = Field(default_factory=list)


# ─────────────────────────── 方案修订 ───────────────────────────


class PlanPatch(BaseModel):
    """单条修订补丁。从用户反馈中解析出的结构化修改意图。"""

    target: Literal["play", "food", "addon", "route"]
    action: Literal["replace", "insert", "remove", "reorder", "lock"]
    constraints: list[str] = Field(default_factory=list)
    category: str | None = None


class PlanSnapshot(BaseModel):
    """方案的不可变快照，每次修订产出一个新版本，支持版本回溯。"""

    version: int
    plan: Plan
    created_at: str = ""
    parent_version: int | None = None
    event_summary: str = ""


class PlanEvent(BaseModel):
    """用户可见的变更事件，前端渲染为 ✓ 列表。"""

    event_type: Literal[
        "plan_created",
        "stage_replaced",
        "stage_inserted",
        "stage_removed",
        "stages_reordered",
        "stage_locked",
    ]
    summary: str
    timestamp: str = ""
    version: int = 0


# ─────────────────────────── Critic 反馈 ───────────────────────────


class CriticIssue(BaseModel):
    severity: Literal["block", "warn"] = "warn"
    field: str  # 涉及的字段，如 "stages[1].primary"
    message: str


class CriticFeedback(BaseModel):
    approved: bool = True
    issues: list[CriticIssue] = Field(default_factory=list)


# ─────────────────────────── Tool 调用记录 ───────────────────────────


class ToolStatus(str, Enum):
    PENDING = "pending"
    OK = "ok"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ToolCall(BaseModel):
    """一次 Tool 调用的全量记录（用于 DryRun / Executor / Compensator）。"""

    id: str  # 全局唯一，便于回滚定位
    stage_name: str  # 属于 Plan 的哪个阶段
    tool_name: str
    args: dict = Field(default_factory=dict)
    status: ToolStatus = ToolStatus.PENDING
    result: dict | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


# ─────────────────────────── 行程卡（最终交付） ───────────────────────────


class SummaryCard(BaseModel):
    title: str
    body_markdown: str
    share_text: str  # 给老婆/朋友的微信可分享文案
