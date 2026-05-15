"""Planner 节点：基于群体画像生成完整方案。

Stub 版本：根据 scene 输出一份硬编码但合理的方案，确保 demo 看起来真实。
"""
from __future__ import annotations

from weekend_agent.schemas import Plan, PlanStage, POICandidate
from weekend_agent.state import AgentState


def _build_family_plan() -> Plan:
    return Plan(
        summary="亲子下午：奥森公园遛娃 → 轻食午餐 → 北欧蛋糕加餐",
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
                backups=[
                    POICandidate(
                        poi_id="poi_park_002",
                        name="朝阳公园童趣园",
                        category="亲子活动",
                        score=0.85,
                        reason="备选：距离稍远但游乐设施更丰富",
                    )
                ],
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
                    reason="低卡符合减肥需求；有儿童椅；UGC 显示周末非高峰",
                ),
                backups=[
                    POICandidate(
                        poi_id="poi_rest_022",
                        name="绿茶餐厅",
                        category="餐厅",
                        score=0.78,
                        reason="备选：清淡选择多，儿童套餐",
                    )
                ],
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
    )


def _build_friends_plan() -> Plan:
    return Plan(
        summary="朋友下午：剧本杀 → 烤肉聚餐 → 鲜花点缀",
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
                    reason="4 人聚餐口碑高；可预订 17 点位置",
                ),
                backups=[
                    POICandidate(
                        poi_id="poi_rest_202",
                        name="炙烤大叔",
                        category="餐厅",
                        score=0.82,
                        reason="备选：人均稍低，无需排队",
                    )
                ],
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
    )


def planner_node(state: AgentState) -> dict:
    profile = state.get("group_profile")
    iteration = state.get("plan_iteration", 0)

    # 触发了重规划：标记一下；这里 stub 仍然返回原 plan，下一步接 LLM 后会真重排
    if iteration > 0:
        trace_prefix = f"[Planner#{iteration}] 重规划"
    else:
        trace_prefix = "[Planner] 首次规划"

    if profile and profile.scene == "friends":
        plan = _build_friends_plan()
    else:
        plan = _build_family_plan()

    return {
        "plan": plan,
        "plan_iteration": iteration + 1,
        "trace": [
            f"{trace_prefix}：{plan.summary}（{len(plan.stages)} 阶段，"
            f"预计 ¥{plan.total_cost_estimate}）"
        ],
    }
