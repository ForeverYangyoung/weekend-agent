"""Researcher 节点：按画像检索每阶段 POI 候选，写入 `research_result`。"""

//入口，只依赖 group_profile（从profiler节点传入）
//输出research_result（ResearchResult），trace（list[str]）
//ResearchResult包含所有阶段的研究结果 

//trace:[Researcher] 阶段 3，候选 7 项｜默认选中：玩=奥林匹克森林公园，吃=Wagas 沙拉轻食（奥森店），加餐=原麦山丘 小蛋糕（送至餐厅）


from __future__ import annotations

from weekend_agent.agents import run_research
from weekend_agent.roles import trace_line
from weekend_agent.state import AgentState


def researcher_node(state: AgentState) -> dict:
    profile = state.get("group_profile")
    research = run_research(profile)

    total_candidates = sum(len(s.candidates) for s in research.stages)
    selected = "，".join(
        f"{s.stage_name}={s.selected.name}"
        for s in research.stages
        if s.selected is not None
    )
    msg = f"阶段 {len(research.stages)}，候选 {total_candidates} 项"
    if selected:
        msg += f"｜默认选中：{selected}"

    return {
        "research_result": research,
        "trace": [trace_line("Researcher", msg)],
    }
