"""核心领域模型（Pydantic）。LLM 输出的 JSON 全部通过这些模型校验。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ─────────────────────────── 群体画像 ───────────────────────────


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


# ─────────────────────────── 方案 ───────────────────────────


class POICandidate(BaseModel):
    poi_id: str
    name: str
    category: str  # 餐厅 / 活动 / 加餐 等
    score: float = 0.0
    reason: str = ""  # 为什么推这家（可解释性）


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
