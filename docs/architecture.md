# 架构说明

**真源文档：**

- [`02.架构和agent.md`](../02.架构和agent.md) — Profiler / Planner+Scorer / Executor、State、打分公式

**代码实现：**

- `backend/graph.py` — LangGraph 编排
- `backend/server.py` — FastAPI、SSE、前端静态资源
- `backend/nodes/` — 各逻辑节点

Super Dev 增量：`output/weekend-agent-architecture.md`（侧重前端联调、路由、部署）

State 字段清单：[`graph-states.md`](graph-states.md)

## 逻辑 Agent vs LangGraph 节点

| 对外（4 个 Agent） | 代码里对应什么 |
|-------------------|----------------|
| Profiler | `nodes/profiler.py` + `graph` 节点 `profiler` |
| Planner（含 Scorer/校验） | `planner.py` + `critic.py` |
| Executor（含预检/提交/回滚/交付） | `dry_run.py` + `executor.py` + `compensator.py` + `notifier.py` |
| ToolHub | `tools/`（无独立 graph 节点） |

映射表与 trace 前缀：[`backend/roles.py`](../backend/roles.py)
