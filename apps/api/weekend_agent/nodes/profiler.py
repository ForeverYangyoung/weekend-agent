"""Profiler 节点：从用户一句话中抽取群体画像。

Stub 版本：用关键词匹配兜底，确保无 LLM 也能跑通。
下一步会接 LLM Function Calling。
"""
from __future__ import annotations

import re

from weekend_agent.schemas import GroupProfile
from weekend_agent.state import AgentState


def _heuristic_profile(text: str) -> GroupProfile:
    """关键词兜底解析。生产版会被 LLM 输出覆盖。"""
    profile = GroupProfile(raw_text=text)

    # 场景识别
    if any(k in text for k in ["老婆", "孩子", "娃", "宝宝", "孩"]):
        profile.scene = "family"
    elif any(k in text for k in ["朋友", "哥们", "闺蜜", "同事"]):
        profile.scene = "friends"
    elif any(k in text for k in ["对象", "女朋友", "男朋友"]):
        profile.scene = "couple"
    else:
        profile.scene = "solo"

    # 人数（"4 个人" / "我们 3 个"）
    m = re.search(r"(\d+)\s*(?:个人|人)", text)
    if m:
        profile.people_count = int(m.group(1))
    elif profile.scene == "family":
        profile.people_count = 3  # 默认一家三口
    elif profile.scene == "friends":
        profile.people_count = 4

    # 孩子年龄（"5 岁"）
    age_match = re.search(r"(\d+)\s*岁", text)
    if age_match and profile.scene == "family":
        profile.kids_ages = [int(age_match.group(1))]

    # 时长（"几个小时" / "4 小时" / "下午"）
    if "几个小时" in text or "下午" in text:
        profile.duration_hours = 5.0
    h = re.search(r"(\d+)\s*小时", text)
    if h:
        profile.duration_hours = float(h.group(1))

    # 距离
    if any(k in text for k in ["别太远", "不要远", "近点", "别离家太远"]):
        profile.distance_limit_km = 8.0

    # 饮食
    if "减肥" in text:
        profile.dietary.append("低卡")
    if "不辣" in text or "微辣" in text:
        profile.dietary.append("不辣")

    # 兴趣
    if profile.scene == "family" and profile.kids_ages:
        profile.interests.append("亲子")
    if "展览" in text or "美术馆" in text:
        profile.interests.append("展览")
    if "citywalk" in text.lower() or "逛街" in text:
        profile.interests.append("citywalk")

    return profile


def profiler_node(state: AgentState) -> dict:
    """节点入口：返回的 dict 会被合并进 AgentState。"""
    text = state.get("user_input", "")
    profile = _heuristic_profile(text)

    return {
        "group_profile": profile,
        "plan_iteration": 0,
        "trace": [
            f"[Profiler] scene={profile.scene} people={profile.people_count} "
            f"kids={profile.kids_ages} dietary={profile.dietary} "
            f"interests={profile.interests}"
        ],
    }
