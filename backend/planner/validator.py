"""方案校验器 — 纯规则，不调用 LLM。

在 Planner 生成方案后、Critic 之前执行。
检查硬约束：距离 / 预算 / 饮食 / 阶段数 / 时长。
不合格直接淘汰，不送给 Critic。
"""

from dataclasses import dataclass, field

from backend.planner.constants import (
    BUDGET_TOLERANCE,
    DURATION_ADDON,
    DURATION_EAT,
    DURATION_PLAY,
    DURATION_TOLERANCE,
    DURATION_TRANSIT,
)
from backend.schemas import GroupProfile, Plan


@dataclass
class ValidationIssue:
    severity: str  # "block" | "warn"
    field: str
    message: str


@dataclass
class ValidationResult:
    passed: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def block_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "block"]

    @property
    def warn_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warn"]


def validate_plan(plan: Plan, profile: GroupProfile) -> ValidationResult:
    """对单个方案执行全部硬约束检查。

    检查维度：
      1. 阶段完整性 — 至少含「玩」和「吃」
      2. 距离约束   — 每个 POI 在 distance_limit_km 内
      3. 预算约束   — 人均消费在预算范围内
      4. 饮食约束   — dietary 每项被至少一个 stage 覆盖
      5. 时长约束   — 方案总时长在用户时间窗内（+15% 宽容）
      6. 场景约束   — family 必须有亲子友好活动
    """
    issues: list[ValidationIssue] = []

    # ── 1. 阶段完整性 ──
    stage_names = {s.name for s in plan.stages}
    if "玩" not in stage_names:
        issues.append(ValidationIssue("block", "stages", "缺少「玩」阶段"))
    if "吃" not in stage_names:
        issues.append(ValidationIssue("block", "stages", "缺少「吃」阶段"))
    if len(plan.stages) < 2:
        issues.append(ValidationIssue("block", "stages", "方案阶段过少（至少 2 个）"))

    # ── 2. 距离约束 ──
    for s in plan.stages:
        d = float(s.primary.metadata.get("distance_km", 0) or 0)
        if d > profile.distance_limit_km + 1e-6:
            issues.append(ValidationIssue(
                "block",
                f"stages[{s.name}].primary",
                f"{s.primary.name} 距离 {d:.1f}km 超出限制 {profile.distance_limit_km}km",
            ))

    # ── 3. 预算约束 ──
    if profile.budget_per_person is not None:
        for s in plan.stages:
            if s.name == "加餐":
                continue
            price = float(s.primary.metadata.get("avg_price", 0) or 0)
            if price > profile.budget_per_person * BUDGET_TOLERANCE:
                issues.append(ValidationIssue(
                    "warn",
                    f"stages[{s.name}].primary",
                    f"{s.primary.name} 人均 ¥{price:.0f} 超出预算 ¥{profile.budget_per_person}",
                ))

    # ── 4. 饮食约束 ──
    for d in profile.dietary:
        covered = False
        for s in plan.stages:
            if s.name != "吃":
                continue
            text = f"{s.primary.name} {s.primary.category} {s.primary.reason}".lower()
            if d.lower() in text or _dietary_keyword(d).lower() in text:
                covered = True
                break
        if not covered:
            issues.append(ValidationIssue(
                "warn",
                "stages[吃].primary",
                f"饮食偏好「{d}」未被餐厅覆盖",
            ))

    # ── 5. 时长约束 ──
    max_minutes = profile.duration_hours * 60 * DURATION_TOLERANCE
    stage_duration = _estimate_total_minutes(plan)
    if stage_duration > max_minutes:
        issues.append(ValidationIssue(
            "warn",
            "stages",
            f"方案总时长 ~{stage_duration:.0f}min 超出时间窗 {profile.duration_hours}h",
        ))

    # ── 6. 场景特定约束 ──
    if profile.scene == "family" and profile.kids_ages:
        plays = [s for s in plan.stages if s.name == "玩"]
        if plays:
            text = f"{plays[0].primary.name} {plays[0].primary.category}".lower()
            kids_keys = ("亲子", "儿童", "公园", "童", "宝宝", "海洋馆")
            if not any(k in text for k in kids_keys):
                issues.append(ValidationIssue(
                    "block",
                    "stages[玩].primary",
                    "家庭场景下缺少亲子友好活动",
                ))

    passed = not any(i.severity == "block" for i in issues)
    return ValidationResult(passed=passed, issues=issues)


def _dietary_keyword(d: str) -> str:
    """饮食偏好 → 餐厅关键词映射。"""
    return {
        "低卡": "轻食",
        "不辣": "清淡",
        "素食": "素食",
    }.get(d, d)


def _estimate_total_minutes(plan: Plan) -> float:
    """估算方案总时长（含路途）。"""
    transit_min = DURATION_TRANSIT * (len(plan.stages) - 1)
    total = 0.0
    for s in plan.stages:
        if s.name == "玩":
            total += DURATION_PLAY
        elif s.name == "吃":
            total += DURATION_EAT
        elif s.name == "加餐":
            total += DURATION_ADDON
    return total + transit_min
